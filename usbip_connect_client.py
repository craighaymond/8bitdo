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

def get_local_subnet():
    """Returns the base subnet (e.g., '192.168.0.') for the current local IP."""
    try:
        # Get the primary local IP address
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        # Common subnets are /24
        parts = local_ip.split('.')
        return ".".join(parts[:-1]) + "."
    except Exception:
        return None

def find_usbip_server():
    """Scans the local subnet for port 3240."""
    subnet = get_local_subnet()
    if not subnet:
        return None
    
    # Iterate through potential host IDs (1 to 254)
    # 0.05s timeout is generally safe for local LAN
    for i in range(1, 255):
        ip = f"{subnet}{i}"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.05)
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
        # 8BitDo VID; check if it's an adapter or controller
        if "Controller" in description or "Gamepad" in description:
            mode = "D-Mode (8BitDo)"
            is_likely_controller = True
        else:
            mode = "8BitDo Adapter"
            is_likely_controller = False
    elif "054c:05c4" in description or "054c:09cc" in description:
        mode = "D-Mode (PS4)"
        is_likely_controller = True
    elif "054c:0ce6" in description:
        mode = "D-Mode (PS5)"
        is_likely_controller = True
    
    # Fallback string matching
    if not is_likely_controller:
        desc_lower = description.lower()
        if "controller" in desc_lower or "gamepad" in desc_lower:
            is_likely_controller = True
            if "switch" in desc_lower: mode = "S-Mode (Switch)"
            elif "xbox" in desc_lower or "x-input" in desc_lower: mode = "X-Mode (Xbox)"
            elif "dualshock" in desc_lower or "sony" in desc_lower: mode = "D-Mode (PS)"
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
        result = subprocess.run(["usbip", "list", "-r", server_ip], capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        devices = []
        for line in lines:
            match = re.search(r"^\s+([0-9a-fA-F.-]+)\s+:\s+(.*)", line)
            if match:
                busid = match.group(1).strip()
                description = match.group(2).strip()
                mode, is_controller = detect_mode(description)
                devices.append((busid, description, mode, is_controller))
        return devices
    except subprocess.CalledProcessError as e:
        print_log(f"Error listing devices: {e}")
        return []

def attach_device(server_ip, busid, description, mode):
    """Attaches a device via usbip."""
    print_log(f"Attempting to attach {busid} ({description}) [Mode: {mode}] from {server_ip}")
    try:
        subprocess.run(["usbip", "attach", "-r", server_ip, "-b", busid], check=True)
        print_log(f"Successfully attached {busid} ({description}) [Mode: {mode}]")
    except subprocess.CalledProcessError as e:
        print_log(f"Failed to attach {busid}: {e}")

def list_local_attachments():
    """Lists locally attached usbip devices and returns a mapping of (server_ip, busid) -> description."""
    try:
        result = subprocess.run(["usbip", "port"], capture_output=True, text=True, check=True)
        attachments = {}
        lines = result.stdout.splitlines()
        current_desc = "Unknown Device"
        
        for line in lines:
            # Look for the description line
            desc_match = re.search(r"^\s{9,}(.*)", line)
            if desc_match and "->" not in line:
                current_desc = desc_match.group(1).strip()
            
            # Look for the connection line
            conn_match = re.search(r"-> usbip://([0-9.]+):\d+/([0-9a-fA-F.-]+)", line)
            if conn_match:
                ip = conn_match.group(1)
                busid = conn_match.group(2)
                attachments[(ip, busid)] = current_desc
                
        return attachments
    except subprocess.CalledProcessError as e:
        print_log(f"Error checking local attachments: {e}")
        return {}

def main():
    server_ip = None
    
    print_log("USBIP Connect Client started. Press Ctrl+C to stop.")
    
    try:
        while True:
            # Check for joy.cpl at each poll interval
            ensure_joy_cpl_running()
            
            if not server_ip:
                print_log("Searching for usbipd server on LAN...")
                server_ip = find_usbip_server()
                if server_ip:
                    print_log(f"Found usbipd server at {server_ip}")
                else:
                    print_log("Could not find usbipd server. Retrying in 60s.")
            
            if server_ip:
                # 1. Get local attachments with descriptions
                attached_map = list_local_attachments()
                
                # 2. Get available devices on the server
                devices = list_devices(server_ip)
                
                if not devices:
                    if find_usbip_server() != server_ip:
                        print_log(f"Server {server_ip} lost.")
                        server_ip = None
                else:
                    for busid, description, mode, is_controller in devices:
                        # ONLY attach if it looks like a controller
                        if is_controller and (server_ip, busid) not in attached_map:
                            attach_device(server_ip, busid, description, mode)
                
                # 3. Build status message with modes
                final_attached = list_local_attachments()
                status_parts = []
                for (ip, busid), desc in final_attached.items():
                    if ip == server_ip:
                        mode, _ = detect_mode(desc)
                        status_parts.append(f"{busid}: {mode}")
                
                status_str = " | ".join(status_parts) if status_parts else "None"
                print_log(f"Status: Server {server_ip} | Connected: {status_str}")
            
            time.sleep(30)
    except KeyboardInterrupt:
        print_log("Exiting USBIP Connect Client...")
        sys.exit(0)

if __name__ == "__main__":
    main()
