import threading, logging, time
from datetime import datetime
from pathlib import Path
from typing import List

import requests 

from config import AUTH_TOKEN, DATA_DIR, IMG_DIR, SERVER_URL, TCP_RETRY_DELAY, UPLOAD_INTERVAL, INITIAL_UPLOAD_WAIT_PERIOD

logger = logging.getLogger(__name__)

def timestamp_from_name(path : Path) -> datetime:
    #extract ISO timestamp from filename
    try:
        return datetime.fromisoformat(path.stem)
    except ValueError:
        return datetime.fromtimestamp(path.stat().st_mtime)
    

class Uploader(threading.Thread):
    def __init__(self, stop_event: threading.Event):
        super().__init__(daemon = True)
        self.stop_event = stop_event
    
    @staticmethod
    def csv_finder() -> List[Path]: # annotations wise
        return(sorted(DATA_DIR.glob("*.csv")))
    
    @staticmethod
    def image_finder_b4range(cutoff : datetime) -> List[Path]:
        return([img for img in IMG_DIR.glob("*.jpg") if timestamp_from_name(img) <= cutoff])
    
    def sender(self, csv_path: Path, images : List[Path]) -> bool:
        files = [("csv", (csv_path.name, csv_path.open('rb'), "text/csv"))]
        for img in images:
            files.append(("images", (img.name, img.open("rb"), "image/jpeg")))
        headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
        
        try: 
            resp = requests.post(SERVER_URL, files=files, headers=headers, timeout=30)
            logger.info("POST %s → %d", SERVER_URL, resp.status_code)
            if resp.ok:
                return True
            logger.error("server rejected upload %d %s", resp.status_code, resp.text[:200])

        except requests.RequestException as exc:
            logger.error("Network error: %s", exc)
        # Either network failure or non‑2xx → wait a bit then retry later
        time.sleep(TCP_RETRY_DELAY)
        return False
    def upload_cycle(self):
        csvs = self.csv_finder()
        if not csvs:
            return # we dont have nothing to send
        
        csv_path = csvs[0]
        
        cutoff = timestamp_from_name(csv_path)
        images = self.image_finder_b4range(cutoff)

        if self.sender(csv_path, images):
            csv_path.unlink(missing_ok=True)
            for img in images:
                img.unlink(missing_ok=True)
            logger.info("Uploaded & purged %s (+%d images)", csv_path.name, len(images))
        
    
    
    def run(self):
        
        self.stop_event.wait(INITIAL_UPLOAD_WAIT_PERIOD)
        while not self.stop_event.is_set():
            try:
                
                self.upload_cycle()
            except Exception:
                logger.exception("unexpected error in upload cycle, retrying")
            self.stop_event.wait(UPLOAD_INTERVAL)
    