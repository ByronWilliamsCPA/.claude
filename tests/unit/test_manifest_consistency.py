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


def test_ids_unique() -> None:
    """No two checks share an ID (IDs are referenced in logs and agent prompts)."""
    seen: set[str] = set()
    duplicates: set[str] = set()
    for check in CHECKS:
        cid = check.get("id")
        if cid is None:
            # A missing or null id is reported by test_required_fields_present;
            # skipping it here keeps this test's failure message about genuine
            # duplicates rather than a misleading "duplicate: None".
            continue
        if cid in seen:
            duplicates.add(str(cid))
        seen.add(cid)
    assert not duplicates, f"duplicate check IDs: {', '.join(sorted(duplicates))}"


def test_severity_in_enum() -> None:
    """Every severity is one of the three recognised tiers."""
    offenders = [c for c in CHECKS if c.get("severity") not in VALID_SEVERITIES]
    assert not offenders, (
        f"checks with unknown severity (allowed: {sorted(VALID_SEVERITIES)}): "
        f"{_ids(offenders)}"
    )


def test_override_eligible_is_bool() -> None:
    """``override_eligible`` is a real boolean, not a truthy string or int."""
    offenders = [c for c in CHECKS if not isinstance(c.get("override_eligible"), bool)]
    assert not offenders, (
        f"checks whose override_eligible is not a bool: {_ids(offenders)}"
    )


def test_critical_implies_non_overridable() -> None:
    """Critical is the non-bypassable tier: it must not be override-eligible.

    A ``critical`` check with ``override_eligible: true`` can be suppressed via
    ``compliance-overrides.md``, which contradicts the tier's meaning. Genuine
    exceptions belong in ``CRITICAL_OVERRIDE_EXCEPTIONS`` with a comment.
    """
    offenders = [
        c
        for c in CHECKS
        if c.get("severity") == "critical"
        and c.get("override_eligible") is True
        and c.get("id") not in CRITICAL_OVERRIDE_EXCEPTIONS
    ]
    assert not offenders, (
        "critical checks must set override_eligible: false "
        f"(or be allowlisted): {_ids(offenders)}"
    )


def test_suggested_not_marked_non_overridable() -> None:
    """Suggested is advisory-only, so ``override_eligible: false`` is meaningless.

    A non-blocking finding cannot be 'blocked' by refusing an override, so marking
    a ``suggested`` check non-overridable is inert and signals a misclassified tier
    or a stale field.
    """
    offenders = [
        c
        for c in CHECKS
        if c.get("severity") == "suggested" and c.get("override_eligible") is False
    ]
    assert not offenders, (
        "suggested checks must not set override_eligible: false "
        f"(the field is inert at this tier): {_ids(offenders)}"
    )


def test_verify_non_empty() -> None:
    """Every check defines a non-empty ``verify`` directive."""
    offenders = [c for c in CHECKS if not _has_valid_verify(c)]
    assert not offenders, (
        f"checks with empty/missing/non-string verify: {_ids(offenders)}"
    )


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


def test_domains_known() -> None:
    """Every ``domain`` is in the known set (catches typos and silent drift)."""
    offenders = [c for c in CHECKS if c.get("domain") not in VALID_DOMAINS]
    assert not offenders, (
        f"checks with unknown domain (allowed: {sorted(VALID_DOMAINS)}): "
        f"{_ids(offenders)}"
    )


def test_applies_to_known() -> None:
    """Every ``applies_to`` value (where present) is in the known set."""
    offenders: list[dict[str, Any]] = []
    for check in CHECKS:
        value = check.get("applies_to")
        if value is None:
            continue
        values = value if isinstance(value, list) else [value]
        if any(v not in VALID_APPLIES_TO for v in values):
            offenders.append(check)
    assert not offenders, (
        f"checks with unknown applies_to (allowed: {sorted(VALID_APPLIES_TO)}): "
        f"{_ids(offenders)}"
    )


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


def test_date_fields_parse_when_present() -> None:
    """Any ``created``/``modified`` field that appears must be an ISO-8601 date.

    No check carries these fields today; this guards future additions so a
    malformed date cannot enter the manifest unnoticed.
    """
    offenders: list[str] = []
    for check in CHECKS:
        for field in ("created", "modified"):
            if field not in check:
                continue
            raw = check[field]
            try:
                datetime.date.fromisoformat(str(raw))
            except ValueError:
                offenders.append(f"{check.get('id', '<no id>')}: {field}={raw!r}")
    assert not offenders, "checks with non-ISO-8601 dates: " + "; ".join(offenders)
