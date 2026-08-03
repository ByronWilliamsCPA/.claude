"""Self-consistency gate for ``docs/standards-manifest.yaml``.

The manifest is the single source of truth for compliance across the fleet. It is
hand-edited and consumed by ``scripts/check-repo-compliance.py`` and by LLM audit
agents, neither of which validate its internal logic. This module asserts the
manifest's cross-field invariants so a contradictory entry fails the build instead
of silently reaching the compliance pipeline.

Each test collects every offending check ID before asserting, so a single run names
all violations at once rather than stopping at the first.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

# Repo root is two levels above tests/unit/.
MANIFEST_PATH = Path(__file__).resolve().parents[2] / "docs" / "standards-manifest.yaml"

# Fixture root for the negative-control corpus backing ``mechanism: proven``
# checks. See test_mechanism_proven_requires_a_negative_control_fixture below.
FIXTURES_DIR: Path = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "test_fixtures"
    / "compliance_auditor"
)

# The three severity tiers the manifest actually uses. There is no ``high`` or
# ``blocker`` tier in the data; adding one is a deliberate schema change that
# should update this set in the same commit.
VALID_SEVERITIES: frozenset[str] = frozenset({"critical", "important", "suggested"})

# Known ``domain`` values. Extracted from the manifest on 2026-05-28. When a new
# domain is introduced, add it here in the same commit and note why.
#
# ``operations`` added 2026-08-02: OPS-* checks covering deployed-system posture
# (runtime config attestation, service credential scoping, log redaction,
# security event logging and alerting, backups and tested restore,
# anti-automation, managed-service console config). Every other domain closes
# over the git tree; this one covers controls that live in a dashboard, a
# connection string, a log stream, or an outbound alerting channel.
VALID_DOMAINS: frozenset[str] = frozenset(
    {
        "api",
        "ci",
        "claude_docs",
        "foundations",
        "mkdocs",
        "operations",
        "ossf",
        "pre_commit",
        "repo_settings",
        "toolchain",
    }
)

# Known ``applies_to`` values. The manifest scopes API checks via ``applies_to:
# api_repos``, MkDocs checks via ``applies_to: docs_repos`` (publishesDocs=true
# repos only), and operations checks via ``applies_to: deployed_repos``
# (isDeployed=true repos only). Extend this set in the same commit that adds a
# new applicability scope.
VALID_APPLIES_TO: frozenset[str] = frozenset(
    {"api_repos", "deployed_repos", "docs_repos"}
)

# IDs deliberately exempt from the critical-implies-non-overridable rule.
# Each entry requires a comment explaining the exception. Keep this empty: a
# critical check that can be suppressed contradicts the meaning of the tier, so
# an exemption is only justified for a documented, reviewed special case.
CRITICAL_OVERRIDE_EXCEPTIONS: frozenset[str] = frozenset()

pytestmark = pytest.mark.unit


def _extract_checks(data: object, source: str) -> list[dict[str, Any]]:
    """Validate parsed manifest data and return its list of check entries.

    Separated from file parsing so the malformed-manifest guards below are
    exercisable with synthetic data; reading the real manifest can only ever
    take the happy path.

    Args:
        data: The object produced by parsing the manifest YAML.
        source: Human-readable manifest location, used in error messages.

    Returns:
        The list of check mappings under the ``checks`` key.

    Raises:
        TypeError: If ``data`` is not a mapping, ``checks`` is not a list, or
            any entry under ``checks`` is not a mapping.
        KeyError: If the ``checks`` key is absent.
    """
    if not isinstance(data, dict):
        raise TypeError(
            f"manifest at {source} must be a YAML mapping; "
            f"got {type(data).__name__!r} (is the file empty or truncated?)"
        )
    if "checks" not in data:
        raise KeyError(
            f"manifest at {source} has no 'checks' key; keys present: {sorted(data)}"
        )
    checks = data["checks"]
    if not isinstance(checks, list):
        raise TypeError(
            f"manifest 'checks' must be a list, got {type(checks).__name__!r}"
        )
    non_mappings = [
        f"index {index}: {type(entry).__name__}"
        for index, entry in enumerate(checks)
        if not isinstance(entry, dict)
    ]
    if non_mappings:
        raise TypeError(
            "manifest 'checks' entries must all be mappings; "
            f"non-mapping entries: {'; '.join(non_mappings)}"
        )
    return checks


def _has_valid_verify(check: dict[str, Any]) -> bool:
    """Return whether ``check`` carries a non-empty string ``verify`` directive.

    Extracted so the non-string rejection (``null``, ``{}``) is testable; the
    live manifest only contains valid string directives.

    Args:
        check: A single check mapping from the manifest.

    Returns:
        ``True`` if ``verify`` is a string with non-whitespace content.
    """
    verify = check.get("verify")
    return isinstance(verify, str) and bool(verify.strip())


def _load_checks() -> list[dict[str, Any]]:
    """Parse the manifest file and return its list of check entries."""
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return _extract_checks(data, str(MANIFEST_PATH))


CHECKS: list[dict[str, Any]] = _load_checks()


def _ids(entries: list[dict[str, Any]]) -> str:
    """Render a sorted, comma-separated ID list for failure messages."""
    return ", ".join(sorted(str(entry.get("id", "<no id>")) for entry in entries))


def test_manifest_has_checks() -> None:
    """The manifest parses and contains at least one check."""
    assert CHECKS, "manifest contains no checks"


def test_required_fields_present() -> None:
    """Every check carries the fields the invariants below depend on."""
    required = (
        "id",
        "domain",
        "severity",
        "description",
        "override_eligible",
        "verify",
    )
    offenders = [
        f"{c.get('id', '<no id>')}: missing {field}"
        for c in CHECKS
        for field in required
        if field not in c
    ]
    assert not offenders, "checks missing required fields: " + "; ".join(offenders)


def _duplicate_ids(checks: list[dict[str, Any]]) -> set[str]:
    """Return every check ID that appears more than once in ``checks``.

    Args:
        checks: A list of check mappings.

    Returns:
        The set of IDs that appear on two or more checks. A missing or null
        ``id`` is skipped: that case is reported by
        ``test_required_fields_present`` instead, so this function's callers
        stay focused on genuine duplicates rather than a misleading
        "duplicate: None".
    """
    seen: set[str] = set()
    duplicates: set[str] = set()
    for check in checks:
        cid = check.get("id")
        if cid is None:
            continue
        if cid in seen:
            duplicates.add(str(cid))
        seen.add(cid)
    return duplicates


def test_ids_unique() -> None:
    """No two checks share an ID (IDs are referenced in logs and agent prompts)."""
    duplicates = _duplicate_ids(CHECKS)
    assert not duplicates, f"duplicate check IDs: {', '.join(sorted(duplicates))}"


def test_duplicate_ids_flags_a_repeated_id() -> None:
    """A synthetic manifest with a repeated ID is caught by the helper.

    The live manifest has no duplicates today, so this positive control is the
    only proof that the detection logic, not just a clean manifest, is why
    ``test_ids_unique`` passes.
    """
    checks = [{"id": "CI-001"}, {"id": "CI-002"}, {"id": "CI-001"}]
    assert _duplicate_ids(checks) == {"CI-001"}


def _offenders_for_severity(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return every check whose severity is not one of the three known tiers.

    Args:
        checks: A list of check mappings.

    Returns:
        Checks whose ``severity`` is absent from ``VALID_SEVERITIES``.
    """
    return [c for c in checks if c.get("severity") not in VALID_SEVERITIES]


