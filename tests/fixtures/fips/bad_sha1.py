"""Sample file with SHA-1 usage."""

import hashlib


def digest(data: bytes) -> str:
    """Compute SHA-1 digest.

    Args:
        data: The bytes to hash.

    Returns:
        Hex digest string.
    """
    return hashlib.sha1(data).hexdigest()  # noqa: S324 -- intentional fixture: tests FIPS scanner against this pattern
