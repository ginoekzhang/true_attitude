import serial
import time

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
time.sleep(2)  # allow Pico serial to settle after open

def send(cmd):
    ser.write((cmd + "\n").encode("utf-8"))
    ser.flush()
    print("SENT:", cmd)
    time.sleep(0.2)
    while ser.in_waiting:
        line = ser.readline().decode(errors="ignore").strip()
        if line:
            print("RECV:", line)

send("ARM")
time.sleep(3)

send("THROTTLE 1100")
time.sleep(2)

send("STOP")
