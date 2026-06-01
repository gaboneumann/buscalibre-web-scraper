"""Unit tests for WindowsManager.

All subprocess calls are mocked. os.environ is patched per test to cover
the Wayland-detection truth table without side effects on the test runner.
"""

import subprocess
import pytest
from unittest.mock import MagicMock, call, patch

from core.windows_manager import WindowsManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_XRANDR_WITH_SECONDARY = """\
Screen 0: minimum 8 x 8, current 3840 x 1080, maximum 32767 x 32767
eDP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 344mm x 194mm
   1920x1080     60.03*+
HDMI-1 connected 1920x1080+1920+0 (normal left inverted right x axis y axis) 527mm x 296mm
   1920x1080     60.00*+  50.00    59.94
"""

_XRANDR_PRIMARY_ONLY = """\
Screen 0: minimum 8 x 8, current 1920 x 1080, maximum 32767 x 32767
eDP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 344mm x 194mm
   1920x1080     60.03*+
"""


def _make_wm_no_subprocess(workspace: int = 1) -> WindowsManager:
    """Build a WindowsManager that never spawns real subprocesses.

    Patches _detect_current_workspace and _detect_native_wayland so the ctor
    does not touch the real environment.
    """
    with patch.object(WindowsManager, '_detect_current_workspace', return_value=workspace), \
         patch.object(WindowsManager, '_detect_native_wayland', return_value=False):
        return WindowsManager()


# ---------------------------------------------------------------------------
# _detect_native_wayland — 4 env combos
# ---------------------------------------------------------------------------

class TestDetectNativeWayland:

    def test_native_wayland_when_only_wayland_display_set(self):
        """WAYLAND_DISPLAY set, DISPLAY absent → native Wayland."""
        env = {"WAYLAND_DISPLAY": "wayland-0"}
        with patch.dict("os.environ", env, clear=True):
            wm = WindowsManager.__new__(WindowsManager)
            assert wm._detect_native_wayland() is True

    def test_xwayland_when_both_set(self):
        """Both WAYLAND_DISPLAY and DISPLAY set → XWayland, NOT native Wayland."""
        env = {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":1"}
        with patch.dict("os.environ", env, clear=True):
            wm = WindowsManager.__new__(WindowsManager)
            assert wm._detect_native_wayland() is False

    def test_x11_when_only_display_set(self):
        """Only DISPLAY set → X11, not native Wayland."""
        env = {"DISPLAY": ":0"}
        with patch.dict("os.environ", env, clear=True):
            wm = WindowsManager.__new__(WindowsManager)
            assert wm._detect_native_wayland() is False

    def test_headless_when_neither_set(self):
        """Neither env var set → not native Wayland."""
        with patch.dict("os.environ", {}, clear=True):
            wm = WindowsManager.__new__(WindowsManager)
            assert wm._detect_native_wayland() is False


# ---------------------------------------------------------------------------
# pin_window dispatch
# ---------------------------------------------------------------------------

class TestPinWindow:

    def test_skips_entirely_when_target_workspace_is_none(self):
        """pin_window does nothing when _target_workspace is None."""
        wm = _make_wm_no_subprocess()
        wm._target_workspace = None
        wm._pin_window_x11 = MagicMock()
        wm._pin_window_wayland = MagicMock()

        wm.pin_window()

        wm._pin_window_x11.assert_not_called()
        wm._pin_window_wayland.assert_not_called()

    def test_routes_to_wayland_on_native_wayland(self):
        """pin_window calls _pin_window_wayland when _is_native_wayland is True."""
        wm = _make_wm_no_subprocess()
        wm._is_native_wayland = True
        wm._pin_window_x11 = MagicMock()
        wm._pin_window_wayland = MagicMock()

        wm.pin_window()

        wm._pin_window_wayland.assert_called_once()
        wm._pin_window_x11.assert_not_called()

    def test_routes_to_x11_on_xwayland(self):
        """pin_window calls _pin_window_x11 when _is_native_wayland is False."""
        wm = _make_wm_no_subprocess()
        wm._is_native_wayland = False
        wm._pin_window_x11 = MagicMock()
        wm._pin_window_wayland = MagicMock()

        wm.pin_window()

        wm._pin_window_x11.assert_called_once_with("chromium")
        wm._pin_window_wayland.assert_not_called()


# ---------------------------------------------------------------------------
# _pin_window_wayland
# ---------------------------------------------------------------------------

