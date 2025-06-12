import csv, logging, threading, serial, time 

from datetime import datetime, timezone
from serial.serialutil import SerialException
from pathlib import Path
from zoneinfo import ZoneInfo
#Import configuration

from config import SERIAL_PORT, BAUD_RATE, DATA_DIR

logger = logging.getLogger(__name__)

class SerialReader(threading.Thread):
    PARIS = ZoneInfo("Europe/Paris") 
    RECONNECT_DELAY = 600
    def __init__(self, stop_event: threading.Event):
        super().__init__(daemon = True)
        self.stop_event = stop_event
        self.ser = None
        logger.info("Started SerialReader Module")
        

    def serialOpen(self):
        try:
                self.ser = serial.Serial(port =SERIAL_PORT, baudrate= BAUD_RATE, timeout=1)
                logger.info("Communication serial etablie en %s @%d", SERIAL_PORT, BAUD_RATE)

        except SerialException as e:
                logger.error("Serial communication errored out: %s - retrying in %d ", e, self.RECONNECT_DELAY)
                self.ser = None
                
    @staticmethod
    def create_path_csv(timestamp : datetime) -> Path:
        """
                Inputs: timestamp with the format of date time to return the 'name' of                the csv in a Path object format to use as a file name
        """
        return DATA_DIR / f"{timestamp.date().isoformat()}.csv"
        
    def run(self):
        while not self.stop_event.is_set():
            if self.ser is None:
                self.serialOpen()
                if self.ser is None:
                        self.stop_event.wait(self.RECONNECT_DELAY)
                        continue

            try:

                line = self.ser.readline().decode("ascii", errors="ignore").strip()
                
                if not line:
                    continue # if nothing aight
                
                timestamp = datetime.now(self.PARIS)
                csv_path = self.create_path_csv(timestamp)
                new_file = not csv_path.exists()
                
                with csv_path.open("a", newline="") as file:
                    writer = csv.writer(file, delimiter =";")
                    if new_file:
                        starting_line = ["Temperature [C] ","Humidity ", "Light ", "Voltage L.Sensor "]
                        writer.writerow(["timestamp"] + starting_line)

                    writer.writerow([f"{timestamp}"] + line.split(';'))
                    
                    logger.info('Ligne serial ecrit')

            except SerialException as exc:
                logger.exception("Echec lors de la lecture du serial arduino ")
                logger.error("Serial read error %s - reconnecting", exc )
                self.ser.close()
                self.ser = None
                self.stop_event.wait(self.RECONNECT_DELAY)
        
        if self.ser:
            self.ser.close()
