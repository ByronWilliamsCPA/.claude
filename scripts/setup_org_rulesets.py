"""Apply an org ruleset JSON body to a GitHub org via gh CLI.

Solo-dev safety: refuses to apply any body that would require human PR
approval (required_approving_review_count > 0). The user merges their own
PRs; restoring approval requirements would lock the repo.

Target/rule compatibility: refuses to apply a body whose rule types are
incompatible with its target. The GitHub Rulesets API rejects mismatches
with HTTP 422 atomically (a single bad rule drops the whole apply), so
catching them client-side gives a clear error before the API call.

Drift detection: after a successful apply, re-fetches the ruleset and
raises RulesetDriftError if any rule type from the request body is
missing in the response, or if the ruleset cannot be located by name
immediately after the apply. The script exits with EXIT_DRIFT_DETECTED
(6) on either condition; the prior warn-and-continue behaviour silently
disabled the safeguard. This catches silent-drop drift where the API
accepts the PUT but discards fields the current API version no longer
recognises.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from scripts.generate_python_tier_repos import python_repos_for_org

CATALOG_DEFAULT = Path("docs/reference/github-repos.json")
EXIT_OK = 0
EXIT_GH_FAILURE = 4
EXIT_SOLO_DEV_VIOLATION = 3
EXIT_TARGET_RULE_MISMATCH = 5
EXIT_DRIFT_DETECTED = 6
# #CRITICAL: external-resource timing dependency. gh CLI calls hit api.github.com
# and will block indefinitely without a timeout. 30s matches check-required-checks.py.
# #VERIFY: smoke-test against a real org and confirm `--dry-run` and apply both
# fail cleanly (TimeoutExpired raised, mapped to EXIT_GH_FAILURE) on a paused link.
_GH_TIMEOUT_SECONDS = 30

# Rule types only valid in target=push bodies. Per the GitHub Rulesets API,
# push rules apply to every push regardless of ref, so they cannot live in
# a branch- or tag-targeted ruleset; the API returns 422 atomically on
# mismatch. Keep this list in sync with GitHub's push-rule documentation at
# https://docs.github.com/en/rest/repos/rules.
# #ASSUME: this allowlist is current as of 2026-05; future GitHub API
# versions may add new push-only rule types.
# #VERIFY: re-check the docs when bumping the documented GitHub API version
# or after seeing an unexpected 422 from a push-target apply.
_PUSH_ONLY_RULE_TYPES = frozenset(
    {
        "file_path_restriction",
        "max_file_size",
        "file_extension_restriction",
        "max_file_path_length",
    }
)


class SoloDevViolationError(RuntimeError):
    """Raised when a ruleset body would lock out the solo-dev workflow."""


class TargetRuleMismatchError(RuntimeError):
    """Raised when a body's rule types are incompatible with its target."""


class RulesetDriftError(RuntimeError):
    """Raised when applied ruleset state diverges from the request body."""


# Backward-compatible alias; use SoloDevViolationError in new code.
SoloDevViolation = SoloDevViolationError


def validate_target_rule_compatibility(body: dict) -> None:
    """Raise TargetRuleMismatchError if rule types do not match the target.

    Push-only rule types (file_path_restriction, max_file_size,
    file_extension_restriction, max_file_path_length, all enumerated in
    _PUSH_ONLY_RULE_TYPES) only validate inside a target=push body.
    Putting them in a branch or tag body causes GitHub to reject the
    entire apply with a 422 atomically. The reverse is also enforced:
    a push body must contain only push-rule types.

    Args:
        body: Parsed ruleset body.

    Raises:
        TargetRuleMismatchError: If push-only rule types appear in a
            non-push body, or non-push rule types appear in a push body.
    """
    target = body.get("target", "branch")
    rule_types = {
        rule.get("type") for rule in body.get("rules", []) if rule.get("type")
    }
    push_only_in_body = rule_types & _PUSH_ONLY_RULE_TYPES
    if target != "push" and push_only_in_body:
        raise TargetRuleMismatchError(
            f"Body has target={target!r} but contains push-only rule types: "
            f"{sorted(push_only_in_body)}. The GitHub Rulesets API rejects "
            "this combination with HTTP 422. Move these rules into a "
            "separate ruleset with target='push'."
        )
    if target == "push":
        non_push_rules = rule_types - _PUSH_ONLY_RULE_TYPES
        if non_push_rules:
            raise TargetRuleMismatchError(
                f"Body has target='push' but contains non-push rule types: "
                f"{sorted(non_push_rules)}. Push rulesets only accept "
                f"push-rule types: {sorted(_PUSH_ONLY_RULE_TYPES)}."
            )


