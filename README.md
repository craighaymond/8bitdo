A collection of python scripts that help with 8bitdo Ultimate controller setup, mapping and mode changes in Windows.  These are design to work with systems utilizng usbip

# 8BitDo Bridge - S Mode to Xbox

A Python-based controller bridge that maps 8BitDo controllers in S Mode (DirectInput) to Xbox (Xinput) gamepad input for Windows. This allows 8BitDo controllers to work seamlessly with games and applications that expect Xbox controller input.  Pair this with Windows .bat scripts when starting and exiting various executables that require the controllers to appear as Xbox controllers.  When those applications exit, your .bat script can terminate this bridge script, returning the controllers to their native S-mode state (for compatibility with other applications that are configured for Direct Input).

This script performs a controller bridging function similar to XOutput, but specific to 8bitdo Ultimate controllers that are set to default in S mode.

## Features

- **Automatic Controller Detection**: Automatically detects connected 8BitDo controllers
- **Full Button Mapping**: Maps all buttons including D-Pad, analog sticks, triggers, and shoulder buttons
- **Deadzone Handling**: Includes adjustable deadzone (default 20%) for stable analog stick input in arcade environments
- **Vibration Feedback**: Pulses connected controllers to indicate the bridge is active
- **Multiple Controller Support**: Can handle multiple controllers simultaneously
- **Clean Shutdown**: Gracefully disconnects virtual controllers on exit

## Requirements

- Python 3.6+
- pygame
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
1. Detect all connected non-Xbox controllers
2. Create virtual Xbox gamepads for each detected controller
3. Map inputs from physical controllers to virtual Xbox controllers
4. Continue running until you press Ctrl+C or the process is terminated

## Button Mapping

| 8BitDo Button | Xbox Button |
|---|---|
| B | Xbox B |
| A | Xbox A |
| Y | Xbox Y |
| X | Xbox X |
| Select | Xbox Back |
| R1 | Xbox RB (Right Shoulder) |
| L1 | Xbox LB (Left Shoulder) |
| L3 | Xbox Left Thumb Button |
| D-Pad Up/Down/Left/Right | D-Pad Up/Down/Left/Right |
| Left Stick | Left Joystick |
| Right Stick | Right Joystick |
| ZL / LT | Left Trigger |
| ZR / RT | Right Trigger |

## Configuration

### Deadzone

The deadzone threshold (default 20% or 0.2) prevents unwanted analog stick drift. To adjust, modify the `self.dz` value in the `ControllerBridge.__init__()` method:

```python
self.dz = 0.2  # Change this value (0.0 to 1.0)
```

Higher values increase the deadzone (less sensitive), lower values decrease it (more sensitive).

## Behavior

- **Console Title**: The script sets the console window title to "8bitdoBridge" for RetroBat integration (as an example usecase)
- **Rumble Feedback**: Each connected controller receives a brief vibration pulse on startup
- **No Rumble Support**: If a controller doesn't support rumble, a note will be printed
- **Update Rate**: Processes controller input at ~100 Hz (10ms sleep between updates)

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

## License

Use as needed for personal emulation purposes.
