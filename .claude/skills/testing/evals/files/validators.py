"""Input validation utilities."""

from __future__ import annotations

import re

# Simplified RFC 5321 pattern (covers the common case without full RFC complexity)
_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

# RFC 5321 length limits
_MAX_LOCAL_LEN = 64
_MAX_TOTAL_LEN = 254


def validate_email(address: str | None) -> bool:
    """Return True if address is a syntactically valid email address.

    Validation rules (in order):
    1. Must not be None and must be a str
    2. Must not be empty or whitespace-only
    3. Total length must be <= 254 characters
    4. Local part (before @) must be <= 64 characters
    5. Must match the RFC 5321 simplified pattern

    Args:
        address: Email address to validate, or None.

    Returns:
        True if the address passes all validation rules, False otherwise.
    """
    if address is None or not isinstance(address, str):
        return False
    if not address.strip():
        return False
    if len(address) > _MAX_TOTAL_LEN:
        return False

    local_part = address.split("@")[0] if "@" in address else address
    if len(local_part) > _MAX_LOCAL_LEN:
        return False

    return bool(_EMAIL_RE.match(address))