def validate_solo_dev_safe(body: dict) -> None:
    """Raise SoloDevViolation if body would require human PR approval.

    Args:
        body: Parsed ruleset body.

    Raises:
        SoloDevViolation: If any pull_request rule would force a human
            approval the solo maintainer cannot self-grant:
            required_approving_review_count > 0, require_code_owner_review
            true, or require_last_push_approval true.
    """
    for rule in body.get("rules", []):
        if rule.get("type") != "pull_request":
            continue
        params = rule.get("parameters", {}) or {}
        count = params.get("required_approving_review_count", 0)
        if count and count > 0:
            raise SoloDevViolation(
                f"Body requires {count} approving reviews "
                f"(required_approving_review_count={count}); solo-dev policy "
                "forbids any value > 0. The user merges their own PRs."
            )
        if params.get("require_code_owner_review"):
            raise SoloDevViolation(
                "Body sets require_code_owner_review=true; with a CODEOWNERS "
                "file this forces a code-owner approval the solo maintainer "
                "cannot self-grant. Solo-dev policy forbids it."
            )
        if params.get("require_last_push_approval"):
            raise SoloDevViolation(
                "Body sets require_last_push_approval=true; this forces a "
                "separate approver after the maintainer's own last push. "
                "Solo-dev policy forbids it."
            )


def render_body(body: dict, org: str, catalog: Path) -> dict:
    """Substitute __GENERATED__ tokens with catalog-derived values.

    Args:
        body: Parsed ruleset body (will be deep-copied).
        org: Organization slug for which to generate Python-tier repo list.
        catalog: Path to docs/reference/github-repos.json.

    Returns:
        Deep-copied body with any ["__GENERATED__"] include lists replaced
        by the Python-tier repo names for `org`.
    """
    out = json.loads(json.dumps(body))  # deep copy
    repo_cond = out.get("conditions", {}).get("repository_name", {})
    if repo_cond.get("include") == ["__GENERATED__"]:
        repo_cond["include"] = python_repos_for_org(org, catalog)
    return out


def find_existing_ruleset(org: str, name: str) -> int | None:
    """Return the id of the org-level ruleset named `name`, or None.

    Args:
        org: GitHub org slug.
        name: Ruleset name to search for.

    Returns:
        Integer ruleset id if found, else None.
    """
    # --paginate + per_page=100 ensures orgs with >30 rulesets do not silently
    # truncate (gh default page size is 30). Without it, a match on page 2+
    # would return None and the script would create a duplicate ruleset.
    out = subprocess.check_output(
        [
            "gh",
            "api",
            "--paginate",
            f"orgs/{org}/rulesets?per_page=100",
            "--jq",
            ".[] | {id, name}",
        ],
        text=True,
        timeout=_GH_TIMEOUT_SECONDS,
    )
    for line in out.strip().split("\n"):
        if not line:
            continue
        # json.JSONDecodeError propagates to main() where it maps to
        # EXIT_GH_FAILURE; the malformed line is surfaced in the message.
        rs = json.loads(line)
        if rs.get("name") == name:
            return rs.get("id")
    return None


