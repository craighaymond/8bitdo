#!/usr/bin/env python3
import subprocess
import time
import os
import sys
import re

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print("=========================================================")
    print("      8BitDo S-Mode (Switch) Troubleshooter for Pi       ")
    print("=========================================================")
    print(" The Linux 'hid-nintendo' driver often crashes (error -32)")
    print(" when an 8BitDo adapter presents itself as a Switch Pro ")
    print(" controller (057e:2009). This tool helps diagnose and fix it.")
    print("=========================================================\n")

def check_dmesg_crashes():
    print("--- Recent Kernel Crashes (dmesg) ---")
    try:
        out = subprocess.run(["dmesg"], capture_output=True, text=True).stdout
        lines = out.splitlines()[-100:]
        found = False
        for line in lines:
            if "nintendo" in line.lower() or "057e:2009" in line or "error -32" in line or "error -71" in line:
                if "nintendo" in line.lower() or "057e" in line.lower():
                    print(line)
                    found = True
        if not found:
            print("No Nintendo/8BitDo crashes found in recent dmesg logs.")
    except Exception as e:
        print(f"Failed to read dmesg: {e}")
    print("-------------------------------------\n")
    input("Press Enter to return to menu...")

def apply_cmdline_quirk():
    print("--- Apply Boot Parameter Quirk (Requires Reboot) ---")
    print("This adds 'usbhid.quirks=0x057e:0x2009:0x0004' to your /boot/cmdline.txt")
    print("This forces the Linux kernel to treat the controller as a generic HID")
    print("device and ignore the crashing hid-nintendo driver entirely.")
    print("NOTE: You MUST run this script with 'sudo' for this to work.")
    
    confirm = input("\nProceed with modifying /boot/cmdline.txt? (y/n): ")
    if confirm.lower() != 'y': return
    
    try:
        cmdline_path = "/boot/cmdline.txt"
        if not os.path.exists(cmdline_path):
            cmdline_path = "/boot/firmware/cmdline.txt" # For newer Pi OS
            
        with open(cmdline_path, 'r') as f:
            content = f.read().strip()
            
        if "usbhid.quirks=0x057e:0x2009:0x0004" in content:
            print("Quirk is already present in cmdline.txt!")
        else:
            new_content = content + " usbhid.quirks=0x057e:0x2009:0x0004\n"
            with open(cmdline_path, 'w') as f:
                f.write(new_content)
            print("Successfully appended quirk to {cmdline_path}.")
            print("PLEASE REBOOT your Raspberry Pi for this to take effect. (Command: sudo reboot)")
    except PermissionError:
        print("\nERROR: Permission denied. You must run this script with 'sudo'.")
        print("Example: sudo python3 8bitdo_smode_troubleshooter.py")
    except Exception as e:
        print(f"\nError: {e}")
    input("\nPress Enter to return to menu...")

def apply_blacklist():
    print("--- Apply Modprobe Blacklist (Requires Reboot) ---")
    print("This creates /etc/modprobe.d/blacklist-nintendo.conf to prevent")
    print("the hid_nintendo driver from loading as a module.")
    print("Note: If the driver is built directly into the core kernel (common on Pi),")
    print("this blacklist will be ignored. The cmdline quirk (Option 3) is more reliable.")
    print("NOTE: You MUST run this script with 'sudo' for this to work.")
    
    confirm = input("\nProceed with creating blacklist? (y/n): ")
    if confirm.lower() != 'y': return
    
    try:
        with open("/etc/modprobe.d/blacklist-nintendo.conf", 'w') as f:
            f.write("blacklist hid_nintendo\nblacklist nintendo\n")
        print("Successfully created blacklist file.")
        print("PLEASE REBOOT your Raspberry Pi for this to take effect. (Command: sudo reboot)")
    except PermissionError:
        print("\nERROR: Permission denied. You must run this script with 'sudo'.")
        print("Example: sudo python3 8bitdo_smode_troubleshooter.py")
    except Exception as e:
        print(f"\nError: {e}")
    input("\nPress Enter to return to menu...")

