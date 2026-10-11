import serial
import socket
import cantools
import math


# Config
SERIAL_PORT = "COM3"
BAUD_RATE = 921600 # Microcontroller frequency

TELEGRAF_HOST = "127.0.0.1"
TELEGRAF_PORT = 7654

DBC_FILE = "EV_Test.dbc"


def escape_field_key(value):
    return str(value).replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


def format_field_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return f"{value}i"
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"InfluxDB does not accept non-finite field values: {value}")
        return repr(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    raise ValueError(f"Unsupported InfluxDB field value: {value!r}")


def to_line_protocol(frame_id, signals):
    tags = f"can_id=0x{frame_id:X}"
    fields = ",".join(
        f"{escape_field_key(name)}={format_field_value(value)}"
        for name, value in signals.items()
    )
    if not fields:
        raise ValueError("Decoded CAN frame contains no signals")
    return f"can_frame,{tags} {fields}\n"


# Load your DBC database file
db = cantools.database.load_file(DBC_FILE)

# Connect to socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((TELEGRAF_HOST, TELEGRAF_PORT))

# Open Serial Port
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

print("Forwarding CAN data to Telegraf...")

try:
    while True:
        if ser.in_waiting > 0:

            # Format: B:X|C:0xXXX|D:XX XX XX XX XX XX XX XX
            line = ser.readline().decode("utf-8").strip()
            if not line:
                continue

            try:
                # Expected serial format: hexadecimal CAN ID followed by space-separated payload bytes.
                bus_id_text, frame_id_text, payload_text = line.split("|")

                print("\n-----------------\n")
                print(f"LINE: {line}")
                print(f"BUS_ID: {bus_id_text}, FRAME ID: {frame_id_text}, PAYLOAD: {payload_text}\n")

                bus_id = int(bus_id_text.split(":")[1])
                frame_id = int(frame_id_text.split(":")[1], 16)
                payload = bytes.fromhex(payload_text.split(":")[1])

                print(f"BUS: {bus_id}, FRAME: {frame_id}, PAYLOAD: {payload}\n")

                signals = db.decode_message(frame_id, payload)

                print(signals)

                line_protocol = to_line_protocol(frame_id, signals)

                print(f"LINE PROTO: {line_protocol}")
                sock.sendall(line_protocol.encode("utf-8"))
                print(f"R_STRIP: {line_protocol.rstrip()}")

                
            except (ValueError, KeyError) as exc:
                print(f"Could not parse CAN frame {line!r}: {exc}")
except KeyboardInterrupt:
    print("Stopping CAN forwarding...")
finally:
    ser.close()
    sock.close()