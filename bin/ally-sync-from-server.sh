#!/usr/bin/env bash
# ally-sync-from-server.sh
# Автоматичне підтягування оновлень з домашнього сервера на ASUS ROG Ally.
# Стандарти: ADR-014 (Automated Sync) та ADR-015 (Zero-Clutter XDG Compliance).

set -euo pipefail

TARGET_USER="V"
USER_HOME="/var/home/$TARGET_USER"
SERVER_USER="v"
SERVER_CANDIDATES=("192.168.1.209" "192.168.1.140" "llm.lan")

ACTIVE_SERVER=""
for srv in "${SERVER_CANDIDATES[@]}"; do
    if ping -c 1 -W 1 "$srv" >/dev/null 2>&1; then
        if ssh -o ConnectTimeout=2 -o BatchMode=yes "$SERVER_USER@$srv" "true" >/dev/null 2>&1; then
            ACTIVE_SERVER="$srv"
            break
        fi
    fi
done

if [ -z "$ACTIVE_SERVER" ]; then
    echo "[sync] Сервер недоступний або пристрій поза домашньою мережею. Пропускаю синхронізацію."
    exit 0
fi

echo "[sync] Знайдено активний сервер: $ACTIVE_SERVER. Перевірка оновлень..."

# Базові каталоги згідно з XDG стандартом (ADR-015)
GL_DIR="$USER_HOME/.local/share/gamelocalize"
GL_APP="$GL_DIR/app"
GL_VENV="$GL_DIR/venv"
GL_MODELS="$GL_DIR/models"
BIN_DIR="$USER_HOME/.local/bin"

mkdir -p "$GL_APP" "$GL_MODELS" "$BIN_DIR" "$USER_HOME/.config/gamelocalize"

# 1. Перевірка хешу версії
SERVER_HASH=$(ssh -o ConnectTimeout=3 "$SERVER_USER@$ACTIVE_SERVER" "git -C /home/v/workspace/gamelocalize rev-parse --short HEAD 2>/dev/null || echo 'latest'")
LOCAL_HASH=$(cat "$GL_DIR/.server_commit" 2>/dev/null || echo "none")

if [ "$SERVER_HASH" != "$LOCAL_HASH" ] || [ ! -d "$GL_APP/gamelocalize" ]; then
    echo "[sync] Оновлення GameLocalize ($LOCAL_HASH -> $SERVER_HASH)..."

    # Синхронізація ядра, словників та плагіна
    rsync -aqz --delete "$SERVER_USER@$ACTIVE_SERVER:/home/v/workspace/gamelocalize/gamelocalize/" "$GL_APP/gamelocalize/"
    rsync -aqz "$SERVER_USER@$ACTIVE_SERVER:/home/v/workspace/gamelocalize/dictionaries/" "$GL_APP/dictionaries/"
    rsync -aqz "$SERVER_USER@$ACTIVE_SERVER:/home/v/workspace/gamelocalize/bazzite_plugin/" "$GL_APP/bazzite_plugin/"

    # Синхронізація моделей (якщо присутні на сервері)
    rsync -aqz "$SERVER_USER@$ACTIVE_SERVER:/home/v/workspace/gamelocalize/models/" "$GL_MODELS/" 2>/dev/null || true

    # Фіксація коміту
    echo "$SERVER_HASH" > "$GL_DIR/.server_commit"

    # Оновлення симлінка для Decky Loader
    if [ -d "/homebrew/plugins" ]; then
        if [ -w "/homebrew/plugins" ]; then
            unlink /homebrew/plugins/GameVoice 2>/dev/null || true
            unlink /homebrew/plugins/GameLocalize 2>/dev/null || true
            ln -sf "$GL_APP/bazzite_plugin" /homebrew/plugins/GameLocalize
        elif sudo -n true 2>/dev/null; then
            sudo unlink /homebrew/plugins/GameVoice 2>/dev/null || true
            sudo unlink /homebrew/plugins/GameLocalize 2>/dev/null || true
            sudo ln -sf "$GL_APP/bazzite_plugin" /homebrew/plugins/GameLocalize
        fi
    fi

    # Перезапуск служби GameLocalize (Zero-Disruption)
    systemctl --user restart gamelocalize.service 2>/dev/null || true
    echo "[sync] GameLocalize успішно оновлено до $SERVER_HASH!"
else
    echo "[sync] GameLocalize актуальний ($LOCAL_HASH)."
fi

# 2. Синхронізація скриптів AllyDock
echo "[sync] Перевірка скриптів AllyDock..."
rsync -aqz "$SERVER_USER@$ACTIVE_SERVER:/home/v/workspace/AllyDock/bin/" "$BIN_DIR/" 2>/dev/null || true
chmod +x "$BIN_DIR"/*.sh "$BIN_DIR"/*.py 2>/dev/null || true

echo "[sync] Синхронізацію успішно завершено!"