def remove_cmdline_quirk():
    print("--- Undo Boot Parameter Quirk (Requires Reboot) ---")
    print("This removes 'usbhid.quirks=0x057e:0x2009:0x0004' from your /boot/cmdline.txt")
    print("NOTE: You MUST run this script with 'sudo' for this to work.")
    
    confirm = input("\nProceed with undoing cmdline.txt modification? (y/n): ")
    if confirm.lower() != 'y': return
    
    try:
        cmdline_path = "/boot/cmdline.txt"
        if not os.path.exists(cmdline_path):
            cmdline_path = "/boot/firmware/cmdline.txt"
            
        with open(cmdline_path, 'r') as f:
            content = f.read().strip()
            
        if "usbhid.quirks=0x057e:0x2009:0x0004" not in content:
            print("Quirk is not present in cmdline.txt. Nothing to undo.")
        else:
            new_content = content.replace(" usbhid.quirks=0x057e:0x2009:0x0004", "")
            new_content = new_content.replace("usbhid.quirks=0x057e:0x2009:0x0004", "")
            with open(cmdline_path, 'w') as f:
                f.write(new_content.strip() + "\n")
            print(f"Successfully removed quirk from {cmdline_path}.")
            print("PLEASE REBOOT your Raspberry Pi for this to take effect. (Command: sudo reboot)")
    except PermissionError:
        print("\nERROR: Permission denied. You must run this script with 'sudo'.")
        print("Example: sudo python3 8bitdo_smode_troubleshooter.py")
    except Exception as e:
        print(f"\nError: {e}")
    input("\nPress Enter to return to menu...")

def remove_blacklist():
    print("--- Undo Modprobe Blacklist (Requires Reboot) ---")
    print("This deletes /etc/modprobe.d/blacklist-nintendo.conf.")
    print("NOTE: You MUST run this script with 'sudo' for this to work.")
    
    confirm = input("\nProceed with deleting blacklist file? (y/n): ")
    if confirm.lower() != 'y': return
    
    try:
        if os.path.exists("/etc/modprobe.d/blacklist-nintendo.conf"):
            os.remove("/etc/modprobe.d/blacklist-nintendo.conf")
            print("Successfully deleted blacklist file.")
            print("PLEASE REBOOT your Raspberry Pi for this to take effect. (Command: sudo reboot)")
        else:
            print("Blacklist file does not exist. Nothing to undo.")
    except PermissionError:
        print("\nERROR: Permission denied. You must run this script with 'sudo'.")
        print("Example: sudo python3 8bitdo_smode_troubleshooter.py")
    except Exception as e:
        print(f"\nError: {e}")
    input("\nPress Enter to return to menu...")

def get_workaround_status():
    status = {"quirk": False, "blacklist": False}
    try:
        cmdline_path = "/boot/cmdline.txt"
        if not os.path.exists(cmdline_path): cmdline_path = "/boot/firmware/cmdline.txt"
        if os.path.exists(cmdline_path):
            with open(cmdline_path, 'r') as f:
                if "usbhid.quirks=0x057e:2009:0x0004" in f.read() or "usbhid.quirks=0x057e:0x2009:0x0004" in f.read():
                    status["quirk"] = True
    except: pass
    
    try:
        if os.path.exists("/etc/modprobe.d/blacklist-nintendo.conf"):
            status["blacklist"] = True
    except: pass
    
    return status

def get_driver_for_device(hwid):
    try:
        out = subprocess.run(["usb-devices"], capture_output=True, text=True).stdout
        current_vendor = ""
        for line in out.splitlines():
            if "Vendor=" in line and "ProdID=" in line:
                match = re.search(r"Vendor=([a-fA-F0-9]{4})\s+ProdID=([a-fA-F0-9]{4})", line)
                if match: current_vendor = f"{match.group(1).lower()}:{match.group(2).lower()}"
            if "Driver=" in line and current_vendor == hwid:
                match = re.search(r"Driver=([^\s]+)", line)
                if match: return match.group(1)
    except: pass
    return "Unknown/Unbound"

