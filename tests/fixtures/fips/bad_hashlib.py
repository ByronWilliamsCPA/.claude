"""Sample file with FIPS-incompatible hashlib usage."""

import hashlib


def compute(data: bytes) -> str:
    # md5 without usedforsecurity=False -- should be flagged
    return hashlib.md5(data).hexdigest()
