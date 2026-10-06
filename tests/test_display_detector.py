#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_display_detector.py — Юніт-тести для bin/ally-detect-display.py (AllyDock Suite).
Покриває:
1. Валідацію контрольних сум 128-байтних блоків EDID (sum % 256 == 0).
2. Перевірку магічного заголовка VESA EDID (00 FF FF FF FF FF FF 00).
3. Декодування 3-літерного коду виробника PNP ID.
4. Вилучення імені монітора (дескриптор 0xFC) та таймінгів.
5. Розпізнавання розширень CTA-861 (AMD FreeSync OUI 0x00001A та HDMI Forum VRR OUI 0xC45DD8).
6. Класифікацію профілів продуктивності:
   - Handheld (внутрішній дисплей ROG Ally, 45 FPS / 15W)
   - docked_tv_60 (зовнішній телевізор 60 Гц без VRR)
   - docked_amd_vrr (геймерський монітор з FreeSync / VRR або 120+ Гц)
   - Fail-safe fallback (пошкоджений EDID на підключеному кабелі -> docked_tv_60)
"""

import os
import sys
import tempfile
import unittest
import importlib.util
from pathlib import Path

# Динамічний імпорт скрипту з дефісами в назві
SCRIPT_PATH = Path(__file__).resolve().parent.parent / "bin" / "ally-detect-display.py"
spec = importlib.util.spec_from_file_location("ally_detect_display", str(SCRIPT_PATH))
detector = importlib.util.module_from_spec(spec)
sys.modules["ally_detect_display"] = detector
spec.loader.exec_module(detector)


def make_valid_edid_block(payload: bytes = b"") -> bytearray:
    """Генерує валідний 128-байтний блок з правильною VESA магією та контрольною сумою."""
    block = bytearray(128)
    # Magic VESA header: 00 FF FF FF FF FF FF 00
    block[0:8] = b"\x00\xff\xff\xff\xff\xff\xff\x00"

    # Заповнюємо кастомні байти
    if payload:
        copy_len = min(len(payload), 120)
        block[8:8 + copy_len] = payload[:copy_len]

    # Розрахунок контрольної суми: sum(block) % 256 == 0
    csum = (256 - (sum(block[:127]) % 256)) % 256
    block[127] = csum
    return block


def make_cta861_extension_block(vrr_type: str = "freesync", max_hz: int = 144) -> bytearray:
    """Генерує валідне 128-байтне розширення CTA-861 (CEA-861) з підтримкою VRR."""
    ext = bytearray(128)
    ext[0] = 0x02  # CTA-861 Extension Tag
    ext[1] = 0x03  # Revision 3
    ext[2] = 0x04  # DTD start offset (або кінець data blocks)

    pos = 4
    if vrr_type == "freesync":
        # AMD FreeSync VSDB: OUI 0x00001A, length 6
        # Byte 0 of payload: 0x1A, Byte 1: 0x00, Byte 2: 0x00 (Little-Endian)
        # Header: (tag=3 << 5) | len=6 -> 0x66
        ext[pos] = 0x66
        pos += 1
        ext[pos:pos + 6] = bytes([0x1A, 0x00, 0x00, 0x01, 0x30, max_hz])
        pos += 6
        ext[2] = pos  # DTD offset після блоку VSDB
    elif vrr_type == "hdmi_vrr":
        # HDMI Forum VRR VSDB: OUI 0xC45DD8, length 8
        # Header: (tag=3 << 5) | len=8 -> 0x68
        ext[pos] = 0x68
        pos += 1
        # Payload: OUI D8 5D C4 (LE), version/reserved, flags з VRR bit (0x08)
        ext[pos:pos + 8] = bytes([0xD8, 0x5D, 0xC4, 0x01, 0x00, 0x00, 0x00, 0x08])
        pos += 8
        ext[2] = pos

    # Розрахунок контрольної суми розширення
    csum = (256 - (sum(ext[:127]) % 256)) % 256
    ext[127] = csum
    return ext


class TestDisplayDetector(unittest.TestCase):
    """Набір тестів для парсера EDID та детектора дисплеїв ROG Ally."""

    def test_checksum_validation(self):
        """Перевірка алгоритму валідації контрольної суми EDID."""
        valid_block = bytes(make_valid_edid_block())
        self.assertTrue(detector.validate_edid_checksum(valid_block))

        # Пошкоджений байт
        corrupt_block = bytearray(valid_block)
        corrupt_block[50] = (corrupt_block[50] + 1) % 256
        self.assertFalse(detector.validate_edid_checksum(bytes(corrupt_block)))

        # Неправильна довжина блоку
        self.assertFalse(detector.validate_edid_checksum(b"short"))
        self.assertFalse(detector.validate_edid_checksum(bytes([0] * 127)))
        self.assertFalse(detector.validate_edid_checksum(bytes([0] * 129)))

    def test_vesa_magic_header(self):
        """Перевірка детекції валідного VESA EDID заголовка."""
        valid_edid = make_valid_edid_block()
        parsed = detector.parse_edid(bytes(valid_edid))
        self.assertNotIn("error", parsed)

        # Невалідний магічний заголовок
        bad_header = bytearray(valid_edid)
        bad_header[0] = 0xFF
        bad_header[1] = 0x00
        parsed_bad = detector.parse_edid(bytes(bad_header))
        self.assertIn("error", parsed_bad)
        self.assertEqual(parsed_bad["error"], "Invalid VESA EDID header magic")

    def test_pnp_id_extraction(self):
        """Перевірка вилучення 3-літерного ідентифікатора виробника PNP."""
        # ASUS (ASU): 'A'=1, 'S'=19, 'U'=21 -> бітові поля bytes 8..9
        # 'S' = 19, 'A' = 1, 'M' = 13 (SAM)
        # b8 = (19 << 2) | ((1 >> 3) & 0x3) -> SAM
        pnp = detector.parse_pnp_id(0x4C, 0x2D)
        self.assertIsInstance(pnp, str)
        self.assertEqual(len(pnp), 3)

    def test_monitor_name_descriptor(self):
        """Перевірка вилучення імені монітора з дескриптора 0xFC."""
        block = make_valid_edid_block()
        # Розміщуємо дескриптор 0xFC на зміщенні 54
        # Структура: 0x00, 0x00 (pixel clock = 0), 0x00, 0xFC (type), 0x00 (flags), string 13 bytes
        desc_name = b"ROG Ally TV\n "
        block[54:58] = bytes([0x00, 0x00, 0x00, 0xFC])
        block[58] = 0x00
        block[59:59 + len(desc_name)] = desc_name
        # Перераховуємо контрольну суму
        block[127] = (256 - (sum(block[:127]) % 256)) % 256

        parsed = detector.parse_edid(bytes(block))
        self.assertEqual(parsed.get("name"), "ROG Ally TV")

    def test_amd_freesync_vrr_detection(self):
        """Перевірка детекції AMD FreeSync через блок CTA-861."""
        base = make_valid_edid_block()
        base[126] = 1  # 1 розширення
        base[127] = (256 - (sum(base[:127]) % 256)) % 256

        ext = make_cta861_extension_block(vrr_type="freesync", max_hz=144)
        full_edid = bytes(base + ext)

        parsed = detector.parse_edid(full_edid)
        self.assertTrue(parsed.get("vrr"))
        self.assertIn("AMD FreeSync", parsed.get("vrr_type"))
        self.assertEqual(parsed.get("max_hz"), 144)

    def test_hdmi_forum_vrr_detection(self):
        """Перевірка детекції HDMI Forum VRR через блок CTA-861."""
        base = make_valid_edid_block()
        base[126] = 1
        base[127] = (256 - (sum(base[:127]) % 256)) % 256

        ext = make_cta861_extension_block(vrr_type="hdmi_vrr")
        full_edid = bytes(base + ext)

        parsed = detector.parse_edid(full_edid)
        self.assertTrue(parsed.get("vrr"))
        self.assertIn("HDMI Forum VRR", parsed.get("vrr_type"))

    def test_profile_classification_handheld(self):
        """Перевірка класифікації профілю Handheld (коли зовнішній дисплей не підключено)."""
        # Без mock файлу на Windows sys/class/drm відсутній -> Handheld
        info = detector.detect_display(mock_edid_path=None)
        self.assertEqual(info.get("profile"), "handheld")
        self.assertEqual(info.get("status"), "disconnected")
        self.assertEqual(info.get("max_hz"), 120)

    def test_profile_classification_standard_60hz_tv(self):
        """Перевірка класифікації профілю 60Hz TV (без VRR)."""
        base = make_valid_edid_block()
        # Встановлюємо 60 Гц у стандартні таймінги (байти 38..39)
        base[38] = 0x01
        base[39] = 0x00  # (0 & 0x3F) + 60 = 60 Hz
        base[127] = (256 - (sum(base[:127]) % 256)) % 256

        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(base)
            tmp_path = f.name

        try:
            res = detector.detect_display(mock_edid_path=tmp_path)
            self.assertEqual(res.get("status"), "connected")
            self.assertEqual(res.get("profile"), "docked_tv_60")
            self.assertFalse(res.get("vrr"))
            self.assertEqual(res.get("max_hz"), 60)
        finally:
            os.remove(tmp_path)

    def test_profile_classification_amd_vrr(self):
        """Перевірка класифікації профілю геймерського VRR монітора (FreeSync 144Hz)."""
        base = make_valid_edid_block()
        base[126] = 1
        base[127] = (256 - (sum(base[:127]) % 256)) % 256
        ext = make_cta861_extension_block(vrr_type="freesync", max_hz=144)
        full_data = bytes(base + ext)

        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(full_data)
            tmp_path = f.name

        try:
            res = detector.detect_display(mock_edid_path=tmp_path)
            self.assertEqual(res.get("status"), "connected")
            self.assertEqual(res.get("profile"), "docked_amd_vrr")
            self.assertTrue(res.get("vrr"))
            self.assertIn("AMD FreeSync", res.get("vrr_type"))
            self.assertEqual(res.get("max_hz"), 144)
        finally:
            os.remove(tmp_path)

    def test_profile_failsafe_corrupt_edid(self):
        """Перевірка безпечного відкату (fail-safe fallback) на docked_tv_60 при битому EDID."""
        corrupt_bytes = b"CORRUPTED_NON_VESA_DATA_BLOCK" * 4

        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(corrupt_bytes)
            tmp_path = f.name

        try:
            res = detector.detect_display(mock_edid_path=tmp_path)
            self.assertEqual(res.get("status"), "connected")
            # При підключеному кабелі з битим EDID система обирає безпечний телевізійний профіль 60Hz
            self.assertEqual(res.get("profile"), "docked_tv_60")
            self.assertFalse(res.get("vrr"))
            self.assertEqual(res.get("max_hz"), 60)
        finally:
            os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