class TestPinWindowWayland:

    def test_emits_warning_log(self, caplog):
        """_pin_window_wayland always emits a WARNING-level log."""
        import logging
        wm = _make_wm_no_subprocess()
        with caplog.at_level(logging.WARNING, logger="core.windows_manager"):
            wm._pin_window_wayland()
        assert any("Native Wayland" in r.message for r in caplog.records)
        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_no_subprocess_spawned(self):
        """_pin_window_wayland must not call subprocess.run or check_output."""
        wm = _make_wm_no_subprocess()
        with patch("subprocess.run") as mock_run, \
             patch("subprocess.check_output") as mock_check:
            wm._pin_window_wayland()
            mock_run.assert_not_called()
            mock_check.assert_not_called()


# ---------------------------------------------------------------------------
# _pin_window_x11
# ---------------------------------------------------------------------------

class TestPinWindowX11:

    def _make_run_result(self, returncode: int, stdout: str) -> MagicMock:
        result = MagicMock()
        result.returncode = returncode
        result.stdout = stdout
        return result

    def test_calls_xdotool_search_then_set_desktop(self):
        """Happy path: xdotool search finds a window, then sets desktop."""
        wm = _make_wm_no_subprocess(workspace=2)
        search_result = self._make_run_result(0, "12345678\n")
        set_result = self._make_run_result(0, "")

        with patch("subprocess.run", side_effect=[search_result, set_result]) as mock_run:
            wm._pin_window_x11("chromium")

        assert mock_run.call_count == 2
        first_call_args = mock_run.call_args_list[0][0][0]
        assert "xdotool" in first_call_args
        assert "search" in first_call_args

        second_call_args = mock_run.call_args_list[1][0][0]
        assert "set_desktop_for_window" in second_call_args
        assert "12345678" in second_call_args
        assert "2" in second_call_args

    def test_swallows_subprocess_exception(self):
        """Any exception from subprocess must not propagate."""
        wm = _make_wm_no_subprocess()
        with patch("subprocess.run", side_effect=FileNotFoundError("xdotool not found")):
            wm._pin_window_x11("chromium")  # must not raise

    def test_returns_early_when_xdotool_search_fails(self):
        """When xdotool search returns non-zero, set_desktop_for_window is not called."""
        wm = _make_wm_no_subprocess()
        search_result = self._make_run_result(1, "")

        with patch("subprocess.run", return_value=search_result) as mock_run:
            wm._pin_window_x11("chromium")

        assert mock_run.call_count == 1  # only the search call


# ---------------------------------------------------------------------------
# detect_secondary_monitor
# ---------------------------------------------------------------------------

class TestDetectSecondaryMonitor:

    def test_returns_tuple_when_secondary_present(self):
        """Parses xrandr output and returns (x, y, width, height)."""
        wm = _make_wm_no_subprocess()
        with patch("subprocess.check_output", return_value=_XRANDR_WITH_SECONDARY):
            result = wm.detect_secondary_monitor()

        assert result == (1920, 0, 1920, 1080)

    def test_returns_none_when_no_secondary(self):
        """Returns None when xrandr shows only a primary monitor."""
        wm = _make_wm_no_subprocess()
        with patch("subprocess.check_output", return_value=_XRANDR_PRIMARY_ONLY):
            result = wm.detect_secondary_monitor()

        assert result is None

    def test_returns_none_on_subprocess_failure(self):
        """Returns None and does not raise when xrandr errors."""
        wm = _make_wm_no_subprocess()
        with patch("subprocess.check_output", side_effect=FileNotFoundError("xrandr not found")):
            result = wm.detect_secondary_monitor()

        assert result is None


# ---------------------------------------------------------------------------
# notify_captcha
# ---------------------------------------------------------------------------

class TestNotifyCaptcha:

    def test_calls_notify_send(self):
        """notify_captcha fires notify-send with urgency=critical."""
        wm = _make_wm_no_subprocess()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()
            wm.notify_captcha()

        mock_run.assert_called_once()
        cmd_args = mock_run.call_args[0][0]
        assert "notify-send" in cmd_args
        assert "--urgency=critical" in cmd_args

    def test_swallows_failure_silently(self):
        """notify_captcha must not raise if notify-send is unavailable."""
        wm = _make_wm_no_subprocess()
        with patch("subprocess.run", side_effect=FileNotFoundError("notify-send not found")):
            wm.notify_captcha()  # must not raise
