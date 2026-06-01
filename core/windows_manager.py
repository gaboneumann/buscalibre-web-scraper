"""
WindowsManager: subprocess-based workspace and window management.

Extracted from HTTPClient to decouple OS-level window pinning from the HTTP
client logic. Provides Wayland-aware dispatch so pin_window() skips gracefully
on native Wayland instead of silently no-opping via xdotool.
"""

import logging
import os
import re
import subprocess
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class WindowsManager:
    """Owns all subprocess-based window and workspace operations.

    Detects the runtime environment (native Wayland vs X11/XWayland) and the
    current GNOME workspace once at construction time. Call sites use the
    public methods; dispatch to the right implementation is internal.
    """

    def __init__(self) -> None:
        self._is_native_wayland: bool = self._detect_native_wayland()
        self._target_workspace: Optional[int] = self._detect_current_workspace()

    # ------------------------------------------------------------------
    # Private: environment detection (called once at construction)
    # ------------------------------------------------------------------

    def _detect_native_wayland(self) -> bool:
        """Return True only when running on native Wayland (no XWayland).

        Condition: WAYLAND_DISPLAY is set AND DISPLAY is absent/empty.
        XWayland sessions keep DISPLAY set, so xdotool works there → X11 path.
        """
        return bool(os.environ.get("WAYLAND_DISPLAY")) and not os.environ.get("DISPLAY")

    def _detect_current_workspace(self) -> Optional[int]:
        """Detect the active GNOME workspace number.

        Uses xdotool get_desktop which returns the current desktop index
        directly, without requiring a window ID. Works on GNOME Wayland via
        XWayland. Returns workspace number (0, 1, 2, ...) or None if detection
        fails.
        """
        try:
            result = subprocess.run(
                ["xdotool", "get_desktop"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip().isdigit():
                workspace = int(result.stdout.strip())
                logger.info("Current desktop: %d", workspace)
                return workspace
            logger.debug(
                "xdotool get_desktop returned non-integer: %r",
                result.stdout.strip(),
            )
        except Exception as e:
            logger.debug("Could not detect workspace: %s", e)

        return None

    # ------------------------------------------------------------------
    # Public: monitor detection
    # ------------------------------------------------------------------

    def detect_secondary_monitor(self) -> Optional[Tuple[int, int, int, int]]:
        """Detect secondary (non-primary) monitor via xrandr.

        Returns (x, y, width, height) of the secondary display, or None if
        there is no secondary monitor or detection fails. Verified to position
        the Chromium window on the secondary monitor under --ozone-platform=x11.
        """
        try:
            output = subprocess.check_output(['xrandr', '--query'], text=True)
            for line in output.split('\n'):
                if 'connected' in line and 'primary' not in line:
                    match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', line)
                    if match:
                        width, height, x, y = (int(match.group(i)) for i in range(1, 5))
                        return (x, y, width, height)
            return None
        except Exception as e:
            logger.debug("Could not detect secondary monitor: %s", e)
            return None

    # ------------------------------------------------------------------
    # Public: window pinning
    # ------------------------------------------------------------------

    def pin_window(self, window_name: str = "chromium") -> None:
        """Pin the browser window to the workspace where the terminal runs.

        Dispatches to the Wayland-aware or X11 implementation depending on
        the environment detected at construction time. No-ops silently when
        the target workspace was not detected.
        """
        if self._target_workspace is None:
            return
        if self._is_native_wayland:
            self._pin_window_wayland()
            return
        self._pin_window_x11(window_name)

    def _pin_window_x11(self, window_name: str) -> None:
        """Pin the browser window to the target workspace on X11/XWayland.

        Uses xdotool to find the window by name and move it to the workspace
        recorded at construction time. Best-effort: logged and ignored on any
        failure.
        """
        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", window_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return

            win_id = result.stdout.strip().split()[0]

            result = subprocess.run(
                ["xdotool", "set_desktop_for_window", win_id, str(self._target_workspace)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.debug("Window pinned to workspace %d", self._target_workspace)
        except Exception as e:
            logger.debug("Could not pin window: %s", e)

    def _pin_window_wayland(self) -> None:
        """Emit a warning and skip window pinning on native Wayland.

        xdotool set_desktop_for_window silently no-ops on native Wayland;
        this method surfaces the limitation explicitly so operators are aware.
        Real Wayland pinning via gdbus/wmctrl is deferred to a future change.
        """
        logger.warning(
            "Native Wayland: window pinning unsupported (xdotool no-ops); "
            "skipping. Window stays on current workspace."
        )

    # ------------------------------------------------------------------
    # Public: desktop notifications
    # ------------------------------------------------------------------

    def notify_captcha(self) -> None:
        """Fire an Ubuntu desktop notification when a CAPTCHA needs solving.

        Best-effort: the operator may be working on the other monitor while
        the browser waits on the secondary screen. Silently ignored if the
        desktop tools are unavailable — never affects the scraper's blocking
        wait.
        """
        try:
            # Preserve DBUS/display environment vars so notify-send works
            # when called from within Playwright context
            env = os.environ.copy()
            result = subprocess.run(
                [
                    "notify-send",
                    "--urgency=critical",
                    "--icon=dialog-warning",
                    "--app-name=BuscaLibre Scraper",
                    "CAPTCHA requerido",
                    "Resolvé el desafío en la ventana del navegador.",
                ],
                timeout=5,
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            if result.returncode != 0:
                logger.warning(
                    "notify-send failed with exit code %d: %s",
                    result.returncode,
                    result.stderr.strip() if result.stderr else "(no error message)"
                )
            else:
                logger.info("CAPTCHA notification sent successfully.")
        except Exception as e:
            logger.warning("Could not fire CAPTCHA notification: %s", e)
