import subprocess
import time
import sys
import os

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
    except Exception:
        pass
    return devices

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    clear_screen()
    print("===============================================================================")
    print("                      8BitDo USB Adapter Mode Monitor")
    print("===============================================================================")
    print(" Button Legend: [Minus] = Select/-, [Share] = Create, [L Bumper] = L1/LB/L ")
    print(" Note: Hold combos for 3-5 seconds. (Use physical switch if applicable)")
    print("-------------------------------------------------------------------------------")
    print("| Mode                   | Primary Combo           | Expected USB ID          |")
    print("|------------------------|-------------------------|--------------------------|")
    print("| X-Input (Xbox/Windows) | [Minus] + [Up]          | 045e:028e                |")
    print("| D-Input (Android)      | [Minus] + [Left]        | 2dc8:3107 or 2dc8:3105   |")
    print("| Switch Mode            | [Minus] + [L Bumper]    | 057e:2009                |")
    print("| macOS Mode             | [Minus] + [Right]       | 054c:05c4 or 054c:0268   |")
    print("| PS Classic Mode        | [Minus] + [Down]        | 054c:0ce6                |")
    print("| MegaDrive Mini         | [Minus] + [Up] + [Left] | 0f0d:00c1                |")
    print("===============================================================================\n")
    print("Press Ctrl+C to exit.\n")
    
    known_vids = ["2dc8", "057e", "054c", "045e", "0f0d"]
    
    # Map for easy lookup
    mode_map = {
        "045e:028e": "X-Input (Xbox)",
        "2dc8:3107": "D-Input (Android) / IDLE",
        "2dc8:3105": "D-Input (Android)",
        "2dc8:3106": "X-Input (8BitDo 2.4G)",
        "057e:2009": "Switch Mode",
        "054c:05c4": "macOS Mode",
        "054c:0268": "macOS Mode",
        "054c:0ce6": "PS Classic Mode",
        "0f0d:00c1": "MegaDrive Mini Mode"
    }

    poll_interval = 3
    
    try:
        while True:
            devs = get_usb_devices()
            target_devs = []
            
            for d in devs:
                if any(vid in d['id'] for vid in known_vids) or "8BitDo" in d['name'].casefold():
                    target_devs.append(d)
            
            # Print the status line and run inner loop for countdown
            for remaining in range(poll_interval, 0, -1):
                if not target_devs:
                    status_str = "No 8BitDo adapters detected."
                else:
                    parts = []
                    for d in target_devs:
                        mode = mode_map.get(d['id'], "Unknown Mode")
                        parts.append(f"[{d['id']} -> {mode}]")
                    status_str = " | ".join(parts)
                
                # \r returns to start of line, \033[K clears to end of line
                sys.stdout.write(f"\r\033[KCurrent State: {status_str}  (Polling in {remaining}s...)")
                sys.stdout.flush()
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n\nExiting...")

if __name__ == "__main__":
    if sys.platform == "win32":
        print("This script uses 'lsusb' and is intended to run on Linux/Raspberry Pi.")
        sys.exit(1)
    main()
