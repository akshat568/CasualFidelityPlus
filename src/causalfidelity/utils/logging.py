"""Logging setup utilities for CausalFidelity+."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    format_str: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    log_file: Optional[Path | str] = None,
) -> None:
    """Configure root logging handlers and formatters.

    Args:
        level: Logging level string (e.g. 'DEBUG', 'INFO', 'WARNING', 'ERROR').
        format_str: Log message format string.
        log_file: Optional file path to write log messages to.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    formatter = logging.Formatter(format_str)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear pre-existing handlers to prevent duplicates
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance.

    Args:
        name: Name of the logger (typically __name__).

    Returns:
        Configured logging.Logger instance.
    """
    return logging.getLogger(name)