def test_severity_in_enum() -> None:
    """Every severity is one of the three recognised tiers."""
    offenders = _offenders_for_severity(CHECKS)
    assert not offenders, (
        f"checks with unknown severity (allowed: {sorted(VALID_SEVERITIES)}): "
        f"{_ids(offenders)}"
    )


def test_offenders_for_severity_flags_an_unknown_tier() -> None:
    """A synthetic check with a bogus severity is caught by the helper."""
    checks = [
        {"id": "CI-001", "severity": "critical"},
        {"id": "CI-002", "severity": "urgent"},
    ]
    offenders = _offenders_for_severity(checks)
    assert [c["id"] for c in offenders] == ["CI-002"]


def test_override_eligible_is_bool() -> None:
    """``override_eligible`` is a real boolean, not a truthy string or int."""
    offenders = [c for c in CHECKS if not isinstance(c.get("override_eligible"), bool)]
    assert not offenders, (
        f"checks whose override_eligible is not a bool: {_ids(offenders)}"
    )


def _offenders_for_critical_override(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return every critical check that is wrongly marked override-eligible.

    Args:
        checks: A list of check mappings.

    Returns:
        Checks with ``severity: critical`` and ``override_eligible: true``
        that are not allowlisted in ``CRITICAL_OVERRIDE_EXCEPTIONS``.
    """
    return [
        c
        for c in checks
        if c.get("severity") == "critical"
        and c.get("override_eligible") is True
        and c.get("id") not in CRITICAL_OVERRIDE_EXCEPTIONS
    ]


def test_critical_implies_non_overridable() -> None:
    """Critical is the non-bypassable tier: it must not be override-eligible.

    A ``critical`` check with ``override_eligible: true`` can be suppressed via
    ``compliance-overrides.md``, which contradicts the tier's meaning. Genuine
    exceptions belong in ``CRITICAL_OVERRIDE_EXCEPTIONS`` with a comment.
    """
    offenders = _offenders_for_critical_override(CHECKS)
    assert not offenders, (
        "critical checks must set override_eligible: false "
        f"(or be allowlisted): {_ids(offenders)}"
    )


def test_offenders_for_critical_override_flags_an_overridable_critical() -> None:
    """A synthetic critical, override-eligible check is caught by the helper."""
    checks = [{"id": "CI-001", "severity": "critical", "override_eligible": True}]
    offenders = _offenders_for_critical_override(checks)
    assert [c["id"] for c in offenders] == ["CI-001"]


def _offenders_for_suggested_override(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return every suggested check with an inert ``override_eligible: false``.

    Args:
        checks: A list of check mappings.

    Returns:
        Checks with ``severity: suggested`` and ``override_eligible: false``.
    """
    return [
        c
        for c in checks
        if c.get("severity") == "suggested" and c.get("override_eligible") is False
    ]


def test_suggested_not_marked_non_overridable() -> None:
    """Suggested is advisory-only, so ``override_eligible: false`` is meaningless.

    A non-blocking finding cannot be 'blocked' by refusing an override, so marking
    a ``suggested`` check non-overridable is inert and signals a misclassified tier
    or a stale field.
    """
    offenders = _offenders_for_suggested_override(CHECKS)
    assert not offenders, (
        "suggested checks must not set override_eligible: false "
        f"(the field is inert at this tier): {_ids(offenders)}"
    )


def test_offenders_for_suggested_override_flags_a_non_overridable_suggestion() -> None:
    """A synthetic suggested, non-overridable check is caught by the helper."""
    checks = [{"id": "CI-001", "severity": "suggested", "override_eligible": False}]
    offenders = _offenders_for_suggested_override(checks)
    assert [c["id"] for c in offenders] == ["CI-001"]


def _offenders_for_verify(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return every check lacking a non-empty ``verify`` directive.

    Args:
        checks: A list of check mappings.

    Returns:
        Checks for which ``_has_valid_verify`` returns ``False``.
    """
    return [c for c in checks if not _has_valid_verify(c)]


def test_verify_non_empty() -> None:
    """Every check defines a non-empty ``verify`` directive."""
    offenders = _offenders_for_verify(CHECKS)
    assert not offenders, (
        f"checks with empty/missing/non-string verify: {_ids(offenders)}"
    )


def test_offenders_for_verify_flags_a_missing_directive() -> None:
    """A synthetic check with no ``verify`` directive is caught by the helper."""
    checks = [{"id": "CI-001", "verify": "file_exists: LICENSE"}, {"id": "CI-002"}]
    offenders = _offenders_for_verify(checks)
    assert [c["id"] for c in offenders] == ["CI-002"]


def test_extract_checks_rejects_non_mapping_manifest() -> None:
    """A manifest that is not a mapping (empty file, list, scalar) is rejected."""
    with pytest.raises(TypeError, match="must be a YAML mapping"):
        _extract_checks([], "test-manifest")


def test_extract_checks_rejects_missing_checks_key() -> None:
    """A mapping without a ``checks`` key raises a path-bearing ``KeyError``."""
    with pytest.raises(KeyError, match="no 'checks' key"):
        _extract_checks({"version": "1.0"}, "test-manifest")


def test_extract_checks_rejects_non_list_checks() -> None:
    """A ``checks`` value that is not a list is rejected."""
    with pytest.raises(TypeError, match="'checks' must be a list"):
        _extract_checks({"checks": {}}, "test-manifest")


def test_extract_checks_rejects_non_mapping_entry() -> None:
    """A ``checks`` list containing a non-mapping entry is rejected at load time."""
    with pytest.raises(TypeError, match="entries must all be mappings"):
        _extract_checks({"checks": [{"id": "OK"}, "CI-001"]}, "test-manifest")


def test_extract_checks_accepts_valid_data() -> None:
    """A well-formed mapping returns its ``checks`` list unchanged."""
    checks = [{"id": "CI-001"}]
    assert _extract_checks({"checks": checks}, "test-manifest") == checks


@pytest.mark.parametrize("verify", [None, {}, [], 42, "", "   "])
def test_has_valid_verify_rejects_invalid(verify: object) -> None:
    """Non-string, empty, or whitespace-only ``verify`` directives are rejected."""
    assert not _has_valid_verify({"verify": verify})


def test_has_valid_verify_accepts_non_empty_string() -> None:
    """A non-empty string ``verify`` directive is accepted."""
    assert _has_valid_verify({"verify": "file_exists: LICENSE"})


def _offenders_for_domain(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return every check whose ``domain`` is outside the known set.

    Args:
        checks: A list of check mappings.

    Returns:
        Checks whose ``domain`` is absent from ``VALID_DOMAINS``.
    """
    return [c for c in checks if c.get("domain") not in VALID_DOMAINS]


def test_domains_known() -> None:
    """Every ``domain`` is in the known set (catches typos and silent drift)."""
    offenders = _offenders_for_domain(CHECKS)
    assert not offenders, (
        f"checks with unknown domain (allowed: {sorted(VALID_DOMAINS)}): "
        f"{_ids(offenders)}"
    )


def test_offenders_for_domain_flags_an_unknown_domain() -> None:
    """A synthetic check with a made-up domain is caught by the helper."""
    checks = [{"id": "CI-001", "domain": "ci"}, {"id": "XX-001", "domain": "bogus"}]
    offenders = _offenders_for_domain(checks)
    assert [c["id"] for c in offenders] == ["XX-001"]


def _offenders_for_applies_to(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return every check whose ``applies_to`` value(s) are outside the known set.

    Args:
        checks: A list of check mappings.

    Returns:
        Checks whose ``applies_to`` (scalar or list, when present) contains a
        value absent from ``VALID_APPLIES_TO``.
    """
    offenders: list[dict[str, Any]] = []
    for check in checks:
        value = check.get("applies_to")
        if value is None:
            continue
        values = value if isinstance(value, list) else [value]
        if any(v not in VALID_APPLIES_TO for v in values):
            offenders.append(check)
    return offenders


def test_applies_to_known() -> None:
    """Every ``applies_to`` value (where present) is in the known set."""
    offenders = _offenders_for_applies_to(CHECKS)
    assert not offenders, (
        f"checks with unknown applies_to (allowed: {sorted(VALID_APPLIES_TO)}): "
        f"{_ids(offenders)}"
    )


def test_offenders_for_applies_to_flags_an_unknown_scope() -> None:
    """A synthetic check with a bogus applies_to scope is caught by the helper.

    Covers both the scalar form and the list form, since the helper handles
    each differently.
    """
    checks = [
        {"id": "API-001", "applies_to": "api_repos"},
        {"id": "XX-001", "applies_to": "bogus_repos"},
        {"id": "XX-002", "applies_to": ["api_repos", "bogus_repos"]},
    ]
    offenders = _offenders_for_applies_to(checks)
    assert [c["id"] for c in offenders] == ["XX-001", "XX-002"]


# Verification classes from .claude/standards/assurance-spine.md. The class
# records HOW a control must be verified, which is the axis the whole operations
# domain exists on: STATIC is the only one a source scanner can reach.
VALID_VERIFICATION_CLASSES: frozenset[str] = frozenset(
    {"STATIC", "DYNAMIC", "RUNTIME-CONFIG", "MANUAL"}
)

# The seventeen assurance-spine categories, SP-01 through SP-17.
VALID_SP_CATEGORIES: frozenset[str] = frozenset(f"SP-{n:02d}" for n in range(1, 18))


def _ops_checks_in(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return every check in the ``operations`` domain within ``checks``.

    Args:
        checks: A list of check mappings.

    Returns:
        The subset of ``checks`` whose ``domain`` is ``operations``.
    """
    return [c for c in checks if c.get("domain") == "operations"]


def _ops_checks() -> list[dict[str, Any]]:
    """Return every check in the ``operations`` domain of the real manifest."""
    return _ops_checks_in(CHECKS)


def _declared_classes(check: dict[str, Any]) -> list[str]:
    """Split a possibly-composite ``verification_class`` into its parts.

    The assurance register uses composite forms such as ``STATIC + DYNAMIC``
    where a control is asserted from source and then exercised against a running
    system. Both halves must be valid.

    Args:
        check: A manifest check mapping.

    Returns:
        The individual class tokens, or an empty list when the field is absent
        or not a string.
    """
    raw = check.get("verification_class")
    if not isinstance(raw, str):
        return []
    return [part.strip() for part in raw.split("+") if part.strip()]


def _offenders_for_verification_class(checks: list[dict[str, Any]]) -> list[Any]:
    """Return the ID of every OPS check with a missing or unknown class.

    Args:
        checks: A list of check mappings.

    Returns:
        IDs of operations-domain checks in ``checks`` whose
        ``verification_class`` is absent, or contains a part outside
        ``VALID_VERIFICATION_CLASSES``.
    """
    return [
        c.get("id")
        for c in _ops_checks_in(checks)
        if not _declared_classes(c)
        or any(part not in VALID_VERIFICATION_CLASSES for part in _declared_classes(c))
    ]


def test_operations_checks_declare_a_verification_class() -> None:
    """Every OPS check states how it must be verified.

    Without the class, nothing records that a check needs a running system or a
    vendor control plane, and the domain silently reads as more source-checkable
    than it is. Composite forms (``STATIC + DYNAMIC``) are allowed; every part
    must be a known class.
    """
    offenders = _offenders_for_verification_class(CHECKS)
    assert not offenders, (
        f"operations checks with a missing or unknown verification_class "
        f"(allowed: {sorted(VALID_VERIFICATION_CLASSES)}, composites joined "
        f"with '+'): {sorted(offenders)}"
    )


def test_offenders_for_verification_class_flags_missing_and_unknown() -> None:
    """Synthetic OPS checks with a missing, unknown, or composite-bad class fail."""
    checks = [
        {"id": "OPS-1", "domain": "operations"},
        {"id": "OPS-2", "domain": "operations", "verification_class": "NOPE"},
        {
            "id": "OPS-3",
            "domain": "operations",
            "verification_class": "STATIC + NOPE",
        },
        {"id": "OPS-4", "domain": "operations", "verification_class": "STATIC"},
        {"id": "CI-1", "domain": "ci", "verification_class": "NOPE"},
    ]
    offenders = _offenders_for_verification_class(checks)
    assert offenders == ["OPS-1", "OPS-2", "OPS-3"]


def _offenders_for_mechanism_status(checks: list[dict[str, Any]]) -> list[Any]:
    """Return the ID of every OPS check with a missing or unknown mechanism.

    Args:
        checks: A list of check mappings.

    Returns:
        IDs of operations-domain checks in ``checks`` whose ``mechanism`` is
        neither ``"unproven"`` nor ``"proven"``.
    """
    return [
        c.get("id")
        for c in _ops_checks_in(checks)
        if c.get("mechanism") not in {"unproven", "proven"}
    ]


def test_operations_checks_declare_a_mechanism_status() -> None:
    """Every OPS check records whether its mechanism has ever been proven.

    Per the assurance spine's instantiation contract, an automated check enters
    at ``mechanism: unproven`` and is promoted only once a negative control has
    demonstrably tripped it. A check with no mechanism field is asserting an
    ability to fail that nobody has observed.
    """
    offenders = _offenders_for_mechanism_status(CHECKS)
    assert not offenders, (
        "operations checks with a missing or unknown mechanism "
        f"(allowed: proven, unproven): {sorted(offenders)}"
    )


def test_offenders_for_mechanism_status_flags_missing_and_unknown() -> None:
    """Synthetic OPS checks with a missing or bogus mechanism value fail."""
    checks = [
        {"id": "OPS-1", "domain": "operations"},
        {"id": "OPS-2", "domain": "operations", "mechanism": "vibes"},
        {"id": "OPS-3", "domain": "operations", "mechanism": "unproven"},
        {"id": "OPS-4", "domain": "operations", "mechanism": "proven"},
    ]
    offenders = _offenders_for_mechanism_status(checks)
    assert offenders == ["OPS-1", "OPS-2"]


def _offenders_for_mechanism_proven_fixture(
    checks: list[dict[str, Any]], fixtures_dir: Path
) -> list[str]:
    """Return the ID of every ``mechanism: proven`` check with no fixture.

    Args:
        checks: A list of check mappings.
        fixtures_dir: Root directory expected to contain one
            ``defect_<ID>/`` subdirectory per promoted check.

    Returns:
        IDs of checks with ``mechanism: proven`` for which
        ``fixtures_dir / f"defect_{id}"`` is not a directory.
    """
    return [
        str(c.get("id"))
        for c in checks
        if c.get("mechanism") == "proven"
        and not (fixtures_dir / f"defect_{c.get('id')}").is_dir()
    ]


def test_mechanism_proven_requires_a_negative_control_fixture() -> None:
    """A check may claim ``mechanism: proven`` only with a fixture behind it.

    This is the anti-hollow rule turned into a gate. Promotion to ``proven``
    means a deliberate violation was demonstrated to trip the check, and the
    durable artifact of that demonstration is a defect fixture in the auditor
    regression corpus. Without this, ``proven`` is self-certification: a field
    an author can set to make a warning go away, which is precisely the failure
    mode the spine's status model exists to surface.
    """
    offenders = _offenders_for_mechanism_proven_fixture(CHECKS, FIXTURES_DIR)
    assert not offenders, (
        "checks claiming mechanism: proven with no negative-control fixture at "
        f"data/test_fixtures/compliance_auditor/defect_<ID>/: {offenders}. "
        "Either add the fixture demonstrating the check can fail, or return the "
        "check to mechanism: unproven."
    )


def test_offenders_for_mechanism_proven_fixture_flags_a_missing_fixture(
    tmp_path: Path,
) -> None:
    """A synthetic ``proven`` check with no fixture directory is reported.

    This is the positive control the live manifest cannot provide: every real
    check is either ``unproven`` or has no ``mechanism`` key, so the guard was
    provably unfalsifiable against real data alone (0 of 197 checks carry
    ``mechanism: proven``). This synthetic check is the only thing that proves
    the detection logic, not just a clean manifest, is why the real-manifest
    test above passes.
    """
    checks = [{"id": "OPS-999", "mechanism": "proven"}]
    offenders = _offenders_for_mechanism_proven_fixture(checks, tmp_path)
    assert offenders == ["OPS-999"]


def test_offenders_for_mechanism_proven_fixture_accepts_a_present_fixture(
    tmp_path: Path,
) -> None:
    """A synthetic ``proven`` check backed by a real fixture directory is clean."""
    (tmp_path / "defect_OPS-999").mkdir()
    checks = [{"id": "OPS-999", "mechanism": "proven"}]
    offenders = _offenders_for_mechanism_proven_fixture(checks, tmp_path)
    assert offenders == []


def test_offenders_for_mechanism_proven_fixture_ignores_unproven(
    tmp_path: Path,
) -> None:
    """An ``unproven`` check with no fixture is not an offender.

    This is the over-match control. The two tests above prove the guard fires
    on a real violation; this one bounds it. Widening the predicate to
    ``!= "unproven"`` or ``in {"proven", "unproven"}`` would still pass both of
    them while turning all 12 live OPS checks into offenders, because none has
    a fixture. Only this direction catches that.
    """
    checks = [{"id": "OPS-998", "mechanism": "unproven"}]
    offenders = _offenders_for_mechanism_proven_fixture(checks, tmp_path)
    assert offenders == []


def _offenders_for_spine_category(checks: list[dict[str, Any]]) -> list[Any]:
    """Return the ID of every OPS check with a missing or unknown sp_category.

    Args:
        checks: A list of check mappings.

    Returns:
        IDs of operations-domain checks in ``checks`` whose ``sp_category`` is
        absent from ``VALID_SP_CATEGORIES``.
    """
    return [
        c.get("id")
        for c in _ops_checks_in(checks)
        if c.get("sp_category") not in VALID_SP_CATEGORIES
    ]


def test_operations_checks_map_to_a_spine_category() -> None:
    """Every OPS check maps to an assurance-spine category.

    The spine is the coverage denominator. A check with no ``sp_category``
    cannot contribute to a coverage matrix, so a gap it was meant to close stays
    invisible.
    """
    offenders = _offenders_for_spine_category(CHECKS)
    assert not offenders, (
        f"operations checks with a missing or unknown sp_category "
        f"(allowed SP-01..SP-17): {sorted(offenders)}"
    )


def test_offenders_for_spine_category_flags_missing_and_unknown() -> None:
    """Synthetic OPS checks with a missing or out-of-range sp_category fail."""
    checks = [
        {"id": "OPS-1", "domain": "operations"},
        {"id": "OPS-2", "domain": "operations", "sp_category": "SP-99"},
        {"id": "OPS-3", "domain": "operations", "sp_category": "SP-01"},
    ]
    offenders = _offenders_for_spine_category(checks)
    assert offenders == ["OPS-1", "OPS-2"]


def _static_only_ops_checks(checks: list[dict[str, Any]]) -> list[Any]:
    """Return the ID of every OPS check whose sole declared class is STATIC.

    Args:
        checks: A list of check mappings.

    Returns:
        IDs of operations-domain checks in ``checks`` for which
        ``_declared_classes`` returns exactly ``["STATIC"]``.
    """
    # Count through _declared_classes, not the raw field: "STATIC " or
    # "STATIC + STATIC" would otherwise escape the count and silently
    # under-report, making this majority guard unfalsifiable by formatting.
    # The equality is deliberate, not a containment test: a composite such as
    # "STATIC + DYNAMIC" does reach past the source tree, so it is not part of
    # the drift this guard measures and must not count toward the static
    # majority. Only a check whose sole declared class is STATIC counts.
    return [
        c.get("id")
        for c in _ops_checks_in(checks)
        if _declared_classes(c) == ["STATIC"]
    ]


def test_operations_domain_is_not_predominantly_static() -> None:
    """The operations domain must keep reaching past the git tree.

    This domain exists because every other assurance loop in the fleet closes
    over a source repository, so a control living in a dashboard, a connection
    string, a log stream, or an alerting channel is invisible to all of them. If
    OPS checks drift into mostly-STATIC, the domain has quietly become another
    source scanner and the original gap reopens with a compliance badge on top.

    The threshold is deliberately loose: some genuinely static evidence belongs
    here (a committed taxonomy, a committed alert rule). What must not happen is
    the domain becoming majority-STATIC.
    """
    ops = _ops_checks()
    assert ops, "operations domain has no checks"
    static = _static_only_ops_checks(CHECKS)
    assert len(static) * 2 < len(ops), (
        f"{len(static)} of {len(ops)} operations checks are STATIC. This domain "
        f"covers what source analysis structurally cannot reach; a majority-STATIC "
        f"operations domain has lost its reason to exist. STATIC checks: "
        f"{sorted(static)}"
    )


def test_static_only_ops_checks_flags_a_majority_static_domain() -> None:
    """A synthetic OPS domain that is majority-STATIC fails the guard's math.

    Two of three checks below are STATIC-only, so ``len(static) * 2 < len(ops)``
    (the real guard's pass condition) evaluates to ``4 < 3``, which is false:
    the guard would fail on this data, exactly as intended.
    """
    checks = [
        {"id": "OPS-1", "domain": "operations", "verification_class": "STATIC"},
        {"id": "OPS-2", "domain": "operations", "verification_class": "STATIC"},
        {"id": "OPS-3", "domain": "operations", "verification_class": "DYNAMIC"},
    ]
    static = _static_only_ops_checks(checks)
    ops = _ops_checks_in(checks)
    assert not (len(static) * 2 < len(ops))


def _domain_agent_rows(text: str) -> set[str]:
    """Return the first-column values of the repo-compliance Domain Agents table.

    Locates the table by its exact header row (``| Domain | Agent | Checks |``)
    and reads the contiguous body rows that follow, so tables elsewhere in the
    document cannot satisfy the caller's membership check.

    Args:
        text: Full contents of the repo-compliance SKILL.md.

    Returns:
        The set of domain names listed in the table's first column. Empty when
        the header row is absent.
    """
    lines = text.splitlines()
    header = "| Domain | Agent | Checks |"
    try:
        index = lines.index(header)
    except ValueError:
        return set()
    rows: set[str] = set()
    # Skip the header and its separator row, then read until the table ends.
    for line in lines[index + 2 :]:
        if not line.startswith("|"):
            break
        cell = line.split("|")[1].strip()
        if cell:
            rows.add(cell)
    return rows


def test_applies_to_scopes_are_defined_in_the_compliance_script() -> None:
    """Every manifest ``applies_to`` scope has a matching SCOPE_DEFINITION.

    Wiring a scoped domain takes several coupled edits across the manifest, the
    compliance script, the consistency enums, and the skill docs. Missing any one
    leaves the domain invisible. This asserts the manifest-to-script half: a
    scope the script cannot resolve would fall through to no evaluation at all.
    """
    from tests.unit._load_check_repo_compliance import load_module

    crc = load_module()
    manifest_scopes = {
        value
        for check in CHECKS
        for value in (
            check["applies_to"]
            if isinstance(check.get("applies_to"), list)
            else [check.get("applies_to")]
        )
        if value is not None
    }
    missing = sorted(manifest_scopes - set(crc.SCOPE_DEFINITIONS))
    assert not missing, (
        "applies_to scopes used in the manifest but absent from "
        f"SCOPE_DEFINITIONS in scripts/check-repo-compliance.py: {missing}. "
        "Add a ScopeDefinition binding each to its catalog flag."
    )


def test_scope_definitions_agree_with_manifest_domains() -> None:
    """Each scope's declared domain matches the domain of the checks using it.

    A ``ScopeDefinition`` that names the wrong domain reports skipped-check
    counts against a domain that does not own those checks, which makes the
    applicability summary quietly wrong.
    """
    from tests.unit._load_check_repo_compliance import load_module

    crc = load_module()
    offenders: list[str] = []
    for scope, definition in crc.SCOPE_DEFINITIONS.items():
        domains = {
            c.get("domain")
            for c in CHECKS
            if scope
            in (
                c["applies_to"]
                if isinstance(c.get("applies_to"), list)
                else [c.get("applies_to")]
            )
        }
        if not domains:
            # No checks carry this scope yet; a scope may be defined ahead of
            # its checks landing. Nothing to disagree with.
            continue
        if domains != {definition.domain}:
            offenders.append(
                f"{scope}: ScopeDefinition says {definition.domain!r}, "
                f"manifest checks say {sorted(str(d) for d in domains)}"
            )
    assert not offenders, "scope/domain disagreement: " + "; ".join(offenders)


def test_scoped_domains_have_an_agent_in_the_skill_table() -> None:
    """Every manifest domain appears in the repo-compliance Domain Agents table.

    A domain with checks but no agent row is never dispatched, so its checks are
    defined and never evaluated. That is the same class of defect as a silent
    applies_to skip: the audit reports clean because nothing ran.
    """
    skill = (
        Path(__file__).resolve().parents[2]
        / ".claude"
        / "skills"
        / "repo-compliance"
        / "SKILL.md"
    )
    # Parse the Domain Agents table's first column rather than substring-matching
    # the document. Two looser anchors were tried and both were unfalsifiable:
    # searching the whole file, and slicing the "## Domain Agents" section, each
    # still match a "| <domain> |" cell in the applies_to scope table that lives
    # in the same section. A guard that cannot fail is worse than no guard, which
    # is the whole reason this test exists.
    listed = _domain_agent_rows(skill.read_text(encoding="utf-8"))

    domains = {str(c.get("domain")) for c in CHECKS}
    # repo_settings is deliberately produced by repo-foundations-auditor under
    # the foundations row rather than carrying its own table row.
    domains.discard("repo_settings")
    missing = sorted(domains - listed)
    assert not missing, (
        f"domains with manifest checks but no row in {skill.name} "
        f"Domain Agents table (rows found: {sorted(listed)}): {missing}"
    )


def test_domain_agent_rows_parser_reads_only_the_agent_table() -> None:
    """The table parser ignores other pipe tables in the same document.

    Guards the guard: if this parser ever widens to match any pipe table, the
    coverage test above silently stops failing.
    """
    doc = (
        "## Domain Agents\n\n"
        "| Domain | Agent | Checks |\n"
        "|--------|-------|--------|\n"
        "| ci | devops | CI-* |\n"
        "| ossf | ossf-auditor | OSSF-* |\n"
        "\n### Some Subsection\n\n"
        "| Scope | Flag | Domain | Checks |\n"
        "| --- | --- | --- | --- |\n"
        "| deployed_repos | isDeployed | operations | OPS-* |\n"
    )
    assert _domain_agent_rows(doc) == {"ci", "ossf"}


def _offenders_for_date_fields(checks: list[dict[str, Any]]) -> list[str]:
    """Return a description of every non-ISO-8601 ``created``/``modified`` field.

    Args:
        checks: A list of check mappings.

    Returns:
        One ``"<id>: <field>=<value>"`` string per check whose ``created`` or
        ``modified`` field (when present) fails ``datetime.date.fromisoformat``.
    """
    offenders: list[str] = []
    for check in checks:
        for field in ("created", "modified"):
            if field not in check:
                continue
            raw = check[field]
            try:
                datetime.date.fromisoformat(str(raw))
            except ValueError:
                offenders.append(f"{check.get('id', '<no id>')}: {field}={raw!r}")
    return offenders


def test_date_fields_parse_when_present() -> None:
    """Any ``created``/``modified`` field that appears must be an ISO-8601 date.

    No check carries these fields today; this guards future additions so a
    malformed date cannot enter the manifest unnoticed.
    """
    offenders = _offenders_for_date_fields(CHECKS)
    assert not offenders, "checks with non-ISO-8601 dates: " + "; ".join(offenders)


def test_offenders_for_date_fields_flags_a_malformed_date() -> None:
    """A synthetic check with a non-ISO-8601 date string is caught by the helper."""
    checks = [
        {"id": "CI-001", "created": "2026-01-15"},
        {"id": "CI-002", "modified": "not-a-date"},
    ]
    offenders = _offenders_for_date_fields(checks)
    assert offenders == ["CI-002: modified='not-a-date'"]
