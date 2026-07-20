import subprocess
import sys
import re
import ctypes
import socket
import time
import os
import threading

# Known 8BitDo Hardware IDs (Native and Emulated modes)
HWID_MAP = {
    "2dc8:3105": "8BitDo Receiver (Searching)",
    "2dc8:3107": "8BitDo Ultimate (D-Mode)",
    "2dc8:3106": "8BitDo Ultimate (X-Mode)",
    "057e:2009": "Switch Pro (S-Mode)",
    "045e:028e": "Xbox 360 (X-Input)",
    "045e:02d1": "Xbox One",
    "054c:05c4": "PS4 (D-Mode)",
    "054c:0ce6": "PS5 (D-Mode)",
    "2dc8": "8BitDo Device"
}
TARGET_HWIDS = list(HWID_MAP.keys())

POLL_INTERVAL = 0.5  # Seconds between checks (0.5 seconds for aggressive binding)
USBIP_PORT = 3240
DEBUG = "--debug" in sys.argv or "--diagnostics" in sys.argv

IS_WINDOWS = sys.platform == "win32"
USBIP_CMD = "usbipd" if IS_WINDOWS else "usbip"

def get_timestamp():
    """Returns a formatted timestamp string [YYYY-MM-DD HH:MM:SS]."""
    return time.strftime("[%Y-%m-%d %H:%M:%S]")

def log(msg, end='\n', flush=False):
    """Prints a message with a timestamp prefix."""
    print(f"{get_timestamp()} {msg}", end=end, flush=flush)

def nintendo_guardian_thread():
    """Runs at 20fps in the background to violently unbind the nintendo driver before it can crash S-Mode adapters."""
    while True:
        try:
            nintendo_dir = "/sys/bus/hid/drivers/nintendo"
            if os.path.exists(nintendo_dir):
                for item in os.listdir(nintendo_dir):
                    if ":" in item:
                        unbind_path = os.path.join(nintendo_dir, "unbind")
                        try:
                            with open(unbind_path, "w") as f:
                                f.write(item)
                        except Exception:
                            pass
        except Exception:
            pass
        time.sleep(0.05)

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
            return "127.0.0.1"

