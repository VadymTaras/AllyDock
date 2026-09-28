#!/usr/bin/env bash
# AllyDock Docked Mode, Display Detector & 3-Tier Adaptive Profiler (v1.1.0)
# Supports Handheld 45 FPS vs Docked 60Hz TV vs Docked AMD FreeSync/VRR Uncapped Gaming.
# Event-driven: Triggered by udev (display/gamepad connection) or resume hook.
# Zero idle CPU consumption, no background while-loop.

LOG_FILE="/var/home/V/.local/share/ally-docked.log"
CTRL_STATE_FILE="/var/home/V/.local/share/ally-docked.state"
TDP_STATE_FILE="/var/home/V/.local/share/ally-tdp.state"
AUDIO_STATE_FILE="/var/home/V/.local/share/ally-audio.state"
FPS_STATE_FILE="/var/home/V/.local/share/ally-fps.state"
PROFILE_STATE_FILE="/var/home/V/.local/share/ally-profile.state"
DISPLAY_STATE_FILE="/var/home/V/.local/share/ally-display.state"
LOCK_FILE="/var/home/V/.local/share/ally-docked.lock"
MANGOHUD_CONF="/var/home/V/.config/MangoHud/MangoHud.conf"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Run audio command in user session with proper PipeWire environment
run_user_audio_cmd() {
    local cmd="$1"
    if [ "$(id -u)" -eq 0 ]; then
        sudo -u V env \
            XDG_RUNTIME_DIR=/run/user/1000 \
            PULSE_SERVER=unix:/run/user/1000/pulse/native \
            DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
            bash -c "$cmd" 2>/dev/null || true
    else
        env \
            XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}" \
            PULSE_SERVER="${PULSE_SERVER:-unix:/run/user/1000/pulse/native}" \
            DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/1000/bus}" \
            bash -c "$cmd" 2>/dev/null || true
    fi
}

get_current_sink() {
    local sink
    if [ "$(id -u)" -eq 0 ]; then
        sink=$(sudo -u V env XDG_RUNTIME_DIR=/run/user/1000 PULSE_SERVER=unix:/run/user/1000/pulse/native pactl get-default-sink 2>/dev/null)
    else
        sink=$(env XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}" PULSE_SERVER="${PULSE_SERVER:-unix:/run/user/1000/pulse/native}" pactl get-default-sink 2>/dev/null)
    fi
    echo "${sink:-N/A}"
}

write_sysfs() {
    local val="$1"
    local path="$2"
    [ -f "$path" ] || return 0
    if [ -w "$path" ]; then
        echo "$val" > "$path" 2>/dev/null || true
    elif command -v sudo >/dev/null 2>&1; then
        sudo sh -c "echo '$val' > '$path'" 2>/dev/null || true
    fi
}

find_detector() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -x "$script_dir/ally-detect-display.py" ]; then
        echo "$script_dir/ally-detect-display.py"
    elif [ -x "/var/home/V/.local/bin/ally-detect-display.py" ]; then
        echo "/var/home/V/.local/bin/ally-detect-display.py"
    elif [ -f "$script_dir/ally-detect-display.py" ]; then
        echo "$script_dir/ally-detect-display.py"
    elif [ -f "/var/home/V/.local/bin/ally-detect-display.py" ]; then
        echo "/var/home/V/.local/bin/ally-detect-display.py"
    fi
}

run_detection() {
    local detector
    detector=$(find_detector)
    if [ -n "$detector" ]; then
        python3 "$detector" --shell 2>/dev/null || true
    else
        # Fallback if python detector is missing
        if is_external_display_connected; then
            echo 'STATUS="connected"'
            echo 'PROFILE="docked_tv_60"'
            echo 'NAME="External Display"'
            echo 'MAX_HZ="60"'
            echo 'VRR="false"'
            echo 'VRR_TYPE="None"'
            echo 'DESCRIPTION="Standard 60Hz TV / Monitor"'
            echo 'CONNECTOR="external"'
        else
            echo 'STATUS="disconnected"'
            echo 'PROFILE="handheld"'
            echo 'NAME="Internal eDP"'
            echo 'MAX_HZ="120"'
            echo 'VRR="true"'
            echo 'VRR_TYPE="ROG Ally FreeSync Premium"'
            echo 'DESCRIPTION="ROG Ally Internal 120Hz FreeSync Display (Handheld)"'
            echo 'CONNECTOR="internal"'
        fi
    fi
}

