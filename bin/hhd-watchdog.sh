#!/usr/bin/env bash
# HHD & InputPlumber Watchdog & Auto-Recovery for ASUS ROG Ally (Bazzite)
# Non-blocking, light footprint, verifies both service and internal hardware controller.

LOG_FILE="/var/home/V/.local/share/hhd-watchdog.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

get_daemon_service() {
    if systemctl list-unit-files inputplumber.service 2>/dev/null | grep -q "inputplumber.service"; then
        echo "inputplumber.service"
    else
        echo "hhd.service"
    fi
}

check_hhd() {
    local daemon
    daemon=$(get_daemon_service)

    # 0. Check if deliberately in docked mode (internal controller disabled)
    local docked_state=""
    [ -f "/var/home/V/.local/share/ally-docked.state" ] && docked_state=$(cat "/var/home/V/.local/share/ally-docked.state")
    if [ "$docked_state" = "docked_disabled" ]; then
        log "INFO: Ally у Docked Mode (вбудований контролер вимкнено навмисно). Пропуск перевірки."
        return 0
    fi

    # 1. Check if the active daemon service is running
    if ! systemctl is-active --quiet "$daemon"; then
        log "WARNING: $daemon не активний! Перезапуск..."
        sudo systemctl restart "$daemon"
        sleep 2
    fi

    # 2. Check if internal ROG Ally gamepad is alive
    local internal_controller_ok=1

    if [ "$daemon" = "inputplumber.service" ]; then
        # InputPlumber must have ASUS ROG Ally in its composite devices list
        if ! inputplumber devices list 2>/dev/null | grep -q "ASUS ROG Ally"; then
            internal_controller_ok=0
        fi
        # And joystick node must be present
        if ! ls /dev/input/js* 1>/dev/null 2>&1; then
            internal_controller_ok=0
        fi
    else
        # For HHD fallback
        if ! ls /dev/input/by-id/*Controller* 1>/dev/null 2>&1 && ! ls /dev/input/js* 1>/dev/null 2>&1; then
            internal_controller_ok=0
        fi
    fi

    if [ "$internal_controller_ok" -eq 1 ]; then
        return 0
    fi

    log "WARNING: $daemon активний, але вбудований геймпад ROG Ally втрачено/скинуто в мишу! Автоматичний ребут сервісу..."
    if [ "$daemon" = "hhd.service" ] && [ -f /etc/hhd/state.yml ]; then
        sudo cp -f /etc/hhd/state.yml /etc/hhd/state.yml.bak
    fi

    sudo systemctl restart "$daemon"
    sleep 2

    if [ "$daemon" = "inputplumber.service" ]; then
        if inputplumber devices list 2>/dev/null | grep -q "ASUS ROG Ally" && ls /dev/input/js* 1>/dev/null 2>&1; then
            log "RECOVERED: InputPlumber успішно відновив вбудований геймпад ROG Ally."
            return 0
        fi
    elif ls /dev/input/js* 1>/dev/null 2>&1; then
        log "RECOVERED: Контролер успішно переініціалізовано."
        return 0
    fi

    log "ERROR: Контролер не з'явився після рестарту. Перевірте journalctl -u $daemon."
    return 1
}

case "${1:-check}" in
    status)
        daemon=$(get_daemon_service)
        systemctl status "$daemon" --no-pager
        echo "=== Input Devices ==="
        ls -la /dev/input/by-id/ 2>/dev/null
        ;;
    restart|recover)
        daemon=$(get_daemon_service)
        sudo systemctl restart "$daemon"
        check_hhd
        ;;
    check)
        check_hhd
        ;;
    log)
        [ -f "$LOG_FILE" ] && tail -n 30 "$LOG_FILE" || echo "Лог порожній."
        ;;
    *)
        echo "Використання: $0 {check|status|restart|recover|log}"
        exit 1
        ;;
esac
