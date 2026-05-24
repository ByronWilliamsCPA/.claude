"""Sample file with FIPS-safe hashlib usage (usedforsecurity=False)."""

import hashlib


def compute(data: bytes) -> str:
    """Compute MD5 hash for non-security purposes.

    Args:
        data: The bytes to hash.

    Returns:
        Hex digest string.
    """
    return hashlib.md5(data, usedforsecurity=False).hexdigest()
