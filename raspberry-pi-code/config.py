from pathlib import Path

W_DIR = Path.cwd()

#Server configs
AUTH_TOKEN = "very-secret-and-difficult-token"
SERVER_URL = 'http://insectes.citi.insa-lyon.fr/allinon/api/upload'
TCP_RETRY_DELAY = 15
UPLOAD_INTERVAL = 300
INITIAL_UPLOAD_WAIT_PERIOD = 300  # x min wait on boot


#Arduino configs
SERIAL_PORT = '/dev/ttyACM0' #to find?
BAUD_RATE = 9600

#Storage Paths
DATA_DIR = Path(f'{W_DIR}/data')
IMG_DIR = DATA_DIR/"images"
LOG_FILE = Path(f'{W_DIR}/logs/app.log') 

#Camera settings
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 15
MOTION_MIN_AREA = 50 # in pxiels


#Create directories if not exist

for p in (DATA_DIR, IMG_DIR, LOG_FILE.parent):
    p.mkdir(parents=True, exist_ok=True)
