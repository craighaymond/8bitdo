import os
import sys
import time

# Hide the pygame welcome prompt
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    # Only initialize the modules we need, preventing an empty window from opening
    pygame.joystick.init()
    pygame.display.init()
    
    clear_screen()
    print("=============================================================")
    print("                CLIENT CONTROLLER TESTER                     ")
    print("=============================================================")
    
    if pygame.joystick.get_count() == 0:
        print("\n[!] No controllers detected.")
        print("Make sure your USBIP client is running and has attached the controller!")
        print("Waiting for controller to be attached...\n")
        
    # Wait for a joystick to be plugged in
    while pygame.joystick.get_count() == 0:
        pygame.joystick.quit()
        pygame.joystick.init()
        time.sleep(1)
        
    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    for joy in joysticks:
        joy.init()
        
    # We'll just monitor the first controller for the dashboard
    joy = joysticks[0]
    
    clear_screen()
    
    try:
        while True:
            # Pump events so pygame updates the joystick states
            pygame.event.pump()
            
            # Move cursor to top-left to redraw without flickering (ANSI escape code)
            sys.stdout.write("\033[H")
            
            print("=============================================================")
            print("                  CONTROLLER INPUT TESTER                    ")
            print("=============================================================\033[K")
            print(f" Detected: {joy.get_name()} (GUID: {joy.get_guid()})\033[K")
            print("-------------------------------------------------------------\033[K")
            
            # --- AXES ---
            print(" AXES (Joysticks & Triggers):\033[K")
            num_axes = joy.get_numaxes()
            for i in range(0, num_axes, 2):
                val1 = joy.get_axis(i)
                str1 = f"Axis {i}: {val1:>5.2f}"
                
                if i + 1 < num_axes:
                    val2 = joy.get_axis(i + 1)
                    str2 = f"Axis {i+1}: {val2:>5.2f}"
                else:
                    str2 = ""
                    
                print(f"   {str1:<25} {str2:<25}\033[K")
                
            # --- HATS (D-PAD) ---
            print("\n D-PAD (Hats):\033[K")
            num_hats = joy.get_numhats()
            if num_hats == 0:
                print("   No D-Pad detected.\033[K")
            for i in range(num_hats):
                hx, hy = joy.get_hat(i)
                dir_str = "Center"
                if hx == -1: dir_str = "Left"
                elif hx == 1: dir_str = "Right"
                elif hy == 1: dir_str = "Up"
                elif hy == -1: dir_str = "Down"
                
                if hx == -1 and hy == 1: dir_str = "Up-Left"
                elif hx == 1 and hy == 1: dir_str = "Up-Right"
                elif hx == -1 and hy == -1: dir_str = "Down-Left"
                elif hx == 1 and hy == -1: dir_str = "Down-Right"
                
                print(f"   Hat {i}: ({hx:>2}, {hy:>2})  [{dir_str}]\033[K")
                
            # --- BUTTONS ---
            print("\n BUTTONS:\033[K")
            num_buttons = joy.get_numbuttons()
            
            # Create a 3-column layout for buttons
            cols = 3
            for r in range(0, num_buttons, cols):
                row_str = "   "
                for c in range(cols):
                    idx = r + c
                    if idx < num_buttons:
                        state = "ON " if joy.get_button(idx) else "OFF"
                        row_str += f"[{idx:>2}]: {state:<5}   "
                print(f"{row_str}\033[K")
                
            print("=============================================================\033[K")
            print(" Press Ctrl+C to exit.\033[K")
            
            # Clear any remaining lines below our print area (just in case)
            sys.stdout.write("\033[J")
            sys.stdout.flush()
            
            time.sleep(0.05) # Run at 20fps to prevent CPU hogging
            
    except KeyboardInterrupt:
        print("\n\nExiting...")
        pygame.quit()

if __name__ == "__main__":
    # Ensure ANSI escape codes work in older Windows terminals
    if os.name == 'nt':
        os.system('color')
    main()
