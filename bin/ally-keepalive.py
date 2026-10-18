#!/usr/bin/env python3
"""
AllyDock Keepalive Daemon (Idle & Screensaver Guard)
Part of AllyDock Suite for Bazzite OS / ROG Ally.

Prevents Steam Game Mode from entering idle/screensaver timeout (300s)
when the external Bluetooth/USB gamepad (GuliKit, Xbox, etc.) falls asleep in Docked mode,
while strictly preserving Player 1 slot for external gamepads upon reconnect.

Features smart 20-minute idle guard:
- Monitors real input from external physical devices in /dev/input/ (ignoring own dummy node).
- If no real input is detected for MAX_IDLE_SECONDS (default 1200s / 20m), keepalive pings cease,
  allowing SteamOS / Bazzite to dim the screen and enter suspend.
- Resumes automatically as soon as any real controller button or stick input is received.
"""

import os
import sys
import time
import signal
import logging
import subprocess

try:
    import evdev
    from evdev import UInput, ecodes as e
    EVDEV_AVAILABLE = True
except ImportError:
    evdev = None
    UInput = None
    e = None
    EVDEV_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [AllyDock Keepalive] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ally-keepalive")

RUNNING = True
MAX_IDLE_SECONDS = int(os.environ.get("ALLY_KEEPALIVE_MAX_IDLE", "1200"))
DEFAULT_INTERVAL = int(os.environ.get("ALLY_KEEPALIVE_INTERVAL", "90"))
KEEPALIVE_DEVICE_NAME = "AllyDock Keepalive Device"


def signal_handler(signum, frame):
    global RUNNING
    logger.info("Received signal %s, initiating graceful shutdown...", signum)
    RUNNING = False


