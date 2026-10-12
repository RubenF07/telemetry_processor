# Temp file for finding serial port

import serial.tools.list_ports

def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports found.")
    else:
        print("Available serial ports:")
        for port in ports:
            print(f"  - {port.device} ({port.description})")

if __name__ == "__main__":
    list_serial_ports()


print("hello")

# My port(Ruben): COM3 
# 
# Cooper's mac USBC port on the right /dev/cu.usbmodem57954501 - may be board dependant
# /dev/cu.usbmodem168101701