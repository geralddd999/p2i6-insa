import threading
from picamera2 import Picamera2
import cv2, logging, time

from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

from config import IMG_DIR, FRAME_WIDTH, FRAME_HEIGHT, FPS, MOTION_MIN_AREA

class MotionDetector(threading.Thread):
    RECONNECT_DELAY = 600
    WARMUP = 50 #let model settle and train the given background
    COOLDOWN = 1 #in seconds
    VAR_THRESHOLD = 44 #increase if false positive
    def __init__(self, stop_event: threading.Event, camera_index : int = 0):
        super().__init__(daemon=True)
        self.stop_event = stop_event #if need to shutdown
        self.camera = None
        self.back_sub = cv2.createBackgroundSubtractorMOG2(history = 600, varThreshold=self.VAR_THRESHOLD, detectShadows=False)
        self.last_save = 0.0

    def openCamera(self):
        while not self.stop_event.is_set():
            try:
                self.camera = Picamera2()
                config = self.camera.create_preview_configuration(
                    main={"format": "RGB888", "size": (FRAME_WIDTH, FRAME_HEIGHT)},
                    controls={"FrameRate": FPS},
                )
                self.camera.configure(config)
                self.camera.start()

                for _ in range(self.WARMUP):
                    self.back_sub.apply(self.camera.capture_array())
                logger.info("Camera initialised")
                
                return
            except Exception as e:
                logger.info("Camera start failed: %s - retrying in %d s",
                            e, self.RECONNECT_DELAY)
                self.camera = None
                self.stop_event.wait(self.RECONNECT_DELAY)
    def grabfromCamera(self):
        try:
            return self.camera.capture_array()
        except Exception:
            return None

    def pictureCapture(self, frame):
        timestamp = datetime.now(timezone.utc) #save it in utc stamp
        name = f"{timestamp.isoformat()}.jpg".replace(':','-') # give the YYYY-MM-DD-HH-SS format
        path = IMG_DIR / name 
        if not cv2.imwrite(str(path), frame):
            logger.debug(f"Image pris le {timestamp}: %s", path)
            return False
        
        return True

    def run(self):
        while not self.stop_event.is_set():
            #prevent various takes
            try:
                if self.camera is None:
                    self.openCamera() # try to reopen 

                frame = self.grabfromCamera()
                if frame is None:
                    logger.error("Camera read failed - retrying in %d s",
                                 self.RECONNECT_DELAY)
                    if self.camera: #if it exists
                        self.camera.close()
                    self.camera = None
                    self.stop_event.wait(self.RECONNECT_DELAY)
                    continue

                fg = self.back_sub.apply(frame)
                _, thr = cv2.threshold(fg, 200,255,cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(thr,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
                
                if any(cv2.contourArea(c) >= MOTION_MIN_AREA for c in contours):
                    now = time.time()
                    if now - self.last_save >= self.COOLDOWN:
                        if self.pictureCapture(frame):
                            logger.debug("Image saved")
                        else:
                            logger.error("imwrite failed")
                        self.last_save = now

            except Exception:
                logger.exception("Camera error")
        
        if self.camera:
            self.camera.close()

