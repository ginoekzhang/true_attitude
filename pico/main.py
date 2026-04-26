from machine import Pin, PWM
import sys
import uselect
import time
import machine

PWM_PINS = [0, 1, 2, 3, 4, 5]
PWM_FREQ = 50
MIN_US = 1000
MAX_US = 2000
ARM_US = 1000

pwms = [PWM(Pin(pin)) for pin in PWM_PINS]
for pwm in pwms:
    pwm.freq(PWM_FREQ)


def clamp_us(us):
    us = int(us)
    if us < MIN_US:
        return MIN_US
    if us > MAX_US:
        return MAX_US
    return us


def set_pulse_us(channel, us):
    if channel < 0 or channel >= len(pwms):
        return
    pwms[channel].duty_ns(clamp_us(us) * 1000)


def set_all_pulse_us(us):
    for i in range(len(pwms)):
        set_pulse_us(i, us)


def stop_all_motors():
    set_all_pulse_us(MIN_US)


def send_resp(msg):
    print("RESP " + msg)


def clean_line(raw):
    filtered = []
    for ch in raw:
        o = ord(ch)
        if ch == " " or (33 <= o <= 126):
            filtered.append(ch)
    return "".join(filtered).strip()

stop_all_motors()
armed = False

poll = uselect.poll()
poll.register(sys.stdin, uselect.POLLIN)

print("PICO READY")
print("INFO Send: CMD ARM / CMD THROTTLE <us> / CMD MOTORS <m1> ... <m6> / CMD STOP / CMD REBOOT")

while True:
    events = poll.poll(50)
    if not events:
        continue

    raw = sys.stdin.readline()
    if not raw:
        continue

    line = clean_line(raw)
    if not line:
        continue

    if not line.startswith("CMD "):
        continue

    cmd = line[4:].strip()
    if not cmd:
        continue

    parts = cmd.split()
    op = parts[0].upper()

    if op == "ARM":
        send_resp("ARMING...")
        set_all_pulse_us(ARM_US)
        time.sleep(4.0)
        armed = True
        send_resp("ARMED")

    elif op == "STOP":
        stop_all_motors()
        send_resp("STOPPED")

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
        set_all_pulse_us(us)
        send_resp("THROTTLE SET {}".format(us))

    elif op == "MOTORS":
        if len(parts) != 7:
            send_resp("ERR MOTORS REQUIRES 6 VALUES")
            continue
        if not armed:
            send_resp("ERR NOT ARMED")
            continue
        motor_values = []
        for idx, part in enumerate(parts[1:]):
            try:
                motor_values.append(int(part))
            except ValueError:
                motor_values = None
                break
        if motor_values is None:
            send_resp("ERR BAD NUMBER")
            continue

        for channel, us in enumerate(motor_values):
            set_pulse_us(channel, us)
        send_resp("MOTORS SET {}".format(" ".join(str(clamp_us(v)) for v in motor_values)))

    elif op == "TEST":
        if not armed:
            send_resp("ERR NOT ARMED")
            continue
        send_resp("TEST START")
        set_all_pulse_us(1200)
        time.sleep(2.0)
        stop_all_motors()
        send_resp("TEST DONE")

    elif op == "REBOOT":
        send_resp("REBOOTING")
        time.sleep(0.2)
        machine.reset()

    else:
        send_resp("ERR UNKNOWN CMD")
        
