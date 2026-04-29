from machine import Pin, PWM
import sys
import uselect
import time
import machine

PWM_PINS = [5, 6, 9, 13, 2, 7, 3, 4, 11, 12, 8, 10] # pitchup, pitchup, pitchdown, pitchdown, yawleft, yawleft, yawright, yawright, rollleft, rollleft, rollright, rollright
#white 2, 3, 4, 5, 6, 7  black 11, 12, 8, 10, 9, 13
PWM_FREQ = 50

# yaw left = up, yaw right = roll right 

OFF_US = 1000
MIN_US = 1155
MAX_US = 1600
ARM_US = 1000
IDLE_US = 1160

pwms = [PWM(Pin(pin)) for pin in PWM_PINS]
for pwm in pwms:
    pwm.freq(PWM_FREQ)


def clamp_motor_us(us):
    us = int(us)

    # allow 0 as OFF command
    if us <= OFF_US:
        return OFF_US

    if us < MIN_US:
        return MIN_US
    if us > MAX_US:
        return MAX_US
    return us


def set_pulse_us(channel, us):
    if 0 <= channel < len(pwms):
        pwms[channel].duty_ns(clamp_motor_us(us) * 1000)


def set_all_pulse_us(us):
    for i in range(len(pwms)):
        set_pulse_us(i, us)


def stop_all_motors():
    set_all_pulse_us(OFF_US)


def send_resp(msg):
    print("RESP " + msg)


def clean_line(raw):
    filtered = []
    for ch in raw:
        o = ord(ch)
        if ch == " " or (33 <= o <= 126):
            filtered.append(ch)
    return "".join(filtered).strip()


def read_all_available_lines():
    lines = []

    while poll.poll(0):
        raw = sys.stdin.readline()
        if not raw:
            break

        line = clean_line(raw)
        if line:
            lines.append(line)

    return lines


def handle_command(line):
    global armed

    if not line.startswith("CMD "):
        return

    cmd = line[4:].strip()
    if not cmd:
        return

    parts = cmd.split()
    op = parts[0].upper()

    if op == "ARM":
        send_resp("ARMING...")
        set_all_pulse_us(ARM_US)
        time.sleep(4.0)
        set_all_pulse_us(IDLE_US)
        armed = True
        send_resp("ARMED_IDLE")
        return

    if op == "STOP":
        stop_all_motors()
        armed = False
        send_resp("STOPPED")
        return

    if op == "MOTORS":
        if not armed:
            send_resp("ERR NOT ARMED")
            return

        if len(parts) != 13:
            send_resp("ERR MOTORS REQUIRES 12 VALUES")
            return

        try:
            motor_values = [int(v) for v in parts[1:]]
        except ValueError:
            send_resp("ERR BAD NUMBER")
            return

        for channel, us in enumerate(motor_values):
            set_pulse_us(channel, us)

        # Do NOT print every motor command.
        # Printing causes serial backlog.
        return

    if op == "THROTTLE":
        if not armed:
            send_resp("ERR NOT ARMED")
            return

        if len(parts) != 2:
            send_resp("ERR BAD THROTTLE FORMAT")
            return

        try:
            us = int(parts[1])
        except ValueError:
            send_resp("ERR BAD NUMBER")
            return

        set_all_pulse_us(us)
        send_resp("THROTTLE SET {}".format(us))
        return

    if op == "TEST":
        if not armed:
            send_resp("ERR NOT ARMED")
            return

        send_resp("TEST START")
        set_all_pulse_us(1200)
        time.sleep(2.0)
        stop_all_motors()
        send_resp("TEST DONE")
        return

    if op == "REBOOT":
        send_resp("REBOOTING")
        time.sleep(0.2)
        machine.reset()

    send_resp("ERR UNKNOWN CMD")


stop_all_motors()
armed = False

poll = uselect.poll()
poll.register(sys.stdin, uselect.POLLIN)

print("PICO READY")
print("INFO Send: CMD ARM / CMD MOTORS <m1> ... <m6> / CMD STOP / CMD REBOOT")

while True:
    events = poll.poll(20)
    if not events:
        continue

    lines = read_all_available_lines()
    if not lines:
        continue

    # STOP has priority over everything queued before it
    stop_found = False
    for line in lines:
        if line.startswith("CMD ") and line[4:].strip().upper().startswith("STOP"):
            stop_found = True
            break

    if stop_found:
        stop_all_motors()
        armed = False
        send_resp("STOPPED")
        continue

    # Latest-command-only behavior:
    # Ignore old queued motor commands and execute only newest line.
    latest_line = lines[-1]
    handle_command(latest_line)