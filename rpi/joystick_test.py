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

pitch = 0
yaw = 0
roll = 0

for event in controller.read_loop():
    if event.type == ecodes.EV_ABS:
        code = ecodes.ABS[event.code]

        if code == "ABS_RZ":
            pitch = -normalize_stick(event.value)

        elif code == "ABS_Z":
            yaw = normalize_stick(event.value)

        elif code == "ABS_X":
            roll = normalize_stick(event.value)

        print(f"Pitch: {pitch:>6} | Yaw: {yaw:>6} | Roll: {roll:>6}")

"""
if needed, ABS_BRAKE = left trigger; ABS_GAS = right trigger
"""