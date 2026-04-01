from machine import Pin, PWM
import sys
import uselect
import time

PWM_PIN = 5
PWM_FREQ = 50
MIN_US = 1000
MAX_US = 2000
ARM_US = 1000
TEST_US = 1100

pwm = PWM(Pin(PWM_PIN))
pwm.freq(PWM_FREQ)

def set_pulse_us(us):
    us = int(us)
    if us < MIN_US:
        us = MIN_US
    if us > MAX_US:
        us = MAX_US
    pwm.duty_ns(us * 1000)

def stop_motor():
    set_pulse_us(MIN_US)

stop_motor()

poll = uselect.poll()
poll.register(sys.stdin, uselect.POLLIN)

armed = False

print("PICO READY")
print("Commands: ARM, STOP, THROTTLE <us>, TEST")

while True:
    events = poll.poll(50)
    if not events:
        continue

    line = sys.stdin.readline()
    if not line:
        continue

    cmd = line.strip()

    if not cmd:
        continue

    parts = cmd.split()
    op = parts[0].upper()

    if op == "ARM":
        print("ARMING...")
        stop_motor()
        time.sleep(2.5)
        armed = True
        print("ARMED")

    elif op == "STOP":
        stop_motor()
        print("STOPPED")

    elif op == "TEST":
        if not armed:
            print("ERR NOT ARMED")
            continue
        print("TEST START")
        set_pulse_us(TEST_US)
        time.sleep(2.0)
        stop_motor()
        print("TEST DONE")

    elif op == "THROTTLE":
        if len(parts) != 2:
            print("ERR BAD THROTTLE FORMAT")
            continue
        if not armed:
            print("ERR NOT ARMED")
            continue
        try:
            us = int(parts[1])
        except ValueError:
            print("ERR BAD NUMBER")
            continue
        set_pulse_us(us)
        print("THROTTLE SET", us)

    else:
        print("ERR UNKNOWN CMD")
