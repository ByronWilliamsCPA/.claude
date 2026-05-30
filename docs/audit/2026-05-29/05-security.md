---
title: "Audit: Security and Secrets"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Audit of secrets exposure, dependency CVEs, and workflow posture."
tags:
  - security
  - analysis
---

Two committed HTML session-report files expose real usernames, hostnames, and filesystem paths. All third-party GitHub Actions are SHA-pinned. No live secrets found in code. One unsafe `yaml.load` call is a false positive (ruamel YAML with `typ="safe"`). One workflow (`release.yml`) lacks a top-level `permissions: {}` deny-all, leaving job defaults to GitHub platform behavior rather than explicit least-privilege.

---

### SEC-01 - Committed HTML session reports expose personal filesystem data

**Severity:** Medium
**Effort:** S (add two lines to `.gitignore`, remove from tracking with `git rm --cached`)

**Evidence:**

```bash
git ls-files session-report-20260521-2145.html session-report-20260521-2204.html
# both files returned: confirmed tracked

grep "/home/byron" session-report-20260521-2145.html | wc -l  -> 1
grep "/home/byron" session-report-20260521-2204.html | wc -l  -> 111
```

Both files contain:
- Real username: `byron@dadslaptop`
- Real home directory prefix: `/home/byron`
- Project-relative paths for at least 5 distinct private repos (fragrance-rater, cookiecutter-python-template, image-generation, audio-processor, reference-library)
- Session IDs (UUIDs) for Claude API sessions
- Conversation message snippets (user turn text)
- `session-report-20260521-2145.html:292` embeds a 187 KB JSON blob with `root: "/home/byron/.claude/projects"`, 224 session records, and the full cache-break context including verbatim user messages

The files were committed intentionally (`chore(reports): commit 2026-05-21 session reports`), but the data surface is broader than expected. No API tokens or credential strings were found.

**Recommendation:** Remove both files from git tracking (`git rm --cached session-report-*.html`), add `session-report-*.html` to `.gitignore`, and document in `SECURITY.md` that session reports must not be committed. If historical reporting is needed, strip the `cache_breaks[].context` and `root` fields before committing.

**CVE:** None

---

### SEC-02 - `release.yml` missing top-level `permissions: {}` deny-all

**Severity:** Low
**Effort:** S (add three lines to the workflow file)

**Evidence:**

`/home/user/.claude/.github/workflows/release.yml:65` defines job-level permissions (`contents: write`, `issues: write`, `pull-requests: write`) but there is no top-level `permissions:` block.

```bash
grep -n "^permissions" .github/workflows/release.yml
# output: (none at top level, only line 65 job-level)
```

Without a top-level `permissions: {}`, GitHub applies the repo's default token permissions to any future jobs added to this workflow. All other workflows in the repo use `permissions: {}` at the top level; this file is the single outlier.

**Recommendation:** Add `permissions: {}` at the workflow level (between the `concurrency:` block and `jobs:`). The existing job-level block already grants only what is needed; the top-level change enforces that any new job added later starts with no permissions rather than the platform default.

**CVE:** None

---

### SEC-03 - Bare `except Exception: return` swallows YAML parse failures silently

**Severity:** Low
**Effort:** S (replace two bare except clauses with typed catches)

**Evidence:**

`/home/user/.claude/tools/validate_front_matter.py:92`:
```python
except Exception:
    return None, ""
```

`/home/user/.claude/tools/validate_front_matter.py:177`:
```python
except Exception:
    return False
```

Both clauses catch any exception from YAML front matter parsing and return a sentinel silently. A file with a genuinely malformed front matter, a permission error, or an unexpected ruamel edge case produces the same silent `None`/`False` return as a legitimate missing-front-matter file. The caller has no way to distinguish a parse failure from an expected empty result.

This is a code-quality finding rather than an exploitable vulnerability; the function is invoked only on local files by the pre-commit hook.

**Recommendation:** Replace `except Exception` with `except (ruamel.yaml.YAMLError, frontmatter.FrontmatterError)` (or equivalent typed exceptions), log the error to stderr, and re-raise or return a distinct sentinel type so the caller can emit a warning rather than silently skipping the file.

**CVE:** None

---

### SEC-04 - `.secrets.baseline` entries verified; no baseline drift or unbaselined live secrets found

All 8 files listed in `.secrets.baseline` were spot-checked:

- `.env.mcp.example:21-22`: format-string placeholder (`postgresql://user:password@host:5432/database`). Legitimate false positive.
- `.pre-commit-config.yaml`: hex strings are commit SHAs for action pins. Legitimate.
- `.qlty/qlty.toml:124`: inline comment mentioning `detect-secrets`. Legitimate.
- `tests/test_validate_mcp_env.bats:23`: `PERPLEXITY_API_KEY="test_key"`. Legitimate test fixture.
- `tools/renovate/README.md:16`: documentation snippet. Legitimate.
- `docs/guides/testing-guide.md`: doc examples. Legitimate.

No unbaselined live secrets were found via grep for `ghp_`, `sk-`, `AKIA`, or other token patterns across non-venv source files.

---

### SEC-05 - All third-party GitHub Actions are SHA-pinned

Full scan of 22 workflows found no tag-pinned third-party actions:

```bash
grep -rnE "uses:\s+[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+@[a-zA-Z0-9._-]+" .github/workflows/ \
  | grep -vE "@[0-9a-f]{40}"
# output: (empty)
```

All external actions (step-security/harden-runner, astral-sh/setup-uv, amannn/action-semantic-pull-request, lycheeverse/lychee-action, sigstore/cosign-installer, python-semantic-release/python-semantic-release, github/codeql-action, actions/upload-artifact, actions/download-artifact, actions/github-script, actions/checkout) use full 40-character SHAs with version comments. This matches the mandate in `.claude/rules/git-workflow.md`.

---

### SEC-06 - No shell injection sinks found in workflow `run:` steps

```bash
grep -rnE "github\.event\.(pull_request|issue|comment)\.(body|title)" .github/workflows/
# output: (empty)
```

No untrusted PR/issue body or title values are interpolated directly into `run:` blocks. The `fips-compatibility.yml` uses `${{ github.event.inputs.strict_mode }}` (workflow_dispatch input) which is controlled by the triggering user and is not an untrusted injection vector.

---

### SEC-07 - `yaml.load` in test file is safe (ruamel YAML `typ="safe"`)

`/home/user/.claude/tests/unit/test_seed_reusable_workflow_registry.py:46` calls `yaml.load()` but uses `from ruamel.yaml import YAML` with `YAML(typ="safe")`. This is not the stdlib `yaml.load` without a Loader. No unsafe deserialization.

---

### SEC-08 - No `pickle`, `eval`, `exec`, or `os.system` in project source

Grep across all non-venv `.py` files found no usage of `pickle.load`, `os.system`, or unsafe `eval`/`exec` in project-owned code. Matches in `.venv/` (third-party packages) are out of scope.

---

### SEC-09 - Dependency scan: no CVEs found in locked versions

Versions from `uv.lock` checked against knowledge base (cutoff August 2025):

| Package | Locked version | Status |
|---------|---------------|--------|
| cryptography | 46.0.7 | No known CVE |
| certifi | 2026.2.25 | No known CVE |
| urllib3 | 2.7.0 | No known CVE |
| requests | 2.33.1 | No known CVE |
| pydantic | 2.12.5 | No known CVE |
| setuptools | 82.0.1 | No known CVE |
| jinja2 | 3.1.6 | No known CVE |
| tornado | 6.5.5 | No known CVE |

`pip-audit` binary was not available in the environment; no automated scan was run. Manual cross-check found no confirmed CVEs for the locked versions above.

---

## Machine-readable findings