def get_connected_clients():
    """Returns a list of unique client IP addresses connected to the USBIP port."""
    clients = set()
    try:
        # Try netstat first
        try:
            output = subprocess.run(["netstat", "-an"], capture_output=True, text=True).stdout
        except FileNotFoundError:
            # Fallback to ss
            output = subprocess.run(["ss", "-H", "-n", "-t", "state", "established", f"( sport = :{USBIP_PORT} )"], capture_output=True, text=True).stdout
        
        # Flexible regex for both Windows (TCP) and Linux (tcp)
        # For netstat
        pattern = re.compile(rf":{USBIP_PORT}\s+([\d\.]+):\d+\s+ESTABLISHED", re.IGNORECASE)
        matches = pattern.findall(output)
        for ip in matches:
            if ip != "0.0.0.0" and ip != "127.0.0.1" and ip != "::1":
                clients.add(ip)
        
        # For ss output (if netstat failed or was different)
        if not clients:
            # ss output format: tcp ESTAB 0 0 192.168.0.46:3240 192.168.0.232:54321
            ss_pattern = re.compile(rf"\s+[\d\.]+:({USBIP_PORT})\s+([\d\.]+):\d+")
            ss_matches = ss_pattern.findall(output)
            for port, ip in ss_matches:
                if ip != "127.0.0.1" and ip != "::1":
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
        try:
            return os.geteuid() == 0
        except AttributeError:
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
            log(f"Error running command {' '.join(command)}: {e.stderr or e.stdout}")
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
    all_usb_ids = [] # Diagnostic
    lines = output.splitlines()
    for i, line in enumerate(lines):
        busid = None
        hwid_raw = None
        
        if IS_WINDOWS:
            match = re.search(r"^\s*([\d-]+)\s+([a-fA-F\d]{4}:[a-fA-F\d]{4})", line)
            if match:
                busid, hwid_raw = match.group(1), match.group(2).lower()
        else:
            # Linux patterns
            match = re.search(r"busid\s+([\d\-\.]+)\s+\(([a-fA-F\d]{4}:[a-fA-F\d]{4})\)", line)
            if not match:
                match = re.search(r"-\s+([\d\-\.]+):\s+.*\(([a-fA-F\d]{4}:[a-fA-F\d]{4})\)", line)
            if not match:
                match = re.search(r"^([\d\-\.]+):\s+.*\(([a-fA-F\d]{4}:[a-fA-F\d]{4})\)", line)
            
            if match:
                busid, hwid_raw = match.group(1), match.group(2).lower()
            
        if busid and hwid_raw:
            all_usb_ids.append(hwid_raw)
            # Identify the mode
            mode = "Unknown"
            is_ignored = False
            is_valid_controller = False
            
            for target_id, target_name in HWID_MAP.items():
                if target_id.lower() in hwid_raw:
                    mode = target_name
                    if "Ignored" in target_name:
                        is_ignored = True
                    else:
                        is_valid_controller = True
                    break
            
            # Fallback for generic 8bitdo string but ONLY if not already ignored
            if not is_ignored and not is_valid_controller:
                search_text = line.lower()
                if i + 1 < len(lines):
                    search_text += " " + lines[i+1].lower()
                
                if "8bitdo" in search_text:
                    mode = "8BitDo Device"
                    is_valid_controller = True
            
            if is_valid_controller and not is_ignored:
                if IS_WINDOWS:
                    status_line = line.strip()
                else:
                    is_bound = os.path.exists(f"/sys/bus/usb/drivers/usbip-host/{busid}")
                    if is_bound:
                        status_line = "Shared"
                        try:
                            with open(f"/sys/bus/usb/drivers/usbip-host/{busid}/usbip_status", "r") as f:
                                if f.read().strip() == "3":
                                    status_line = "Attached"
                        except Exception:
                            pass
                    else:
                        status_line = "Not shared"
                
                bitdo_devs.append({
                    "busid": busid, 
                    "hwid": hwid_raw, 
                    "mode": mode,
                    "line": status_line
                })
    
    # Diagnostic print if it changes
    global last_diagnostic_ids
    if 'last_diagnostic_ids' not in globals() or last_diagnostic_ids != all_usb_ids:
        log(f"All USB IDs seen on bus: {', '.join(all_usb_ids)}")
        last_diagnostic_ids = all_usb_ids

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
                # Attempt to manually unbind interfaces on Linux before binding to usbip-host
                try:
                    dev_path = f"/sys/bus/usb/devices/{dev['busid']}"
                    if os.path.exists(dev_path):
                        for iface_dir in os.listdir(dev_path):
                            if iface_dir.startswith(f"{dev['busid']}:"):
                                unbind_path = f"{dev_path}/{iface_dir}/driver/unbind"
                                if os.path.exists(unbind_path):
                                    try:
                                        with open(unbind_path, 'w') as f:
                                            f.write(iface_dir)
                                    except Exception:
                                        pass
                except Exception:
                    pass
                cmd = None
                
            if cmd:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    print("Successfully bound.")
                except subprocess.CalledProcessError as e:
                    error_msg = (e.stderr or e.stdout or "Unknown error").strip()
                    print(f"Failed: {error_msg}")
            else:
                # Linux manual sysfs bind (bypassing usbip binary which is broken on modern kernels)
                try:
                    busid = dev['busid']
                    match_busid_path = "/sys/bus/usb/drivers/usbip-host/match_busid"
                    bind_path = "/sys/bus/usb/drivers/usbip-host/bind"
                    
                    if os.path.exists(match_busid_path):
                        try:
                            with open(match_busid_path, 'w') as f:
                                f.write(f"add {busid}")
                        except Exception as e:
                            print(f"Failed to write match_busid: {e}")
                            
                    try:
                        with open(bind_path, 'w') as f:
                            f.write(busid)
                        print("Successfully bound.")
                    except Exception as e:
                        print(f"Failed to bind directly (sysfs): {e}")
                        
                        if DEBUG:
                            try:
                                drivers = os.listdir("/sys/bus/usb/drivers/")
                                print(f"   [Diagnostic] Available USB drivers: {', '.join(drivers)}")
                                dmesg_out = subprocess.run(["dmesg"], capture_output=True, text=True).stdout
                                dmesg_usbip = "\n".join([line for line in dmesg_out.splitlines() if "usbip" in line.lower()][-10:])
                                print(f"   [Diagnostic] dmesg (last 10 usbip lines):\n{dmesg_usbip}")
                            except Exception:
                                pass
                        
                        print(f"   > Falling back to 'usbip bind -b {busid}'...")
                        try:
                            result = subprocess.run([USBIP_CMD, "bind", "-b", busid], capture_output=True, text=True, check=True)
                            print("Successfully bound (fallback).")
                        except subprocess.CalledProcessError as err:
                            print(f"Fallback failed: {(err.stderr or err.stdout or 'Unknown error').strip()}")
                except Exception as e:
                    print(f"Failed: {e}")

