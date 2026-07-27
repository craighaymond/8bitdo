#!/usr/bin/env python3
"""
Wi-Fi & Local Network Congestion Monitor
-----------------------------------------
Monitors network latency, jitter, and packet loss between your Host PC, 
Router Gateway, and Moonlight TV client to detect Wi-Fi airtime contention.

Author: Antigravity AI
"""

import os
import sys
import time
import re
import subprocess
import socket
from datetime import datetime

# Default Target Configuration
TARGETS = {
    "Router": "192.168.0.1",
    "TV (Moonlight)": "192.168.0.20",
    "Internet (DNS)": "1.1.1.1"
}

PING_INTERVAL = 1.0  # Seconds between ping checks
LOG_FILE = "network_monitor_log.csv"

def get_default_gateway():
    """Detects default router gateway IP on Windows/Linux."""
    try:
        if sys.platform == "win32":
            output = subprocess.check_output("ipconfig", text=True)
            match = re.search(r"Default Gateway[.\s]+:\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", output)
            if match:
                return match.group(1)
        else:
            output = subprocess.check_output("ip route | grep default", shell=True, text=True)
            match = re.search(r"default via ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", output)
            if match:
                return match.group(1)
    except Exception:
        pass
    return "192.168.0.1"

def ping_host(host, timeout_ms=1000):
    """Pings a target host once and returns response latency in ms, or None if packet dropped."""
    if sys.platform == "win32":
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(int(timeout_ms / 1000)), host]

    try:
        start_time = time.time()
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            if sys.platform == "win32":
                match = re.search(r"time[=<]([0-9]+)ms", res.stdout)
                if match:
                    return float(match.group(1))
                return (time.time() - start_time) * 1000.0
            else:
                match = re.search(r"time=([0-9.]+)", res.stdout)
                if match:
                    return float(match.group(1))
                return (time.time() - start_time) * 1000.0
    except Exception:
        pass
    return None

def init_csv_log():
    """Initializes CSV header if log file does not exist."""
    if not os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "w") as f:
                f.write("Timestamp,Target,IP,Latency_ms,Status\n")
        except Exception:
            pass

def log_event(target_name, ip, latency, status):
    """Appends high-latency or packet drop events to CSV."""
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lat_str = f"{latency:.1f}" if latency is not None else "TIMEOUT"
        with open(LOG_FILE, "a") as f:
            f.write(f"{ts},{target_name},{ip},{lat_str},{status}\n")
    except Exception:
        pass

def main():
    if sys.platform == "win32":
        os.system('')  # Enable VT100 / ANSI escape sequence parsing in Windows console

    gateway_ip = get_default_gateway()
    TARGETS["Router"] = gateway_ip

    print("==============================================================")
    print("        Wi-Fi & Network Congestion Monitor Active            ")
    print("==============================================================")
    print(f" Monitoring Targets every {PING_INTERVAL}s:")
    for name, ip in TARGETS.items():
        print(f"   - {name:<16}: {ip}")
    print(f" High Latency Spikes (>20ms) & Drops logged to: {LOG_FILE}")
    print(" Press Ctrl+C to stop.")
    print("==============================================================\n")

    init_csv_log()

    # Track statistics per target
    stats = {name: {"sent": 0, "recv": 0, "last_lat": 0.0, "history": []} for name in TARGETS}

    try:
        while True:
            timestamp = datetime.now().strftime("%H:%M:%S")
            line_parts = [f"[{timestamp}]"]

            for name, ip in TARGETS.items():
                target_stat = stats[name]
                target_stat["sent"] += 1
                
                lat = ping_host(ip, timeout_ms=1000)
                
                if lat is not None:
                    target_stat["recv"] += 1
                    target_stat["last_lat"] = lat
                    target_stat["history"].append(lat)
                    if len(target_stat["history"]) > 20:
                        target_stat["history"].pop(0)

                    # Calculate Jitter (average absolute difference between consecutive pings)
                    hist = target_stat["history"]
                    jitter = sum(abs(hist[i] - hist[i-1]) for i in range(1, len(hist))) / (len(hist) - 1) if len(hist) > 1 else 0.0

                    if lat > 20.0:
                        status = "HIGH LATENCY (SPIKE)"
                        log_event(name, ip, lat, status)
                        status_str = f"{lat:>5.1f}ms (SPIKE!)"
                        # Print a permanent timestamped alert line above the status line
                        sys.stdout.write(f"\r\033[K[{timestamp}] ALERT: High latency spike on {name} ({ip}): {lat:.1f}ms!\n")
                    else:
                        status_str = f"{lat:>5.1f}ms"

                    line_parts.append(f"{name}: {status_str} (jitter: {jitter:.1f}ms)")
                else:
                    status = "PACKET LOSS (TIMEOUT)"
                    log_event(name, ip, None, status)
                    status_str = "TIMEOUT"
                    # Print a permanent timestamped alert line above the status line
                    sys.stdout.write(f"\r\033[K[{timestamp}] ALERT: Packet loss / timeout on {name} ({ip})!\n")
                    line_parts.append(f"{name}: {status_str}")

            # Print single-line updating status
            output = " | ".join(line_parts)
            sys.stdout.write(f"\r\033[K{output}")
            sys.stdout.flush()

            time.sleep(PING_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n==============================================================")
        print("               Network Monitoring Summary                     ")
        print("==============================================================")
        for name, data in stats.items():
            loss = ((data["sent"] - data["recv"]) / data["sent"]) * 100.0 if data["sent"] > 0 else 0.0
            avg_lat = (sum(data["history"]) / len(data["history"])) if data["history"] else 0.0
            print(f" {name:<16} ({TARGETS[name]}): Loss={loss:.1f}%, Avg Latency={avg_lat:.1f}ms")
        print("==============================================================\n")

if __name__ == "__main__":
    main()