is_external_display_connected() {
    for s in /sys/class/drm/card*-*/status; do
        [ -e "$s" ] || continue
        # Ignore internal panel (eDP) and virtual writeback
        case "$s" in
            *-eDP-*|*-Writeback-*) continue ;;
        esac
        if grep -q "^connected" "$s" 2>/dev/null; then
            return 0
        fi
    done
    return 1
}

is_external_controller_connected() {
    local ext_found=0
    for js in /dev/input/js*; do
        [ -e "$js" ] || continue
        local devpath=""
        devpath=$(udevadm info -q property -n "$js" 2>/dev/null | grep '^DEVPATH=' | cut -d= -f2)

        # 1. Skip ROG Ally internal hardware (USB port 1-2)
        case "$devpath" in
            */usb1/1-2/*) continue ;;
        esac

        # 2. Skip virtual devices (uinput, HHD virtual Xbox Elite pad, steam virtual)
        case "$devpath" in
            */virtual/input/*) continue ;;
        esac

        local name=""
        name=$(cat "/sys/class/input/$(basename "$js")/device/name" 2>/dev/null || true)
        case "$name" in
            *"Handheld Daemon"*|*"Steam"*|*"ASUSTeK"*) continue ;;
        esac

        ext_found=1
        break
    done
    [ "$ext_found" -eq 1 ]
}

set_power_profile() {
    local target="$1" # "performance" or "balanced"
    local cur_target=""
    [ -f "$TDP_STATE_FILE" ] && cur_target=$(cat "$TDP_STATE_FILE" 2>/dev/null)

    if [ "$cur_target" != "$target" ]; then
        log "Зміна режиму TDP: $target (попередній: ${cur_target:-none})"

        # 1. HHD daemon TDP mode (Bazzite Handheld Daemon)
        if command -v hhdctl >/dev/null 2>&1; then
            sudo hhdctl set tdp.asus.tdp_v2.mode="$target" 2>/dev/null || true
        fi

        # 2. Kernel ACPI platform_profile direct set
        if [ -f /sys/firmware/acpi/platform_profile ]; then
            write_sysfs "$target" "/sys/firmware/acpi/platform_profile"
        fi

        # 3. powerprofilesctl (якщо присутній у системі)
        if command -v powerprofilesctl >/dev/null 2>&1; then
            powerprofilesctl set "$target" 2>/dev/null || true
        fi

        echo "$target" > "$TDP_STATE_FILE"
        local actual_profile
        actual_profile=$(cat /sys/firmware/acpi/platform_profile 2>/dev/null || echo "unknown")
        log "Профіль TDP встановлено: $target (актуальний ACPI platform_profile: $actual_profile)"
    fi
}

set_cpu_epp() {
    local target="$1" # "balance_power", "balance_performance", or "performance"
    local count=0
    local epp_files=(/sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference)
    if [ ! -e "${epp_files[0]}" ]; then
        epp_files=(/sys/devices/system/cpu/cpufreq/policy*/energy_performance_preference)
    fi
    if [ ! -e "${epp_files[0]}" ]; then
        epp_files=(/sys/devices/system/cpu/cpu*/power/energy_performance_preference)
    fi
    for epp in "${epp_files[@]}"; do
        [ -f "$epp" ] || continue
        write_sysfs "$target" "$epp"
        count=$((count + 1))
    done
    log "CPU EPP встановлено: $target ($count ядер)"
}

set_gpu_dpm() {
    local target="$1" # "high" or "auto"
    for dpm in /sys/class/drm/card*/device/power_dpm_force_performance_level; do
        [ -f "$dpm" ] || continue
        write_sysfs "$target" "$dpm"
    done
    log "GPU DPM рівень встановлено: $target"
}

