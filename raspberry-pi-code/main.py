import signal, logging, threading

from datetime import datetime, timezone
from pathlib import Path

from config import LOG_FILE
from serialRead import SerialReader
#from camera_detect import MotionDetector
from sender import Uploader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)

stop_event = threading.Event()

def graceful_shutdown(signum, frame):
    stop_event.set()

signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)

threads = [
    SerialReader(stop_event),
    #MotionDetector(stop_event),
    #Uploader(stop_event)
]

for t in threads:
    t.start()

print("Program started succesfully")

for t in threads:
    t.join()
print("Shutdown complete.")