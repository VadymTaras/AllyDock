#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_keepalive.py — Unit tests for bin/ally-keepalive.py (AllyDock Suite).
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import importlib.util

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "bin" / "ally-keepalive.py"
spec = importlib.util.spec_from_file_location("ally_keepalive", str(SCRIPT_PATH))
keepalive = importlib.util.module_from_spec(spec)
sys.modules["ally_keepalive"] = keepalive
spec.loader.exec_module(keepalive)


class TestAllyKeepalive(unittest.TestCase):
    @patch("subprocess.run")
    def test_reset_steam_idle_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        keepalive.reset_steam_idle()
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("SimulateUserActivity", args)
        self.assertIn("org.freedesktop.ScreenSaver", args)

    @patch("subprocess.run")
    def test_reset_steam_idle_failure_resilience(self, mock_run):
        mock_run.side_effect = Exception("DBus connection failed")
        # Should not raise exception
        keepalive.reset_steam_idle()

    def test_signal_handler(self):
        keepalive.RUNNING = True
        keepalive.signal_handler(15, None)
        self.assertFalse(keepalive.RUNNING)
        keepalive.RUNNING = True

    def test_max_idle_seconds_default(self):
        self.assertEqual(keepalive.MAX_IDLE_SECONDS, 1200)

    def test_input_monitor_ignores_keepalive_device(self):
        monitor = keepalive.InputActivityMonitor()
        self.assertIn("AllyDock Keepalive Device", monitor.ignore_names)

        mock_dev1 = MagicMock()
        mock_dev1.name = "AllyDock Keepalive Device"
        mock_dev2 = MagicMock()
        mock_dev2.name = "Xbox Wireless Controller"

        mock_evdev = MagicMock()
        mock_evdev.list_devices.return_value = ["/dev/input/event0", "/dev/input/event1"]

        def mock_input_device(path):
            if path == "/dev/input/event0":
                return mock_dev1
            return mock_dev2

        mock_evdev.InputDevice.side_effect = mock_input_device

        with patch.object(keepalive, "EVDEV_AVAILABLE", True), \
             patch.object(keepalive, "evdev", mock_evdev):
            monitor.refresh_devices()
            mock_dev1.close.assert_called_once()
            self.assertNotIn("/dev/input/event0", monitor.devices)
            self.assertIn("/dev/input/event1", monitor.devices)
            self.assertEqual(monitor.devices["/dev/input/event1"], mock_dev2)

    def test_input_monitor_poll_activity(self):
        monitor = keepalive.InputActivityMonitor()
        mock_dev = MagicMock()
        mock_dev.fd = 10

        # Mock events
        class MockEc:
            EV_SYN = 0
            EV_KEY = 1
            EV_REL = 2
            EV_ABS = 3
            KEY_RESERVED = 0

        mock_event_btn = MagicMock()
        mock_event_btn.type = MockEc.EV_KEY
        mock_event_btn.code = 304  # BTN_A
        mock_dev.read.return_value = [mock_event_btn]

        monitor.devices["/dev/input/event1"] = mock_dev
        monitor.last_scan = 1000000000.0  # skip rescan

        mock_evdev = MagicMock()
        with patch.object(keepalive, "EVDEV_AVAILABLE", True), \
             patch.object(keepalive, "evdev", mock_evdev), \
             patch.object(keepalive, "e", MockEc), \
             patch("select.select", return_value=([10], [], [])):
            activity = monitor.poll_activity(timeout=0.1)
            self.assertTrue(activity)

    def test_input_monitor_poll_ignores_syn_and_reserved_key(self):
        monitor = keepalive.InputActivityMonitor()
        mock_dev = MagicMock()
        mock_dev.fd = 10

        class MockEc:
            EV_SYN = 0
            EV_KEY = 1
            EV_REL = 2
            EV_ABS = 3
            KEY_RESERVED = 0

        ev_syn = MagicMock()
        ev_syn.type = MockEc.EV_SYN

        ev_reserved = MagicMock()
        ev_reserved.type = MockEc.EV_KEY
        ev_reserved.code = MockEc.KEY_RESERVED

        mock_dev.read.return_value = [ev_syn, ev_reserved]
        monitor.devices["/dev/input/event1"] = mock_dev
        monitor.last_scan = 1000000000.0

        mock_evdev = MagicMock()
        with patch.object(keepalive, "EVDEV_AVAILABLE", True), \
             patch.object(keepalive, "evdev", mock_evdev), \
             patch.object(keepalive, "e", MockEc), \
             patch("select.select", return_value=([10], [], [])):
            activity = monitor.poll_activity(timeout=0.1)
            self.assertFalse(activity)


if __name__ == "__main__":
    unittest.main()
