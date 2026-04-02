import serial
import time

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=0.3)
ser.dtr = False
ser.rts = False

print("Connected. Type commands like: ARM, THROTTLE 1200, STOP")
time.sleep(3.0)

def drain():
    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            break
        print(line)

drain()

try:
    while True:
        cmd = input("> ").strip()
        if not cmd:
            continue
        ser.write(("CMD " + cmd + "\n").encode())
        ser.flush()
        time.sleep(0.3)
        drain()
finally:
    ser.close()