def fetch_ruleset(org: str, ruleset_id: int) -> dict:
    """Fetch the live ruleset body by id from the org rulesets endpoint.

    Args:
        org: GitHub org slug.
        ruleset_id: Numeric ruleset id (returned by find_existing_ruleset).

    Returns:
        Parsed JSON body of the live ruleset.

    Raises:
        RulesetDriftError: If the gh response is not parseable JSON. This
            runs after a successful apply, so signalling drift (not a gh
            CLI failure) is the appropriate exit code.
    """
    out = subprocess.check_output(
        ["gh", "api", f"orgs/{org}/rulesets/{ruleset_id}"],
        text=True,
        timeout=_GH_TIMEOUT_SECONDS,
    )
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        raise RulesetDriftError(
            f"apply succeeded but post-apply fetch of ruleset id "
            f"{ruleset_id} returned unparseable JSON"
        ) from exc


def detect_drift(request_body: dict, response_body: dict) -> list[str]:
    """Return human-readable drift entries between request and response.

    Compares rule types present in the sent body versus those present in
    the live ruleset state. Rule types in the request that are absent from
    the response indicate the API silently dropped them (the most common
    drift signal).

    Scope: type-level only. This does NOT compare rule parameters; a
    silent parameter rewrite (e.g., max_file_size 100 -> 50, or a
    shrunken restricted_file_paths list) will pass undetected. Parameter
    drift can be added in a future revision if it becomes a concern.

    Args:
        request_body: The body sent in the PUT/POST.
        response_body: The body returned by re-fetching the ruleset.

    Returns:
        List of drift descriptions; empty if no drift detected.
    """
    drift: list[str] = []
    request_types = {
        rule.get("type") for rule in request_body.get("rules", []) if rule.get("type")
    }
    response_types = {
        rule.get("type") for rule in response_body.get("rules", []) if rule.get("type")
    }
    dropped = request_types - response_types
    if dropped:
        drift.append(
            f"rule types missing from live state: {sorted(dropped)} "
            f"(sent {len(request_types)}, live has {len(response_types)})"
        )
    return drift


def apply(
    org: str,
    body_path: Path,
    enforcement: str | None,
    catalog: Path,
    dry_run: bool,
) -> None:
    """Apply the body to org as a ruleset (POST if new, PUT if exists).

    Args:
        org: Target GitHub org slug.
        body_path: Path to a ruleset JSON body file.
        enforcement: If set, override body['enforcement'] (active|evaluate|disabled).
        catalog: Path to the repo catalog (for __GENERATED__ substitution).
        dry_run: If True, print the action and payload but make no API call.

    Raises:
        SoloDevViolationError: If the body would lock out solo-dev workflow.
        TargetRuleMismatchError: If push-only and non-push rule types are
            mixed in a way the GitHub API rejects.
        RulesetDriftError: If the post-apply re-fetch shows the API
            dropped any rule types from the request body, or if the
            ruleset cannot be located by name immediately after apply.
        subprocess.CalledProcessError: If the gh CLI invocation fails
            (auth error, 4xx response, network failure).
    """
    body = json.loads(body_path.read_text(encoding="utf-8"))
    validate_solo_dev_safe(body)
    validate_target_rule_compatibility(body)
    body = render_body(body, org, catalog)
    if enforcement:
        body["enforcement"] = enforcement
    name = body["name"]
    existing_id = find_existing_ruleset(org, name)
    payload = json.dumps(body)
    if dry_run:
        action = "PUT" if existing_id else "POST"
        print(f"DRY RUN: would {action} ruleset '{name}' to org '{org}'")
        print(payload)
        return
    if existing_id:
        cmd = [
            "gh",
            "api",
            "-X",
            "PUT",
            f"orgs/{org}/rulesets/{existing_id}",
            "--input",
            "-",
        ]
    else:
        cmd = ["gh", "api", "-X", "POST", f"orgs/{org}/rulesets", "--input", "-"]
    subprocess.run(
        cmd,
        input=payload,
        text=True,
        check=True,
        timeout=_GH_TIMEOUT_SECONDS,
    )
    enforcement_value = body.get("enforcement", "<unset>")
    print(f"Applied ruleset '{name}' to org '{org}' (enforcement={enforcement_value})")
    # Post-apply drift detection. A successful PUT response does not guarantee
    # the API persisted every field; re-fetching is the only reliable check.
    # Fail closed when the ruleset cannot be located: a missing ruleset name
    # after a successful apply means either the apply did not persist or the
    # API rewrote the name, both of which are drift signals the caller must
    # see, not warn-and-continue.
    live_id = existing_id or find_existing_ruleset(org, name)
    if live_id is None:
        raise RulesetDriftError(
            f"Apply reported success but ruleset {name!r} could not be located "
            f"in org {org!r} immediately after apply; cannot verify drift. "
            "The apply may not have persisted, or the API may have rewritten "
            "the ruleset name."
        )
    response_body = fetch_ruleset(org, live_id)
    drift = detect_drift(body, response_body)
    if drift:
        details = "; ".join(drift)
        raise RulesetDriftError(
            f"Apply succeeded but live state diverged from request: {details}"
        )


