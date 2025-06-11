import csv, logging, threading, serial, time 

from datetime import datetime, timezone
from serial.serialutil import SerialException
from pathlib import Path
#Import configuration

from config import SERIAL_PORT, BAUD_RATE, DATA_DIR

logger = logging.getLogger(__name__)

class SerialReader(threading.Thread):
    RECONNECT_DELAY = 5
    def __init__(self, stop_event: threading.Event):
        super().__init__(daemon = True)
        self.stop_event = stop_event
        self.ser = None
        logger.info("Started SerialReader Module")
        

    def serialOpen(self):
        while not self.stop_event.is_set():
            try:
                self.ser = serial.Serial(port =SERIAL_PORT, baudrate= BAUD_RATE, timeout=1)
                logger.info("Communication serial etablie en %s @%d", SERIAL_PORT, BAUD_RATE)
            except SerialException as e:
                logger.error("Serial communication errored out: %s - retrying in %d ", e, self.RECONNECT_DELAY)
                self.ser = None
                self.stop_event.wait(self.RECONNECT_DELAY)

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

            try:
                line = self.ser.readline().decode(errors="ignore")
                
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
                    # just why?: logger.debug('Ligne serial ecrit:', line)

            except SerialException as exc:
                logger.exception("Echec lors de la lecture du serial arduino ")
                logger.error("Serial read error %s - reconnecting", exc )
                self.ser.close()
                self.ser = None
                self.stop_event.wait(self.RECONNECT_DELAY)
        if self.ser:
            self.ser.close()