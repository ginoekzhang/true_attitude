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

def send_resp(msg):
    print("RESP " + msg)

def clean_cmd(raw):
    filtered = []
    for ch in raw:
        o = ord(ch)
        if ch == " " or (33 <= o <= 126):
            filtered.append(ch)
    return "".join(filtered).strip()

stop_motor()
armed = False

poll = uselect.poll()
poll.register(sys.stdin, uselect.POLLIN)

print("PICO READY")
print("INFO Send commands as: CMD ARM / CMD THROTTLE 1100 / CMD STOP")

while True:
    events = poll.poll(50)
    if not events:
        continue

    raw = sys.stdin.readline()
    if not raw:
        continue

    line = clean_cmd(raw)
    if not line:
        continue

    # Only accept explicit command lines from Pi
    if not line.startswith("CMD "):
        continue

    cmd = line[4:].strip()
    if not cmd:
        continue

    parts = cmd.split()
    op = parts[0].upper()

    if op == "ARM":
        send_resp("ARMING...")
        set_pulse_us(ARM_US)
        time.sleep(2.5)
        armed = True
        send_resp("ARMED")

    elif op == "STOP":
        stop_motor()
        send_resp("STOPPED")

    elif op == "TEST":
        if not armed:
            send_resp("ERR NOT ARMED")
            continue
        send_resp("TEST START")
        set_pulse_us(TEST_US)
        time.sleep(2.0)
        stop_motor()
        send_resp("TEST DONE")

    elif op == "THROTTLE":
        if len(parts) != 2:
            send_resp("ERR BAD THROTTLE FORMAT")
            continue
        if not armed:
            send_resp("ERR NOT ARMED")
            continue
        try:
            us = int(parts[1])
        except ValueError:
            send_resp("ERR BAD NUMBER")
            continue
        set_pulse_us(us)
        send_resp("THROTTLE SET {}".format(us))

    else:
        send_resp("ERR UNKNOWN CMD")
