import socket
import subprocess
import time
import datetime
import re
import os
import sys
import ctypes

# Enable ANSI escape codes on Windows for \033 to work
if os.name == 'nt':
    os.system("")

PORT = 3240

def get_timestamp():
    """Returns a simple date and time in [YYYY-MM-DD HH:MM] format."""
    now = datetime.datetime.now()
    return f"[{now.strftime('%Y-%m-%d %H:%M')}]"

# Known 8BitDo Hardware IDs
HWID_MAP = {
    "2dc8:3105": ("D-Mode (Adapter)",   "Hold [-] + [Left]"),
    "2dc8:3107": ("D-Mode (Native BT)", "Native [-] + [B]"),
    "2dc8:3106": ("X-Mode (Native BT)", "Native [-] + [X]"),
    "057e:2009": ("S-Mode (Switch)",    "Hold [-] + [L Bumper]"),
    "045e:028e": ("X-Mode (Adapter)",   "Hold [-] + [Up]"),
    "045e:02d1": ("X-Mode (XOne)",      "Native USB"),
    "054c:05c4": ("D-Mode (PS4)",       "Hold [-] + [Right]"),
    "054c:0ce6": ("D-Mode (PS5)",       "Hold [-] + [Down]")
}

def print_supported_devices():
    """Prints a concise ASCII table of supported controllers and their combos."""
    print("\n" + "=" * 62)
    print(f"| {'Target ID':<9} | {'Controller Mode':<17} | {'Button Combo (Hold 3s)':<26} |")
    print("=" * 62)
    
    for hwid, (mode, combo) in HWID_MAP.items():
        print(f"| {hwid:<9} | {mode:<17} | {combo:<26} |")
    print("=" * 62 + "\n")

last_action_id = None

def print_log(message, action_id=None):
    """Prints a message with a timestamp. Overwrites the previous line if the action_id matches."""
    global last_action_id
    
    # If no explicit action_id is provided, use the message itself without numbers as the template
    if not action_id:
        action_id = re.sub(r'\d+', '', message)
        
    # Clear any active countdown/status line first
    sys.stdout.write("\r\033[K")
        
    if action_id == last_action_id and last_action_id is not None:
        # Move cursor up one line (\033[1A), clear the line (\033[K), and overwrite
        sys.stdout.write(f"\033[1A\033[K{get_timestamp()} {message}\n")
    else:
        # Print normally on a new line
        sys.stdout.write(f"{get_timestamp()} {message}\n")
        
    sys.stdout.flush()
    last_action_id = action_id

def ensure_joy_cpl_running():
    """Checks if the Game Controllers (joy.cpl) window is open, and launches it if not."""
    # FindWindowW checks for the window title. 
    # "Game Controllers" is the standard title for joy.cpl on English Windows.
    if ctypes.windll.user32.FindWindowW(None, "Game Controllers") == 0:
        print_log("joy.cpl (Game Controllers) not detected. Launching...")
        try:
            os.startfile("joy.cpl")
        except Exception as e:
            print_log(f"Failed to launch joy.cpl: {e}")

def get_local_subnets():
    """Returns a list of potential subnets to scan."""
    subnets = []
    try:
        # Get the primary local IP address without needing internet access
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            local_ip = s.getsockname()[0]
        
        parts = local_ip.split('.')
        if len(parts) == 4 and not local_ip.startswith("127."):
            subnets.append(".".join(parts[:-1]) + ".")
    except Exception:
        pass
        
    # Add common home subnets as fallback if they aren't already there
    for default in ["192.168.0.", "192.168.1.", "192.168.7."]:
        if default not in subnets:
            subnets.append(default)
    return subnets

def find_usbip_server(last_ip=None):
    """Scans subnets for port 3240. Tries last_ip first if provided."""
    # 0. Try last_ip
    if last_ip:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            if s.connect_ex((last_ip, PORT)) == 0:
                return last_ip

    # 1. Try common hostnames
    for host in ["raspberrypi.local", "raspberrypi", "pi-zero.local", "8bitdo-server.local"]:
        try:
            ip = socket.gethostbyname(host)
            print_log(f"Resolved {host} to {ip}. Checking port {PORT}...", action_id="scan")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                if s.connect_ex((ip, PORT)) == 0:
                    return ip
        except socket.gaierror:
            continue

    # 2. Scan subnets
    potential_subnets = get_local_subnets()
    for subnet in potential_subnets:
        print_log(f"Scanning subnet {subnet}0/24...", action_id="scan")
        for i in range(1, 255):
            ip = f"{subnet}{i}"
            if ip == last_ip: continue
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1) # Slightly slower but more reliable scan
                if s.connect_ex((ip, PORT)) == 0:
                    return ip
    return None

