from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict

from . import __name__ as _pkg_name

DEFAULT_LOG_LEVEL = "INFO"


class JsonFormatter(logging.Formatter):
    """Formatter that outputs logs as JSON with timestamp and structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # If exception info is present, add it
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        # Include extra attributes if provided
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_record.update(record.extra)
        return json.dumps(log_record, ensure_ascii=False)


def get_logger(name: str | None = None) -> logging.Logger:
    """Create and configure a structured JSON logger.

    Args:
        name: Optional logger name. If None, package name is used.

    Returns:
        Configured logging.Logger instance.
    """
    logger_name = name or _pkg_name
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        # Avoid duplicate handlers when called multiple times
        return logger

    handler = logging.StreamHandler()
    fmt = JsonFormatter()
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.setLevel(DEFAULT_LOG_LEVEL)
    return logger
