import serial
import time
from evdev import InputDevice, ecodes, list_devices

SERIAL_PORT = "/dev/ttyACM0"
BAUD = 115200
SERIAL_TIMEOUT = 0.05

OFF_PWM = 0          # change to 1000 if Pico/ESC does not accept 0
MOTOR_MIN = 1155
MOTOR_MAX = 1300

DEADZONE = 0.08
INPUT_THRESHOLD = 0.10

SEND_HZ = 20
SEND_PERIOD = 1.0 / SEND_HZ

PRINT_PERIOD = 0.5
LOOP_SLEEP = 0.005

KILL_BUTTON_CODE = ecodes.BTN_SOUTH  # Xbox A button

PITCH_UP = 0
PITCH_DOWN = 1
YAW_LEFT = 2
YAW_RIGHT = 3
ROLL_LEFT = 4
ROLL_RIGHT = 5


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


def mix_motors(pitch, roll, yaw):
    motors = [OFF_PWM] * 6
    span = MOTOR_MAX - MOTOR_MIN

    if pitch > 0:
        motors[PITCH_UP] = MOTOR_MIN + pitch * span
    elif pitch < 0:
        motors[PITCH_DOWN] = MOTOR_MIN + (-pitch) * span

    if yaw > 0:
        motors[YAW_RIGHT] = MOTOR_MIN + yaw * span
    elif yaw < 0:
        motors[YAW_LEFT] = MOTOR_MIN + (-yaw) * span

    if roll > 0:
        motors[ROLL_RIGHT] = MOTOR_MIN + roll * span
    elif roll < 0:
        motors[ROLL_LEFT] = MOTOR_MIN + (-roll) * span

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

    serial_port.write((full_cmd + "\n").encode("utf-8"))


def send_motors(serial_port, motor_pwms):
    send_cmd(serial_port, "MOTORS " + " ".join(str(p) for p in motor_pwms), quiet=True)


def arm_escs(serial_port):
    print("Arming ESCs...")
    send_cmd(serial_port, "ARM", quiet=False)
    time.sleep(4.5)
    drain(serial_port)

    send_motors(serial_port, [OFF_PWM] * 6)
    print("Armed. Motors OFF.")


def emergency_stop(serial_port):
    print("!!! EMERGENCY STOP PRESSED !!!")

    # Clear unsent old commands from Pi side
    serial_port.reset_output_buffer()

    # Send only OFF + STOP
    send_motors(serial_port, [OFF_PWM] * 6)
    time.sleep(0.02)
    send_cmd(serial_port, "STOP", quiet=False)

    # Wait and read Pico response
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
        last_motor_pwms = None
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
                        last_motor_pwms = [OFF_PWM] * 6
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
                if now - last_print_time >= PRINT_PERIOD:
                    print("SYSTEM KILLED — press Enter to re-arm, or Ctrl+C to exit.")
                    last_print_time = now

                try:
                    user_input = input()
                    if user_input == "":
                        arm_escs(ser)

                        clear_controller_events(controller)
                        print("Controller event queue cleared.")

                        killed = False
                        pitch = 0.0
                        yaw = 0.0
                        roll = 0.0

                        last_motor_pwms = None
                        last_active = None
                        last_send_time = 0.0
                        last_print_time = 0.0

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
                motor_pwms = [OFF_PWM] * 6

            if now - last_send_time >= SEND_PERIOD:
                if motor_pwms != last_motor_pwms:
                    send_motors(ser, motor_pwms)
                    last_motor_pwms = motor_pwms[:]

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
            send_motors(ser, [OFF_PWM] * 6)
            time.sleep(0.1)
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