def print_mode_shortcuts():
    """Prints the button shortcuts for changing 8BitDo controller modes."""
    log("-----------------------------------")
    log("8BitDo Controller Mode Shortcuts (Native Bluetooth):")
    log("  [S] Switch Mode:  Hold [Minus] + [Y] for 5s -> ID: 057e:2009")
    log("  [X] X-Input:      Hold [Minus] + [X] for 5s -> ID: 2dc8:3106")
    log("  [D] D-Input:      Hold [Minus] + [B] for 5s -> ID: 2dc8:3107")
    log("  [Idle] Searching: Baseline receiver state     -> ID: 2dc8:3105")
    log("  (Note: Hold until the controller vibrates)")
    log("-----------------------------------")
    log("8BitDo USB Wireless Adapter Shortcuts:")
    log("  [S] Switch Mode:  Hold [Minus] + [L Bumper] for 3s")
    log("  [X] X-Input:      Hold [Minus] + [Up] for 3s")
    log("  [D] D-Input:      Hold [Minus] + [Left] for 3s")
    log("  [Mac] macOS:      Hold [Minus] + [Right] for 3s")
    log("  [PS] PS Classic:  Hold [Minus] + [Down] for 3s")
    log("  [MD] MegaDrive:   Hold [Minus] + [Up] + [Left] for 3s")
    log("-----------------------------------")

last_dmesg_timestamp = 0.0

def check_kernel_crashes():
    global last_dmesg_timestamp
    if IS_WINDOWS:
        return
        
    try:
        out = subprocess.run(["dmesg"], capture_output=True, text=True).stdout
        lines = out.splitlines()[-50:] # Check last 50 lines
        
        crashed_id = None
        recent_timestamp = last_dmesg_timestamp
        
        for line in lines:
            # Parse timestamp: [ 1331.167083] 
            match_ts = re.search(r"^\[\s*([\d\.]+)\]", line)
            if not match_ts: continue
            
            ts = float(match_ts.group(1))
            if ts <= last_dmesg_timestamp:
                continue
                
            recent_timestamp = max(recent_timestamp, ts)
            
            # Detect USB device
            match_usb = re.search(r"idVendor=([a-fA-F0-9]{4}), idProduct=([a-fA-F0-9]{4})", line)
            if match_usb:
                vid, pid = match_usb.group(1).lower(), match_usb.group(2).lower()
                crashed_id = f"{vid}:{pid}"
                
            # Detect errors indicating the kernel rejected/crashed it
            if crashed_id and ("probe with driver nintendo failed" in line or "Failed handshake" in line or "error -32" in line or "error -71" in line):
                mode_name = HWID_MAP.get(crashed_id, "Unknown Mode")
                print("\n")
                log(f"\033[91m[CRITICAL KERNEL WARNING] The Linux kernel saw a valid controller (ID: {crashed_id} - {mode_name}) but its internal driver crashed and rejected it!\033[0m")
                log("\033[93mThe controller is being violently disconnected by the operating system.\033[0m")
                log("\033[92mSUGGESTION: Please put the controller into X-Mode (Hold [Minus] + [Up] for 3s) to bypass the crashing driver!\033[0m\n")
                last_dmesg_timestamp = ts
                crashed_id = None # Reset so we don't spam multiple times for the same block
                
        last_dmesg_timestamp = recent_timestamp
    except Exception:
        pass

