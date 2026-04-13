import subprocess
import sys
import re
import ctypes
import socket
import time

# Known 8BitDo Hardware IDs (Native and Emulated modes)
HWID_MAP = {
    "2dc8": "Native",
    "057e:2009": "Switch",
    "045e:028e": "X-Input"
}
TARGET_HWIDS = list(HWID_MAP.keys())

POLL_INTERVAL = 60  # Seconds between checks (1 minute)
USBIP_PORT = 3240

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
        pattern = rf"TCP\s+\S+:{USBIP_PORT}\s+([\d\.]+):\d+\s+ESTABLISHED"
        matches = re.findall(pattern, output)
        for ip in matches:
            if ip != "0.0.0.0" and ip != "127.0.0.1":
                clients.add(ip)
    except Exception:
        pass
    return sorted(list(clients))

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

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
    # Use silent_fail=True in the loop to keep script alive if usbipd is busy
    output = run_command(["usbipd", "list"], exit_on_fail=False, silent_fail=True)
    if not output:
        return []

    bitdo_devs = []
    lines = output.splitlines()
    for line in lines:
        match = re.search(r"^\s*([\d-]+)\s+([a-fA-F\d]{4}:[a-fA-F\d]{4})", line)
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
            
            if not is_match and "8bitdo" in line.lower():
                mode = "Native"
                is_match = True
            
            if is_match:
                bitdo_devs.append({
                    "busid": busid, 
                    "hwid": hwid_raw, 
                    "mode": mode,
                    "line": line.strip()
                })
    return bitdo_devs

def bind_8bitdo(devices):
    if not devices:
        return
    for dev in devices:
        if "Not shared" in dev['line']:
            ts = get_timestamp()
            # Use --force for more reliable takeover from Windows HID driver
            print(f"{ts}   > Binding {dev['busid']} ({dev['hwid']} - {dev['mode']})... ", end='', flush=True)
            result = run_command(["usbipd", "bind", "--force", "--busid", dev['busid']], exit_on_fail=False, silent_fail=True)
            if result is not None:
                print("Successfully bound.")
            else:
                print("Failed.")

def main():
    if not is_admin():
        print(f"{get_timestamp()} This script must be run as Administrator.")
        sys.exit(1)

    server_ip = get_ip_address()
    log("--- USBIP 8BitDo Manager (v2.0) ---")
    log(f"Server IP Address: {server_ip}")
    log("-----------------------------------")
    
    log("Initial cleanup: Unbinding ALL currently shared USB devices...")
    run_command(["usbipd", "unbind", "--all"], exit_on_fail=False, silent_fail=True)

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
                print(" " * 120, end='\r')
                log(f"Detected {len(not_shared_devs)} unbound device(s) in {mode_str} mode(s).")
                bind_8bitdo(not_shared_devs)
            else:
                # Heartbeat message
                msg = f"{get_timestamp()} Polling: {waiting_count} Waiting, {in_use_count} In-Use ({mode_str}){client_info}"
                print(msg.ljust(120), end='\r', flush=True)
            
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print(f"\n\n{get_timestamp()} Exiting... Devices remain bound in usbipd.")

if __name__ == "__main__":
    main()
