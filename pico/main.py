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

def clean_cmd(raw):
    # Keep only printable ASCII plus spaces
    filtered = []
    for ch in raw:
        o = ord(ch)
        if ch == " " or (33 <= o <= 126):
            filtered.append(ch)
    return "".join(filtered).strip()

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

    raw = sys.stdin.readline()
    if not raw:
        continue

    cmd = clean_cmd(raw)

    # Ignore startup junk / blank lines
    if not cmd:
        continue

    parts = cmd.split()
    if len(parts) == 0:
        continue

    op = parts[0].upper()
    print("DEBUG CMD:", repr(cmd), "OP:", repr(op))

    if op == "ARM":
        print("ARMING...")
        set_pulse_us(ARM_US)
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
        # Ignore unknown junk silently if you want:
        # continue
        print("ERR UNKNOWN CMD")
