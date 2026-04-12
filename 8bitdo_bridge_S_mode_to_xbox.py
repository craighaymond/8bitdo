import pygame
import vgamepad as vg
import time
import sys
import ctypes
from datetime import datetime

# --- CONFIGURATION & MAPPING ---
DEADZONE = 0.2
POLLING_RATE = 0.01  # 100Hz

# Set console title for RetroBat stop script
try:
    ctypes.windll.kernel32.SetConsoleTitleW("8bitdoBridge")
except Exception:
    pass

# Pygame Button to Xbox Button Mapping (S-mode / Switch Pro layout)
BUTTON_MAP = {
    0: vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    1: vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    2: vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    3: vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    4: vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,   # Minus button
    6: vg.XUSB_BUTTON.XUSB_GAMEPAD_START,  # Plus button
    9: vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    10: vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    7: vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    8: vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
}

# D-pad Mapping (Buttons 11-14 in S-mode)
DPAD_MAP = {
    11: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    12: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    13: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    14: vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT
}

# Axis Mapping for S-mode
AXIS_LX, AXIS_LY = 0, 1
AXIS_RX, AXIS_RY = 2, 3
AXIS_LT, AXIS_RT = 4, 5

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")

class ControllerBridge:
    def __init__(self, joy):
        self.joy = joy
        self.xbox = vg.VX360Gamepad()
        self.name = self.joy.get_name()
        self.instance_id = self.joy.get_instance_id()
        self.num_axes = self.joy.get_numaxes()
        self.num_buttons = self.joy.get_numbuttons()
        
        self.button_states = {} 
        self.dpad_states = {btn: False for btn in DPAD_MAP.keys()}
        self.trigger_active = {AXIS_LT: False, AXIS_RT: False}
        
        log(f"Bound: {self.name} (ID: {self.instance_id})")
        
        # Diagnostic warning for "Running Left" issue
        if self.num_axes > 0:
            lx = self.joy.get_axis(AXIS_LX)
            if abs(lx) > 0.5:
                log(f"  [WARNING] Axis LX (0) is reporting a high value: {lx:.2f}")

        try:
            self.joy.rumble(0.6, 0.6, 200)         
        except pygame.error:
            pass

    def apply_deadzone(self, value):
        return value if abs(value) >= DEADZONE else 0.0

    def update(self):
        # 1. Buttons & D-Pad
        for mapping, states in [(BUTTON_MAP, self.button_states), (DPAD_MAP, self.dpad_states)]:
            for phys_btn, virt_btn in mapping.items():
                if phys_btn < self.num_buttons:
                    curr = self.joy.get_button(phys_btn)
                    if curr != states.get(phys_btn, False):
                        if curr: self.xbox.press_button(button=virt_btn)
                        else: self.xbox.release_button(button=virt_btn)
                        states[phys_btn] = curr

        # 2. Sticks
        self.xbox.left_joystick_float(
            x_value_float=self.apply_deadzone(self.joy.get_axis(AXIS_LX)) if AXIS_LX < self.num_axes else 0.0,
            y_value_float=self.apply_deadzone(self.joy.get_axis(AXIS_LY)) if AXIS_LY < self.num_axes else 0.0
        )
        self.xbox.right_joystick_float(
            x_value_float=self.apply_deadzone(self.joy.get_axis(AXIS_RX)) if AXIS_RX < self.num_axes else 0.0,
            y_value_float=self.apply_deadzone(self.joy.get_axis(AXIS_RY)) if AXIS_RY < self.num_axes else 0.0
        )
        
        # 3. Triggers (Initialization Fix)
        for axis_id, is_left in [(AXIS_LT, True), (AXIS_RT, False)]:
            if axis_id < self.num_axes:
                raw_val = self.joy.get_axis(axis_id)
                if not self.trigger_active[axis_id] and abs(raw_val) > 0.01:
                    self.trigger_active[axis_id] = True
                
                norm_val = (raw_val + 1.0) / 2.0 if self.trigger_active[axis_id] else 0.0
                if is_left: self.xbox.left_trigger_float(value_float=norm_val)
                else: self.xbox.right_trigger_float(value_float=norm_val)

        self.xbox.update()

    def shutdown(self):
        log(f"Unplugging {self.name} (ID: {self.instance_id})")
        if hasattr(self, 'xbox'): del self.xbox

def main():
    pygame.init()
    pygame.joystick.init()
    bridges = {}
    log("8BitDo Bridge Running. Press Ctrl+C to stop.")
    
    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.JOYDEVICEADDED:
                    # Create temporary object to check name
                    temp_joy = pygame.joystick.Joystick(event.device_index)
                    name = temp_joy.get_name().lower()
                    
                    # STRICT FILTERING: Ignore virtual Xbox controllers AND sensors/peripherals
                    skip_keywords = ["xbox", "keyboard", "mouse", "motion", "sensor", "accel"]
                    if any(kw in name for kw in skip_keywords):
                        continue
                        
                    temp_joy.init()
                    iid = temp_joy.get_instance_id()
                    if iid not in bridges:
                        bridges[iid] = ControllerBridge(temp_joy)
                
                elif event.type == pygame.JOYDEVICEREMOVED:
                    if event.instance_id in bridges:
                        bridges[event.instance_id].shutdown()
                        del bridges[event.instance_id]
            
            for iid in list(bridges.keys()):
                try:
                    bridges[iid].update()
                except Exception:
                    bridges[iid].shutdown()
                    del bridges[iid]
            
            time.sleep(POLLING_RATE)
            
    except (KeyboardInterrupt, SystemExit):
        log("Stopping...")
    finally:
        for b in bridges.values(): b.shutdown()
        pygame.quit()

if __name__ == "__main__":
    main()
