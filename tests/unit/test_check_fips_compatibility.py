"""Tests for scripts/check_fips_compatibility.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit._load_check_fips_compatibility import load_module

_fips = load_module()

_FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fips"


@pytest.mark.unit
def test_bad_hashlib_md5_flagged() -> None:
    """MD5 without usedforsecurity=False must be reported as an error.

    Verifies that the AST walker flags a bare hashlib.md5() call
    with severity 'error' and a message containing 'md5'.
    """
    issues = _fips.check_python_file(_FIXTURES / "bad_hashlib.py")
    assert any("md5" in i.message.lower() and i.severity == "error" for i in issues), (
        f"Expected md5 error, got: {[i.message for i in issues]}"
    )


@pytest.mark.unit
def test_good_hashlib_md5_not_flagged() -> None:
    """hashlib.md5(usedforsecurity=False) must not produce any md5 findings.

    The usedforsecurity=False keyword argument explicitly opts out of FIPS
    enforcement; the walker must suppress the finding.
    """
    issues = _fips.check_python_file(_FIXTURES / "good_hashlib.py")
    hash_issues = [i for i in issues if "md5" in i.message.lower()]
    assert hash_issues == [], f"usedforsecurity=False should suppress: {hash_issues}"


@pytest.mark.unit
def test_sha1_flagged_as_warning() -> None:
    """SHA-1 without usedforsecurity=False must be reported as a warning.

    SHA-1 is in NON_FIPS_HASHES but the walker assigns severity 'warning'
    (not 'error') for algorithms other than md5/md4.
    """
    issues = _fips.check_python_file(_FIXTURES / "bad_sha1.py")
    assert any(
        "sha1" in i.message.lower() and i.severity == "warning" for i in issues
    ), f"Expected sha1 warning, got: {[i.message for i in issues]}"


@pytest.mark.unit
def test_clean_file_has_no_issues() -> None:
    """A file with no crypto usage must produce zero FIPS findings."""
    issues = _fips.check_python_file(_FIXTURES / "clean.py")
    assert issues == [], f"Clean file should have no issues, got: {issues}"


@pytest.mark.unit
def test_new_call_with_md5_string_flagged() -> None:
    """hashlib.new('md5', ...) must be flagged by the .new() handler.

    The walker inspects the first positional string argument to .new()
    calls and flags non-FIPS algorithm names.
    """
    issues = _fips.check_python_file(_FIXTURES / "bad_new_call.py")
    assert any("md5" in i.message.lower() for i in issues), (
        f"Expected md5 finding from .new() call, got: {[i.message for i in issues]}"
    )


@pytest.mark.unit
def test_cipher_call_flagged_as_error() -> None:
    """A method-call attribute matching NON_FIPS_CIPHERS must be reported.

    Exercises the _check_cipher_call branch of the dispatcher independently
    of hashlib/.new() paths. The fixture calls FakeCipher().des(...), which
    matches the 'des' entry in NON_FIPS_CIPHERS by attribute name.
    """
    issues = _fips.check_python_file(_FIXTURES / "bad_cipher.py")
    cipher_issues = [
        i for i in issues if i.category == "cipher" and i.severity == "error"
    ]
    assert cipher_issues, (
        f"Expected cipher error from .des() call, got: {[i.message for i in issues]}"
    )
