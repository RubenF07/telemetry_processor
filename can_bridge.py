import serial
import socket
import cantools
import time

from telegraf_format import to_line_protocol

# Config
SERIAL_PORT = "COM3"
BAUD_RATE = 921600  # Microcontroller frequency

TELEGRAF_HOST = "127.0.0.1"
TELEGRAF_PORT = 7654

DBC_FILE = "EV_Test.dbc"

RECONNECT_DELAY = 1.0  # seconds between reconnect attempts


def open_serial():
    """Block until the serial port opens."""
    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            ser.reset_input_buffer()  # drop stale/partial data from before the (re)connect
            print(f"Serial port {SERIAL_PORT} open")
            return ser
        except serial.SerialException as exc:
            print(f"{time.time()}| Cannot open {SERIAL_PORT}: {exc}. Retrying...")
            time.sleep(RECONNECT_DELAY)


def open_socket():
    """Block until the Telegraf socket connects."""
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((TELEGRAF_HOST, TELEGRAF_PORT))
            print(f"Connected to Telegraf at {TELEGRAF_HOST}:{TELEGRAF_PORT}")
            return sock
        except OSError as exc:
            print(f"{time.time()}| Cannot connect to Telegraf: {exc}. Retrying...")
            time.sleep(RECONNECT_DELAY)


def process_line(line, db, sock):
    # Format: B:X|C:0xXXX|D:XX XX XX XX XX XX XX XX
    bus_id_text, frame_id_text, payload_text = line.split("|")

    bus_id = int(bus_id_text.split(":")[1])
    frame_id = int(frame_id_text.split(":")[1], 16)
    payload = bytes.fromhex(payload_text.split(":")[1])

    signals = db.decode_message(frame_id, payload)
    line_protocol = to_line_protocol(frame_id, signals)

    print(f"BUS {bus_id} | ID 0x{frame_id:X} | {line_protocol.rstrip()}")
    sock.sendall(line_protocol.encode("utf-8"))  # may raise OSError -> handled by caller


def main():
    db = cantools.database.load_file(DBC_FILE)
    sock = open_socket()
    ser = open_serial()

    print("Forwarding CAN data to Telegraf...")

    try:
        while True:
            try:
                # Blocks up to `timeout` seconds; no need to poll in_waiting
                raw = ser.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                try:
                    process_line(line, db, sock)
                except (ValueError, KeyError, IndexError, cantools.database.errors.Error) as exc:
                    # Bad line, unknown frame ID, wrong payload length, etc.
                    print(f"Could not parse CAN frame {line!r}: {exc}")

            except serial.SerialException as exc:
                print(f"Serial error: {exc}. Reconnecting...")
                try:
                    ser.close()
                except Exception:
                    pass
                time.sleep(RECONNECT_DELAY)
                ser = open_serial()

            except OSError as exc:
                # Telegraf socket dropped (BrokenPipe, ConnectionReset, etc.)
                print(f"Socket error: {exc}. Reconnecting...")
                try:
                    sock.close()
                except Exception:
                    pass
                sock = open_socket()

    except KeyboardInterrupt:
        print("Stopping CAN forwarding...")

    finally:
        try:
            ser.close()
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()