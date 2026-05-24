"""Sample file invoking a method whose name matches NON_FIPS_CIPHERS.

Used by the unit test suite to exercise _check_cipher_call. The walker
inspects attribute-call names (not imports), so a local class with a
matching method name is sufficient to cover the dispatch path without
requiring a third-party crypto package at test time.
"""


class FakeCipher:
    """Stand-in for a non-FIPS cipher API for AST-walker coverage."""

    def des(self, data: bytes) -> bytes:
        """Pretend-encrypt by returning the input unchanged.

        Args:
            data: The bytes to "encrypt".

        Returns:
            The input bytes, unchanged.
        """
        return data


def encrypt(data: bytes) -> bytes:
    """Call the non-FIPS cipher method so the AST walker can flag it.

    Args:
        data: The bytes to pass through the cipher.

    Returns:
        The cipher output (passthrough in this fixture).
    """
    return FakeCipher().des(data)