def reset_steam_idle():
    """Signals user activity to Steam ScreenSaver interface via D-Bus."""
    try:
        res = subprocess.run(
            [
                "busctl", "--user", "call",
                "org.freedesktop.ScreenSaver", "/ScreenSaver",
                "org.freedesktop.ScreenSaver", "SimulateUserActivity",
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if res.returncode != 0:
            logger.debug("SimulateUserActivity returned %d: %s", res.returncode, res.stderr.strip())
        else:
            logger.debug("Steam idle timer successfully refreshed via D-Bus.")
    except Exception as exc:
        logger.debug("Failed to call SimulateUserActivity: %s", exc)


class InputActivityMonitor:
    """Monitors /dev/input devices for real user activity (buttons, sticks, keys),
    strictly ignoring the virtual AllyDock Keepalive dummy device.
    """

    def __init__(self, ignore_names=None, scan_interval=5.0):
        self.ignore_names = set(ignore_names or [KEEPALIVE_DEVICE_NAME])
        self.devices = {}  # path -> evdev.InputDevice
        self.last_scan = 0.0
        self.scan_interval = scan_interval

    def refresh_devices(self):
        if not EVDEV_AVAILABLE or evdev is None:
            return

        current_paths = set()
        try:
            device_paths = evdev.list_devices()
        except Exception as exc:
            logger.debug("Failed to enumerate input devices: %s", exc)
            return

        for path in device_paths:
            current_paths.add(path)
            if path not in self.devices:
                try:
                    dev = evdev.InputDevice(path)
                    # Strictly ignore virtual keepalive device
                    if any(ignored in dev.name for ignored in self.ignore_names):
                        dev.close()
                        continue
                    self.devices[path] = dev
                    logger.debug("Monitoring input device: %s (%s)", dev.name, path)
                except (PermissionError, OSError) as exc:
                    logger.debug("Could not open input device %s: %s", path, exc)

        # Close and remove any disconnected devices
        for path in list(self.devices.keys()):
            if path not in current_paths:
                try:
                    self.devices[path].close()
                except Exception:
                    pass
                del self.devices[path]

    def poll_activity(self, timeout=1.0) -> bool:
        """Polls monitored input devices for real user interaction.
        Returns True if any key, button, relative or absolute axis motion is detected.
        """
        if not EVDEV_AVAILABLE or evdev is None:
            time.sleep(timeout)
            return False

        now = time.monotonic()
        if now - self.last_scan >= self.scan_interval:
            self.refresh_devices()
            self.last_scan = now

        if not self.devices:
            time.sleep(timeout)
            return False

        import select

        fds = [dev.fd for dev in self.devices.values()]
        try:
            readable, _, _ = select.select(fds, [], [], timeout)
        except (ValueError, OSError) as exc:
            logger.debug("Select error in input monitor: %s", exc)
            self.refresh_devices()
            return False

        if not readable:
            return False

        activity = False
        fd_to_path = {dev.fd: path for path, dev in self.devices.items()}

        for fd in readable:
            path = fd_to_path.get(fd)
            if not path or path not in self.devices:
                continue
            dev = self.devices[path]
            try:
                for event in dev.read():
                    if event.type == e.EV_SYN:
                        continue
                    if event.type == e.EV_KEY and event.code == e.KEY_RESERVED:
                        continue
                    if event.type in (e.EV_KEY, e.EV_ABS, e.EV_REL):
                        activity = True
            except (OSError, BlockingIOError):
                logger.debug("Device %s read error or disconnected, removing.", path)
                try:
                    dev.close()
                except Exception:
                    pass
                self.devices.pop(path, None)

        return activity

    def close(self):
        for dev in list(self.devices.values()):
            try:
                dev.close()
            except Exception:
                pass
        self.devices.clear()


def is_maintenance_active() -> bool:
    """Checks if active interactive SSH sessions (with terminal pts/) or development is running.

    Non-interactive background SSH commands (like automated hourly scanners) do NOT block sleep.
    """
    try:
        res = subprocess.run(["who"], capture_output=True, text=True, timeout=1)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "pts/" in line:
                    return True
    except Exception:
        pass
    return False


def is_game_running() -> bool:
    """Checks if an actual game (Proton/Wine/emulator or non-menu Steam AppID) is currently running.

    When in Steam Deck menus or homescreen, keepalive sleeps to allow natural Steam power-saving.
    """
    try:
        # 1. Check gamescope focused app
        for path in ("/tmp/gamescope_focused_app", "/run/user/1000/gamescope_focused_app"):
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    app_id_str = f.read().strip()
                if app_id_str.isdigit() and int(app_id_str) > 769:
                    return True

        # 2. Check for active game engines (wine, proton, emulators, native games)
        res = subprocess.run(
            ["pgrep", "-f", "wineserver|pressure-vessel|rpcs3|yuzu|ryujinx|ppsspp|pcsx2"],
            capture_output=True,
            timeout=1,
        )
        if res.returncode == 0 and res.stdout.strip():
            return True
    except Exception:
        pass
    return False


def trigger_system_suspend():
    """Triggers clean system suspend when user is truly idle to prevent infinite screensaver on TV."""
    try:
        logger.info("Initiating system suspend (putting ROG Ally / TV to sleep cleanly)...")
        subprocess.run(
            [
                "busctl", "call", "org.freedesktop.login1",
                "/org/freedesktop/login1", "org.freedesktop.login1.Manager",
                "Suspend", "b", "true",
            ],
            timeout=5,
            check=False,
        )
    except Exception as exc:
        logger.debug("busctl suspend failed: %s, falling back to systemctl suspend", exc)
        try:
            subprocess.run(["systemctl", "suspend"], timeout=5, check=False)
        except Exception:
            pass


def main():
    global RUNNING
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    interval = int(os.environ.get("ALLY_KEEPALIVE_INTERVAL", str(DEFAULT_INTERVAL)))
    max_idle = int(os.environ.get("ALLY_KEEPALIVE_MAX_IDLE", str(MAX_IDLE_SECONDS)))
    logger.info(
        "Starting AllyDock Keepalive Daemon (interval: %ds, max idle: %ds)...",
        interval,
        max_idle,
    )

    # Initialize non-gamepad uinput dummy node
    ui = None
    if EVDEV_AVAILABLE and UInput is not None and e is not None:
        try:
            capabilities = {
                e.EV_KEY: [e.KEY_RESERVED],
            }
            ui = UInput(capabilities, name=KEEPALIVE_DEVICE_NAME)
            logger.info("Virtual keepalive input device initialized: %s", ui.name)
        except Exception as exc:
            logger.warning(
                "Could not initialize uinput keepalive device: %s. Continuing with D-Bus only.",
                exc,
            )
    else:
        logger.info("python-evdev not installed. Running in D-Bus only mode.")

    monitor = InputActivityMonitor()

    # Initial ping upon startup
    reset_steam_idle()
    if ui:
        try:
            ui.write(e.EV_KEY, e.KEY_RESERVED, 0)
            ui.syn()
        except Exception:
            pass

    last_ping = time.monotonic()
    last_real_input = time.monotonic()
    was_idle = False

    try:
        while RUNNING:
            activity = monitor.poll_activity(timeout=1.0)
            if not RUNNING:
                break

            now = time.monotonic()

            # Якщо гри немає і немає активного терміналу розробника — не втручаємося в сон Steam!
            if not is_game_running() and not is_maintenance_active():
                time.sleep(1.0)
                continue

            if activity:
                last_real_input = now
                if was_idle:
                    logger.info("Real user input detected! Resuming Steam idle keepalive.")
                    was_idle = False
                    reset_steam_idle()
                    last_ping = now

            # If evdev is not available, we cannot monitor input devices, so we do not enforce idle cutoff
            if EVDEV_AVAILABLE and evdev is not None:
                if is_maintenance_active():
                    # While SSH session or remote development is active, strictly prevent screensaver and sleep
                    last_real_input = now
                    if was_idle:
                        was_idle = False
                        reset_steam_idle()
                        last_ping = now

                idle_seconds = now - last_real_input
                if idle_seconds >= max_idle:
                    if not was_idle:
                        logger.info(
                            "User idle for %.1f seconds (>= %ds) with no active SSH. Triggering sleep to turn off screen.",
                            idle_seconds,
                            max_idle,
                        )
                        was_idle = True
                        trigger_system_suspend()
                    continue

            if now - last_ping >= interval:
                last_ping = now
                logger.info("Sending periodic keepalive ping (evdev syn + D-Bus activity)...")

                # 1. Micro-sync on evdev
                if ui:
                    try:
                        ui.write(e.EV_KEY, e.KEY_RESERVED, 0)
                        ui.syn()
                    except Exception as exc:
                        logger.debug("Error writing to uinput: %s", exc)

                # 2. D-Bus SimulateUserActivity
                reset_steam_idle()
    finally:
        monitor.close()
        if ui:
            try:
                ui.close()
            except Exception:
                pass
        logger.info("AllyDock Keepalive Daemon stopped cleanly.")


if __name__ == "__main__":
    main()
