import serial
import time

PORT = "/dev/ttyACM0"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=0.3)
ser.dtr = False
ser.rts = False

print("Connected to", PORT)
time.sleep(3.0)

def drain():
    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            break
        print("RAW:", line)

def send(cmd, wait=1.0):
    full = "CMD " + cmd
    print("SENT:", full)
    ser.write((full + "\n").encode("utf-8"))
    ser.flush()
    time.sleep(wait)
    drain()

try:
    print("Draining startup text...")
    drain()

    # Arm ESC
    send("ARM", wait=4.5)

    # Gentle ramp test
    send("THROTTLE 1100", wait=2.0)
    send("THROTTLE 1150", wait=2.0)
    send("THROTTLE 1200", wait=2.0)

    # Stop
    send("STOP", wait=1.0)

finally:
    ser.close()
    print("Serial closed")
