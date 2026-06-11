"""
WindowsManager: subprocess-based desktop helpers.

Window-to-workspace placement is NOT handled here. The browser window is created
once and never recreated, so it simply stays on the workspace the scraper was
launched from - no window manager rules or post-creation moves are needed.

This class only owns best-effort desktop integrations that the scraper still
needs: secondary-monitor detection and the CAPTCHA notification.
"""

import logging
import os
import re
import subprocess
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class WindowsManager:
    """Owns best-effort, subprocess-based desktop integrations.

    Workspace pinning is intentionally absent: it is delegated to the GNOME
    Auto Move Windows extension (see module docstring).
    """

    def __init__(self) -> None:
        logger.debug(
            "WindowsManager initialized: workspace pinning delegated to GNOME "
            "Auto Move Windows extension (matched via WM_CLASS)"
        )

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
            output = subprocess.check_output(["xrandr", "--query"], text=True)
            for line in output.split("\n"):
                if "connected" in line and "primary" not in line:
                    match = re.search(r"(\d+)x(\d+)\+(\d+)\+(\d+)", line)
                    if match:
                        width, height, x, y = (int(match.group(i)) for i in range(1, 5))
                        return (x, y, width, height)
            return None
        except Exception as e:
            logger.debug("Could not detect secondary monitor: %s", e)
            return None

    # ------------------------------------------------------------------
    # Public: desktop notifications
    # ------------------------------------------------------------------

    def notify_captcha(self) -> None:
        """Fire an Ubuntu desktop notification when a CAPTCHA needs solving.

        Best-effort: the operator may be working on the other monitor while
        the browser waits on the secondary screen. Silently ignored if the
        desktop tools are unavailable - never affects the scraper's blocking
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
                    result.stderr.strip() if result.stderr else "(no error message)",
                )
        except Exception as e:
            logger.warning("Could not fire CAPTCHA notification: %s", e)