def detect_mode(description):
    """Detects the controller mode and returns (mode, is_likely_controller)."""
    desc_lower = description.lower()
    
    # 1. Check exact HWIDs first
    for hwid, mode_info in HWID_MAP.items():
        mode_name = mode_info[0]
        if hwid in desc_lower:
            return mode_name, True
            
    # 2. Generic fallback checks
    is_likely_controller = False
    mode = "Unknown"
    
    if "8bitdo" in desc_lower or "controller" in desc_lower or "gamepad" in desc_lower or "joystick" in desc_lower or "2dc8:" in desc_lower:
        is_likely_controller = True
        if "switch" in desc_lower: mode = "S-Mode (Switch)"
        elif "xbox" in desc_lower or "x-input" in desc_lower or "xinput" in desc_lower: mode = "X-Mode (Xbox)"
        elif "dualshock" in desc_lower or "sony" in desc_lower or "playstation" in desc_lower: mode = "D-Mode (PS)"
        elif "2dc8:" in desc_lower or "8bitdo" in desc_lower: mode = "8BitDo Device"
        else: mode = "Unknown Controller"
    elif "hub" in desc_lower or "root hub" in desc_lower:
        mode = "USB Hub"
    elif "adapter" in desc_lower or "receiver" in desc_lower:
        mode = "Adapter/Receiver"

    return mode, is_likely_controller

last_seen_hwids = None

