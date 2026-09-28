#!/usr/bin/env bash
# ASUS ROG Ally Backup & Restoration Script
# Runs on ROG Ally (Bazzite OS) to restore all tuned scripts, udev rules, systemd units, HHD state, and Steam desktop configurations.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION=$(cat VERSION 2>/dev/null || echo "1.0.0")
echo "===================================================="
echo "       ⚓ AllyDock Suite for Bazzite OS v$VERSION"
echo "===================================================="

if [ "$EUID" -ne 0 ]; then
    echo "[-] Будь ласка, запустіть цей скрипт з правами sudo або від root: sudo ./restore.sh"
    exit 1
fi

TARGET_USER="V"
USER_HOME="/var/home/$TARGET_USER"

echo "[+] Відновлення скриптів у $USER_HOME/.local/bin..."
mkdir -p "$USER_HOME/.local/bin"
cp -f bin/ally-docked-mode.sh "$USER_HOME/.local/bin/"
cp -f bin/hhd-watchdog.sh "$USER_HOME/.local/bin/"
chmod +x "$USER_HOME/.local/bin/"*.sh
chown -R "$TARGET_USER:$TARGET_USER" "$USER_HOME/.local/bin"

echo "[+] Відновлення udev правил..."
cp -f udev/99-ally-docked.rules /etc/udev/rules.d/
udevadm control --reload-rules
udevadm trigger

echo "[+] Відновлення systemd служб та таймерів..."
cp -f systemd/ally-docked.service /etc/systemd/system/
cp -f systemd/hhd-watchdog.service /etc/systemd/system/
cp -f systemd/hhd-watchdog.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now hhd-watchdog.timer

echo "[+] Відновлення sleep хука..."
mkdir -p /etc/systemd/system-sleep
cp -f sleep/10-hhd-watchdog-sleep.sh /etc/systemd/system-sleep/
chmod +x /etc/systemd/system-sleep/10-hhd-watchdog-sleep.sh

echo "[+] Відновлення HHD state..."
mkdir -p /etc/hhd
cp -f hhd/state.yml /etc/hhd/state.yml
chown root:root /etc/hhd/state.yml
chmod 644 /etc/hhd/state.yml

echo "[+] Відновлення конфігурацій Steam Input Desktop Layout..."
mkdir -p "$USER_HOME/.local/share/Steam/controller_base"
cp -f steam/desktop_xboxone.vdf "$USER_HOME/.local/share/Steam/controller_base/"
cp -f steam/desktop_neptune.vdf "$USER_HOME/.local/share/Steam/controller_base/"
chown -R "$TARGET_USER:$TARGET_USER" "$USER_HOME/.local/share/Steam/controller_base"

echo "[+] Відновлення завершено успішно!"
echo "[+] Рекомендується зробити перезавантаження: sudo systemctl reboot"
