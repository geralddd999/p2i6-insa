import csv, logging, threading, serial

from datetime import datetime, timezone
from pathlib import Path

#Import configuration

from config import SERIAL_PORT, BAUD_RATE, DATA_DIR

logger = logging.getLogger(__name__)

class SerialReader(threading.Thread):
    def __init__(self, stop_event: threading.Event):
        super().__init__(daemon = True)
        self.stop_event = stop_event
        self.ser = serial.Serial(port =SERIAL_PORT, baudrate= BAUD_RATE, timeout=1)

        logger.info("Communication serial etablie en %s @%d", SERIAL_PORT, BAUD_RATE)

        logger.info("after")

    @staticmethod
    def create_path_csv(timestamp : datetime) -> Path:
        """
                Inputs: timestamp with the format of date time to return the 'name' of                the csv in a Path object format to use as a file name
        """
        return DATA_DIR / f"{timestamp.date().isoformat()}.csv"
        
    def run(self):
        while not self.stop_event.is_set():
            try:
                line = self.ser.readline().decode(errors="ignore")
                
                logger.debug('Ligne serial read: %s', line)

                if not line:
                    continue # if nothing aight
                
                timestamp = datetime.now(timezone.utc)
                csv_path = self.create_path_csv(timestamp)
                new_file = not csv_path.exists()
                
                with csv_path.open("a", newline="") as file:
                    writer = csv.writer(file)
                    if new_file:
                        starting_line = ["Temperature [C]","Humidity", "Light", "Voltage L.Sensor"]
                        writer.writerow(["timestamp"] + starting_line)
                    logger.debug('Ligne serial ecrit:', line)

            except Exception as exc:
                logger.exception("Echec lors de la lecture du serial arduino ")
        
        self.ser.close()