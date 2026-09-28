# ROG Ally Bazzite OS Configuration & Backup Repository

> [!IMPORTANT]
> **Personal Setup & No Support Disclaimer**
>
> This repository is maintained strictly for personal backup and tailored specifically to the author's individual hardware setup (ASUS ROG Ally running Bazzite OS).
> - **No support, updates, or maintenance are guaranteed.** Issues and pull requests are not monitored or serviced.
> - Provided **"AS-IS"** without warranties or guarantees of any kind.
> - Feel free to inspect, fork, or adapt these scripts for your own needs at your own risk.

Autonomous configuration repository for ASUS ROG Ally running **Bazzite OS**. This repo contains all custom-tuned scripts, systemd units, udev rules, HHD states, and Steam Input Desktop Layout patches (including left-stick smooth scrolling with Turbo and enhanced right-stick precision).

## Contents (`rog-ally-bazzite-config/`)
- `bin/ally-docked-mode.sh` — Automatic TDP switcher (Performance vs Balanced), audio router (HDMI TV vs ROG Ally speakers), and Console-Style-style controller hiding.
- `bin/hhd-watchdog.sh` — Watchdog daemon for auto-recovering Handheld Daemon (`hhd`) and gamepads.
- `udev/99-ally-docked.rules` — Udev rules triggering docking events.
- `systemd/` — Systemd services and timers (`ally-docked.service`, `hhd-watchdog.service`, `hhd-watchdog.timer`).
- `sleep/10-hhd-watchdog-sleep.sh` — Resume/sleep hook for HHD watchdog.
- `hhd/state.yml` — Handheld Daemon saved state configuration.
- `steam/` — Patched Steam Input Desktop Layout templates (`desktop_xboxone.vdf`, `desktop_neptune.vdf`) featuring left-stick scroll with Turbo repeat and tuned right-stick `joystick_mouse` settings (`response_curve=2`, `sensitivity=130`, `mouse_smoothing=1`, `deadzone_inner_radius=6000`).

## One-Command Restoration
To restore all configurations on your ROG Ally (e.g. after a system rebase or fresh reinstall):

1. Clone or copy this repository to the console.
2. Run the restoration script with `sudo`:
   ```bash
   sudo ./restore.sh
   ```
3. Reboot the console:
   ```bash
   sudo systemctl reboot
   ```