def main():
    if sys.platform not in ["win32", "linux"]:
        log(f"Unsupported platform: {sys.platform}")
        sys.exit(1)
    
    if not is_admin():
        system = "Administrator" if sys.platform == "win32" else "root"
        log(f"This script must be run as {system}.")
        sys.exit(1)

    server_ip = get_ip_address()
    log("--- USBIP 8BitDo Manager (v2.2.3) ---")
    log(f"Server IP Address: {server_ip}")
    print_mode_shortcuts()
    
    # Start the Guardian thread to protect S-Mode
    if not IS_WINDOWS:
        threading.Thread(target=nintendo_guardian_thread, daemon=True).start()
    
    if IS_WINDOWS:
        log("Initial cleanup: Unbinding ALL currently shared USB devices...")
        run_command([USBIP_CMD, "unbind", "--all"], exit_on_fail=False, silent_fail=True)
    else:
        log("Initial cleanup (Linux): Ensuring usbip-host kernel module is loaded...")
        # Forcefully unbind everything first
        run_command(["usbip", "unbind", "--all"], exit_on_fail=False, silent_fail=True)
        run_command(["modprobe", "usbip-core"], exit_on_fail=False, silent_fail=True)
        run_command(["modprobe", "usbip-host"], exit_on_fail=False, silent_fail=True)
        
        # Diagnostic print of loaded usb modules
        if DEBUG:
            try:
                lsmod_out = subprocess.run(["lsmod"], capture_output=True, text=True).stdout
                usb_mods = [line.split()[0] for line in lsmod_out.splitlines() if "usb" in line or "vhci" in line]
                log(f"[Diagnostic] Loaded USB modules: {', '.join(usb_mods)}")
            except Exception:
                pass
            
        # Restart the daemon - Try common paths
        log("Killing any existing usbipd processes and clearing port 3240...")
        run_command(["pkill", "-9", "usbipd"], exit_on_fail=False, silent_fail=True)
        # Fallback: use fuser to kill anything on the usbip port if fuser is available
        run_command(["fuser", "-k", "3240/tcp"], exit_on_fail=False, silent_fail=True)
        time.sleep(1)
        
        log("Starting usbipd daemon...")
        daemon_started = False
        for cmd in ["usbipd", "/usr/sbin/usbipd", "/usr/lib/linux-tools/$(uname -r)/usbipd"]:
            # Evaluate $(uname -r) if needed
            if "$(uname -r)" in cmd:
                kernel_v = subprocess.run(["uname", "-r"], capture_output=True, text=True).stdout.strip()
                cmd = cmd.replace("$(uname -r)", kernel_v)
            
            res = run_command([cmd, "-D"], exit_on_fail=False, silent_fail=True)
            if res is not None:
                log(f"Daemon started successfully using: {cmd}")
                daemon_started = True
                break
        
        if not daemon_started:
            log("WARNING: Could not start usbipd daemon. Remote clients will not be able to connect.")

    log(f"Entering polling loop (Interval: {POLL_INTERVAL}s).")
    log("The script will automatically bind any 8BitDo devices found.")
    log("Press Ctrl+C to exit.\n")

    last_status_hash = None

    try:
        while True:
            bitdo_devs = get_8bitdo_devices()
            
            # Calculate counts
            waiting_count = sum(1 for d in bitdo_devs if "Shared" in d['line'])
            in_use_count = sum(1 for d in bitdo_devs if "Attached" in d['line'])
            not_shared_devs = [d for d in bitdo_devs if "Not shared" in d['line']]
            
            # Create a status hash to detect changes
            current_status_list = []
            for d in bitdo_devs:
                status = "Attached" if "Attached" in d['line'] else "Waiting" if "Shared" in d['line'] else "Not Shared"
                current_status_list.append(f"{d['busid']}:{d['hwid']}:{d['mode']}:{status}")
            
            clients = get_connected_clients()
            status_hash = hash(tuple(current_status_list) + tuple(clients))

            if status_hash != last_status_hash:
                # Clear heartbeat line
                print("\r" + " " * 120 + "\r", end='', flush=True)
                
                if not_shared_devs:
                    log(f"Detected {len(not_shared_devs)} unbound device(s).")
                    bind_8bitdo(not_shared_devs)
                    # Refresh devs after binding
                    bitdo_devs = get_8bitdo_devices()
                
                log("Current Controller Status:")
                if not bitdo_devs:
                    print("   [None]")
                for d in bitdo_devs:
                    status = "IN-USE (Attached)" if "Attached" in d['line'] else "READY (Waiting)" if "Shared" in d['line'] else "IDLE (Not shared)"
                    print(f"   - {d['busid']} ({d['hwid']}): {d['mode']} [{status}]")
                
                if clients:
                    print(f"   Connected Clients: {', '.join(clients)}")
                print("-" * 50)
                last_status_hash = status_hash

            # Heartbeat message
            mode_counts = {}
            for d in bitdo_devs:
                mode_counts[d['mode']] = mode_counts.get(d['mode'], 0) + 1
            mode_summary = ", ".join([f"{c} {m}" for m, c in mode_counts.items()]) if mode_counts else "None"
            
            msg = f"{get_timestamp()} Polling: {waiting_count} Waiting, {in_use_count} In-Use ({mode_summary})"
            print("\r" + msg.ljust(120), end='', flush=True)
            
            check_kernel_crashes()
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print(f"\n\n{get_timestamp()} Exiting... Devices remain bound in usbipd.")

if __name__ == "__main__":
    main()
