import subprocess
import sys
import re
import ctypes
import socket
import time
import os

# Known 8BitDo Hardware IDs (Native and Emulated modes)
HWID_MAP = {
    "2dc8": "Native",
    "057e:2009": "Switch",
    "045e:028e": "X-Input"
}
TARGET_HWIDS = list(HWID_MAP.keys())

POLL_INTERVAL = 60  # Seconds between checks (1 minute)
USBIP_PORT = 3240

IS_WINDOWS = sys.platform == "win32"
USBIP_CMD = "usbipd" if IS_WINDOWS else "usbip"

def get_timestamp():
    """Returns a formatted timestamp string [YYYY-MM-DD HH:MM:SS]."""
    return time.strftime("[%Y-%m-%d %H:%M:%S]")

def log(msg, end='\n', flush=False):
    """Prints a message with a timestamp prefix."""
    print(f"{get_timestamp()} {msg}", end=end, flush=flush)

def get_ip_address():
    """Get the primary local IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "Unknown"

def get_connected_clients():
    """Returns a list of unique client IP addresses connected to the USBIP port."""
    clients = set()
    try:
        # Run netstat to find established connections on the USBIP port
        output = subprocess.run(["netstat", "-an"], capture_output=True, text=True).stdout
        # Flexible regex for both Windows (TCP) and Linux (tcp)
        pattern = re.compile(rf":{USBIP_PORT}\s+([\d\.]+):\d+\s+ESTABLISHED", re.IGNORECASE)
        matches = pattern.findall(output)
        for ip in matches:
            if ip != "0.0.0.0" and ip != "127.0.0.1":
                clients.add(ip)
    except Exception:
        pass
    return sorted(list(clients))

def is_admin():
    """Check if script is running with elevated privileges on Windows or root on Linux."""
    try:
        # Windows check
        return ctypes.windll.shell32.IsUserAnAdmin()
    except AttributeError:
        # Linux/Unix check - windll doesn't exist on non-Windows
        return os.geteuid() == 0

def run_command(command, exit_on_fail=True, silent_fail=False):
    """Executes a command and returns stdout. Gracefully handles failures if requested."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout
    except FileNotFoundError:
        if not silent_fail:
            log(f"Error: Command '{command[0]}' not found.")
        if exit_on_fail: sys.exit(1)
        return None
    except subprocess.CalledProcessError as e:
        if not silent_fail:
            log(f"Error running command {' '.join(command)}: {e.stderr}")
        if exit_on_fail: sys.exit(1)
        return None

def get_8bitdo_devices():
    """Returns a list of 8BitDo devices found on the system."""
    if IS_WINDOWS:
        output = run_command([USBIP_CMD, "list"], exit_on_fail=False, silent_fail=True)
    else:
        output = run_command([USBIP_CMD, "list", "-l"], exit_on_fail=False, silent_fail=True)
        
    if not output:
        return []

    bitdo_devs = []
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if IS_WINDOWS:
            match = re.search(r"^\s*([\d-]+)\s+([a-fA-F\d]{4}:[a-fA-F\d]{4})", line)
        else:
            # Match lines like: " - busid 1-1.2 (046d:c52b)"
            match = re.search(r"busid\s+([\d\-\.]+)\s+\(([a-fA-F\d]{4}:[a-fA-F\d]{4})\)", line)
            
        if match:
            busid = match.group(1)
            hwid_raw = match.group(2).lower()
            
            # Identify the mode
            mode = "Unknown"
            is_match = False
            for target_id, target_name in HWID_MAP.items():
                if target_id.lower() in hwid_raw:
                    mode = target_name
                    is_match = True
                    break
            
            if not is_match:
                # Check current line or next line (Linux) for "8bitdo"
                search_text = line.lower()
                if not IS_WINDOWS and i + 1 < len(lines):
                    search_text += " " + lines[i+1].lower()
                
                if "8bitdo" in search_text:
                    mode = "Native"
                    is_match = True
            
            if is_match:
                if IS_WINDOWS:
                    status_line = line.strip()
                else:
                    # Check if bound to usbip-host
                    is_bound = os.path.exists(f"/sys/bus/usb/drivers/usbip-host/{busid}")
                    status_line = "Shared" if is_bound else "Not shared"
                
                bitdo_devs.append({
                    "busid": busid, 
                    "hwid": hwid_raw, 
                    "mode": mode,
                    "line": status_line
                })
    return bitdo_devs