set_fps_target() {
    local target="$1" # 45, 60, or 0 (uncapped)
    local cur_target=""
    [ -f "$FPS_STATE_FILE" ] && cur_target=$(cat "$FPS_STATE_FILE" 2>/dev/null)

    if [ "$cur_target" != "$target" ]; then
        log "Зміна цільового FPS: $target (попередній: ${cur_target:-none})"

        # 1. Update MangoHud configuration
        mkdir -p "$(dirname "$MANGOHUD_CONF")"
        if [ -f "$MANGOHUD_CONF" ]; then
            if grep -q "^fps_limit=" "$MANGOHUD_CONF"; then
                sed -i "s/^fps_limit=.*/fps_limit=$target/" "$MANGOHUD_CONF"
            else
                echo "fps_limit=$target" >> "$MANGOHUD_CONF"
            fi
        else
            echo "fps_limit=$target" > "$MANGOHUD_CONF"
        fi

        if [ "$(id -u)" -eq 0 ]; then
            chown V:V "$MANGOHUD_CONF" 2>/dev/null || true
        fi

        # 2. Record state file
        echo "$target" > "$FPS_STATE_FILE"
        if [ "$(id -u)" -eq 0 ]; then
            chown V:V "$FPS_STATE_FILE" 2>/dev/null || true
        fi

        log "Цільовий FPS ліміт оновлено: $target FPS (MangoHud: $MANGOHUD_CONF)"
    fi
}

set_audio_sink() {
    local target="$1" # "hdmi" or "speaker"
    local cur_target=""
    [ -f "$AUDIO_STATE_FILE" ] && cur_target=$(cat "$AUDIO_STATE_FILE" 2>/dev/null)

    if [ "$cur_target" != "$target" ]; then
        log "Зміна аудіо-виходу: $target (попередній: ${cur_target:-none})"

        if [ "$target" = "hdmi" ]; then
            run_user_audio_cmd '
                pactl set-default-sink alsa_output.pci-0000_09_00.1.hdmi-stereo 2>/dev/null || true
            '
            echo "hdmi" > "$AUDIO_STATE_FILE"
            local cur_sink
            cur_sink=$(get_current_sink)
            log "Аудіо встановлено: HDMI / ТВ (актуальний sink: $cur_sink)"
        else
            run_user_audio_cmd '
                # Перевага віддається каліброваному DSP-профілю "ROG Ally"
                if pactl list sinks short 2>/dev/null | grep -q "ROG Ally"; then
                    pactl set-default-sink "ROG Ally" 2>/dev/null || true
                else
                    pactl set-default-sink alsa_output.pci-0000_09_00.6.analog-stereo 2>/dev/null || true
                fi
            '
            echo "speaker" > "$AUDIO_STATE_FILE"
            local cur_sink
            cur_sink=$(get_current_sink)
            log "Аудіо встановлено: Динаміки ROG Ally (актуальний sink: $cur_sink)"
        fi
    fi
}

enable_internal_controller() {
    local cur_state=""
    [ -f "$CTRL_STATE_FILE" ] && cur_state=$(cat "$CTRL_STATE_FILE")
    if [ "$cur_state" != "enabled" ]; then
        log "UNDOCKED / STANDALONE: Відновлення вбудованого контролера..."
        # Restore HHD mode to uinput cleanly (DO NOT touch raw USB / xpad unbind!)
        if command -v hhdctl >/dev/null 2>&1; then
            sudo hhdctl set controllers.rog_ally.controller_mode.mode=uinput 2>/dev/null || true
        fi
        echo "enabled" > "$CTRL_STATE_FILE"
        log "Вбудований контролер відновлено (Handheld Mode)."
    fi
}

disable_internal_controller() {
    local cur_state=""
    [ -f "$CTRL_STATE_FILE" ] && cur_state=$(cat "$CTRL_STATE_FILE")
    if [ "$cur_state" != "docked_disabled" ]; then
        log "DOCKED (ТВ + зовнішній геймпад): Приховування вбудованого контролера..."
        # Set HHD controller mode to hidden cleanly (DO NOT touch raw USB / xpad unbind!)
        if command -v hhdctl >/dev/null 2>&1; then
            sudo hhdctl set controllers.rog_ally.controller_mode.mode=hidden 2>/dev/null || true
        fi
        echo "docked_disabled" > "$CTRL_STATE_FILE"
        log "Вбудований контролер приховано. Зовнішній контролер тепер Гравець 1 (TV Mode)."
    fi
}

