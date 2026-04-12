A collection of python scripts that help with 8bitdo Ultimate controller setup, mapping and mode changes in Windows.  These are design to work with systems utilizng usbip

# 8BitDo Bridge - S Mode to Xbox

A Python-based controller bridge that maps 8BitDo controllers in S Mode (DirectInput) to Xbox (Xinput) gamepad input for Windows. This allows 8BitDo controllers to work seamlessly with games and applications.

This script performs a controller bridging function similar to XOutput, but specific to 8bitdo Ultimate controllers that are set to default in S mode.

## Features

- **Automatic Hot-Plugging**: Automatically detects and binds controllers as they are plugged in or out without restarting the script
- **Full Analog Mapping**: Maps all buttons and provides full pressure sensitivity for triggers (ZL/ZR)
- **Deadzone Handling**: Includes adjustable deadzone (default 20%) via a global constant for stable analog stick input
- **Vibration Feedback**: Pulses connected controllers to indicate a successful bridge connection
- **Multiple Controller Support**: Can handle multiple controllers simultaneously
- **Graceful Cleanup**: Explicitly releases virtual controllers on exit or disconnect

## Requirements

- Python 3.6+
- pygame 2.0+
- vgamepad (virtual gamepad library)
- Windows OS

## Installation

1. **Install Python dependencies**:
   ```bash
   pip install pygame vgamepad
   ```

2. **Place the script** in your RetroBat directory or any accessible location

## Usage

Run the script from command line:
```bash
python 8bitdo_bridge_S_mode_to_xbox.py
```

The script will:
1. Start a persistent listener for game controllers
2. Create virtual Xbox gamepads for each 8BitDo controller detected (S-mode)
3. Support hot-swapping/reconnecting controllers while running
4. Continue running until you press Ctrl+C or the process is terminated

## Button Mapping

| 8BitDo Button (S-Mode) | Xbox Button |
|---|---|
| B (Bottom) | Xbox A |
| A (Right) | Xbox B |
| Y (Left) | Xbox X |
| X (Top) | Xbox Y |
| Plus (+) | Xbox Start |
| Minus (-) | Xbox Back |
| R (Bumper) | Xbox RB (Right Shoulder) |
| L (Bumper) | Xbox LB (Left Shoulder) |
| ZR (Trigger) | Xbox RT (Right Trigger - Analog) |
| ZL (Trigger) | Xbox LT (Left Trigger - Analog) |
| Left Stick Click | Xbox L3 |
| Right Stick Click | Xbox R3 |
| D-Pad Up/Down/Left/Right | D-Pad Up/Down/Left/Right |
| Left Stick | Left Joystick |
| Right Stick | Right Joystick |

## Configuration

### Deadzone & Polling

The configuration values are located at the top of the script:

```python
DEADZONE = 0.2      # 0.0 to 1.0 threshold for analog drift
POLLING_RATE = 0.01 # 100Hz update frequency
```

### Behavior

- **Console Title**: The script sets the console window title to "8bitdoBridge" for RetroBat integration
- **Rumble Feedback**: Each connected controller receives a brief vibration pulse upon successful binding
- **Logging**: All connection events are logged with timestamps to the console

## Troubleshooting

**No controllers detected**:
- Ensure controllers are connected and recognized by Windows
- Check that controllers are NOT already mapped as Xbox controllers
- Verify controllers are in S Mode (not Android/iOS mode)

**Controllers not responding**:
- Confirm pygame and vgamepad are properly installed
- Try unplugging and re-plugging the controller
- Restart the bridge script

**Rumble not working**:
- Not all controllers support rumble; this is normal
- The script will log "Rumble not supported" for affected devices

**Alt+Tab cycling issue**:
- The deadzone is designed to prevent unwanted analog stick input that can trigger Alt+Tab
- If issues persist, increase the deadzone value

## Exit

- Press **Ctrl+C** in the terminal, or
- Use **Task Manager** to terminate the process

The script will cleanly disconnect all virtual controllers on exit.

## Notes

- This script is designed for RetroBat and arcade emulation environments
- The bridge runs in the foreground; minimize or background the window as needed
- Multiple instances of this script should not run simultaneously for the same controller

