import pygame
import vgamepad as vg
import time
import sys
import ctypes

# Set window title for the RetroBat stop script
ctypes.windll.kernel32.SetConsoleTitleW("8bitdoBridge")

pygame.init()
pygame.joystick.init()

# --- PRESERVED MAPPING ---
BUTTON_MAP = {
    0: vg.XUSB_BUTTON.XUSB_GAMEPAD_B, 1: vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    2: vg.XUSB_BUTTON.XUSB_GAMEPAD_Y, 3: vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    4: vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK, 6: vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    9: vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER, 10: vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB
}

class ControllerBridge:
    def __init__(self, joy, slot_index):
            self.joy = joy
            self.xbox = vg.VX360Gamepad()
            self.name = self.joy.get_name()
            self.instance_id = self.joy.get_instance_id()
            
            # State tracking to prevent "input leaking" and driver spam
            self.button_states = {} 
            self.dpad_states = {btn: False for btn in range(11, 15)}
            self.trigger_states = {7: False, 8: False}
            
            # Define Deadzone
            self.dz = 0.2

            print(f"Slot {slot_index + 1}: Bound {self.name} (ID: {self.instance_id})")
            
            # --- Pulse each controller ---
            try:
                self.joy.rumble(1.0, 1.0, 300)         
            except pygame.error:
                pass

    def apply_deadzone(self, value):
            if abs(value) < self.dz:
                return 0.0
            return value

    def update(self):
        # Buttons with state tracking
        for phys_btn, virt_btn in BUTTON_MAP.items():
            current_state = self.joy.get_button(phys_btn)
            if current_state != self.button_states.get(phys_btn, False):
                if current_state: self.xbox.press_button(button=virt_btn)
                else: self.xbox.release_button(button=virt_btn)
                self.button_states[phys_btn] = current_state

        # D-PAD (11-14) with state tracking
        dpad_map = {
            11: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
            12: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
            13: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
            14: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT
        }
        for phys, virt in dpad_map.items():
            state = self.joy.get_button(phys)
            if state != self.dpad_states[phys]:
                if state: self.xbox.press_button(button=virt)
                else: self.xbox.release_button(button=virt)
                self.dpad_states[phys] = state

        # Sticks (As requested, preserved raw passing)
        self.xbox.left_joystick_float(x_value_float=self.joy.get_axis(0), y_value_float=self.joy.get_axis(1))
        self.xbox.right_joystick_float(x_value_float=self.joy.get_axis(2), y_value_float=self.joy.get_axis(3))
        
        # Triggers with state tracking
        for phys, is_left in [(7, True), (8, False)]:
            state = self.joy.get_button(phys)
            if state != self.trigger_states[phys]:
                val = 1.0 if state else 0.0
                if is_left: self.xbox.left_trigger_float(value_float=val)
                else: self.xbox.right_trigger_float(value_float=val)
                self.trigger_states[phys] = state

        self.xbox.update()

# --- MAIN LOOP ---
bridges = []

# Phase 1: Initialize physical controllers
physical_joysticks = []
print("Searching for 8BitDo controllers...")
for i in range(pygame.joystick.get_count()):
    joy = pygame.joystick.Joystick(i)
    name = joy.get_name()
    if "Xbox" not in name:
        joy.init()
        guid = joy.get_guid()
        instance_id = joy.get_instance_id()
        physical_joysticks.append(joy)
        print(f"Found Physical: {name}")
        print(f"  - GUID: {guid}")
        print(f"  - ID:   {instance_id}")

if not physical_joysticks:
    print("No physical controllers found!")
    sys.exit()

# Phase 2: Create virtual gamepads with a cooldown
print("\nInitializing Virtual Xbox Controllers...")
for index, joy in enumerate(physical_joysticks):
    bridge = ControllerBridge(joy, index)
    bridges.append(bridge)
    # Ensure virtual controller starts in a neutral state
    bridge.xbox.reset()
    bridge.xbox.update()
    time.sleep(0.5) 

print(f"\nSuccessfully bridged {len(bridges)} controllers.")
print("CHECK: Are all GUIDs above unique? If not, usbip is mirroring them.")
try:
    while True:
        pygame.event.pump()
        for b in bridges:
            b.update()
        time.sleep(0.01)
except (KeyboardInterrupt, SystemExit):
    # This is triggered by the 'Soft' taskkill
    print("\nBridge stopped.")
    pass 
finally:
    # This is the 'Unplug' signal for the driver
    for b in bridges:
        if hasattr(b, 'xbox'):
            del b.xbox 
    pygame.quit()