apply_profile() {
    local target_profile="$1"
    local disp_name="${2:-Internal eDP}"
    local disp_hz="${3:-120}"
    local disp_vrr="${4:-true}"
    local disp_vrr_type="${5:-ROG Ally FreeSync Premium}"

    local ext_ctrl=0
    is_external_controller_connected && ext_ctrl=1

    echo "$target_profile" > "$PROFILE_STATE_FILE"
    echo "$disp_name (${disp_hz}Hz, VRR: $disp_vrr [$disp_vrr_type])" > "$DISPLAY_STATE_FILE"

    case "$target_profile" in
        handheld)
            log ">>> Профіль [HANDHELD]: Balanced 15-20W TDP, EPP balance_power, 45 FPS Cap, DSP Speakers, Internal Gamepad"
            set_power_profile "balanced"
            set_cpu_epp "balance_power"
            set_gpu_dpm "auto"
            set_fps_target "45"
            set_audio_sink "speaker"
            enable_internal_controller
            ;;
        docked_tv_60)
            log ">>> Профіль [DOCKED TV 60Hz]: Performance 25W TDP, EPP balance_performance, 60 FPS Fixed Lock, HDMI Audio"
            set_power_profile "performance"
            set_cpu_epp "balance_performance"
            set_gpu_dpm "auto"
            set_fps_target "60"
            set_audio_sink "hdmi"
            if [ "$ext_ctrl" -eq 1 ]; then
                disable_internal_controller
            else
                enable_internal_controller
            fi
            ;;
        docked_amd_vrr)
            log ">>> Профіль [DOCKED AMD VRR]: Turbo 30W Performance TDP, EPP performance, GPU DPM high, Uncapped (0 FPS), HDMI Audio"
            set_power_profile "performance"
            set_cpu_epp "performance"
            set_gpu_dpm "high"
            set_fps_target "0"
            set_audio_sink "hdmi"
            if [ "$ext_ctrl" -eq 1 ]; then
                disable_internal_controller
            else
                enable_internal_controller
            fi
            ;;
        *)
            log "УВАГА: Невідомий профіль '$target_profile', відкат до handheld"
            apply_profile "handheld" "$disp_name" "$disp_hz" "$disp_vrr" "$disp_vrr_type"
            ;;
    esac
}

check_mode() {
    # File lock to prevent race conditions during rapid udev events
    exec 200>"$LOCK_FILE"
    flock -n 200 || { log "Пропуск check_mode: інший екземпляр уже виконується"; return 0; }

    # Small settle time for USB / Bluetooth / DRM topology
    sleep 0.3

    local det_output
    det_output=$(run_detection)

    local STATUS="disconnected"
    local PROFILE="handheld"
    local NAME="Internal eDP"
    local MAX_HZ="120"
    local VRR="true"
    local VRR_TYPE="ROG Ally FreeSync Premium"
    local DESCRIPTION="ROG Ally Internal 120Hz FreeSync Display (Handheld)"
    local CONNECTOR="internal"

    eval "$det_output"

    log "Дисплейний статус: $NAME ($CONNECTOR, ${MAX_HZ}Hz, VRR=$VRR [$VRR_TYPE]) -> Профіль: $PROFILE"

    apply_profile "$PROFILE" "$NAME" "$MAX_HZ" "$VRR" "$VRR_TYPE"

    flock -u 200
}

