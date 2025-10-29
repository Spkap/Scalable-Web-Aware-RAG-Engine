from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse
import re


ALLOWED_STATUSES = {"pending", "processing", "completed", "failed"}


def is_valid_url(url: str) -> bool:
    """Return True when the provided URL is syntactically valid and uses http/https.

    This is a lightweight validator intended for user input checks. It deliberately
    does not perform network I/O.
    """
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def sanitize_text(text: Optional[str]) -> str:
    """Normalize and sanitize free-text input.

    - Collapse multiple whitespace to single space
    - Strip leading/trailing whitespace
    - Normalize newlines to single space (this is simple but effective for small text)
    """
    if not text:
        return ""
    # Replace newlines and tabs with spaces, collapse many spaces
    s = re.sub(r"[\t\r\n]+", " ", text)
    s = re.sub(r" {2,}", " ", s)
    return s.strip()


def validate_job_status(status: str) -> bool:
    """Return True if status is one of the allowed job statuses."""
    return status in ALLOWED_STATUSES

