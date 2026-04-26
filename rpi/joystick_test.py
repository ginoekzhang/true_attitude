import serial
import time

from evdev import InputDevice, ecodes, list_devices

SERIAL_PORT = "/dev/ttyACM0"
BAUD = 115200
SERIAL_TIMEOUT = 0.3

MOTOR_MIN = 1155
MOTOR_MAX = 1300
BASE_THROTTLE = 1227
DEADZONE = 0.08

# Motor assignments
PITCH_UP = 0
PITCH_DOWN = 1
YAW_LEFT = 2
YAW_RIGHT = 3
ROLL_LEFT = 4
ROLL_RIGHT = 5

# Joystick axes: -1 to 1, where -1 is down/left, 1 is up/right


def find_xbox_controller():
    devices = [InputDevice(path) for path in list_devices()]
    for dev in devices:
        name = dev.name.lower()
        if "xbox" in name or "controller" in name or "gamepad" in name:
            return dev
    return None


def normalize_stick(value):
    return (value - 32768) / 32768


def deadzone(value):
    return 0.0 if abs(value) < DEADZONE else value


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def mix_motors(pitch, roll, yaw):
    motors = [BASE_THROTTLE] * 6

    # Pitch: motor 0 (up), motor 1 (down)
    if pitch > 0:
        motors[PITCH_UP] = BASE_THROTTLE + pitch * (MOTOR_MAX - BASE_THROTTLE)
    elif pitch < 0:
        motors[PITCH_DOWN] = BASE_THROTTLE + (-pitch) * (MOTOR_MAX - BASE_THROTTLE)

    # Yaw: motor 2 (left), motor 3 (right)
    if yaw > 0:  # right
        motors[YAW_RIGHT] = BASE_THROTTLE + yaw * (MOTOR_MAX - BASE_THROTTLE)
    elif yaw < 0:  # left
        motors[YAW_LEFT] = BASE_THROTTLE + (-yaw) * (MOTOR_MAX - BASE_THROTTLE)

    # Roll: motor 4 (left), motor 5 (right)
    if roll > 0:  # right
        motors[ROLL_RIGHT] = BASE_THROTTLE + roll * (MOTOR_MAX - BASE_THROTTLE)
    elif roll < 0:  # left
        motors[ROLL_LEFT] = BASE_THROTTLE + (-roll) * (MOTOR_MAX - BASE_THROTTLE)

    return [int(round(m)) for m in motors]


def drain(serial_port):
    while serial_port.in_waiting:
        line = serial_port.readline().decode(errors="ignore").strip()
        if line:
            print("PICO:", line)


def send_cmd(serial_port, cmd, wait=0.1):
    full_cmd = "CMD " + cmd
    print("SEND:", full_cmd)
    serial_port.write((full_cmd + "\n").encode("utf-8"))
    serial_port.flush()
    time.sleep(wait)
    drain(serial_port)


def main():
    controller = find_xbox_controller()
    if controller is None:
        print("No Xbox controller found.")
        return

    print(f"Connected to: {controller.name}")
    print(f"Device path: {controller.path}")
    print("Reading joystick axes and sending 6-motor throttle values...")

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD, timeout=SERIAL_TIMEOUT)
        ser.dtr = False
        ser.rts = False
    except Exception as exc:
        print("Failed to open serial port:", exc)
        return

    time.sleep(3.0)
    drain(ser)

    try:
        input("Press Enter to ARM ESCs and begin motor control (Ctrl+C to cancel)...")
        send_cmd(ser, "ARM", wait=4.5)
        send_cmd(ser, "MOTORS " + " ".join(str(BASE_THROTTLE) for _ in range(6)), wait=0.2)

        pitch = 0.0
        yaw = 0.0
        roll = 0.0

        for event in controller.read_loop():
            if event.type != ecodes.EV_ABS:
                continue

            code = ecodes.ABS[event.code]
            if code == "ABS_RZ":
                pitch = -normalize_stick(event.value)
            elif code == "ABS_Z":
                yaw = normalize_stick(event.value)
            elif code == "ABS_X":
                roll = normalize_stick(event.value)
            else:
                continue

            pitch = deadzone(pitch)
            yaw = deadzone(yaw)
            roll = deadzone(roll)

            motor_pwms = mix_motors(pitch, roll, yaw)
            send_cmd(ser, "MOTORS " + " ".join(str(p) for p in motor_pwms), wait=0.05)

            print(
                f"Pitch: {pitch:+.2f} | Yaw: {yaw:+.2f} | Roll: {roll:+.2f} | "
                f"PitchUp:{motor_pwms[PITCH_UP]} PitchDown:{motor_pwms[PITCH_DOWN]} | "
                f"YawLeft:{motor_pwms[YAW_LEFT]} YawRight:{motor_pwms[YAW_RIGHT]} | "
                f"RollLeft:{motor_pwms[ROLL_LEFT]} RollRight:{motor_pwms[ROLL_RIGHT]}"
            )

    except KeyboardInterrupt:
        print("\nStopping and closing serial port...")
    finally:
        send_cmd(ser, "STOP", wait=0.2)
        ser.close()


if __name__ == "__main__":
    main()