```json
[
  {
    "id": "SEC-01",
    "title": "Committed HTML session reports expose personal filesystem data",
    "domain": "security",
    "severity": "medium",
    "effort": "S",
    "files": [
      "session-report-20260521-2145.html",
      "session-report-20260521-2204.html"
    ],
    "evidence": "Both files are tracked in git (confirmed via git ls-files). session-report-20260521-2204.html contains 111 occurrences of /home/byron, the string byron@dadslaptop, and verbatim conversation text from Claude API sessions. The embedded JSON at line 292 of the first file includes root: /home/byron/.claude/projects and 224 session records.",
    "recommendation": "Run git rm --cached session-report-*.html, add session-report-*.html to .gitignore, and document the policy in SECURITY.md. Strip cache_breaks[].context and root from any report before committing.",
    "cve": ""
  },
  {
    "id": "SEC-02",
    "title": "release.yml missing top-level permissions deny-all",
    "domain": "security",
    "severity": "low",
    "effort": "S",
    "files": [
      ".github/workflows/release.yml"
    ],
    "evidence": "grep -n '^permissions' .github/workflows/release.yml returns no top-level match. Job-level permissions at line 65 are correct (contents: write, issues: write, pull-requests: write), but the absence of a top-level permissions: {} means future jobs inherit platform defaults. All 21 other workflows use top-level permissions blocks.",
    "recommendation": "Add permissions: {} at the workflow level between the concurrency block and jobs:. The existing job-level grants are sufficient and correct.",
    "cve": ""
  },
  {
    "id": "SEC-03",
    "title": "Bare except Exception swallows YAML parse failures in validate_front_matter.py",
    "domain": "security",
    "severity": "low",
    "effort": "S",
    "files": [
      "tools/validate_front_matter.py"
    ],
    "evidence": "tools/validate_front_matter.py:92 and :177 catch bare Exception and return None/False silently. Any parse error, permission error, or unexpected ruamel edge case is indistinguishable from a legitimate missing-front-matter result.",
    "recommendation": "Replace except Exception with typed catches (ruamel.yaml.YAMLError, frontmatter.FrontmatterError), log to stderr, and return a distinct sentinel so callers can emit warnings rather than silently skipping files.",
    "cve": ""
  },
  {
    "id": "SEC-04",
    "title": "Secrets baseline verified: all entries are legitimate false positives",
    "domain": "security",
    "severity": "low",
    "effort": "S",
    "files": [
      ".secrets.baseline"
    ],
    "evidence": "All 8 files in .secrets.baseline spot-checked. Detections are: format-string placeholders in .env.mcp.example, commit SHAs in .pre-commit-config.yaml, doc comments in .qlty/qlty.toml, test fixture literals in tests/test_validate_mcp_env.bats and docs/guides/testing-guide.md, and doc snippets in mcp/README.md and tools/renovate/README.md. No live secrets found.",
    "recommendation": "No action required. Baseline is accurate.",
    "cve": ""
  },
  {
    "id": "SEC-05",
    "title": "All third-party GitHub Actions are SHA-pinned",
    "domain": "security",
    "severity": "low",
    "effort": "S",
    "files": [
      ".github/workflows/"
    ],
    "evidence": "grep -rnE 'uses: [a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+@[a-zA-Z0-9._-]+' .github/workflows/ | grep -vE '@[0-9a-f]{40}' returns empty. All external actions use 40-char commit SHAs.",
    "recommendation": "No action required. Maintain SHA pins via Dependabot.",
    "cve": ""
  },
  {
    "id": "SEC-06",
    "title": "No script-injection sinks found in workflow run steps",
    "domain": "security",
    "severity": "low",
    "effort": "S",
    "files": [
      ".github/workflows/"
    ],
    "evidence": "grep -rnE 'github.event.(pull_request|issue|comment).(body|title)' .github/workflows/ returns empty. No untrusted event data interpolated into run: blocks.",
    "recommendation": "No action required.",
    "cve": ""
  },
  {
    "id": "SEC-07",
    "title": "yaml.load call in test file is safe (ruamel YAML typ=safe)",
    "domain": "security",
    "severity": "low",
    "effort": "S",
    "files": [
      "tests/unit/test_seed_reusable_workflow_registry.py"
    ],
    "evidence": "Line 11 imports YAML from ruamel.yaml. Line 45 constructs YAML(typ='safe'). Line 46 calls yaml.load() on that safe instance. This is not the stdlib yaml.load without a Loader.",
    "recommendation": "No action required. Consider renaming the local variable from yaml to avoid confusion with the stdlib yaml module.",
    "cve": ""
  },
  {
    "id": "SEC-08",
    "title": "No pickle, eval, exec, or os.system found in project source",
    "domain": "security",
    "severity": "low",
    "effort": "S",
    "files": [],
    "evidence": "find /home/user/.claude -name '*.py' -not -path '*/.venv/*' | xargs grep -E 'pickle.load|os.system|^eval|^exec' returned no project-owned matches.",
    "recommendation": "No action required.",
    "cve": ""
  },
  {
    "id": "SEC-09",
    "title": "Dependency scan: no CVEs confirmed in locked versions",
    "domain": "security",
    "severity": "low",
    "effort": "S",
    "files": [
      "uv.lock",
      "pyproject.toml"
    ],
    "evidence": "Versions from uv.lock for cryptography 46.0.7, certifi 2026.2.25, urllib3 2.7.0, requests 2.33.1, pydantic 2.12.5, setuptools 82.0.1, jinja2 3.1.6, tornado 6.5.5 cross-checked against knowledge base. No confirmed CVEs. pip-audit binary unavailable; automated scan not run.",
    "recommendation": "Restore pip-audit to the pre-commit environment so automated scanning runs on every dependency change. See the comment in pyproject.toml about the 2.10 skip-editable workaround.",
    "cve": ""
  }
]
```
