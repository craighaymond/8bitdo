import socket
import subprocess
import time
import datetime
import re
import os
import sys
import ctypes

PORT = 3240

def get_timestamp():
    """Returns a simple date and time in [YYYY-MM-DD HH:MM] format."""
    now = datetime.datetime.now()
    return f"[{now.strftime('%Y-%m-%d %H:%M')}]"

def print_log(message):
    """Prints a message with a timestamp and flushes stdout."""
    print(f"{get_timestamp()} {message}")
    sys.stdout.flush()

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
            print_log(f"Resolved {host} to {ip}. Checking port {PORT}...")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                if s.connect_ex((ip, PORT)) == 0:
                    return ip
        except socket.gaierror:
            continue

    # 2. Scan subnets
    potential_subnets = get_local_subnets()
    for subnet in potential_subnets:
        print_log(f"Scanning subnet {subnet}0/24...")
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
    is_likely_controller = False
    mode = "Unknown"
    
    # Check for specific Controller VID:PIDs
    if "057e:2009" in description:
        mode = "S-Mode (Switch)"
        is_likely_controller = True
    elif "045e:028e" in description or "045e:02d1" in description:
        mode = "X-Mode (Xbox)"
        is_likely_controller = True
    elif "2dc8" in description:
        # 8BitDo VID
        mode = "D-Mode (8BitDo)"
        is_likely_controller = True
    elif "054c:05c4" in description or "054c:09cc" in description:
        mode = "D-Mode (PS4)"
        is_likely_controller = True
    elif "054c:0ce6" in description:
        mode = "D-Mode (PS5)"
        is_likely_controller = True
    
    # Fallback string matching
    if not is_likely_controller:
        desc_lower = description.lower()
        if "8bitdo" in desc_lower or "controller" in desc_lower or "gamepad" in desc_lower or "joystick" in desc_lower:
            is_likely_controller = True
            if "switch" in desc_lower: mode = "S-Mode (Switch)"
            elif "xbox" in desc_lower or "x-input" in desc_lower or "xinput" in desc_lower: mode = "X-Mode (Xbox)"
            elif "dualshock" in desc_lower or "sony" in desc_lower or "playstation" in desc_lower: mode = "D-Mode (PS)"
            elif "8bitdo" in desc_lower: mode = "8BitDo Device"
            else: mode = "Unknown Controller"
        elif "hub" in desc_lower or "root hub" in desc_lower:
            mode = "USB Hub"
            is_likely_controller = False
        elif "adapter" in desc_lower or "receiver" in desc_lower:
            mode = "Adapter/Receiver"
            is_likely_controller = False

    return mode, is_likely_controller

def list_devices(server_ip):
    """Lists available devices on the usbip server and returns (busid, description, mode, is_controller) tuples."""
    try:
        # Increased timeout for usbip list -r
        result = subprocess.run(["usbip", "list", "-r", server_ip], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            if result.stderr:
                print_log(f"USBIP Error: {result.stderr.strip()}")
            return None # Signal failure vs empty list
            
        lines = result.stdout.splitlines()
        devices = []
        for line in lines:
            # Match busid and description. 
            # Format usually: "      1-1.2: unknown vendor : unknown product (046d:c52b)"
            # Or: " - 192.168.0.46" (skip this)
            
            # Pattern 1: Indented busid: description (HWID)
            match = re.search(r"^\s+([0-9a-fA-F.-]+)\s*:\s*(.*)", line)
            if match:
                busid = match.group(1).strip()
                description = match.group(2).strip()
                
                # Skip the busid if it matches the server IP line (e.g. " - 192.168.0.1")
                if busid == server_ip or description.startswith("/sys/"):
                    continue
                
                mode, is_controller = detect_mode(description)
                devices.append((busid, description, mode, is_controller))
            else:
                # Pattern 2: Sometimes it's "busid busid (HWID)"
                match = re.search(r"busid\s+([0-9a-fA-F.-]+)\s+\((.*)\)", line)
                if match:
                    busid = match.group(1).strip()
                    description = match.group(2).strip()
                    mode, is_controller = detect_mode(description)
                    devices.append((busid, description, mode, is_controller))

        return devices
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print_log(f"Error listing devices on {server_ip}: {e}")
        return None

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
        result = subprocess.run(["usbip", "port"], capture_output=True, text=True, check=True, timeout=5)
        attachments = {}
        lines = result.stdout.splitlines()
        current_desc = "Unknown Device"
        
        for line in lines:
            # Look for the description line (indented, no '->', no 'Port' or 'Imported')
            if re.search(r"^\s{4,}\S+", line) and "->" not in line and "Port" not in line and "Imported" not in line:
                current_desc = line.strip()
            
            # Look for the connection line (e.g. "1-1.4 -> usbip://...")
            conn_match = re.search(r"([0-9a-fA-F.-]+)\s+->\s+usbip://([0-9.]+):\d+/([0-9a-fA-F.-]+)", line)
            if conn_match:
                ip = conn_match.group(2)
                busid = conn_match.group(3)
                attachments[(ip, busid)] = current_desc
                
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
    if manual_ip:
        print_log(f"Targeting specific server: {manual_ip}")
    
    try:
        while True:
            ensure_joy_cpl_running()
            
            if not server_ip:
                print_log("Searching for usbipd server on LAN...")
                server_ip = find_usbip_server(last_found_ip)
                if server_ip:
                    print_log(f"Found usbipd server at {server_ip}")
                    last_found_ip = server_ip
                else:
                    print_log("Could not find usbipd server. Retrying in 10s.")
                    time.sleep(10)
                    continue
            
            # 1. Get local attachments
            attached_map = list_local_attachments()
            has_local_attachments = any(ip == server_ip for (ip, _) in attached_map.keys())
            
            # 2. Get available devices on the server
            devices = list_devices(server_ip)
            
            if devices is None: # Command failed (timeout or error)
                if not has_local_attachments:
                    print_log(f"Server {server_ip} unresponsive. Re-scanning...")
                    server_ip = None
                else:
                    print_log(f"Server {server_ip} unresponsive, but devices are still attached. Keeping connection.")
            elif not devices: # Command succeeded but list is empty
                if not has_local_attachments:
                    if not manual_ip:
                        print_log(f"No exportable devices on {server_ip}. Re-scanning...")
                        server_ip = None
                    else:
                        print_log(f"Waiting for devices on {server_ip}...")
            else:
                # We have devices!
                for busid, description, mode, is_controller in devices:
                    if is_controller and (server_ip, busid) not in attached_map:
                        attach_device(server_ip, busid, description, mode)
            
            # 3. Status reporting
            final_attached = list_local_attachments()
            status_parts = []
            for (ip, busid), desc in final_attached.items():
                if ip == server_ip:
                    mode, _ = detect_mode(desc)
                    status_parts.append(f"{busid}: {mode}")
            
            status_str = " | ".join(status_parts) if status_parts else "None"
            server_label = server_ip if server_ip else "None"
            print_log(f"Status: Server {server_label} | Connected: {status_str}")
            
            time.sleep(10) # Reduced poll interval for better responsiveness
    except KeyboardInterrupt:
        print_log("Exiting USBIP Connect Client...")
        sys.exit(0)

if __name__ == "__main__":
    main()