def bind_8bitdo(devices):
    if not devices:
        return
    for dev in devices:
        if "Not shared" in dev['line']:
            ts = get_timestamp()
            print(f"{ts}   > Binding {dev['busid']} ({dev['hwid']} - {dev['mode']})... ", end='', flush=True)
            if IS_WINDOWS:
                # Use --force for more reliable takeover from Windows HID driver
                cmd = [USBIP_CMD, "bind", "--force", "--busid", dev['busid']]
            else:
                cmd = [USBIP_CMD, "bind", "-b", dev['busid']]
                
            result = run_command(cmd, exit_on_fail=False, silent_fail=True)
            if result is not None:
                print("Successfully bound.")
            else:
                print("Failed.")

def main():
    if sys.platform not in ["win32", "linux"]:
        log(f"Unsupported platform: {sys.platform}")
        sys.exit(1)
    
    if not is_admin():
        system = "Administrator" if sys.platform == "win32" else "root"
        log(f"This script must be run as {system}.")
        sys.exit(1)

    server_ip = get_ip_address()
    log("--- USBIP 8BitDo Manager (v2.0) ---")
    log(f"Server IP Address: {server_ip}")
    log("-----------------------------------")
    
    if not IS_WINDOWS:
        log("Ensuring kernel modules are loaded and usbipd daemon is running...")
        run_command(["modprobe", "usbip-core"], exit_on_fail=False, silent_fail=True)
        run_command(["modprobe", "usbip-host"], exit_on_fail=False, silent_fail=True)
        run_command(["usbipd", "-D"], exit_on_fail=False, silent_fail=True)

    log("Initial cleanup: Unbinding ALL currently shared USB devices...")
    if IS_WINDOWS:
        run_command([USBIP_CMD, "unbind", "--all"], exit_on_fail=False, silent_fail=True)
    else:
        # On Linux, manual unbind of all currently bound devices
        try:
            usbip_host_path = "/sys/bus/usb/drivers/usbip-host/"
            if os.path.exists(usbip_host_path):
                bound_devs = os.listdir(usbip_host_path)
                for busid in bound_devs:
                    # Simple check for valid busid format (e.g., 1-1 or 1-1.2)
                    if re.match(r"^\d+-\d+(\.\d+)*$", busid):
                        run_command([USBIP_CMD, "unbind", "-b", busid], exit_on_fail=False, silent_fail=True)
        except Exception:
            pass

    log(f"Entering polling loop (Interval: {POLL_INTERVAL}s).")
    log("The script will automatically bind any 8BitDo devices found.")
    log("Press Ctrl+C to exit.\n")

    try:
        while True:
            bitdo_devs = get_8bitdo_devices()
            
            # Calculate counts
            waiting_count = sum(1 for d in bitdo_devs if "Shared" in d['line'])
            in_use_count = sum(1 for d in bitdo_devs if "Attached" in d['line'])
            not_shared_devs = [d for d in bitdo_devs if "Not shared" in d['line']]
            
            # Mode summary (e.g., "1 Switch, 1 X-Input")
            modes_seen = {}
            for d in bitdo_devs:
                modes_seen[d['mode']] = modes_seen.get(d['mode'], 0) + 1
            mode_str = ", ".join([f"{count} {m}" for m, count in modes_seen.items()]) if modes_seen else "None"

            # Client info
            clients = get_connected_clients()
            client_info = f" | Clients: {', '.join(clients)}" if clients else " | No clients"

            if not_shared_devs:
                # Clear heartbeat line
                print("\r" + " " * 120 + "\r", end='', flush=True)
                log(f"Detected {len(not_shared_devs)} unbound device(s) in {mode_str} mode(s).")
                bind_8bitdo(not_shared_devs)
            else:
                # Heartbeat message
                msg = f"{get_timestamp()} Polling: {waiting_count} Waiting, {in_use_count} In-Use ({mode_str}){client_info}"
                print("\r" + msg.ljust(120), end='', flush=True)
            
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print(f"\n\n{get_timestamp()} Exiting... Devices remain bound in usbipd.")

if __name__ == "__main__":
    main()
