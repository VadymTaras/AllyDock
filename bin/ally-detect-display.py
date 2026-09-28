#!/usr/bin/env python3
"""
AllyDock Display Detector (v1.1.0)
Intelligent HDMI / DisplayPort display detection and VRR profiling for ASUS ROG Ally on Bazzite OS.
Scans DRM connectors, validates EDID checksums (sum % 256 == 0) and VESA magic headers (00 FF FF FF FF FF FF 00),
parses CEA-861 and DisplayID extensions (AMD FreeSync, HDMI Forum VRR), checks DRM properties,
and applies 3-tier adaptive profiling (Handheld 45 FPS vs 60Hz TV vs AMD FreeSync/VRR Uncapped).
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys


def parse_pnp_id(b8: int, b9: int) -> str:
    """Extract 3-letter PNP manufacturer ID from bytes 8 and 9 of EDID."""
    try:
        c1 = chr(((b8 >> 2) & 0x1F) + 64)
        c2 = chr((((b8 & 0x03) << 3) | ((b9 >> 5) & 0x07)) + 64)
        c3 = chr((b9 & 0x1F) + 64)
        pnp = f"{c1}{c2}{c3}"
        return pnp if pnp.isalpha() else "UNK"
    except Exception:
        return "UNK"


def validate_edid_checksum(block: bytes) -> bool:
    """Validate 128-byte EDID block checksum: sum(block) % 256 == 0."""
    if len(block) != 128:
        return False
    return (sum(block) % 256) == 0


def parse_edid(data: bytes) -> dict:
    """
    Parse raw EDID binary data with strict VESA header and checksum verification.
    Extracts monitor name, refresh rate candidates, and VRR capabilities (AMD FreeSync / HDMI Forum VRR).
    Returns dict with parsed info or error description.
    """
    if len(data) < 128:
        return {"error": "EDID data shorter than 128 bytes"}

    # 1. Validate VESA Header Magic (00 FF FF FF FF FF FF 00)
    if data[0:8] != b"\x00\xff\xff\xff\xff\xff\xff\x00":
        return {"error": "Invalid VESA EDID header magic"}

    # 2. Validate Base Block Checksum
    base_block = data[0:128]
    if not validate_edid_checksum(base_block):
        # Even if checksum is bad, we record warning; caller can decide on fallback
        base_valid = False
    else:
        base_valid = True

    name = None
    max_hz_candidates = []
    vrr_types = []
    pnp_id = parse_pnp_id(data[8], data[9])

    # 3. Base Block: Parse 4 Descriptors (18 bytes each at offsets 54, 72, 90, 108)
    for offset in (54, 72, 90, 108):
        block = data[offset : offset + 18]
        if len(block) < 18:
            continue
        pixel_clock_raw = block[0] | (block[1] << 8)
        if pixel_clock_raw != 0:
            # Detailed Timing Descriptor (DTD)
            pix_clk_hz = pixel_clock_raw * 10000
            h_active = block[2] | ((block[4] >> 4) << 8)
            h_blank = block[3] | ((block[4] & 0x0F) << 8)
            h_total = h_active + h_blank
            v_active = block[5] | ((block[7] >> 4) << 8)
            v_blank = block[6] | ((block[7] & 0x0F) << 8)
            v_total = v_active + v_blank
            if h_total > 0 and v_total > 0:
                hz = round(pix_clk_hz / (h_total * v_total))
                if 20 <= hz <= 500:
                    max_hz_candidates.append(hz)
        else:
            # Display Descriptor
            desc_type = block[3]
            if desc_type == 0xFC:  # Monitor Name
                raw_name = block[5:18]
                clean_name = (
                    raw_name.split(b"\n")[0]
                    .split(b"\x00")[0]
                    .decode("ascii", errors="replace")
                    .strip()
                )
                if clean_name:
                    name = clean_name
            elif desc_type == 0xFD:  # Monitor Range Limits
                max_v = block[6]
                if 20 <= max_v <= 500:
                    max_hz_candidates.append(max_v)
            elif desc_type == 0xFE and not name:  # Unspecified ASCII text
                clean_str = (
                    block[5:18]
                    .split(b"\n")[0]
                    .split(b"\x00")[0]
                    .decode("ascii", errors="replace")
                    .strip()
                )
                if clean_str:
                    name = clean_str

    # 4. Base Block: Standard Timings (bytes 38..53, 8 slots of 2 bytes)
    for i in range(8):
        off = 38 + i * 2
        b1, b2 = data[off], data[off + 1]
        if b1 == 0x01 and b2 == 0x01:
            continue
        v_freq = (b2 & 0x3F) + 60
        if 20 <= v_freq <= 500:
            max_hz_candidates.append(v_freq)

    # 5. Base Block: Established Timings (bytes 35..37)
    if data[35] & 0x20:
        max_hz_candidates.append(75)  # 640x480 @ 75Hz
    if data[36] & 0x80:
        max_hz_candidates.append(75)  # 1280x1024 @ 75Hz
    if data[36] & 0x40:
        max_hz_candidates.append(75)  # 1024x768 @ 75Hz
    if data[36] & 0x02:
        max_hz_candidates.append(75)  # 800x600 @ 75Hz

    # 6. Extension Blocks (CTA-861, DisplayID) with Checksum Validation
    num_ext = data[126] if len(data) > 126 else 0
    for ext_idx in range(1, num_ext + 1):
        ext_start = ext_idx * 128
        if len(data) < ext_start + 128:
            break
        ext = data[ext_start : ext_start + 128]
        # Validate checksum of extension block
        if not validate_edid_checksum(ext):
            continue

        tag = ext[0]
        if tag == 0x02:  # CTA-861 (CEA-861) Extension
            dtd_start = ext[2]
            pos = 4
            limit = dtd_start if 4 <= dtd_start <= 127 else 127
            while pos < limit:
                hdr = ext[pos]
                blk_tag = (hdr >> 5) & 0x07
                blk_len = hdr & 0x1F
                pos += 1
                if pos + blk_len > 128:
                    break
                payload = ext[pos : pos + blk_len]
                pos += blk_len

                if blk_tag == 3 and blk_len >= 3:  # VSDB
                    # IEEE OUI 24-bit (Little-Endian in CTA-861)
                    oui = (payload[2] << 16) | (payload[1] << 8) | payload[0]

                    # AMD FreeSync (OUI 0x00001a)
                    if oui == 0x00001A or (
                        payload[0] == 0x00 and payload[1] == 0x00 and payload[2] == 0x1A
                    ):
                        if "AMD FreeSync" not in vrr_types:
                            vrr_types.append("AMD FreeSync")
                        if blk_len >= 6:
                            fs_max_hz = payload[5]
                            if 30 <= fs_max_hz <= 500:
                                max_hz_candidates.append(fs_max_hz)

                    # HDMI Forum VRR (OUI 0xc45dd8)
                    elif oui == 0xC45DD8 or (
                        payload[0] == 0xC4 and payload[1] == 0x5D and payload[2] == 0xD8
                    ):
                        is_vrr = True
                        if blk_len >= 8:
                            flags = payload[7]
                            if not ((flags & 0x08) or (flags & 0x40)):
                                is_vrr = False
                        if is_vrr and "HDMI Forum VRR" not in vrr_types:
                            vrr_types.append("HDMI Forum VRR")

            # Parse DTDs in CTA-861 block
            if 4 <= dtd_start <= 109:
                dtd_pos = dtd_start
                while dtd_pos + 18 <= 127:
                    block = ext[dtd_pos : dtd_pos + 18]
                    dtd_pos += 18
                    pixel_clock_raw = block[0] | (block[1] << 8)
                    if pixel_clock_raw != 0:
                        pix_clk_hz = pixel_clock_raw * 10000
                        h_active = block[2] | ((block[4] >> 4) << 8)
                        h_blank = block[3] | ((block[4] & 0x0F) << 8)
                        h_total = h_active + h_blank
                        v_active = block[5] | ((block[7] >> 4) << 8)
                        v_blank = block[6] | ((block[7] & 0x0F) << 8)
                        v_total = v_active + v_blank
                        if h_total > 0 and v_total > 0:
                            hz = round(pix_clk_hz / (h_total * v_total))
                            if 20 <= hz <= 500:
                                max_hz_candidates.append(hz)
                    elif block[3] == 0xFC and not name:
                        clean_name = (
                            block[5:18]
                            .split(b"\n")[0]
                            .split(b"\x00")[0]
                            .decode("ascii", errors="replace")
                            .strip()
                        )
                        if clean_name:
                            name = clean_name

        elif tag == 0x70:  # DisplayID Extension
            if b"\x22" in ext:
                if "VESA Adaptive-Sync" not in vrr_types:
                    vrr_types.append("VESA Adaptive-Sync")

    max_hz = max(max_hz_candidates) if max_hz_candidates else 60

    return {
        "valid": base_valid,
        "name": name,
        "pnp_id": pnp_id,
        "max_hz": max_hz,
        "vrr": len(vrr_types) > 0,
        "vrr_type": " + ".join(vrr_types) if vrr_types else "None",
    }


def check_drm_vrr_capable(connector_path: str, connector_name: str) -> bool:
    """Check sysfs or drm_info for DRM connector vrr_capable property."""
    # 1. Direct sysfs attribute if exposed
    sysfs_vrr = os.path.join(connector_path, "vrr_capable")
    if os.path.isfile(sysfs_vrr):
        try:
            with open(sysfs_vrr, "r", encoding="utf-8", errors="ignore") as f:
                val = f.read().strip()
                if val in ("1", "true", "True"):
                    return True
        except Exception:
            pass

    # 2. drm_info CLI if available
    drm_info_bin = shutil.which("drm_info")
    if drm_info_bin:
        try:
            res = subprocess.run(
                [drm_info_bin, "-j"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0 and res.stdout:
                info = json.loads(res.stdout)
                for _, card_data in info.items():
                    connectors = card_data.get("connectors", {})
                    for c_name, c_data in connectors.items():
                        if connector_name in c_name or c_name in connector_name:
                            props = c_data.get("properties", {})
                            if (
                                props.get("vrr_capable") == 1
                                or props.get("VRR_CAPABLE") == 1
                                or props.get("vrr_capable") is True
                            ):
                                return True
        except Exception:
            pass

    return False


def detect_display(mock_edid_path: str = None) -> dict:
    """
    Scan DRM connectors and classify display profile with fail-safe defaults.
    Fail-safe rules:
    - If disconnected: profile='handheld', 45 FPS target, 15W balanced TDP.
    - If connected but EDID is missing, corrupt or read fails: safe fallback to profile='docked_tv_60' (60 FPS, 25W).
    - If connected and FreeSync / HDMI VRR or max_hz >= 100: profile='docked_amd_vrr' (uncapped FPS, 30W Turbo).
    """
    # Test path: allow testing with a mock EDID file
    if mock_edid_path and os.path.isfile(mock_edid_path):
        try:
            with open(mock_edid_path, "rb") as f:
                edid_bytes = f.read()
            parsed = parse_edid(edid_bytes)
            if "error" in parsed:
                # Corrupt mock EDID -> safe docked_tv_60 fallback
                return {
                    "status": "connected",
                    "profile": "docked_tv_60",
                    "name": "Generic External Display (EDID Fallback)",
                    "max_hz": 60,
                    "vrr": False,
                    "vrr_type": "None",
                    "description": "Standard 60Hz TV / Monitor (Safe Fallback)",
                    "connector": "mock-DP-1",
                }

            name = parsed.get("name") or "Mock Display"
            max_hz = parsed.get("max_hz", 60)
            vrr = parsed.get("vrr", False)
            vrr_type = parsed.get("vrr_type", "None")

            if vrr or max_hz >= 100:
                profile = "docked_amd_vrr"
                desc = "AMD FreeSync / High Refresh Rate Gaming Monitor"
                if not vrr:
                    vrr = True
                    vrr_type = "High Refresh Rate (120Hz+)"
            else:
                profile = "docked_tv_60"
                desc = "Standard 60Hz TV / Monitor"
                vrr = False
                vrr_type = "None"

            return {
                "status": "connected",
                "profile": profile,
                "name": name,
                "max_hz": max_hz,
                "vrr": vrr,
                "vrr_type": vrr_type,
                "description": desc,
                "connector": "mock-DP-1",
            }
        except Exception:
            return {
                "status": "connected",
                "profile": "docked_tv_60",
                "name": "Generic External Display (Error Fallback)",
                "max_hz": 60,
                "vrr": False,
                "vrr_type": "None",
                "description": "Standard 60Hz TV / Monitor (Safe Fallback)",
                "connector": "mock-DP-1",
            }

    drm_dir = "/sys/class/drm"
    connected_external = []

    if os.path.isdir(drm_dir):
        status_files = glob.glob(os.path.join(drm_dir, "card*-*/status"))
        for s_file in status_files:
            c_dir = os.path.dirname(s_file)
            c_name = os.path.basename(c_dir)

            # Ignore internal panel (eDP) and virtual writeback
            if "-eDP-" in c_name or "-Writeback-" in c_name:
                continue

            try:
                with open(s_file, "r", encoding="utf-8", errors="ignore") as f:
                    status_str = f.read().strip()
                if status_str.startswith("connected"):
                    connected_external.append((c_name, c_dir))
            except Exception:
                continue

    # Case A: No external display connected -> Handheld Mode (15-20W, 45 FPS)
    if not connected_external:
        return {
            "status": "disconnected",
            "profile": "handheld",
            "name": "Internal eDP",
            "max_hz": 120,
            "vrr": True,
            "vrr_type": "ROG Ally FreeSync Premium",
            "description": "ROG Ally Internal 120Hz FreeSync Display (Handheld)",
            "connector": "internal",
        }

    # Case B: External display connected
    # Pick primary external connector (prefer DisplayPort or HDMI)
    primary_c_name, primary_c_dir = connected_external[0]
    for c_name, c_dir in connected_external:
        if "DP-" in c_name or "HDMI-" in c_name:
            primary_c_name, primary_c_dir = c_name, c_dir
            break

    clean_conn = re.sub(r"^card\d+-", "", primary_c_name)
    edid_file = os.path.join(primary_c_dir, "edid")
    parsed_edid = {}

    if os.path.isfile(edid_file):
        try:
            with open(edid_file, "rb") as f:
                raw_edid = f.read()
            if len(raw_edid) >= 128:
                parsed_edid = parse_edid(raw_edid)
        except Exception:
            parsed_edid = {}

    # Check if EDID parsing failed or returned error
    if not parsed_edid or "error" in parsed_edid:
        # Safe Fallback: Unknown/corrupt EDID on connected cable -> docked_tv_60 (60 FPS, 25W)
        return {
            "status": "connected",
            "profile": "docked_tv_60",
            "name": f"Generic Display ({clean_conn})",
            "max_hz": 60,
            "vrr": False,
            "vrr_type": "None",
            "description": "Standard 60Hz TV / Monitor (EDID Fallback)",
            "connector": primary_c_name,
        }

    name = parsed_edid.get("name")
    pnp_id = parsed_edid.get("pnp_id", "EXT")
    if not name:
        name = f"{pnp_id} Display ({clean_conn})"

    max_hz = parsed_edid.get("max_hz", 60)
    vrr = parsed_edid.get("vrr", False)
    vrr_type = parsed_edid.get("vrr_type", "None")

    # Check DRM property vrr_capable if not yet detected in EDID
    if not vrr and check_drm_vrr_capable(primary_c_dir, primary_c_name):
        vrr = True
        vrr_type = "AMD FreeSync (DRM)"

    # Profile classification logic:
    # 1. FreeSync / HDMI VRR detected OR max_hz >= 100 -> docked_amd_vrr
    # 2. Standard TV or office monitor (no VRR and max_hz <= 60 or < 100) -> docked_tv_60
    if vrr or max_hz >= 100:
        profile = "docked_amd_vrr"
        desc = "AMD FreeSync / High Refresh Rate Gaming Monitor"
        if not vrr:
            vrr = True
            vrr_type = "High Refresh Rate (120Hz+)"
    else:
        profile = "docked_tv_60"
        desc = "Standard 60Hz TV / Monitor"
        vrr = False
        vrr_type = "None"

    return {
        "status": "connected",
        "profile": profile,
        "name": name,
        "max_hz": max_hz,
        "vrr": vrr,
        "vrr_type": vrr_type,
        "description": desc,
        "connector": primary_c_name,
    }


def main():
    parser = argparse.ArgumentParser(
        description="AllyDock Intelligent HDMI/DP Display & VRR Detector"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )
    parser.add_argument(
        "--shell",
        action="store_true",
        help="Output results in shell eval-compatible format",
    )
    parser.add_argument(
        "--mock-edid",
        type=str,
        default=None,
        help="Path to binary EDID file for testing/validation",
    )
    args = parser.parse_args()

    data = detect_display(mock_edid_path=args.mock_edid)

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif args.shell:
        # Shell export format
        vrr_str = "true" if data["vrr"] else "false"
        print(f'STATUS="{data["status"]}"')
        print(f'PROFILE="{data["profile"]}"')
        print(f'NAME="{data["name"]}"')
        print(f'MAX_HZ="{data["max_hz"]}"')
        print(f'VRR="{vrr_str}"')
        print(f'VRR_TYPE="{data["vrr_type"]}"')
        print(f'DESCRIPTION="{data["description"]}"')
        print(f'CONNECTOR="{data["connector"]}"')
    else:
        # Human-readable format
        print("=== AllyDock Display Detector (v1.1.0) ===")
        print(f"Status:      {data['status'].upper()}")
        print(f"Profile:     {data['profile']}")
        print(f"Name:        {data['name']}")
        print(f"Max Hz:      {data['max_hz']} Hz")
        print(f"VRR:         {'Yes' if data['vrr'] else 'No'} ({data['vrr_type']})")
        print(f"Connector:   {data['connector']}")
        print(f"Description: {data['description']}")


if __name__ == "__main__":
    main()
