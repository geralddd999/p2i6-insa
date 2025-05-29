import threading
from picamera2 import Picamera2
import cv2, logging, time

from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

from config import IMG_DIR, FRAME_WIDTH, FRAME_HEIGHT, FPS, MOTION_MIN_AREA

class MotionDetector(threading.Thread):
    def __init__(self, stop_event: threading.Event, camera_index : int = 0):
        super().__init__(daemon=True)
        self.stop_event = stop_event #if need to shutdown
        self.camera = Picamera2()
        config = self.camera.create_preview_configuration(
            main={"format": "RGB888", "size": (FRAME_WIDTH, FRAME_HEIGHT)},
            controls={"FrameRate": FPS},
        )
        self.camera.configure(config)
        self.camera.start()
        self.back_sub = cv2.createBackgroundSubtractorMOG2(history = 600, varThreshold=16, detectShadows=False)
        
        logger.info("Camera initialised")

    def pictureCapture(self, frame):
        timestamp = datetime.now(timezone.utc) #save it in utc stamp
        name = f"{timestamp.isoformat()}.jpg".replace(':','-') # give the YYYY-MM-DD-HH-SS format
        path = IMG_DIR / name 
        cv2.imwrite(str(path), frame)
        logger.debug(f"Image pris le {timestamp}: %s", path)

    def run(self):
        while not self.stop_event.is_set():
            #prevent various takes
            last_save = 0
            try:
                frame = self.camera.capture_array()
                fg = self.back_sub.apply(frame)
                _, thr = cv2.threshold(fg, 200,255,cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(thr,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
                
                if any(cv2.contourArea(c) >= MOTION_MIN_AREA for c in contours):
                    now = time.time()
                    if now - last_save >1:
                        if not self.pictureCapture(frame):
                            logger.error("imwrite failed")
                        last_save = now

            except Exception:
                logger.exception("Camera error")
        self.camera.close()