def list_devices(server_ip):
    """Lists available devices on the usbip server and returns (devices, all_hwids)."""
    try:
        # Increased timeout for usbip list -r
        result = subprocess.run(["usbip", "list", "-r", server_ip], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            if result.stderr:
                print_log(f"USBIP Error: {result.stderr.strip()}")
            return None, [] # Signal failure vs empty list
            
        lines = result.stdout.splitlines()
        devices = []
        all_hwids = []
        
        for line in lines:
            # Pattern 1: Indented busid: description (HWID)
            match = re.search(r"^\s+([0-9a-fA-F.-]+)\s*:\s*(.*)", line)
            if match:
                busid = match.group(1).strip()
                description = match.group(2).strip()
                
                if busid == server_ip or description.startswith("/sys/"):
                    continue
                    
                match_id = re.search(r"\(([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\)", description)
                if match_id:
                    all_hwids.append(match_id.group(1).lower())
                
                mode, is_controller = detect_mode(description)
                devices.append((busid, description, mode, is_controller))
            else:
                # Pattern 2: Sometimes it's "busid busid (HWID)"
                match = re.search(r"busid\s+([0-9a-fA-F.-]+)\s+\((.*)\)", line)
                if match:
                    busid = match.group(1).strip()
                    description = match.group(2).strip()
                    
                    match_id = re.search(r"\(([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\)", description)
                    if match_id:
                        all_hwids.append(match_id.group(1).lower())
                        
                    mode, is_controller = detect_mode(description)
                    devices.append((busid, description, mode, is_controller))

        return devices, all_hwids
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print_log(f"Error listing devices on {server_ip}: {e}")
        return None, []

def attach_device(server_ip, busid, description, mode):
    """Attaches a device via usbip."""
    print_log(f"Attempting to attach {busid} ({description}) [Mode: {mode}] from {server_ip}")
    try:
        subprocess.run(["usbip", "attach", "-r", server_ip, "-b", busid], check=True, timeout=10)
        print_log(f"Successfully attached {busid}")
    except Exception as e:
        print_log(f"Failed to attach {busid}: {e}")

def list_local_attachments():
    """Lists locally attached usbip devices and returns a mapping of (server_ip, busid) -> description."""
    try:
        # Use shell=True for better output handling on Windows if needed, but subprocess.run is usually fine
        result = subprocess.run(["usbip", "port"], capture_output=True, text=True, check=True, timeout=5)
        attachments = {}
        lines = result.stdout.splitlines()
        
        # Example output:
        # Port 01: device in use at Full Speed(12Mbps)
        #          8BitDo : unknown product (2dc8:3107)
        #            -> usbip://192.168.0.46:3240/1-1.4
        
        current_port = None
        current_desc = "Unknown Device"
        
        for line in lines:
            # Port header
            if line.startswith("Port"):
                current_port = line.split(":")[0].strip()
                current_desc = "Unknown Device"
                continue
                
            # Description line (usually the first indented line after Port)
            if current_port and re.search(r"^\s{2,}\S+", line) and "->" not in line:
                current_desc = line.strip()
            
            # Connection line
            conn_match = re.search(r"->\s+usbip://([0-9.]+):\d+/([0-9a-fA-F.-]+)", line)
            if conn_match:
                ip = conn_match.group(1)
                busid = conn_match.group(2)
                attachments[(ip, busid)] = current_desc
                current_port = None # Reset for next port
                
        return attachments
    except Exception as e:
        print_log(f"Error checking local attachments: {e}")
        return {}

def is_admin():
    """Check if script is running with elevated privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def main():
    if not is_admin():
        print_log("WARNING: Script is NOT running as Administrator. USBIP attach will likely fail.")
    
    # Allow manual IP override via command line
    manual_ip = sys.argv[1] if len(sys.argv) > 1 else None
    server_ip = manual_ip
    last_found_ip = manual_ip
    
    print_log("USBIP Connect Client started. Press Ctrl+C to stop.")
    print_supported_devices()
    
    if manual_ip:
        print_log(f"Targeting specific server: {manual_ip}")
    
    try:
        while True:
            ensure_joy_cpl_running()
            
            if not server_ip:
                print_log("Searching for usbipd server on LAN...", action_id="scan")
                server_ip = find_usbip_server(last_found_ip)
                if server_ip:
                    print_log(f"Found usbipd server at {server_ip}")
                    last_found_ip = server_ip
                else:
                    print_log("Could not find usbipd server. Retrying in 10s.", action_id="scan")
                    time.sleep(10)
                    continue
            
            # 1. Get local attachments
            attached_map = list_local_attachments()
            has_local_attachments = any(ip == server_ip for (ip, _) in attached_map.keys())
            
            # 2. Get available devices on the server
            devices, all_hwids = list_devices(server_ip)
            
            if devices is None: # Command failed (timeout or error)
                if not has_local_attachments:
                    print_log(f"Server {server_ip} unresponsive. Re-scanning...", action_id="scan")
                    server_ip = None
                else:
                    print_log(f"Server {server_ip} unresponsive, but devices are still attached. Keeping connection.")
            elif not devices: # Command succeeded but list is empty
                # We have no exportable devices, but the server is still responding.
                # Do not drop the IP, just silently wait for devices to be exported.
                pass
            else:
                # We have devices!
                for busid, description, mode, is_controller in devices:
                    if is_controller and (server_ip, busid) not in attached_map:
                        attach_device(server_ip, busid, description, mode)
            
            # 3. Status reporting
            final_attached = list_local_attachments()
            status_parts = []
            server_has_attachments = False
            for (ip, busid), desc in final_attached.items():
                if ip == server_ip:
                    server_has_attachments = True
                    mode, _ = detect_mode(desc)
                    # Shorten mode name (e.g., "X-Mode (Native BT)" -> "X-Mode")
                    short_mode = mode.split()[0]
                    status_parts.append(f"{busid} ({short_mode})")
                    
                    match_id = re.search(r"\(([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\)", desc)
                    if match_id:
                        hwid = match_id.group(1).lower()
                        if hwid not in all_hwids:
                            all_hwids.append(hwid)
            
            # Deduplicate IDs for a cleaner display
            unique_hwids = sorted(list(set(all_hwids))) if 'all_hwids' in locals() and all_hwids else []
            
            status_str = " | ".join(status_parts) if status_parts else "None"
            server_label = server_ip if server_ip else "None"
            device_str = ", ".join(unique_hwids) if unique_hwids else "None"
            
            for remaining in range(10, 0, -1):
                # Omit the timestamp here to save space and prevent terminal wrapping!
                msg = f"Server IDs: [{device_str}] | Target: {server_label} | Connected: {status_str} | Next in {remaining}s"
                sys.stdout.write(f"\r\033[K{msg}")
                sys.stdout.flush()
                time.sleep(1)
    except KeyboardInterrupt:
        print_log("Exiting USBIP Connect Client...")
        sys.exit(0)

if __name__ == "__main__":
    main()
