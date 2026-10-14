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


if __name__ == "__main__":
    unittest.main()