_POLICY_EXCEPTION_EXIT: dict[type[Exception], int] = {
    SoloDevViolationError: EXIT_SOLO_DEV_VIOLATION,
    TargetRuleMismatchError: EXIT_TARGET_RULE_MISMATCH,
    RulesetDriftError: EXIT_DRIFT_DETECTED,
}

_POLICY_EXCEPTION_PREFIX: dict[type[Exception], str] = {
    SoloDevViolationError: "REFUSED",
    TargetRuleMismatchError: "REFUSED",
    RulesetDriftError: "DRIFT",
}


def _gh_error_message(exc: Exception) -> str:
    """Return a human-readable message for a gh-related subprocess exception.

    Args:
        exc: The caught exception (CalledProcessError, TimeoutExpired,
            JSONDecodeError, or FileNotFoundError).

    Returns:
        A single-line error string suitable for stderr.
    """
    if isinstance(exc, subprocess.TimeoutExpired):
        return f"gh command timed out after {_GH_TIMEOUT_SECONDS}s: {exc}"
    if isinstance(exc, json.JSONDecodeError):
        return f"gh produced unparseable JSON output: {exc}"
    if isinstance(exc, FileNotFoundError):
        return (
            f"gh CLI not on PATH: {exc}"
            if exc.filename == "gh"
            else f"body file not found: {exc.filename}"
        )
    return f"gh command failed: {exc}"


def main(argv: list[str]) -> int:
    """CLI entry point.

    Args:
        argv: Command-line argument vector (excluding program name).

    Returns:
        Exit code:
          EXIT_OK (0)                 on success
          EXIT_SOLO_DEV_VIOLATION (3) when a solo-dev policy guard refused
          EXIT_GH_FAILURE (4)         on gh CLI failure, timeout, missing
                                      gh binary, missing --body file, or
                                      unparseable gh output
          EXIT_TARGET_RULE_MISMATCH (5) when push-only and non-push rules
                                      are mixed for a single target
          EXIT_DRIFT_DETECTED (6)     when post-apply re-fetch shows the
                                      API dropped rule types, the ruleset
                                      could not be located after apply,
                                      or the re-fetch returned unparseable
                                      JSON
        Argparse errors exit directly with code 2.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", required=True)
    parser.add_argument("--body", required=True, type=Path)
    parser.add_argument("--enforcement", choices=("active", "evaluate", "disabled"))
    parser.add_argument("--catalog", type=Path, default=CATALOG_DEFAULT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        apply(args.org, args.body, args.enforcement, args.catalog, args.dry_run)
    except (SoloDevViolationError, TargetRuleMismatchError, RulesetDriftError) as exc:
        prefix = _POLICY_EXCEPTION_PREFIX.get(type(exc), "ERROR")
        print(f"{prefix}: {exc}", file=sys.stderr)
        return _POLICY_EXCEPTION_EXIT.get(type(exc), EXIT_GH_FAILURE)
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        FileNotFoundError,
    ) as e:
        print(_gh_error_message(e), file=sys.stderr)
        return EXIT_GH_FAILURE
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
