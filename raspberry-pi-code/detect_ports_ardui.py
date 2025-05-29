import serial.tools.list_ports
ports = list(serial.tools.list_ports.comports(include_links=True))
print("Ports trouvés, avec leur description :")
for p in ports:
 print(f" * {p.device:40s} : {p.description} ")