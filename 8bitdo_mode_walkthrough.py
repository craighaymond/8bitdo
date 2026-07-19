import subprocess
import time
import sys

def get_usb_devices():
    """Returns a list of dicts representing USB devices."""
    devices = []
    try:
        lsusb_out = subprocess.run(["lsusb"], capture_output=True, text=True, check=True).stdout
        for line in lsusb_out.splitlines():
            line = line.strip()
            if not line: continue
            parts = line.split()
            if len(parts) >= 6:
                vid_pid = parts[5]
                name = " ".join(parts[6:])
                devices.append({'id': vid_pid, 'name': name, 'line': line})
    except Exception as e:
        print(f"Warning: Could not run lsusb. ({e})")
    return devices

def main():
    print("=========================================")
    print("   8BitDo USB Adapter Mode Walkthrough   ")
    print("=========================================")
    print("This script guides you through changing the modes of your 8BitDo USB Adapter.")
    print("Ensure your controller is powered on and connected to the adapter.\n")
    
    devs = get_usb_devices()
    # Looking for 8BitDo, Nintendo, Sony, and Microsoft VIDs which the adapter masquerades as
    known_vids = ["2dc8", "057e", "054c", "045e", "0f0d"] 
    
    print("Currently detected USB Gamepad/Adapter devices:")
    found = False
    for d in devs:
        if any(vid in d['id'] for vid in known_vids) or "8BitDo" in d['name'].casefold():
            print(f"  -> ID: {d['id']} | {d['name']}")
            found = True
            
    if not found:
        print("  (No 8BitDo or compatible gamepad devices detected)")
        
    modes = [
        ("X-Input (Xbox/Windows)", "[Minus] + [Up]", "045e:028e (Microsoft Xbox 360 Controller)"),
        ("D-Input (Android)", "[Minus] + [Left]", "2dc8:3107 or 2dc8:3105 (8BitDo D-Input)"),
        ("Switch Mode", "[Minus] + [L Bumper]", "057e:2009 (Nintendo Switch Pro Controller)"),
        ("macOS Mode", "[Minus] + [Right]", "054c:05c4 or 054c:0268 (Sony DualShock)"),
        ("PS Classic Mode", "[Minus] + [Down]", "054c:0ce6 (Sony PS Classic Controller)"),
        ("MegaDrive Mini", "[Minus] + [Up] + [Left]", "0f0d:00c1 or similar (Sega/Hori MegaDrive)")
    ]
    
    for mode_name, combo, expected_id in modes:
        print("\n" + "-"*50)
        print(f"Next Mode: {mode_name}")
        print(f"Action: Hold {combo} for 3 seconds.")
        print(f"Expected USB ID: {expected_id}")
        print("Wait for the adapter LED to blink and the controller to reconnect.")
        input("Press Enter when you have changed the mode and it has reconnected...")
        
        time.sleep(1.5) # Allow USB bus to settle just in case
        current_devs = get_usb_devices()
        print(f"\n[Result] Detected USB devices after change:")
        found_any = False
        for d in current_devs:
            if any(vid in d['id'] for vid in known_vids) or "8BitDo" in d['name'].casefold():
                print(f"  -> ID: {d['id']} | {d['name']}")
                found_any = True
        if not found_any:
            print("  (No 8BitDo or compatible gamepad devices detected)")
                
    print("\n=========================================")
    print("Walkthrough complete!")
    print("=========================================")

if __name__ == "__main__":
    if sys.platform == "win32":
        print("This script uses 'lsusb' and is intended to run on Linux/Raspberry Pi.")
        sys.exit(1)
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
