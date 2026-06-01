"""Centralized logging configuration for BuscaLibre web scraper."""

import logging
import os
import sys

_RESET = "\033[0m"

# Custom log level for successful data extraction
SUCCESS = 25
logging.addLevelName(SUCCESS, "SUCCESS")

_LEVEL_COLORS = {
    logging.DEBUG: "\033[90m",
    logging.INFO: "\033[32m",
    SUCCESS: "\033[36m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[35m",
}


class ColoredFormatter(logging.Formatter):
    """Formatter that adds ANSI color codes to log level based on severity."""

    def format(self, record):
        color = _LEVEL_COLORS.get(record.levelno, _RESET)
        record = logging.makeLogRecord(record.__dict__)
        record.levelname = f"{color}[{record.levelname}]{_RESET}"
        return super().format(record)


def setup_logging() -> None:
    """
    Configure root logger for the scraper.

    Reads SCRAPER_LOG_LEVEL from environment to set log level.
    Defaults to INFO. Set SCRAPER_LOG_LEVEL=DEBUG for verbose output.

    Uses ColoredFormatter if stdout is a TTY (terminal), plain formatter for pipes/files.

    Must be called exactly once from main.py before pipeline execution.
    """
    level_name = os.environ.get("SCRAPER_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # fmt = "%(asctime)s %(levelname)s  %(message)s"
    # datefmt = "%H:%M:%S"
    fmt = "%(levelname)s  %(message)s"
    datefmt = None

    use_color = False
    try:
        use_color = sys.stdout.isatty()
    except Exception:
        pass

    formatter = (
        ColoredFormatter(fmt=fmt, datefmt=datefmt)
        if use_color
        else logging.Formatter(fmt=fmt, datefmt=datefmt)
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if not root_logger.handlers:
        root_logger.addHandler(handler)

    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
