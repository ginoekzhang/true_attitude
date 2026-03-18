from machine import Pin, PWM
import sys
import uselect
import time

# ===== User settings =====
PWM_PIN = 15           # Pico GPIO used for ESC signal
PWM_FREQ = 50          # 50 Hz is the common hobby ESC/servo rate
MIN_US = 1000          # adjust if your ESC manual says otherwise
MAX_US = 2000
ARM_US = 1000          # most ESCs arm at minimum throttle
START_US = 1100        # gentle initial spin test
# =========================

pwm = PWM(Pin(PWM_PIN))
pwm.freq(PWM_FREQ)

def set_pulse_us(us: int):
    if us < MIN_US:
        us = MIN_US
    if us > MAX_US:
        us = MAX_US
    pwm.duty_ns(us * 1000)

def stop_motor():
    set_pulse_us(MIN_US)

# Start safe
stop_motor()

poll = uselect.poll()
poll.register(sys.stdin, uselect.POLLIN)

print("PICO READY")
print("Commands: ARM, STOP, THROTTLE <us>, TEST")

armed = False

while True:
    events = poll.poll(50)  # 50 ms poll
    if not events:
        continue

    line = sys.stdin.readline()
    if not line:
        continue

    cmd = line.strip().upper()

    if cmd == "ARM":
        print("ARMING...")
        # Hold minimum throttle so ESC can arm
        stop_motor()
        time.sleep(2.5)
        armed = True
        print("ARMED")

    elif cmd == "STOP":
        stop_motor()
        print("STOPPED")

    elif cmd.startswith("THROTTLE"):
        parts = cmd.split()
        if len(parts) != 2:
            print("ERR BAD THROTTLE FORMAT")
            continue
        try:
            us = int(parts[1])
        except ValueError:
            print("ERR BAD NUMBER")
            continue

        if not armed:
            print("ERR NOT ARMED")
            continue

        set_pulse_us(us)
        print("THROTTLE SET", us)

    elif cmd == "TEST":
        if not armed:
            print("ERR NOT ARMED")
            continue
        print("TEST START")
        set_pulse_us(START_US)
        time.sleep(2.0)
        stop_motor()
        print("TEST DONE")

    else:
        print("ERR UNKNOWN CMD")
