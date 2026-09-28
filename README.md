# ⚓ AllyDock (v1.1.0) - Autonomous Docking & System Optimization Suite for ASUS ROG Ally on Bazzite OS
### Intelligent Display Detection, 3-Tier Adaptive Profiling & Seamless Docked Gaming Suite

[![Project](https://img.shields.io/badge/Project-AllyDock-orange.svg)](#)
[![Version](https://img.shields.io/badge/Version-v1.1.0-blue.svg)](VERSION)
[![OS](https://img.shields.io/badge/OS-Bazzite%2043%20%7C%2044-purple.svg)](https://bazzite.gg)
[![Hardware](https://img.shields.io/badge/Hardware-ASUS%20ROG%20Ally%20(RC71L)-red.svg)](https://rog.asus.com/gaming-handhelds/rog-ally/rog-ally-2023/)
[![Kernel](https://img.shields.io/badge/Kernel-Linux%206.17.x%20(fsync)-green.svg)](https://kernel.org)
[![Status](https://img.shields.io/badge/Status-Tested%20%26%20Verified-success.svg)](#-tested-environment--compatibility-matrix)
[![Desktop](https://img.shields.io/badge/Desktop-KDE%20Plasma%206%20(Wayland)-informational.svg)](https://kde.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> [!IMPORTANT]
> **AllyDock v1.1.0 Autonomous Docking & Optimization Suite**  
> **AllyDock** is a comprehensive, production-tested suite of automation scripts, udev rules, `systemd` system services, sleep/wake hooks, Handheld Daemon (`hhd`) state profiles, tuned Steam Input Desktop Layout configurations, and an **intelligent display detector with 3-tier adaptive profiling (Handheld 45 FPS vs. 60Hz TV vs. AMD FreeSync/VRR Uncapped)** engineered specifically for the **ASUS ROG Ally (RC71L)** running **Bazzite OS**.  
> The suite has been extensively battle-tested under real-world gaming conditions: it dynamically inspects connected displays via raw binary EDID and DRM sysfs interfaces, automatically selects optimal TDP and frame rate caps, resolves gamepad flapping loops, routes PipeWire audio seamlessly, and turns desktop joystick navigation into an ergonomic, responsive trackpad and turbo scroller.

> [!NOTE]
> **Personal Backup & Disclaimer**  
> This repository is maintained for personal backup and automated deployment of the author's ASUS ROG Ally (RC71L) setup running Bazzite OS. The code is provided "AS-IS", without warranties or official support. You are warmly welcome to fork, modify, and adapt these scripts to suit your own handheld configurations.

---

## 🏷️ Tags & Keywords (SEO / Discoverability)

`allydock` • `ally-dock` • `asus-rog-ally` • `rog-ally` • `bazzite-os` • `display-detection` • `edid-parser` • `amd-freesync` • `vrr` • `handheld-daemon` • `hhd` • `steam-input` • `docked-mode` • `tdp-switcher` • `mangohud-fps` • `pipewire-audio` • `decky-loader` • `ge-proton` • `linux-gaming` • `kde-plasma-6` • `handheld-pc` • `gamepad-flapping-fix`

---

## 📋 Tested Environment & Compatibility Matrix

| Component / Subsystem | Version / Configuration | Technical Notes |
| :--- | :--- | :--- |
| **Hardware Platform** | **ASUS ROG Ally (RC71L.319)** | AMD Ryzen Z1 Extreme, 16GB LPDDR5, 120Hz FreeSync Premium |
| **Operating System** | **Bazzite 43 / 44 (Kinoite)** | Linux Kernel `6.17.x-ba29.fc43.x86_64` (fsync kernel) |
| **Desktop Environment** | **KDE Plasma 6 (Wayland)** | Gamescope Session in Game Mode, SDDM passwordless autologin |
| **Display Detection** | **`bin/ally-detect-display.py`** | Pure Python 3: raw binary EDID parsing (CEA-861, DisplayID, AMD FreeSync OUI `0x00001a`, HDMI Forum VRR OUI `0xc45dd8`, VESA checksum) |
| **Adaptive Profiler** | **`bin/ally-docked-mode.sh`** | 3 Tiers: Handheld (45 FPS / 15W), TV 60Hz (60 FPS / 25W), AMD VRR (0 Uncapped / 30W Turbo) |
| **Gamepad Daemon** | **Handheld Daemon (`hhd`)** | Version `2888122e` (v2.88+), verified compatible with Bazzite 44 `inputplumber` |
| **Decky Loader** | **v3.2.9** (`plugin_loader.service`) | Fully verified with `decky-lsfg-vk`, `CssLoader`, `Junk-Store`, `Bazzite Buddy` |
| **Proton Runner** | **`GE-Proton11-7`** | Set environment variable: `PROTON_FSR4_RDNA3_UPGRADE=1` |
| **Audio Server (Sound)** | **PipeWire + WirePlumber** | Calibrated speaker DSP filter + Valve HRTF 7.1 spatializer (`sadie_d1.sofa`) |
| **Storage (NVMe SSD)** | **Samsung PM991a 1TB NVMe** (`SAMSUNG MZ9LQ1T0HBLB-00B00`) | Btrfs subvolumes `subvol=root` (`/`) and `subvol=home` (`/var/home`) |

---

## 🚀 Key Features & Problems Solved

### 1. 🖥️ Intelligent Display & VRR Detection with 3-Tier Adaptive Profiling
- **Hardware Display Detector (`bin/ally-detect-display.py`):**
  - Written in pure Python 3 using standard library modules only (zero external runtime dependencies).
  - Scans kernel DRM connector endpoints at `/sys/class/drm/card*-*/status` (ignoring internal `eDP` and virtual `Writeback` connectors).
  - Reads raw binary `edid` directly from the connector sysfs node with strict validation:
    - VESA header signature verification: `00 FF FF FF FF FF FF 00`.
    - Checksum validation across base and extension blocks (`sum(block) % 256 == 0`).
  - Extracts the exact commercial monitor or TV model string from `0xFC` descriptor blocks (e.g., "LG OLED TV", "ASUS ROG XG27").
  - Dynamically calculates maximum supported refresh rate (`max_hz`) across Detailed Timing Descriptors (DTD), standard timing bytes, and the Range Limits descriptor (`0xFD`).
  - Deep-scans CTA-861 and DisplayID extension blocks for:
    - **AMD FreeSync** (Vendor-Specific Data Block, IEEE OUI `0x00001a`);
    - **HDMI Forum VRR** (HF-VSDB, IEEE OUI `0xc45dd8`);
    - **VESA Adaptive-Sync** (DisplayID 2.0 block `0x22`).
  - Verifies the kernel DRM `vrr_capable` connector property via sysfs and `drm_info`.
  - Supports `--shell` formatted output (for instantaneous `eval` ingestion in bash scripts) and structured `--json` output.

- **3-Tier Adaptive Operating Profiles:**
  1. 📱 **`handheld` (Undocked / Handheld Mode):**
     - **TDP:** `balanced` (15–20W)
     - **CPU EPP:** `balance_power`
     - **GPU DPM:** `auto`
     - **Target FPS:** **45 FPS** (applied to `MangoHud.conf` and `ally-fps.state` for whisper-quiet fan operation, smooth 2:1 pulldown on the 120Hz native screen, and extended battery runtimes)
     - **Audio:** Calibrated `ROG Ally` speaker DSP equalizer profile
     - **Controller:** Internal controller enabled in standard mode (`mode=uinput`)
  2. 📺 **`docked_tv_60` (Standard Living Room TV or 60Hz Office Monitor):**
     - **TDP:** `performance` (25W)
     - **CPU EPP:** `balance_performance`
     - **GPU DPM:** `auto`
     - **Target FPS:** **60 FPS** (fixed frame cap eliminating tearing, judder, and unnecessary thermal accumulation on fixed 60Hz displays)
     - **Audio:** External HDMI audio sink (`alsa_output.pci-0000_09_00.1.hdmi-stereo`)
     - **Controller:** Console Docked Mode (when an external controller is connected, the built-in controller hides into `mode=hidden`, promoting the external pad to Player 1)
  3. ⚡ **`docked_amd_vrr` (AMD FreeSync / 120Hz+ High-Refresh Gaming Monitor):**
     - **TDP:** `performance` (Turbo 30W)
     - **CPU EPP:** `performance`
     - **GPU DPM:** `high` (locks RDNA3 compute engines at maximum dynamic frequency ceiling)
     - **Target FPS:** **0 (Uncapped / No frame limiter)**
     - **Audio:** External HDMI audio sink
     - **Controller:** Console Docked Mode

- **Fail-Safe Architecture:**
  - If an external display is physically connected but the EDID is corrupted, missing, or fails checksum validation, AllyDock safely defaults to `docked_tv_60` (60 FPS, 25W).
  - When an external display is disconnected, the system unconditionally reverts to `handheld` (45 FPS, 15W).

---

### 2. 🎮 Console-Style Docked Mode (External Controller Priority & Arbitration)
- **The Problem:** When placing the ROG Ally into a docking station and connecting it to a TV along with a wireless or USB gamepad (such as an Xbox Wireless Controller or DualSense), the handheld's internal controller remained registered as the primary gamepad (`/dev/input/js0` / Player 1). Games launched from couch distance assigned the external pad to "Player 2", rendering couch gameplay impossible without tedious manual controller reordering.
- **The AllyDock Solution:** `ally-docked-mode.sh` coordinates with udev to monitor external display and external controller attachment events:
  - **TV Connected + External Gamepad Present:** The Ally's internal gamepad is instantaneously hidden via the HHD IPC API (`controllers.rog_ally.controller_mode.mode=hidden`), elevating the external gamepad to **Player 1**.
  - **TV Connected without External Gamepad:** The internal gamepad remains fully active (`mode=uinput`) for comfortable handheld-style controls while playing in front of a big screen.
  - **Handheld Mode (Undocked):** Internal controller mode is immediately restored to its default state.

---

### 3. 🛡️ Controller Flapping Fix (Loop Elimination)
- **The Problem (Why controllers were disconnecting and cycling):**
  1. Legacy community scripts attempted to disable the built-in controller by physically unbinding the kernel USB device: `echo 1-2:1.0 > /sys/bus/usb/drivers/xpad/unbind`. This forcibly invalidated file descriptors inside Gamescope (`Failed to open device /dev/input/event17`) and flooded kernel logs with URB transfer errors (`unable to receive magic message: -32`).
  2. HHD emulates an `Xbox Elite` controller to expose the rear macro paddles (M1/M2) to Steam Input. Outdated scripts mistakenly identified this **virtual Xbox Elite device as a physical external gamepad**!
  3. This triggered a recursive flapping loop (cycling 10+ times per minute): the system detected its own virtual gamepad, disabled the controller, noticed zero gamepads were present, re-enabled it, and repeated indefinitely.
- **The AllyDock Solution:**
  - Completely purged destructive `xpad unbind` calls. Controller arbitration is managed exclusively via the official HHD high-level API.
  - Strict udev filtering explicitly ignores `/devices/virtual/input/*`, guaranteeing deterministic distinction between physical USB/Bluetooth gamepads and virtual emulated input nodes.
  - File-based mutex lock (`flock` on `/var/home/V/.local/share/ally-docked.lock`) guarantees atomic execution and eliminates race conditions during rapid hotplug events.

---

### 4. 🔊 Smart PipeWire Audio Router (HDMI TV vs. Calibrated DSP Speakers)
- **The Problem:** PipeWire exposes 4 distinct audio endpoints on the ROG Ally: the raw Realtek ALC294 DAC (`analog-stereo`), the HDMI audio output (`hdmi-stereo`), the spatial audio filter `effect_input.spatializer`, and the hardware-calibrated `ROG Ally` DSP speaker processing node. When docking to a TV, audio frequently routed to the raw ALC294 DAC (yielding flat, tinny sound without bass) or remained trapped on the handheld.
- **The AllyDock Solution:** `ally-docked-mode.sh` automatically arbitrates the active Default Audio Sink:
  - When docked to a TV: Audio routes to `alsa_output.pci-0000_09_00.1.hdmi-stereo` (TV speakers or living-room soundbar).
  - When undocked: Audio returns to the hardware-calibrated **`ROG Ally`** DSP equalizer sink, restoring rich acoustic dynamics and deep bass response.

---

### 5. 🐕 Robust Watchdog & System-Sleep Recovery
- **Dynamic Watchdog (`bin/hhd-watchdog.sh`):** Intelligently detects the active input daemon stack (`hhd.service` on Bazzite 43 or `inputplumber.service` on Bazzite 44) and manages service health. Runs seamlessly as a `systemd` timer every 15 minutes with zero measurable CPU overhead.
- **Sleep Recovery Hook (`sleep/10-hhd-watchdog-sleep.sh`):** Installed into `/etc/systemd/system-sleep/`. Re-synchronizes controller states and restores proper input mappings immediately after the device wakes from suspend.

---

### 6. 📜 Steam Desktop Layout: Smooth Vertical Turbo-Scrolling
- **The Problem:** The stock Steam Desktop Layout configures analog sticks for discrete single keystrokes or arrow clicks, turning web browsing and document navigation into a painfully slow, staccato chore.
- **The AllyDock Solution:** In `desktop_xboxone.vdf` and `desktop_neptune.vdf`, the left analog stick is mapped to `mouse_wheel SCROLL_UP` and `mouse_wheel SCROLL_DOWN` with calibrated **Turbo Repeat**:
  ```vdf
  "hold_repeats" "1"
  "repeat_rate"  "20"
  ```
  Tilting the left stick up or down delivers continuous, fluid, momentum-like scrolling through websites and documents.

---

### 7. 🎯 Precision Right Stick (Cursor Ballistics & Jitter Smoothing)
- **The Problem:** Cursor jitter when targeting fine desktop UI elements, or unpredictable non-linear cursor acceleration.
- **The AllyDock Solution:** Calibrated tracking parameters:
  - `"sensitivity" "130"` — tuned baseline sensitivity.
  - `"response_curve" "2"` — exponential response curve: micro-movements near deadzone provide sub-pixel accuracy, full deflections sweep rapidly across the 1080p display.
  - `"mouse_smoothing" "1"` — hardware-level micro-jitter suppression for finger tremor elimination.
  - `"deadzone_inner_radius" "6000"` — clean deadzone completely eliminating stick drift.

---

## 📂 Repository Structure & File Overview

```
AllyDock/
├── VERSION                          # Version identifier (1.1.0)
├── README.md                        # Comprehensive documentation and technical specification
├── restore.sh                       # Unified bash deployment script (one-command setup)
├── bin/
│   ├── ally-detect-display.py       # Display detection engine: EDID, VESA checksum, FreeSync, HDMI VRR, Hz
│   ├── ally-docked-mode.sh          # Primary adaptive orchestrator (3 profiles, TDP, EPP, FPS, Audio)
│   └── hhd-watchdog.sh              # Watchdog daemon for self-healing HHD / InputPlumber services
├── hhd/
│   └── state.yml                    # Exported working HHD configuration (DualSense/Xbox, paddles as Steam Input)
├── sleep/
│   └── 10-hhd-watchdog-sleep.sh     # System sleep hook for /etc/systemd/system-sleep/ (suspend/resume handler)
├── steam/
│   ├── desktop_neptune.vdf          # Patched Steam Input Desktop Layout (Neptune / Deck style)
│   └── desktop_xboxone.vdf          # Patched Steam Input Desktop Layout (Xbox One / Ally style)
├── systemd/
│   ├── ally-docked.service          # Oneshot system service executing dock state transitions
│   ├── hhd-watchdog.service         # Background service unit verifying input daemon health
│   └── hhd-watchdog.timer           # Systemd timer unit triggering watchdog checks every 15 minutes
└── udev/
    └── 99-ally-docked.rules         # Udev event rules for DRM/HDMI display and USB gamepad hotplug
```

---

## ⚡ Quick Installation & Restoration (Quick Start)

Whether you reinstalled Bazzite OS, performed a system rebase to a new Fedora release, or are deploying AllyDock on a fresh configuration:

### Step 1. Clone the repository and navigate into the project directory
```bash
git clone https://github.com/VadymTaras/AllyDock.git && cd AllyDock && sudo ./restore.sh
```

### What `restore.sh` executes automatically:
- Creates required directory structures across `/etc/` and the user home directory (`/var/home/V/`).
- Installs and applies executable permissions to `ally-docked-mode.sh`, `ally-detect-display.py`, and `hhd-watchdog.sh`.
- Installs udev rules and executes `udevadm control --reload-rules && udevadm trigger`.
- Deploys `ally-docked.service`, `hhd-watchdog.service`, and activates `hhd-watchdog.timer`.
- Installs the system sleep hook `/etc/systemd/system-sleep/10-hhd-watchdog-sleep.sh`.
- Restores `/etc/hhd/state.yml` with proper system permissions.
- Installs the modified Steam Input Desktop Layout templates into `controller_base`.

### Step 2. Reboot your console
```bash
sudo systemctl reboot
```

---

## 🕹️ Desktop Mode Controls & Shortcuts

### Hardware Mouse Mode (HHD MCU Level)
Operates directly at the hardware microcontroller level (`0b05:1abe`), remaining fully functional even if Steam is closed or unresponsive:
- 🔘 **Toggle ON / OFF:** Press and hold the **Armoury Crate** button (top-right button with the ROG triangle logo) for **~1.5 seconds**.
  - **Double Haptic Pulse:** Hardware Mouse Mode ENABLED.
  - **Single Haptic Pulse:** Reverted to standard gamepad mode.
- 🕹️ **Right Stick:** Mouse cursor positioning.
- 🔘 **RB (Right Bumper):** Left Mouse Button (LMB).
- 🔘 **RT (Right Trigger):** Right Mouse Button (RMB).
- 🕹️ **Left Stick / D-Pad:** Vertical mouse wheel scroll.

### Software Mouse Mode (Steam Input Desktop Layout)
Active by default in KDE Plasma 6 Wayland desktop when Steam is running in the background:
- 🕹️ **Right Stick:** High-precision cursor ballistics (exponential curve + jitter smoothing).
- 🕹️ **Left Stick:** Smooth vertical turbo scrolling with rapid auto-repeat.
- 🔘 **RT (Right Trigger):** Left Mouse Button (LMB).
- 🔘 **LT (Left Trigger):** Right Mouse Button (RMB).

### Virtual Keyboard in Desktop Mode
- ⌨️ **HHD Shortcut:** Quick single tap on the **Armoury Crate** button.
- 👆 **Touchscreen Gesture:** Swipe up with one finger from the bottom screen bezel.
- 🎮 **Steam Shortcut:** Press **Command Center** button (left side of display) + **`X`**.
- 🖥️ **Wayland Virtual Keyboard:** Automatically pops up upon focusing text input fields in KDE Plasma.

---

## 🛠️ CLI Diagnostic Commands

### Comprehensive System & Display Status
```bash
/var/home/V/.local/bin/ally-docked-mode.sh status
```

### Direct Display Detection Utility
```bash
# Human-readable diagnostic output:
/var/home/V/.local/bin/ally-detect-display.py

# Structured JSON output:
/var/home/V/.local/bin/ally-detect-display.py --json

# Shell environment format (for script evaluation):
/var/home/V/.local/bin/ally-detect-display.py --shell
```

### Manual Profile Switching
```bash
# Force handheld profile (15W Balanced, 45 FPS, internal DSP speakers):
/var/home/V/.local/bin/ally-docked-mode.sh handheld

# Force TV 60Hz profile (25W Performance, 60 FPS, HDMI audio):
/var/home/V/.local/bin/ally-docked-mode.sh docked-tv

# Force VRR Gaming profile (30W Turbo, Uncapped FPS, GPU High DPM, HDMI audio):
/var/home/V/.local/bin/ally-docked-mode.sh docked-vrr
```

### Manual Frame Rate Targets (MangoHud)
```bash
/var/home/V/.local/bin/ally-docked-mode.sh fps-45
/var/home/V/.local/bin/ally-docked-mode.sh fps-60
/var/home/V/.local/bin/ally-docked-mode.sh fps-uncapped
```

### Manual Audio Sink Switching
```bash
# Route audio to HDMI (TV / soundbar):
/var/home/V/.local/bin/ally-docked-mode.sh audio-hdmi

# Route audio to calibrated ROG Ally DSP speakers:
/var/home/V/.local/bin/ally-docked-mode.sh audio-speaker
```

### Logs & Service Verification
```bash
/var/home/V/.local/bin/ally-docked-mode.sh log
systemctl status hhd-watchdog.timer
systemctl status hhd-watchdog.service
```

---

## 📜 Disclaimer & MIT License

The **AllyDock** suite was designed, tuned, and tested for the ASUS ROG Ally on Bazzite OS. Distributed under the permissive [MIT License](LICENSE) — feel free to use, modify, and integrate it into your own handheld builds!
