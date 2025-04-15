import serial
import time
import csv
from datetime import datetime as dt

#declare serial

arduino_address = '/dev/ttyUSB0'
bauds = 115200
arduino_serial = serial.Serial(arduino_address, bauds)

time.sleep(2)

while arduino_serial.in_waiting > 0:
    arduino_serial.read(arduino_serial.in_waiting)

arduino_serial.flushInput()

#maybe write for error reportage
arduino_serial.write(bytes("msg to shit",'UTF-8'))

while True:
    try:
        ser_bytes = arduino_serial.readline()
        decoded_bytes = float(ser_bytes[0:len(ser_bytes)-2].decode("utf-8"))
        print(decoded_bytes)
        data_capteurs = decoded_bytes.split(";")
        humidity = data_capteurs[0]
        temperature = data_capteurs[1]
        lumens = data_capteurs[2]
        #would have to have control over this
        with open("test_data.csv","a") as f:
            writer = csv.writer(f,delimiter=",")
            current_time = dt.now().isoformat()
            writer.writerow([current_time, temperature, humidity, lumens, 'other shit'])
    except:
        print("Keyboard Interrupt")
        break

arduino_serial.close()