---

# USBIP Connect Client

A Python-based client for connecting USB devices over the network using the USBIP protocol. This script automatically discovers USBIP servers on the local network, detects compatible game controllers, and manages connections.

## Purpose

The USBIP Connect Client enables remote access to USB devices over your local network as if they were directly connected to your machine. It's particularly useful for centralizing controller connections and managing multiple devices remotely.

## Features

- **Automatic Server Discovery**: Scans the local subnet for available USBIP servers
- **Controller Detection**: Intelligently identifies game controllers and distinguishes them from other USB devices
- **Auto-Attach**: Automatically attaches compatible controllers when the server is discovered
- **Mode Detection**: Identifies controller modes (S-Mode, X-Mode, D-Mode, PS4, PS5, etc.)
- **Game Controllers Panel Integration**: Automatically launches Windows Game Controllers (joy.cpl) for device management
- **Status Monitoring**: Logs connection status with timestamps
- **Graceful Reconnection**: Handles server disconnections and reconnects automatically

## Requirements

- Python 3.6+
- USBIP client tools (usbip command-line utility)
- Network connectivity to the USBIP server
- Windows OS (for joy.cpl integration)

## Installation

1. **Install USBIP tools** on Windows:
   - Download and install from the USBIP project or use Windows Package Manager:
     ```bash
     winget install usbip
     ```

2. **Place the script** in your desired location or add to your PATH

## Usage

Run the script from command line:
```bash
python usbip_connect_client.py
```

The script will:
1. Search for a USBIP server on your local network
2. Upon discovery, list available devices on the server
3. Automatically attach detected game controllers
4. Launch the Game Controllers panel (joy.cpl) if not already open
5. Monitor and log connection status every 30 seconds
6. Reconnect automatically if the server becomes unavailable

Press **Ctrl+C** to exit the script.

## Device Detection

The script recognizes the following device types and modes:

| VID:PID / Description | Mode | Auto-Attach |
|---|---|---|
| 057e:2009 | S-Mode (Switch) | ✓ |
| 045e:028e, 045e:02d1 | X-Mode (Xbox) | ✓ |
| 2dc8 (8BitDo) | D-Mode (8BitDo) | ✓ |
| 054c:05c4, 054c:09cc | D-Mode (PS4) | ✓ |
| 054c:0ce6 | D-Mode (PS5) | ✓ |
| Hub / Root Hub | USB Hub | ✗ |
| Adapter / Receiver | Adapter | ✗ |

## Configuration

The script has minimal configuration:
- **PORT**: Set to 3240 (standard USBIP port)
- **Poll Interval**: 30 seconds between status checks
- **Subnet Scan**: Scans 192.168.x.1-254 range (auto-detected from your local IP)

## Logging

All operations are logged to the console with timestamps in `[YYYY-MM-DD HH:MM]` format:
```
[2026-04-11 14:30] USBIP Connect Client started. Press Ctrl+C to stop.
[2026-04-11 14:30] Searching for usbipd server on LAN...
[2026-04-11 14:31] Found usbipd server at 192.168.1.100
[2026-04-11 14:31] Attempting to attach 1-1 (8BitDo Controller) [Mode: D-Mode (8BitDo)]
[2026-04-11 14:31] Successfully attached 1-1 (8BitDo Controller) [Mode: D-Mode (8BitDo)]
```

## Troubleshooting

**Could not find usbipd server**:
- Ensure your USBIP server is running and connected to the same network
- Verify network connectivity between client and server
- Check that the server is listening on port 3240

**Controllers not attaching**:
- Verify the Game Controllers panel (joy.cpl) is accessible
- Check that devices are actually recognized as controllers on the server
- Ensure you have appropriate permissions to attach devices

**Failed to launch joy.cpl**:
- This is typically a non-critical error; the script will continue operating
- Manually open Game Controllers from Windows Settings if needed

## Notes

- This script is designed to run continuously in the background
- Do not run multiple instances simultaneously for the same server
- The script requires administrative privileges for device attachment on some systems

## License

Use as needed for personal emulation purposes.