case "${1:-check}" in
    status)
        det_output=$(run_detection)
        STATUS="disconnected"
        PROFILE="handheld"
        NAME="Internal eDP"
        MAX_HZ="120"
        VRR="true"
        VRR_TYPE="ROG Ally FreeSync Premium"
        DESCRIPTION="ROG Ally Internal 120Hz FreeSync Display (Handheld)"
        CONNECTOR="internal"
        eval "$det_output"

        cur_profile="unknown"
        [ -f "$PROFILE_STATE_FILE" ] && cur_profile=$(cat "$PROFILE_STATE_FILE")
        cur_disp="unknown"
        [ -f "$DISPLAY_STATE_FILE" ] && cur_disp=$(cat "$DISPLAY_STATE_FILE")
        cur_ctrl="enabled"
        [ -f "$CTRL_STATE_FILE" ] && cur_ctrl=$(cat "$CTRL_STATE_FILE")
        cur_tdp="not recorded"
        [ -f "$TDP_STATE_FILE" ] && cur_tdp=$(cat "$TDP_STATE_FILE")
        cur_fps="not recorded"
        [ -f "$FPS_STATE_FILE" ] && cur_fps=$(cat "$FPS_STATE_FILE")
        cur_audio="not recorded"
        [ -f "$AUDIO_STATE_FILE" ] && cur_audio=$(cat "$AUDIO_STATE_FILE")

        cur_acpi=$(cat /sys/firmware/acpi/platform_profile 2>/dev/null || echo "N/A")
        cur_epp=$(cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference 2>/dev/null || cat /sys/devices/system/cpu/cpufreq/policy0/energy_performance_preference 2>/dev/null || cat /sys/devices/system/cpu/cpu0/power/energy_performance_preference 2>/dev/null || echo "N/A")
        cur_dpm=$(cat /sys/class/drm/card0/device/power_dpm_force_performance_level 2>/dev/null || cat /sys/class/drm/card1/device/power_dpm_force_performance_level 2>/dev/null || echo "N/A")

        echo "======================================================================"
        echo "       ⚓ AllyDock Suite v1.1.0 — Status & Adaptive Profiling"
        echo "======================================================================"
        echo " [Display Detection]"
        echo "   Status:           ${STATUS^^}"
        echo "   Display Name:     $NAME"
        echo "   Connector:        $CONNECTOR"
        echo "   Max Refresh Rate: ${MAX_HZ} Hz"
        echo "   VRR Capable:      $VRR ($VRR_TYPE)"
        echo "   Classification:   $DESCRIPTION"
        echo ""
        echo " [Active System Profile]"
        echo "   Current Profile:  $cur_profile"
        echo "   Last Configured:  $cur_disp"
        echo "   Target FPS:       ${cur_fps} FPS (45=Handheld, 60=TV, 0=Uncapped VRR)"
        echo "   MangoHud Config:  $(grep -E '^fps_limit=' "$MANGOHUD_CONF" 2>/dev/null || echo 'Not configured')"
        echo ""
        echo " [Power & Hardware Clocks]"
        echo "   TDP Target:       $cur_tdp"
        echo "   ACPI Profile:     $cur_acpi"
        echo "   CPU EPP:          $cur_epp"
        echo "   GPU DPM Level:    $cur_dpm"
        if command -v hhdctl >/dev/null 2>&1; then
            echo "   HHD TDP Mode:     $(sudo hhdctl get tdp.asus.tdp_v2.mode 2>/dev/null || echo 'N/A')"
        fi
        echo ""
        echo " [Audio Output]"
        echo "   Target Route:     $cur_audio"
        echo "   Active Sink:      $(get_current_sink)"
        echo ""
        echo " [Controllers (Console-Style Mode)]"
        echo "   External Gamepad: $(is_external_controller_connected && echo 'YES (Connected)' || echo 'NO (None)')"
        echo "   Internal Gamepad: $cur_ctrl"
        if command -v hhdctl >/dev/null 2>&1; then
            echo "   HHD Mode:         $(sudo hhdctl get controllers.rog_ally.controller_mode.mode 2>/dev/null || echo 'N/A')"
            echo "   HHD Paddles As:   $(sudo hhdctl get controllers.rog_ally.controller_mode.uinput.paddles_as 2>/dev/null || echo 'N/A')"
        fi
        echo "======================================================================"
        ;;
    check|auto)
        check_mode
        ;;
    detect)
        det_bin=$(find_detector)
        if [ -n "$det_bin" ]; then
            python3 "$det_bin"
        else
            echo "ally-detect-display.py not found!"
        fi
        ;;
    handheld|profile-handheld)
        apply_profile "handheld" "Internal eDP" 120 "true" "ROG Ally FreeSync Premium"
        ;;
    docked-tv|profile-tv60)
        apply_profile "docked_tv_60" "Standard TV" 60 "false" "None"
        ;;
    docked-vrr|profile-vrr)
        apply_profile "docked_amd_vrr" "Gaming VRR Display" 120 "true" "AMD FreeSync"
        ;;
    enable)
        enable_internal_controller
        ;;
    disable)
        disable_internal_controller
        ;;
    tdp-performance)
        set_power_profile "performance"
        ;;
    tdp-balanced)
        set_power_profile "balanced"
        ;;
    fps-45)
        set_fps_target "45"
        ;;
    fps-60)
        set_fps_target "60"
        ;;
    fps-uncapped)
        set_fps_target "0"
        ;;
    audio-hdmi)
        set_audio_sink "hdmi"
        ;;
    audio-speaker)
        set_audio_sink "speaker"
        ;;
    log)
        [ -f "$LOG_FILE" ] && tail -n 35 "$LOG_FILE" || echo "Лог порожній."
        ;;
    *)
        echo "Використання: $0 {check|status|detect|handheld|docked-tv|docked-vrr|enable|disable|tdp-performance|tdp-balanced|fps-45|fps-60|fps-uncapped|audio-hdmi|audio-speaker|log}"
        exit 1
        ;;
esac
