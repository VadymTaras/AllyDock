#!/usr/bin/env python3
"""
AllyDock Keepalive Daemon (Idle & Screensaver Guard)
Part of AllyDock Suite for Bazzite OS / ROG Ally.

Prevents Steam Game Mode from entering idle/screensaver timeout (300s)
when the external Bluetooth/USB gamepad (GuliKit, Xbox, etc.) falls asleep in Docked mode,
while strictly preserving Player 1 slot for external gamepads upon reconnect.

How it works:
1. Registers a non-gamepad dummy evdev device via /dev/uinput (EV_KEY: KEY_RESERVED).
   Because it has no joystick buttons/axes, it does NOT register as js* / Gamepad,
   leaving Gamepad Slot 1 100% available for external controllers.
2. Periodically (default 90s) emits a no-op event on the evdev bus to prevent input bus silence.
3. Simultaneously calls org.freedesktop.ScreenSaver.SimulateUserActivity on user D-Bus
   to reset Steam's internal 300-second idle timer.
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


def main():
    global RUNNING
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    interval = int(os.environ.get("ALLY_KEEPALIVE_INTERVAL", "90"))
    logger.info("Starting AllyDock Keepalive Daemon (interval: %ds)...", interval)

    # Initialize non-gamepad uinput dummy node
    ui = None
    if EVDEV_AVAILABLE and UInput is not None and e is not None:
        try:
            capabilities = {
                e.EV_KEY: [e.KEY_RESERVED],
            }
            ui = UInput(capabilities, name="AllyDock Keepalive Device")
            logger.info("Virtual keepalive input device initialized: %s", ui.name)
        except Exception as exc:
            logger.warning("Could not initialize uinput keepalive device: %s. Continuing with D-Bus only.", exc)
    else:
        logger.info("python-evdev not installed. Running in D-Bus only mode.")

    # Initial ping upon startup
    reset_steam_idle()
    if ui:
        try:
            ui.write(e.EV_KEY, e.KEY_RESERVED, 0)
            ui.syn()
        except Exception:
            pass

    last_ping = time.monotonic()
    while RUNNING:
        time.sleep(1)
        if not RUNNING:
            break

        now = time.monotonic()
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

    if ui:
        try:
            ui.close()
        except Exception:
            pass
    logger.info("AllyDock Keepalive Daemon stopped cleanly.")


if __name__ == "__main__":
    main()
