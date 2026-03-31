import pygame
import vgamepad as vg
import time
import sys
import ctypes

# Set window title for the RetroBat stop script
ctypes.windll.kernel32.SetConsoleTitleW("TeknoParrotBridge")

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
    def __init__(self, joystick_index):
            self.joy = pygame.joystick.Joystick(joystick_index)
            self.joy.init()
            self.xbox = vg.VX360Gamepad()
            self.name = self.joy.get_name()
            
            # Define Deadzone (20% is standard for arcade stability)
            self.dz = 0.2

            print(f"Connected: {self.name} to Xbox Slot {joystick_index + 1}")
            
            # --- Pulse each controller to indicate that this bridge is enabled and working ---
            try:
                self.joy.rumble(1.0, 1.0, 300)         
            except pygame.error:
                print(f"Note: Rumble not supported for {self.name}")

    def apply_deadzone(self, value):
            """Returns 0.0 if the tilt is within the deadzone."""
            if abs(value) < self.dz:
                return 0.0
            return value

    def update(self):
        pygame.event.pump()
        
        # Buttons
        for phys_btn, virt_btn in BUTTON_MAP.items():
            if self.joy.get_button(phys_btn): self.xbox.press_button(button=virt_btn)
            else: self.xbox.release_button(button=virt_btn)

        # D-PAD (11-14)
        if self.joy.get_button(11): self.xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
        else: self.xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
        if self.joy.get_button(12): self.xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        else: self.xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        if self.joy.get_button(13): self.xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
        else: self.xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
        if self.joy.get_button(14): self.xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)
        else: self.xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)

        # ANALOG STICKS (The culprit for Alt+Tab cycling)
        # We apply the deadzone to every axis before sending to Windows
        ls_x = self.apply_deadzone(self.joy.get_axis(0))
        ls_y = self.apply_deadzone(self.joy.get_axis(1))
        rs_x = self.apply_deadzone(self.joy.get_axis(2))
        rs_y = self.apply_deadzone(self.joy.get_axis(3))

        # Sticks & Triggers (Preserved)
        self.xbox.left_joystick_float(x_value_float=self.joy.get_axis(0), y_value_float=self.joy.get_axis(1))
        self.xbox.right_joystick_float(x_value_float=self.joy.get_axis(2), y_value_float=self.joy.get_axis(3))
        
        if self.joy.get_button(7): self.xbox.left_trigger_float(value_float=1.0)
        else: self.xbox.left_trigger_float(value_float=0.0)
        if self.joy.get_button(8): self.xbox.right_trigger_float(value_float=1.0)
        else: self.xbox.right_trigger_float(value_float=0.0)

        self.xbox.update()

# --- MAIN LOOP ---
bridges = []
for i in range(pygame.joystick.get_count()):
    if "Xbox" not in pygame.joystick.Joystick(i).get_name():
        bridges.append(ControllerBridge(i))

if not bridges:
    print("No physical controllers found!")
    sys.exit()

try:
    while True:
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