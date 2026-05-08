"""Logging configuration for DOMjudge CLI.

This module sets up structured logging with proper handlers, formatters,
and log levels for the entire application.
"""

import logging
import sys
from pathlib import Path

from rich.logging import RichHandler

from dom.ui import console


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    enable_rich: bool = True,
    console_output: bool = False,
) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to write logs to file
        enable_rich: Whether to use Rich for console output
        console_output: Whether to show logs on console (False = only operation descriptions)

    Returns:
        Configured logger instance
    """
    # Get root logger
    logger = logging.getLogger("dom")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove any existing handlers
    logger.handlers.clear()

    # Console handler with rich formatting (only if console_output enabled)
    if console_output:
        console_handler: logging.Handler
        if enable_rich:
            console_handler = RichHandler(
                console=console,
                show_time=True,
                show_path=False,
                rich_tracebacks=True,
                tracebacks_show_locals=False,  # Security: Don't expose local variables in logs
            )
            console_handler.setLevel(logging.INFO)
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
            console_handler.setFormatter(console_formatter)

        logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Name of the logger (typically __name__, which already starts with "dom.")

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
