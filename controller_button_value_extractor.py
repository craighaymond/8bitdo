import pygame
import sys

# Initialize the joystick module
pygame.init()
pygame.joystick.init()

# Verify the controller is detected
if pygame.joystick.get_count() == 0:
    print("No controllers found. Please plug in your 8BitDo and try again.")
    sys.exit()

# Connect to the first controller
joystick = pygame.joystick.Joystick(0)
joystick.init()

# Create a clock to limit the CPU usage
clock = pygame.time.Clock()

print(f"Connected to: {joystick.get_name()}")
print(f"Hardware SDL2 ID: {joystick.get_guid()}")  # Not the same as the GUID in the XML, but can be useful for troubleshooting
print("Listening for inputs... (CPU usage is now capped at 60 FPS!)")
print("Press CTRL+C in this window to exit.\n")
print("-" * 50)

try:
    while True:
        for event in pygame.event.get():
            
            # 1. Standard Buttons (Including your Switch-mode D-Pad)
            if event.type == pygame.JOYBUTTONDOWN:
                btn_val = event.button
                pov_val = 0 
                
                print(f"[BUTTON DETECTED] Raw Button Code: {btn_val} | PovDirection: {pov_val}")
                print(f"   XML -> <Button>{btn_val}</Button> | <PovDirection>{pov_val}</PovDirection> | <IsAxis>false</IsAxis>\n")

            # 2. Traditional D-Pad (If it ever reads as a 'Hat')
            elif event.type == pygame.JOYHATMOTION:
                hat_x, hat_y = event.value
                
                if hat_x == 0 and hat_y == 0:
                    continue
                    
                btn_val = 0 
                pov_val = 0
                
                if hat_y == 1:   pov_val = 1 
                elif hat_x == 1: pov_val = 2 
                elif hat_y == -1:pov_val = 3 
                elif hat_x == -1:pov_val = 4 

                print(f"[HAT DETECTED] Raw Button Code: {btn_val} | PovDirection: {pov_val}")
                print(f"   XML -> <Button>{btn_val}</Button> | <PovDirection>{pov_val}</PovDirection> | <IsAxis>false</IsAxis>\n")

            # 3. Joysticks and Triggers (Analog Axes)
            elif event.type == pygame.JOYAXISMOTION:
                if abs(event.value) > 0.5:
                    axis_val = event.axis
                    pov_val = 0 
                    
                    print(f"[AXIS DETECTED] Raw Axis Code: {axis_val} | PovDirection: {pov_val} | Tilt: {event.value:.2f}")
                    print(f"   XML -> <Button>{axis_val}</Button> | <PovDirection>{pov_val}</PovDirection> | <IsAxis>true</IsAxis>\n")

        # This single line saves your CPU! It tells the loop to wait before running again.
        clock.tick(60)

except KeyboardInterrupt:
    print("\nExiting tester...")
    pygame.quit()
    sys.exit()