def live_monitor():
    print("--- Live Mode & Crash Monitor ---")
    print("Plug in your adapter, change modes, and watch for crashes in real-time.")
    print("Press Ctrl+C to stop monitoring and return to menu.\n")
    
    try:
        last_dmesg_ts = 0.0
        while True:
            # 1. Print connected 8bitdo devices and their bound drivers
            lsusb_out = subprocess.run(["lsusb"], capture_output=True, text=True).stdout
            devices = []
            for line in lsusb_out.splitlines():
                if "057e:2009" in line:
                    drv = get_driver_for_device("057e:2009")
                    devices.append(f"S-Mode [057e:2009] (Driver: {drv})")
                elif "2dc8:3106" in line:
                    drv = get_driver_for_device("2dc8:3106")
                    devices.append(f"X-Mode [2dc8:3106] (Driver: {drv})")
                elif "2dc8:3105" in line:
                    drv = get_driver_for_device("2dc8:3105")
                    devices.append(f"D-Mode [2dc8:3105] (Driver: {drv})")
                elif "045e:028e" in line:
                    drv = get_driver_for_device("045e:028e")
                    devices.append(f"X-Mode [045e:028e] (Driver: {drv})")
            
            sys.stdout.write("\r\033[K")
            if devices:
                sys.stdout.write("Detected: " + " | ".join(devices))
            else:
                sys.stdout.write("Detected: None")
            sys.stdout.flush()
            
            # 2. Check dmesg for crashes
            dmesg_out = subprocess.run(["dmesg"], capture_output=True, text=True).stdout
            lines = dmesg_out.splitlines()[-30:]
            recent_timestamp = last_dmesg_ts
            for line in lines:
                match_ts = re.search(r"^\[\s*([\d\.]+)\]", line)
                if match_ts:
                    ts = float(match_ts.group(1))
                    if ts > last_dmesg_ts:
                        recent_timestamp = max(recent_timestamp, ts)
                        if "probe with driver nintendo failed" in line or "error -32" in line or "error -71" in line:
                            print(f"\n\n\033[91m[CRASH DETECTED] {line}\033[0m")
                            print("\033[93mThe kernel killed the connection! Handshake failed.\033[0m")
                            print("Change to X-Mode or apply a workaround from the main menu.\n")
            
            last_dmesg_ts = recent_timestamp
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nReturning to menu...")
        time.sleep(1)

def main():
    if os.name == 'nt':
        print("This script is designed to run on the Raspberry Pi (Linux).")
        sys.exit(1)
        
    while True:
        status = get_workaround_status()
        q_stat = "[ACTIVE]" if status['quirk'] else "[NOT APPLIED]"
        b_stat = "[ACTIVE]" if status['blacklist'] else "[NOT APPLIED]"
        
        print_header()
        print("1) Live Monitor (Watch USB IDs, drivers, and crashes in real-time)")
        print("2) View Recent Kernel Logs (dmesg)")
        print(f"3) Apply Workaround: Add USBHID Quirk to Boot Cmdline {q_stat}")
        print(f"4) Apply Workaround: Blacklist 'hid_nintendo' Driver {b_stat}")
        print("5) Undo Workaround: Remove USBHID Quirk from Boot Cmdline")
        print("6) Undo Workaround: Delete 'hid_nintendo' Blacklist")
        print("7) Exit")
        
        choice = input("\nSelect an option (1-7): ").strip()
        
        if choice == '1':
            live_monitor()
        elif choice == '2':
            check_dmesg_crashes()
        elif choice == '3':
            apply_cmdline_quirk()
        elif choice == '4':
            apply_blacklist()
        elif choice == '5':
            remove_cmdline_quirk()
        elif choice == '6':
            remove_blacklist()
        elif choice == '7':
            clear_screen()
            break
        else:
            print("Invalid choice.")
            time.sleep(1)

if __name__ == "__main__":
    main()
