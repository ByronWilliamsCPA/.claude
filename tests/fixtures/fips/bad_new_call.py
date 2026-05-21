"""Sample file using .new() with a non-FIPS algorithm name."""

import hashlib


def digest(data: bytes) -> str:
    """Compute digest using hashlib.new with md5.

    Args:
        data: The bytes to hash.

    Returns:
        Hex digest string.
    """
    h = hashlib.new("md5", data)  # noqa: S324 -- intentional fixture: tests FIPS scanner against this pattern
    return h.hexdigest()
