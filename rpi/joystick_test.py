import serial
import time
from evdev import InputDevice, ecodes, list_devices

SERIAL_PORT = "/dev/ttyACM0"
BAUD = 115200
SERIAL_TIMEOUT = 0.05

OFF_PWM = 1000
IDLE_PWM = 1000
MOTOR_MIN = 1165
MOTOR_MAX = 1800

DEADZONE = 0.15
INPUT_THRESHOLD = 0.2

SEND_HZ = 10
SEND_PERIOD = 1.0 / SEND_HZ

PRINT_PERIOD = 0.5
LOOP_SLEEP = 0.005

KILL_BUTTON_CODE = ecodes.BTN_SOUTH  # Xbox A button

# 12 motor layout:
# Pitch up:    motors 0, 1
# Pitch down:  motors 2, 3
# Yaw left:    motors 4, 5
# Yaw right:   motors 6, 7
# Roll left:   motors 8, 9
# Roll right:  motors 10, 11

PITCH_UP = [0, 1]
PITCH_DOWN = [2, 3]
YAW_LEFT = [4, 5]
YAW_RIGHT = [6, 7]
ROLL_LEFT = [8, 9]
ROLL_RIGHT = [10, 11]

NUM_MOTORS = 12


def find_xbox_controller():
    for path in list_devices():
        dev = InputDevice(path)
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


def set_group(motors, indices, value):
    for i in indices:
        motors[i] = value


def mix_motors(pitch, roll, yaw):
    motors = [IDLE_PWM] * NUM_MOTORS
    span = MOTOR_MAX - MOTOR_MIN

    if pitch > 0:
        value = MOTOR_MIN + pitch * span
        set_group(motors, PITCH_UP, value)
    elif pitch < 0:
        value = MOTOR_MIN + (-pitch) * span
        set_group(motors, PITCH_DOWN, value)

    if yaw > 0:
        value = MOTOR_MIN + yaw * span
        set_group(motors, YAW_RIGHT, value)
    elif yaw < 0:
        value = MOTOR_MIN + (-yaw) * span
        set_group(motors, YAW_LEFT, value)

    if roll > 0:
        value = MOTOR_MIN + roll * span
        set_group(motors, ROLL_RIGHT, value)
    elif roll < 0:
        value = MOTOR_MIN + (-roll) * span
        set_group(motors, ROLL_LEFT, value)

    return [int(round(clamp(m, OFF_PWM, MOTOR_MAX))) for m in motors]


def drain(serial_port):
    while serial_port.in_waiting:
        line = serial_port.readline().decode(errors="ignore").strip()
        if line:
            print("PICO:", line)


def clear_controller_events(controller):
    try:
        while True:
            list(controller.read())
    except BlockingIOError:
        pass


def send_cmd(serial_port, cmd, quiet=True):
    full_cmd = "CMD " + cmd

    if not quiet:
        print("SEND:", full_cmd)

    serial_port.reset_output_buffer()
    serial_port.write((full_cmd + "\n").encode("utf-8"))


def send_motors(serial_port, motor_pwms):
    send_cmd(
        serial_port,
        "MOTORS " + " ".join(str(p) for p in motor_pwms),
        quiet=True,
    )


def arm_escs(serial_port):
    print("Arming ESCs...")
    send_cmd(serial_port, "ARM", quiet=False)
    time.sleep(4.5)
    drain(serial_port)

    send_motors(serial_port, [IDLE_PWM] * NUM_MOTORS)
    print("Armed. Motors IDLE.")


def emergency_stop(serial_port):
    print("!!! EMERGENCY STOP PRESSED !!!")

    send_motors(serial_port, [OFF_PWM] * NUM_MOTORS)
    time.sleep(0.02)

    send_cmd(serial_port, "STOP", quiet=False)

    time.sleep(0.1)
    drain(serial_port)


def main():
    controller = find_xbox_controller()
    if controller is None:
        print("No Xbox controller found.")
        return

    print(f"Connected to: {controller.name}")
    print(f"Device path: {controller.path}")

    try:
        controller.grab()
        print("Controller grabbed.")
    except Exception:
        print("Could not grab controller. Continuing anyway.")

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
        input("Press Enter to ARM ESCs and begin motor control...")

        arm_escs(ser)

        clear_controller_events(controller)
        print("Controller event queue cleared.")

        pitch = 0.0
        yaw = 0.0
        roll = 0.0

        last_send_time = 0.0
        last_print_time = 0.0
        last_active = None

        killed = False

        print("Controller active.")
        print("Press A / BTN_SOUTH for emergency software stop.")
        print("Ctrl+C to exit.")

        while True:
            try:
                events = list(controller.read())
            except BlockingIOError:
                events = []

            for event in events:
                if event.type == ecodes.EV_KEY:
                    if event.code == KILL_BUTTON_CODE and event.value == 1:
                        emergency_stop(ser)

                        killed = True
                        pitch = 0.0
                        yaw = 0.0
                        roll = 0.0

                        clear_controller_events(controller)
                        continue

                elif event.type == ecodes.EV_ABS and not killed:
                    code = ecodes.ABS[event.code]

                    if code == "ABS_RZ":
                        pitch = -normalize_stick(event.value)
                    elif code == "ABS_Z":
                        yaw = normalize_stick(event.value)
                    elif code == "ABS_X":
                        roll = normalize_stick(event.value)

            now = time.time()

            if killed:
                print("SYSTEM KILLED — press Enter to re-arm, or Ctrl+C to exit.")

                try:
                    input()
                    arm_escs(ser)

                    clear_controller_events(controller)
                    print("Controller event queue cleared.")

                    killed = False
                    pitch = 0.0
                    yaw = 0.0
                    roll = 0.0

                    last_send_time = 0.0
                    last_print_time = 0.0
                    last_active = None

                    print("Controller active again.")
                except KeyboardInterrupt:
                    break

                continue

            pitch = deadzone(pitch)
            yaw = deadzone(yaw)
            roll = deadzone(roll)

            active = max(abs(pitch), abs(yaw), abs(roll)) > INPUT_THRESHOLD

            if active:
                motor_pwms = mix_motors(pitch, roll, yaw)
            else:
                motor_pwms = [IDLE_PWM] * NUM_MOTORS

            if now - last_send_time >= SEND_PERIOD:
                send_motors(ser, motor_pwms)
                last_send_time = now

            if active != last_active or now - last_print_time >= PRINT_PERIOD:
                print(
                    f"Active:{active} | "
                    f"Pitch:{pitch:+.2f} Yaw:{yaw:+.2f} Roll:{roll:+.2f} | "
                    f"Motors:{motor_pwms}"
                )
                last_active = active
                last_print_time = now

            time.sleep(LOOP_SLEEP)

    except KeyboardInterrupt:
        print("\nStopping motors...")

    finally:
        try:
            send_motors(ser, [OFF_PWM] * NUM_MOTORS)
            time.sleep(0.05)
            send_cmd(ser, "STOP", quiet=False)
            time.sleep(0.1)
            drain(ser)
        except Exception:
            pass

        try:
            controller.ungrab()
        except Exception:
            pass

        ser.close()
        print("Serial port closed.")


if __name__ == "__main__":
    main()