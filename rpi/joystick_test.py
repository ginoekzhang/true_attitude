from evdev import InputDevice, categorize, ecodes, list_devices

def find_xbox_controller():
    devices = [InputDevice(path) for path in list_devices()]
    for dev in devices:
        name = dev.name.lower()
        if "xbox" in name or "controller" in name or "gamepad" in name:
            return dev
    return None

def normalize_stick(value):
    # Xbox sticks are usually 0–65535, center around 32768
    return round((value - 32768) / 32768, 3)

def normalize_trigger(value):
    # Triggers are usually 0–1023 or 0–255 depending on controller
    return value

controller = find_xbox_controller()

if controller is None:
    print("No Xbox controller found.")
    exit()

print(f"Connected to: {controller.name}")
print(f"Device path: {controller.path}")
print("Reading right joystick, RT, and LT...")

right_x = 0
right_y = 0
lt = 0
rt = 0

for event in controller.read_loop():
    if event.type == ecodes.EV_ABS:
        code = ecodes.ABS[event.code]

        if code == "ABS_RX":
            right_x = normalize_stick(event.value)

        elif code == "ABS_RY":
            right_y = normalize_stick(event.value)

        elif code == "ABS_Z":
            lt = normalize_trigger(event.value)

        elif code == "ABS_RZ":
            rt = normalize_trigger(event.value)

        print(f"Right X: {right_x:>6} | Right Y: {right_y:>6} | LT: {lt:>4} | RT: {rt:>4}")