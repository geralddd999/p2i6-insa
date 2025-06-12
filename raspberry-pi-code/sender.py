import threading, logging, time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests 

from config import AUTH_TOKEN, DATA_DIR, IMG_DIR, SERVER_URL, TCP_RETRY_DELAY, UPLOAD_INTERVAL, INITIAL_UPLOAD_WAIT_PERIOD, LOG_FILE

logger = logging.getLogger(__name__)

def timestamp_from_name(path : Path) -> datetime:
    #extract ISO timestamp from filename
    try:
        return datetime.fromisoformat(path.stem)
    except ValueError:
        return datetime.fromtimestamp(path.stat().st_mtime)
    

class Uploader(threading.Thread):
    LOG_MIN_SIZE = 0
    
    def __init__(self, stop_event: threading.Event):
        super().__init__(daemon = True)
        self.stop_event = stop_event
    
    @staticmethod
    def csv_finder() -> List[Path]: # annotations wise
        return(sorted(DATA_DIR.glob("*.csv")))
    
    @staticmethod
    def image_finder_b4range(cutoff : datetime) -> List[Path]:
        return([img for img in IMG_DIR.glob("*.jpg") if timestamp_from_name(img) <= cutoff])
    
    @staticmethod
    def image_finder() -> List[Path]:
        return(sorted(IMG_DIR.glob("*.jpg")))

    def sender(self, csv_path: Optional[Path], images : List[Path]) -> bool:
        files = []
        #files = [("csv", (csv_path.name, csv_path.open('rb'), "text/csv"))]
        if csv_path is not None:
            files.append(("csv", (csv_path.name, csv_path.open('rb'), "text/csv")))
        for img in images:
            files.append(("images", (img.name, img.open("rb"), "image/jpeg")))

        headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
        
        try: 
            for h in logging.getLogger().handlers:
                try:
                    h.flush()
                except Exception:
                    pass
            if LOG_FILE.exists() and LOG_FILE.stat().st_size >= self.LOG_MIN_SIZE:
                files.append(("log", (LOG_FILE.name, LOG_FILE.open("rb"), "text/plain")))
        except Exception as exc:
            logger.warning("Could not attach log file: %s",exc)

        if not files:
            return True
        
        try:
            resp = requests.post(
                SERVER_URL,
                files=files,
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                timeout=30,
            )
            logger.info("POST %s → %d", SERVER_URL, resp.status_code)
            if resp.ok:
                # truncate log so only fresh lines go next time
                try:
                    LOG_FILE.touch(exist_ok=True)
                    with LOG_FILE.open("w"):
                        pass

                except Exception as exc:
                    logger.warning("Log-truncate failed: %s", exc)
                return True
            
            logger.error("Server rejected upload: %d %s",
                         resp.status_code, resp.text[:200])
        except requests.RequestException as exc:
            logger.error("Network error: %s", exc)
            time.sleep(TCP_RETRY_DELAY)        # back-off
        return False
    
    def upload_cycle(self):
        csvs = self.csv_finder()
        
        if csvs:
            csv_path = csvs[0]
            cutoff = timestamp_from_name(csv_path)
            images = self.image_finder_b4range(cutoff)
            
            if self.sender(csv_path,images):
                csv_path.unlink(missing_ok=True)
                for img in images:
                    img.unlink(missing_ok=True)
                logger.info("Uploaded and purged %s (+%d images)",csv_path.name, len(images))
        #cutoff = timestamp_from_name(csv_path)
        #images = self.image_finder_b4range(cutoff)

        else:
            images = self.image_finder()
            if images and self.sender(None, images):
                #if self.sender(csv_path, images):
                #csv_path.unlink(missing_ok=True)
                for img in images:
                    img.unlink(missing_ok=True)
                logger.info("Uploaded & purged %s independant (+%d images)", len(images))
            elif self.sender(None, []):
                logger.info("Uploaded log only")
    
    
    def run(self):
        
        self.stop_event.wait(INITIAL_UPLOAD_WAIT_PERIOD)
        while not self.stop_event.is_set():
            try:
                
                self.upload_cycle()
            except Exception:
                logger.exception("unexpected error in upload cycle, retrying")
            self.stop_event.wait(UPLOAD_INTERVAL)
    
