#!/usr/bin/env python3
"""
Raspberry Pi side - serial reader, spooler, uploader, heartbeat.
Run as a systemd service (see mycollector.service).

"""

import os, gzip, json, time, shutil, queue, pathlib, logging, zipfile
from datetime import datetime, timedelta
from threading import Thread
from typing import Optional

import serial              # pyserial
import requests
import tomllib             # Python ≥3.11 (for TOML)

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

CONFIG = tomllib.load(open("config.toml", "rb"))

# ------------------------------------------------------------
# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("client.log"),
        logging.StreamHandler()
    ]
)

# ------------------------------------------------------------
# Helpers
def iso_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")

def make_session_dir(base: str) -> pathlib.Path:
    now = datetime.utcnow()
    p = pathlib.Path(base) / now.strftime("%Y-%m-%d") / now.strftime("%H-%M-%S")
    p.mkdir(parents=True, exist_ok=True)
    return p

def has_low_space(path: str, threshold_gb: float) -> bool:
    st = os.statvfs(path)
    free_gb = st.f_bavail * st.f_frsize / 1_000_000_000
    return free_gb < threshold_gb

def zip_oldest_unsent(base: str) -> None:
    oldest = min(
        (p for p in pathlib.Path(base).rglob("*") if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        default=None
    )
    if oldest:
        zname = oldest.with_suffix(".zip")
        logging.warning("Free space low - zipping %s → %s", oldest, zname)
        shutil.make_archive(str(zname).replace(".zip", ""), "zip", oldest)
        shutil.rmtree(oldest)

# ------------------------------------------------------------
# Serial reader
class SerialReader(Thread):
    def __init__(self, q: queue.Queue):
        super().__init__(daemon=True)
        self.ser = serial.Serial(
            CONFIG["port"], CONFIG["baud_rate"], timeout=1
        )
        self.q = q
        self.current_dir = make_session_dir(CONFIG["sample_folder"])
        self.csv = open(self.current_dir / "raw.csv", "a", buffering=1)

    def roll_session(self):
        """Create a new folder every hour so uploads stay small."""
        if (datetime.utcnow() - datetime.strptime(self.current_dir.name, "%H-%M-%S")) > timedelta(hours=1):
            self.csv.close()
            self.current_dir = make_session_dir(CONFIG["sample_folder"])
            self.csv = open(self.current_dir / "raw.csv", "a", buffering=1)

    def run(self):
        while True:
            try:
                line = self.ser.readline().decode("utf-8").strip()
                if not line:
                    continue
                ts = iso_now()
                self.csv.write(f"{ts},{line}\n")
                self.q.put((ts, line))
                self.roll_session()
            except Exception as e:
                self.log_error(e)

    def log_error(self, exc: Exception):
        err_path = pathlib.Path(CONFIG["error_folder"])
        err_path.mkdir(parents=True, exist_ok=True)
        fname = err_path / f"{iso_now()}.log.gz"
        with gzip.open(fname, "wt") as f:
            logging.exception("Serial read error → %s", fname, exc_info=exc, file=f)

# ------------------------------------------------------------
# Uploader
class Uploader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"x-device-token": CONFIG["device_token"]})
        self.base_url = CONFIG["server_url"].rstrip("/")

    def upload_folder(self, folder: pathlib.Path) -> bool:
        csv_path = folder / "raw.csv"
        if not csv_path.exists():
            return False

        files = [("csv", csv_path.open("rb"))]
        for img in folder.glob("*.jpg"):
            files.append(("images", img.open("rb")))

        try:
            r = self.session.post(
                self.base_url + CONFIG["ingest_path"],
                files=files,
                timeout=30
            )
            r.raise_for_status()
            if r.json().get("status") == "ok":
                shutil.rmtree(folder)
                logging.info("Uploaded & deleted %s", folder)
                return True
            logging.error("Server NACK for %s : %s", folder, r.text)
        except Exception as e:
            logging.warning("Upload failed (%s): %s", folder, e)
        return False

    def retry_spool(self):
        base = pathlib.Path(CONFIG["sample_folder"])
        for day in sorted(base.glob("*")):
            for sess in sorted(day.glob("*")):
                self.upload_folder(sess)

    def push_errors(self):
        err_dir = pathlib.Path(CONFIG["error_folder"])
        for gz in err_dir.glob("*.gz"):
            try:
                with open(gz, "rb") as fh:
                    r = self.session.post(
                        self.base_url + CONFIG["error_path"],
                        files={"log": fh},
                        timeout=15
                    )
                r.raise_for_status()
                gz.unlink()
            except Exception as e:
                logging.debug("Error push failed, will retry: %s", e)

    def heartbeat(self):
        payload = {
            "device_id" : os.uname().nodename,
            "utc_time"  : iso_now(),
            "free_gb"   : round(shutil.disk_usage("/").free / 1_000_000_000, 2)
        }
        try:
            r = self.session.post(
                self.base_url + CONFIG["heartbeat_path"],
                json=payload,
                timeout=10
            )
            r.raise_for_status()
            logging.debug("Heartbeat OK")
        except Exception as e:
            logging.debug("Heartbeat failed: %s", e)

# ------------------------------------------------------------
# Scheduler setup
def main():
    q = queue.Queue(maxsize=0)
    sr = SerialReader(q)
    sr.start()

    up = Uploader()

    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(
        up.retry_spool,
        IntervalTrigger(minutes=CONFIG["upload_period_minutes"]),
        max_instances=1,
        coalesce=True
    )
    sched.add_job(
        up.push_errors,
        IntervalTrigger(minutes=CONFIG["upload_period_minutes"]),
        max_instances=1
    )
    sched.add_job(
        up.heartbeat,
        IntervalTrigger(minutes=CONFIG["heartbeat_period_minutes"])
    )
    sched.add_job(
        lambda: zip_oldest_unsent(CONFIG["sample_folder"]) if has_low_space("/", CONFIG["min_free_gb"]) else None,
        IntervalTrigger(hours=6)
    )
    sched.start()

    logging.info("Client started. Press Ctrl+C to quit.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logging.info("Exiting…")

if __name__ == "__main__":
    main()
