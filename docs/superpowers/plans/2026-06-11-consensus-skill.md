---
schema_type: planning
title: Consensus Skill Implementation Plan
status: draft
owner: engineering
component: Development-Tools
source: "docs/superpowers/specs/2026-06-11-consensus-skill-design.md"
tags: [skills, tooling, automation]
purpose: Step-by-step plan to build the consensus umbrella skill that replaces the zen-mcp-server consensus suite. Creates one uv-run engine script (OpenRouter fan-out, band-based roster selection, live catalog validation, failover, cost caps), three data files salvaged from the zen repo, SKILL.md plus three workflow files, unit tests, and registration. Implements the approved spec at docs/superpowers/specs/2026-06-11-consensus-skill-design.md.
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `consensus` umbrella skill in `~/dev/.claude` with two modes (flexible consensus, tiered IT review team) driving one OpenRouter engine script, per the approved spec.

**Architecture:** One PEP 723 uv-run script (`consensus_cli.py`, httpx only) provides `select`/`estimate`/`run`/`refresh` subcommands emitting JSON. Curated model data salvaged from zen-mcp-server feeds band-based roster selection; live OpenRouter validation (24h disk cache) prevents stale rosters; Claude synthesizes raw responses. Workflow prose routes the two modes.

**Tech Stack:** Python 3.10+, httpx, uv (PEP 723 inline deps), pytest, argparse, asyncio.

**Spec:** `docs/superpowers/specs/2026-06-11-consensus-skill-design.md`

**Repo:** ALL work happens in `/home/byron/dev/.claude` (not zen-mcp-server; that repo is frozen). Run all commands from the repo root unless a step says otherwise.

**Conventions that apply** (verified 2026-06-11):
- Tests live in `tests/unit/`; run with `uv run pytest tests/unit/test_consensus_cli.py -v --no-cov` (`--no-cov` because repo coverage gates target `src/claude_config` only).
- The script path contains `.claude/` (a dot-directory), so tests load it via `importlib.util.spec_from_file_location`, matching `tests/integration/test_scripts.py`.
- Ruff applies (88 cols, py310, Google docstrings); basedpyright, interrogate, and pydoclint exclude `.claude/skills/`.
- No em-dash characters anywhere. Signed commits (`git commit -S`), conventional messages.
- The script uses `emit()`/`sys.stderr.write` instead of `print` to stay clear of flake8-print rules.

---

### Task 1: Branch, scaffold, and salvage data files

**Files:**
- Create: `.claude/skills/consensus/data/models.csv` (copy)
- Create: `.claude/skills/consensus/data/bands_config.json` (copy)
- Create: `.claude/skills/consensus/data/roles.json` (export)
- Modify: `pyproject.toml` (dev dependency: httpx)

- [ ] **Step 1: Create the branch**

```bash
cd /home/byron/dev/.claude
git checkout main && git pull --ff-only
git checkout -b feat/consensus-skill
```

- [ ] **Step 2: Scaffold the skill directory**

```bash
mkdir -p .claude/skills/consensus/workflows .claude/skills/consensus/scripts .claude/skills/consensus/data
```

- [ ] **Step 3: Copy the curated datasets from the zen repo**

```bash
cp /home/byron/dev/zen-mcp-server/docs/models/models.csv .claude/skills/consensus/data/models.csv
cp /home/byron/dev/zen-mcp-server/docs/models/bands_config.json .claude/skills/consensus/data/bands_config.json
head -2 .claude/skills/consensus/data/models.csv
```

Expected: header line starting `rank,model,provider,tier,status,context,input_cost,output_cost,...` then the `openai/gpt-5.1` row.

- [ ] **Step 4: Export roles.json from the zen role module**

The zen module has no third-party imports, so load it directly by file path (avoids importing the `tools` package):

```bash
python3 - << 'EOF'
import importlib.util, json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "consensus_roles",
    "/home/byron/dev/zen-mcp-server/tools/custom/consensus_roles.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
out = {
    "role_definitions": mod.ROLE_DEFINITIONS,
    "domain_roles": {
        domain: {str(level): roles for level, roles in levels.items()}
        for domain, levels in mod.DOMAIN_ROLES.items()
    },
}
dest = Path("/home/byron/dev/.claude/.claude/skills/consensus/data/roles.json")
dest.write_text(json.dumps(out, indent=2) + "\n")
print(f"wrote {dest}: {len(out['role_definitions'])} roles, {len(out['domain_roles'])} domains")
EOF
```

Expected: `wrote .../roles.json: 19 roles, 4 domains`

- [ ] **Step 5: Ensure httpx is available to tests (the test file imports the script, which imports httpx)**

This repo declares dev dependencies in `[project.optional-dependencies]`, not `[dependency-groups]`, so `uv add --dev` is the wrong flag here. httpx may already be present transitively; add it explicitly only if missing:

```bash
uv run python -c "import httpx; print('httpx available:', httpx.__version__)" || uv add --optional dev httpx
```

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/consensus/data/ pyproject.toml uv.lock
git commit -S -m "feat(consensus): scaffold skill and salvage curated model data from zen-mcp-server"
```

---

### Task 2: Engine skeleton, catalog loading, and cost-tier filtering

**Files:**
- Create: `.claude/skills/consensus/scripts/consensus_cli.py`
- Create: `tests/unit/test_consensus_cli.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_consensus_cli.py`:

```python
"""Unit tests for the consensus skill engine script.

The script lives under .claude/skills/ (a dot-directory), so it is loaded by
file path rather than imported as a package, matching the pattern in
tests/integration/test_scripts.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / ".claude" / "skills" / "consensus" / "scripts" / "consensus_cli.py"

_spec = importlib.util.spec_from_file_location("consensus_cli", SCRIPT)
assert _spec is not None and _spec.loader is not None
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)


def make_model(name, inp, out, he=70.0, swe=60.0, context=131000, spec="general"):
    """Build a Model row for tests."""
    return cli.Model(
        name=name,
        provider="testprov",
        input_cost=inp,
        output_cost=out,
        humaneval=he,
        swe_bench=swe,
        context=context,
        specialization=spec,
    )


class TestParseContext:
    def test_k_suffix(self):
        assert cli.parse_context("131K") == 131_000

    def test_m_suffix(self):
        assert cli.parse_context("1M") == 1_000_000

    def test_plain_number(self):
        assert cli.parse_context("200000") == 200_000

    def test_numeric_passthrough(self):
        assert cli.parse_context(65000) == 65_000

    def test_garbage_returns_zero(self):
        assert cli.parse_context("unknown") == 0


class TestLoadData:
    def test_load_models_returns_rows(self):
        models = cli.load_models()
        assert len(models) > 20
        names = {m.name for m in models}
        assert "openai/gpt-5.1" in names

    def test_load_bands_has_cost_tiers(self):
        bands = cli.load_bands()
        assert set(bands["cost_tier_bands"]) >= {"free", "economy", "value", "premium"}

    def test_load_roles_has_domains(self):
        roles = cli.load_roles()
        assert set(roles["domain_roles"]) == {"code_review", "security", "architecture", "general"}
        assert len(roles["role_definitions"]) == 19


class TestCostTierFilter:
    def test_free_requires_zero_input_and_output(self):
        bands = cli.load_bands()
        models = [make_model("a:free", 0.0, 0.0), make_model("b", 0.0, 0.5)]
        free = cli.models_in_cost_tier(models, "free", bands)
        assert [m.name for m in free] == ["a:free"]

    def test_sorted_by_humaneval_descending(self):
        bands = cli.load_bands()
        models = [make_model("low:free", 0, 0, he=70), make_model("high:free", 0, 0, he=90)]
        free = cli.models_in_cost_tier(models, "free", bands)
        assert [m.name for m in free] == ["high:free", "low:free"]

    def test_economy_band_range(self):
        bands = cli.load_bands()
        models = [make_model("cheap", 0.5, 0.9), make_model("expensive", 5.0, 20.0)]
        econ = cli.models_in_cost_tier(models, "economy", bands)
        assert [m.name for m in econ] == ["cheap"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_consensus_cli.py -v --no-cov
```

Expected: collection error or failures (`FileNotFoundError` / `AttributeError`: module has no attribute `Model`), because the script does not exist yet.

- [ ] **Step 3: Write the engine skeleton with data loading**

Create `.claude/skills/consensus/scripts/consensus_cli.py`:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27"]
# ///
"""Consensus engine CLI: multi-model fan-out via OpenRouter.

Subcommands (all emit JSON on stdout):
    select    Build a band-filtered roster with role assignments for a level/domain.
    estimate  Cost preview for a level without live validation or API calls.
    run       Fan a prompt out to models in parallel; emit raw responses.
    refresh   Diff the curated dataset against the live OpenRouter catalog.

OPENROUTER_API_KEY must be set in the environment for the run subcommand.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import httpx

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_PATH = Path.home() / ".cache" / "consensus-skill" / "openrouter-models.json"
CACHE_TTL_SECONDS = 24 * 3600
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
EST_INPUT_TOKENS = 2000
EST_OUTPUT_TOKENS = 1500
LEVEL_COST_CAPS_USD = {1: 0.50, 2: 1.00, 3: 10.00}
LEVEL_TIER_COUNTS = {
    1: {"free": 3},
    2: {"free": 3, "economy": 3},
    3: {"free": 3, "economy": 3, "premium": 2},
}
TIER_FALLBACK_ORDER = {
    "free": ["free", "economy"],
    "economy": ["economy", "value"],
    "premium": ["premium", "value"],
}
REQUEST_TIMEOUT_SECONDS = 120
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2.0


@dataclass
class Model:
    """One row of the curated model dataset."""

    name: str
    provider: str
    input_cost: float
    output_cost: float
    humaneval: float
    swe_bench: float
    context: int
    specialization: str


def emit(payload: dict, stream: TextIO | None = None) -> None:
    """Write a JSON payload to stdout (or the given stream)."""
    (stream or sys.stdout).write(json.dumps(payload, indent=2) + "\n")


def parse_context(value: str | int | float) -> int:
    """Convert context sizes like '131K' or '1M' to a token count."""
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().upper()
    multiplier = 1
    if text.endswith("K"):
        multiplier, text = 1_000, text[:-1]
    elif text.endswith("M"):
        multiplier, text = 1_000_000, text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return 0


def load_models(csv_path: Path | None = None) -> list[Model]:
    """Load the curated model dataset from CSV, skipping malformed rows."""
    path = csv_path or DATA_DIR / "models.csv"
    models: list[Model] = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                models.append(
                    Model(
                        name=row["model"],
                        provider=row.get("provider", ""),
                        input_cost=float(row.get("input_cost") or 0),
                        output_cost=float(row.get("output_cost") or 0),
                        humaneval=float(row.get("humaneval_score") or 0),
                        swe_bench=float(row.get("swe_bench_score") or 0),
                        context=parse_context(row.get("context", 0)),
                        specialization=row.get("specialization", "general"),
                    )
                )
            except (ValueError, KeyError):
                continue
    return models


def load_bands(path: Path | None = None) -> dict:
    """Load band criteria (cost tiers, org levels) from JSON."""
    return json.loads((path or DATA_DIR / "bands_config.json").read_text())


def load_roles(path: Path | None = None) -> dict:
    """Load role definitions and per-domain level assignments from JSON."""
    return json.loads((path or DATA_DIR / "roles.json").read_text())


def models_in_cost_tier(models: list[Model], tier: str, bands: dict) -> list[Model]:
    """Filter models to a cost tier band, sorted by benchmark scores descending.

    The free tier requires both input and output cost to be exactly zero;
    other tiers compare input cost against the band's min/max.
    """
    criteria = bands["cost_tier_bands"][tier]
    max_cost = criteria.get("max_cost")
    min_cost = criteria.get("min_cost")
    kept = []
    for m in models:
        if max_cost is not None:
            if max_cost == 0.0:
                if m.input_cost != 0.0 or m.output_cost != 0.0:
                    continue
            elif m.input_cost > max_cost:
                continue
        if min_cost is not None and m.input_cost < min_cost:
            continue
        kept.append(m)
    return sorted(kept, key=lambda m: (-m.humaneval, -m.swe_bench))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_consensus_cli.py -v --no-cov
```

Expected: all `TestParseContext`, `TestLoadData`, `TestCostTierFilter` tests PASS.

- [ ] **Step 5: Lint, then commit**

```bash
uv run ruff check .claude/skills/consensus/scripts/consensus_cli.py tests/unit/test_consensus_cli.py --fix
uv run ruff format .claude/skills/consensus/scripts/consensus_cli.py tests/unit/test_consensus_cli.py
git add .claude/skills/consensus/scripts/consensus_cli.py tests/unit/test_consensus_cli.py
git commit -S -m "feat(consensus): engine skeleton with catalog loading and cost-tier filtering"
```

---

### Task 3: Role system prompts

**Files:**
- Modify: `.claude/skills/consensus/scripts/consensus_cli.py` (append after `models_in_cost_tier`)
- Modify: `tests/unit/test_consensus_cli.py` (append)

- [ ] **Step 1: Write the failing tests (append to test file)**

```python
class TestRolePrompts:
    def test_known_role_renders_definition(self):
        roles = cli.load_roles()
        prompt = cli.role_system_prompt("code_reviewer", roles)
        assert "code reviewer" in prompt
        assert "Code quality, standards, maintainability" in prompt
        assert "Security vulnerabilities?" in prompt

    def test_unknown_role_passes_through_as_literal_prompt(self):
        roles = cli.load_roles()
        literal = "Argue against this proposal as a skeptic."
        assert cli.role_system_prompt(literal, roles) == literal
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/unit/test_consensus_cli.py::TestRolePrompts -v --no-cov
```

Expected: FAIL with `AttributeError: module 'consensus_cli' has no attribute 'role_system_prompt'`.

- [ ] **Step 3: Implement (append to consensus_cli.py)**

```python
def role_system_prompt(role: str, roles_data: dict) -> str:
    """Build the system prompt for a professional role.

    Unknown role names are treated as literal system prompts, which is how
    flexible-mode stances ("argue for", "argue against") are passed in.
    """
    definition = roles_data["role_definitions"].get(role)
    if definition is None:
        return role
    return (
        f"You are acting as a {role.replace('_', ' ')}.\n\n"
        f"**Your Focus:** {definition['focus']}\n\n"
        f"**Key Questions to Address:** {definition['questions']}\n\n"
        f"**Your Perspective:** {definition['perspective']}\n\n"
        "Instructions:\n"
        "1. Analyze the question from your professional role's perspective\n"
        "2. Address the key questions relevant to your expertise\n"
        "3. Identify risks, concerns, or opportunities within your domain\n"
        "4. Provide specific, actionable insights\n"
        "5. Be concise but thorough; focus on what matters most from your perspective"
    )
```

- [ ] **Step 4: Run to verify pass**

```bash
uv run pytest tests/unit/test_consensus_cli.py::TestRolePrompts -v --no-cov
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/consensus/scripts/consensus_cli.py tests/unit/test_consensus_cli.py
git commit -S -m "feat(consensus): role system prompts with literal-stance passthrough"
```

---

### Task 4: Cost estimation and cap enforcement

**Files:**
- Modify: `.claude/skills/consensus/scripts/consensus_cli.py` (append)
- Modify: `tests/unit/test_consensus_cli.py` (append)

- [ ] **Step 1: Write the failing tests (append)**

```python
import pytest


class TestCost:
    def test_estimate_model_cost(self):
        m = make_model("m", 1.0, 10.0)
        expected = round((1.0 * cli.EST_INPUT_TOKENS + 10.0 * cli.EST_OUTPUT_TOKENS) / 1_000_000, 6)
        assert cli.estimate_model_cost(m) == expected

    def test_level1_cap_is_fifty_cents(self):
        assert cli.LEVEL_COST_CAPS_USD[1] == 0.50

    def test_cap_exceeded_raises_system_exit(self):
        with pytest.raises(SystemExit):
            cli.enforce_cost_cap(0.60, level=1, max_cost=None)

    def test_under_cap_passes(self):
        cli.enforce_cost_cap(0.40, level=1, max_cost=None)

    def test_max_cost_overrides_level_cap(self):
        cli.enforce_cost_cap(5.0, level=1, max_cost=10.0)
```

Note: keep the `import pytest` at the top of the test file with the other imports, not mid-file; ruff will flag E402 otherwise.

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/unit/test_consensus_cli.py::TestCost -v --no-cov
```

Expected: FAIL with `AttributeError` for `estimate_model_cost`.

- [ ] **Step 3: Implement (append to consensus_cli.py)**

```python
def estimate_model_cost(m: Model) -> float:
    """Estimate one consultation's cost in USD using assumed token counts."""
    return round(
        (m.input_cost * EST_INPUT_TOKENS + m.output_cost * EST_OUTPUT_TOKENS) / 1_000_000,
        6,
    )


def enforce_cost_cap(total: float, level: int | None, max_cost: float | None) -> None:
    """Exit with code 2 if the estimated cost exceeds the applicable cap.

    The explicit --max-cost flag overrides the per-level default cap.
    """
    cap = max_cost if max_cost is not None else LEVEL_COST_CAPS_USD.get(level or 0)
    if cap is not None and total > cap:
        emit(
            {
                "error": (
                    f"Estimated cost ${total:.4f} exceeds cap ${cap:.2f}. "
                    "Override with --max-cost if intended."
                )
            },
            stream=sys.stderr,
        )
        raise SystemExit(2)
```

- [ ] **Step 4: Run to verify pass**

```bash
uv run pytest tests/unit/test_consensus_cli.py::TestCost -v --no-cov
```

Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/consensus/scripts/consensus_cli.py tests/unit/test_consensus_cli.py
git commit -S -m "feat(consensus): cost estimation and per-level cap enforcement"
```

---

### Task 5: Live catalog fetch with disk cache

**Files:**
- Modify: `.claude/skills/consensus/scripts/consensus_cli.py` (append)
- Modify: `tests/unit/test_consensus_cli.py` (append; also add `import httpx`, `import json`, `import os`, `import time` to the top imports)

- [ ] **Step 1: Write the failing tests (append)**

```python
class TestLiveCatalog:
    def _client(self, handler):
        return httpx.Client(transport=httpx.MockTransport(handler))

    def test_fetch_and_cache(self, tmp_path):
        calls = {"n": 0}

        def handler(request):
            calls["n"] += 1
            return httpx.Response(200, json={"data": [{"id": "a/x"}, {"id": "b/y:free"}]})

        cache = tmp_path / "cache.json"
        ids = cli.fetch_live_model_ids(client=self._client(handler), cache_path=cache)
        assert ids == {"a/x", "b/y:free"}
        ids2 = cli.fetch_live_model_ids(client=self._client(handler), cache_path=cache)
        assert ids2 == ids
        assert calls["n"] == 1  # second call served from cache

    def test_stale_cache_used_on_network_error(self, tmp_path):
        def handler(request):
            raise httpx.ConnectError("boom")

        cache = tmp_path / "cache.json"
        cache.write_text(json.dumps(["old/model"]))
        two_days_ago = time.time() - 2 * 86400
        os.utime(cache, (two_days_ago, two_days_ago))
        ids = cli.fetch_live_model_ids(client=self._client(handler), cache_path=cache)
        assert ids == {"old/model"}

    def test_network_error_without_cache_raises(self, tmp_path):
        def handler(request):
            raise httpx.ConnectError("boom")

        with pytest.raises(httpx.HTTPError):
            cli.fetch_live_model_ids(client=self._client(handler), cache_path=tmp_path / "missing.json")
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/unit/test_consensus_cli.py::TestLiveCatalog -v --no-cov
```

Expected: FAIL with `AttributeError` for `fetch_live_model_ids`.

- [ ] **Step 3: Implement (append to consensus_cli.py)**

```python
def fetch_live_model_ids(
    client: httpx.Client | None = None,
    cache_path: Path | None = None,
    ttl: int = CACHE_TTL_SECONDS,
) -> set[str]:
    """Return the set of live OpenRouter model ids, using a disk cache.

    A fresh cache (younger than ttl) is served without a network call. On
    network failure a stale cache is used as fallback; with no cache at all
    the httpx error propagates.
    """
    cache = cache_path or CACHE_PATH
    if cache.exists() and time.time() - cache.stat().st_mtime < ttl:
        return set(json.loads(cache.read_text()))

    owns_client = client is None
    http = client or httpx.Client(timeout=30)
    try:
        resp = http.get(f"{OPENROUTER_BASE}/models")
        resp.raise_for_status()
        ids = {entry["id"] for entry in resp.json()["data"]}
    except httpx.HTTPError:
        if cache.exists():
            return set(json.loads(cache.read_text()))
        raise
    finally:
        if owns_client:
            http.close()

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(sorted(ids)))
    return ids
```

- [ ] **Step 4: Run to verify pass**

```bash
uv run pytest tests/unit/test_consensus_cli.py::TestLiveCatalog -v --no-cov
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/consensus/scripts/consensus_cli.py tests/unit/test_consensus_cli.py
git commit -S -m "feat(consensus): live OpenRouter catalog fetch with 24h disk cache and stale fallback"
```

---

### Task 6: Roster selection with role assignment and failover

**Files:**
- Modify: `.claude/skills/consensus/scripts/consensus_cli.py` (append)
- Modify: `tests/unit/test_consensus_cli.py` (append)

- [ ] **Step 1: Write the failing tests (append)**

```python
def fake_dataset():
    """Synthetic dataset spanning all cost tiers."""
    return [
        make_model("free-a:free", 0, 0, he=90),
        make_model("free-b:free", 0, 0, he=85),
        make_model("free-c:free", 0, 0, he=80),
        make_model("free-d:free", 0, 0, he=75),
        make_model("econ-a", 0.5, 0.9, he=88),
        make_model("econ-b", 0.3, 0.8, he=84),
        make_model("econ-c", 0.2, 0.7, he=82),
        make_model("val-a", 3.0, 9.0, he=89),
        make_model("prem-a", 12.0, 30.0, he=92),
        make_model("prem-b", 11.0, 28.0, he=91),
    ]


class TestRosterSelection:
    def setup_method(self):
        self.bands = cli.load_bands()
        self.roles = cli.load_roles()

    def test_level1_is_three_free_models_with_level1_roles(self):
        roster = cli.select_roster(fake_dataset(), self.bands, self.roles, 1, "code_review")
        assert [r["model"] for r in roster] == ["free-a:free", "free-b:free", "free-c:free"]
        assert [r["role"] for r in roster] == ["code_reviewer", "security_checker", "technical_validator"]

    def test_level2_is_additive_six_models(self):
        roster = cli.select_roster(fake_dataset(), self.bands, self.roles, 2, "code_review")
        assert len(roster) == 6
        assert [r["model"] for r in roster][:3] == ["free-a:free", "free-b:free", "free-c:free"]
        assert {r["model"] for r in roster[3:]} == {"econ-a", "econ-b", "econ-c"}

    def test_level3_adds_two_premium(self):
        roster = cli.select_roster(fake_dataset(), self.bands, self.roles, 3, "architecture")
        assert len(roster) == 8
        assert {r["model"] for r in roster[6:]} == {"prem-a", "prem-b"}

    def test_live_validation_skips_dead_model(self):
        live = {m.name for m in fake_dataset()} - {"free-a:free"}
        roster = cli.select_roster(fake_dataset(), self.bands, self.roles, 1, "code_review", live=live)
        assert [r["model"] for r in roster] == ["free-b:free", "free-c:free", "free-d:free"]

    def test_free_exhaustion_fails_over_to_economy(self):
        live = {"free-a:free", "econ-a", "econ-b", "econ-c", "val-a", "prem-a", "prem-b"}
        roster = cli.select_roster(fake_dataset(), self.bands, self.roles, 1, "code_review", live=live)
        assert [r["model"] for r in roster] == ["free-a:free", "econ-a", "econ-b"]

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError):
            cli.select_roster(fake_dataset(), self.bands, self.roles, 4, "code_review")

    def test_invalid_domain_raises(self):
        with pytest.raises(ValueError):
            cli.select_roster(fake_dataset(), self.bands, self.roles, 1, "nonsense")
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/unit/test_consensus_cli.py::TestRosterSelection -v --no-cov
```

Expected: FAIL with `AttributeError` for `select_roster`.

- [ ] **Step 3: Implement (append to consensus_cli.py)**

```python
def select_roster(
    models: list[Model],
    bands: dict,
    roles_data: dict,
    level: int,
    domain: str,
    live: set[str] | None = None,
) -> list[dict]:
    """Pick models per tier for a level, validate against live ids, assign roles.

    Tier counts are additive (level 2 includes level 1's free picks). When a
    tier runs out of live candidates, the fallback tier order in
    TIER_FALLBACK_ORDER supplies substitutes, which is how level 1 can use
    cheap paid models (within its cost cap) when free models are unavailable.
    """
    if level not in LEVEL_TIER_COUNTS:
        raise ValueError(f"Invalid level: {level}. Must be 1, 2, or 3.")
    domain_levels = roles_data["domain_roles"].get(domain)
    if domain_levels is None:
        valid = ", ".join(roles_data["domain_roles"])
        raise ValueError(f"Invalid domain: {domain}. Valid domains: {valid}")
    roles = domain_levels[str(level)]

    picked: list[Model] = []
    for tier, count in LEVEL_TIER_COUNTS[level].items():
        candidates: list[Model] = []
        for fallback_tier in TIER_FALLBACK_ORDER[tier]:
            candidates.extend(models_in_cost_tier(models, fallback_tier, bands))
        taken = 0
        for candidate in candidates:
            if taken >= count:
                break
            if any(p.name == candidate.name for p in picked):
                continue
            if live is not None and candidate.name not in live:
                continue
            picked.append(candidate)
            taken += 1

    return [
        {
            "model": m.name,
            "role": role,
            "est_cost_usd": estimate_model_cost(m),
        }
        for m, role in zip(picked, roles)
    ]
```

- [ ] **Step 4: Run to verify pass**

```bash
uv run pytest tests/unit/test_consensus_cli.py::TestRosterSelection -v --no-cov
```

Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/consensus/scripts/consensus_cli.py tests/unit/test_consensus_cli.py
git commit -S -m "feat(consensus): band-based roster selection with live validation and tier failover"
```

---

### Task 7: Parallel fan-out (run)

**Files:**
- Modify: `.claude/skills/consensus/scripts/consensus_cli.py` (append)
- Modify: `tests/unit/test_consensus_cli.py` (append; add `import asyncio` to top imports)

- [ ] **Step 1: Write the failing tests (append)**

```python
def _ok_response(model_name):
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": f"answer from {model_name}"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        },
    )


class TestRunConsensus:
    def test_partial_failure_returns_successes_and_errors(self, monkeypatch):
        monkeypatch.setattr(cli, "RETRY_BACKOFF_SECONDS", 0.0)

        def handler(request):
            body = json.loads(request.content)
            if body["model"] == "bad/model":
                return httpx.Response(404, json={"error": "not found"})
            return _ok_response(body["model"])

        entries = [
            {"model": "good/model", "role": None, "system_prompt": None},
            {"model": "bad/model", "role": None, "system_prompt": None},
        ]
        out = asyncio.run(
            cli.run_consensus(
                entries, "question?", "test-key", catalog={}, transport=httpx.MockTransport(handler)
            )
        )
        assert out["succeeded"] == 1
        assert out["failed"] == 1
        good = next(r for r in out["results"] if r["model"] == "good/model")
        assert good["response"] == "answer from good/model"
        bad = next(r for r in out["results"] if r["model"] == "bad/model")
        assert "404" in bad["error"]

    def test_system_prompt_is_sent(self):
        seen = {}

        def handler(request):
            body = json.loads(request.content)
            seen["messages"] = body["messages"]
            return _ok_response(body["model"])

        entries = [{"model": "m/x", "role": "skeptic", "system_prompt": "Be skeptical."}]
        asyncio.run(
            cli.run_consensus(
                entries, "q?", "k", catalog={}, transport=httpx.MockTransport(handler)
            )
        )
        assert seen["messages"][0] == {"role": "system", "content": "Be skeptical."}
        assert seen["messages"][1] == {"role": "user", "content": "q?"}

    def test_retry_on_429_then_success(self, monkeypatch):
        monkeypatch.setattr(cli, "RETRY_BACKOFF_SECONDS", 0.0)
        attempts = {"n": 0}

        def handler(request):
            attempts["n"] += 1
            if attempts["n"] == 1:
                return httpx.Response(429, json={"error": "rate limited"})
            return _ok_response("m/x")

        entries = [{"model": "m/x", "role": None, "system_prompt": None}]
        out = asyncio.run(
            cli.run_consensus(
                entries, "q?", "k", catalog={}, transport=httpx.MockTransport(handler)
            )
        )
        assert out["succeeded"] == 1
        assert attempts["n"] == 2

    def test_cost_computed_from_catalog(self):
        def handler(request):
            return _ok_response("m/x")

        catalog = {"m/x": make_model("m/x", 1.0, 2.0)}
        entries = [{"model": "m/x", "role": None, "system_prompt": None}]
        out = asyncio.run(
            cli.run_consensus(
                entries, "q?", "k", catalog=catalog, transport=httpx.MockTransport(handler)
            )
        )
        expected = round((1.0 * 100 + 2.0 * 50) / 1_000_000, 6)
        assert out["results"][0]["cost_usd"] == expected
        assert out["total_cost_usd"] == expected
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/unit/test_consensus_cli.py::TestRunConsensus -v --no-cov
```

Expected: FAIL with `AttributeError` for `run_consensus`.

- [ ] **Step 3: Implement (append to consensus_cli.py)**

```python
async def call_model(
    client: httpx.AsyncClient,
    entry: dict,
    prompt: str,
    api_key: str,
    catalog: dict[str, Model],
) -> dict:
    """Send one chat completion and return a result record; never raises.

    Retries 429 and 5xx responses with backoff; other HTTP errors are
    terminal for this model only.
    """
    messages = []
    if entry.get("system_prompt"):
        messages.append({"role": "system", "content": entry["system_prompt"]})
    messages.append({"role": "user", "content": prompt})
    record = {
        "model": entry["model"],
        "role": entry.get("role"),
        "response": None,
        "tokens": None,
        "cost_usd": None,
        "error": None,
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = await client.post(
                f"{OPENROUTER_BASE}/chat/completions",
                json={"model": entry["model"], "messages": messages},
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                usage = data.get("usage", {})
                record["response"] = data["choices"][0]["message"]["content"]
                record["tokens"] = usage
                row = catalog.get(entry["model"])
                if row is not None:
                    record["cost_usd"] = round(
                        (
                            row.input_cost * usage.get("prompt_tokens", 0)
                            + row.output_cost * usage.get("completion_tokens", 0)
                        )
                        / 1_000_000,
                        6,
                    )
                return record
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS * (2**attempt))
                    continue
            record["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
            return record
        except httpx.HTTPError as exc:
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (2**attempt))
                continue
            record["error"] = f"{type(exc).__name__}: {exc}"
            return record
    record["error"] = "retries exhausted"
    return record


async def run_consensus(
    entries: list[dict],
    prompt: str,
    api_key: str,
    catalog: dict[str, Model],
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict:
    """Fan the prompt out to all entries in parallel and aggregate results."""
    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT_SECONDS, transport=transport
    ) as client:
        results = await asyncio.gather(
            *[call_model(client, e, prompt, api_key, catalog) for e in entries]
        )
    succeeded = [r for r in results if r["error"] is None]
    return {
        "results": list(results),
        "succeeded": len(succeeded),
        "failed": len(results) - len(succeeded),
        "total_cost_usd": round(sum(r["cost_usd"] or 0 for r in succeeded), 6),
    }
```

- [ ] **Step 4: Run to verify pass**

```bash
uv run pytest tests/unit/test_consensus_cli.py::TestRunConsensus -v --no-cov
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/consensus/scripts/consensus_cli.py tests/unit/test_consensus_cli.py
git commit -S -m "feat(consensus): parallel OpenRouter fan-out with retries and per-model error isolation"
```

---

### Task 8: Refresh report

**Files:**
- Modify: `.claude/skills/consensus/scripts/consensus_cli.py` (append)
- Modify: `tests/unit/test_consensus_cli.py` (append)

- [ ] **Step 1: Write the failing test (append)**

```python
class TestRefresh:
    def test_reports_dead_and_new_free_models(self):
        curated = [make_model("alive/x", 0, 0), make_model("dead/y", 1.0, 2.0)]
        live = {"alive/x", "brand/new:free", "paid/other"}
        report = cli.refresh_report(curated, live)
        assert report["dead_in_curated"] == ["dead/y"]
        assert report["live_free_not_in_curated"] == ["brand/new:free"]
        assert report["curated_count"] == 2
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/unit/test_consensus_cli.py::TestRefresh -v --no-cov
```

Expected: FAIL with `AttributeError` for `refresh_report`.

- [ ] **Step 3: Implement (append to consensus_cli.py)**

```python
def refresh_report(models: list[Model], live: set[str]) -> dict:
    """Compare the curated dataset against live OpenRouter model ids.

    Reports rows that no longer exist upstream and free models that exist
    upstream but are not yet curated. Never edits the dataset: the
    benchmark and specialization fields are hand-rated.
    """
    curated = {m.name for m in models}
    return {
        "dead_in_curated": sorted(curated - live),
        "live_free_not_in_curated": sorted(
            i for i in live if i.endswith(":free") and i not in curated
        ),
        "curated_count": len(curated),
        "live_count": len(live),
    }
```

- [ ] **Step 4: Run to verify pass**

```bash
uv run pytest tests/unit/test_consensus_cli.py::TestRefresh -v --no-cov
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/consensus/scripts/consensus_cli.py tests/unit/test_consensus_cli.py
git commit -S -m "feat(consensus): refresh report diffing curated dataset against live catalog"
```

---

### Task 9: CLI wiring (argparse and main)

**Files:**
- Modify: `.claude/skills/consensus/scripts/consensus_cli.py` (append)
- Modify: `tests/unit/test_consensus_cli.py` (append)

- [ ] **Step 1: Write the failing tests (append)**

```python
class TestCliWiring:
    def test_select_defaults(self):
        args = cli.build_parser().parse_args(["select", "--level", "2"])
        assert args.domain == "code_review"
        assert args.no_validate is False

    def test_run_requires_prompt_file(self):
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(["run"])

    def test_main_select_no_validate_emits_roster_json(self, capsys):
        rc = cli.main(["select", "--level", "1", "--no-validate"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["level"] == 1
        assert len(payload["roster"]) == 3
        assert payload["cap_usd"] == 0.50

    def test_main_run_without_api_key_fails_fast(self, monkeypatch, tmp_path, capsys):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")
        rc = cli.main(["run", "--prompt-file", str(prompt), "--models", "m/x"])
        assert rc == 1
        assert "OPENROUTER_API_KEY" in capsys.readouterr().err
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/unit/test_consensus_cli.py::TestCliWiring -v --no-cov
```

Expected: FAIL with `AttributeError` for `build_parser`.

- [ ] **Step 3: Implement (append to consensus_cli.py)**

```python
DOMAIN_CHOICES = ["code_review", "security", "architecture", "general"]


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with the four subcommands."""
    parser = argparse.ArgumentParser(prog="consensus_cli", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_select = sub.add_parser("select", help="Build a roster for a level and domain")
    p_select.add_argument("--level", type=int, required=True, choices=[1, 2, 3])
    p_select.add_argument("--domain", default="code_review", choices=DOMAIN_CHOICES)
    p_select.add_argument("--limit", type=int, default=None)
    p_select.add_argument(
        "--no-validate", action="store_true", help="Skip live OpenRouter validation"
    )

    p_estimate = sub.add_parser("estimate", help="Cost preview for a level")
    p_estimate.add_argument("--level", type=int, required=True, choices=[1, 2, 3])
    p_estimate.add_argument("--domain", default="code_review", choices=DOMAIN_CHOICES)

    p_run = sub.add_parser("run", help="Fan a prompt out to models in parallel")
    p_run.add_argument("--prompt-file", required=True)
    p_run.add_argument("--roster-file", help="Roster JSON produced by select")
    p_run.add_argument("--models", help="Comma-separated model ids (flexible mode)")
    p_run.add_argument(
        "--roles-file",
        help="JSON object mapping model id to a role name or literal system prompt",
    )
    p_run.add_argument("--level", type=int, choices=[1, 2, 3], help="Cap context for run")
    p_run.add_argument("--max-cost", type=float, help="Override the cost cap in USD")

    sub.add_parser("refresh", help="Diff curated dataset against the live catalog")
    return parser


def build_entries(args: argparse.Namespace, roles_data: dict) -> list[dict]:
    """Resolve run arguments into model entries with system prompts."""
    entries: list[dict] = []
    if args.roster_file:
        roster = json.loads(Path(args.roster_file).read_text())
        items = roster["roster"] if isinstance(roster, dict) else roster
        for item in items:
            role = item.get("role")
            entries.append(
                {
                    "model": item["model"],
                    "role": role,
                    "system_prompt": role_system_prompt(role, roles_data) if role else None,
                }
            )
    elif args.models:
        roles_map = (
            json.loads(Path(args.roles_file).read_text()) if args.roles_file else {}
        )
        for name in args.models.split(","):
            name = name.strip()
            role = roles_map.get(name)
            entries.append(
                {
                    "model": name,
                    "role": role,
                    "system_prompt": role_system_prompt(role, roles_data) if role else None,
                }
            )
    else:
        emit({"error": "run requires --roster-file or --models"}, stream=sys.stderr)
        raise SystemExit(2)
    return entries


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns a process exit code."""
    args = build_parser().parse_args(argv)
    models = load_models()
    bands = load_bands()
    roles = load_roles()

    if args.command in ("select", "estimate"):
        live = None
        if args.command == "select" and not args.no_validate:
            live = fetch_live_model_ids()
        roster = select_roster(models, bands, roles, args.level, args.domain, live=live)
        limit = getattr(args, "limit", None)
        if limit:
            roster = roster[:limit]
        emit(
            {
                "level": args.level,
                "domain": args.domain,
                "roster": roster,
                "estimated_cost_usd": round(sum(r["est_cost_usd"] for r in roster), 6),
                "cap_usd": LEVEL_COST_CAPS_USD[args.level],
            }
        )
        return 0

    if args.command == "run":
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            emit({"error": "OPENROUTER_API_KEY is not set"}, stream=sys.stderr)
            return 1
        prompt = Path(args.prompt_file).read_text()
        entries = build_entries(args, roles)
        catalog = {m.name: m for m in models}
        estimate = round(
            sum(
                estimate_model_cost(catalog[e["model"]])
                for e in entries
                if e["model"] in catalog
            ),
            6,
        )
        enforce_cost_cap(estimate, args.level, args.max_cost)
        outcome = asyncio.run(run_consensus(entries, prompt, api_key, catalog))
        emit(outcome)
        return 0 if outcome["succeeded"] else 3

    live = fetch_live_model_ids()
    emit(refresh_report(models, live))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the full test file**

```bash
uv run pytest tests/unit/test_consensus_cli.py -v --no-cov
```

Expected: ALL tests PASS (67 as delivered).

- [ ] **Step 5: Manual sanity check with real data (no API key needed)**

```bash
uv run .claude/skills/consensus/scripts/consensus_cli.py select --level 1 --no-validate
uv run .claude/skills/consensus/scripts/consensus_cli.py estimate --level 3 --domain architecture
```

Expected: first prints a 3-model roster of `:free` models with `cap_usd: 0.5`; second prints an 8-model roster with a nonzero estimate under 10.0.

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check .claude/skills/consensus/scripts/consensus_cli.py tests/unit/test_consensus_cli.py --fix
uv run ruff format .claude/skills/consensus/scripts/consensus_cli.py tests/unit/test_consensus_cli.py
uv run pytest tests/unit/test_consensus_cli.py -q --no-cov
git add .claude/skills/consensus/scripts/consensus_cli.py tests/unit/test_consensus_cli.py
git commit -S -m "feat(consensus): CLI wiring for select, estimate, run, and refresh"
```

---

### Task 10: SKILL.md and workflow files

**Files:**
- Create: `.claude/skills/consensus/SKILL.md`
- Create: `.claude/skills/consensus/workflows/tiered-review.md`
- Create: `.claude/skills/consensus/workflows/consensus.md`
- Create: `.claude/skills/consensus/workflows/refresh-data.md`

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: consensus
description: Multi-model consensus via OpenRouter, replacing the zen/pal MCP consensus tools. Two modes; tiered-review (structured IT review team, levels 1-3, professional roles per domain) and consensus (fully flexible models and stances). Use when the user wants second opinions from multiple AI models, a tiered review, multi-model consensus, or to consult other models. Triggers on; consensus, tiered consensus, tiered review, second opinion, multi-model review, ask other models, review team, model roster.
---

# Consensus

Fan a question out to multiple AI models via OpenRouter and synthesize their
responses. The engine script handles selection, parallel calls, retries,
failover, and cost caps. You (Claude) do the synthesis; never delegate
synthesis to a model template.

## Prerequisites

- `OPENROUTER_API_KEY` set in the environment. If `run` fails with a key
  error, tell the user and stop.
- All commands run from the repo root with `uv run` (the script carries
  PEP 723 inline dependencies).

## Mode routing

| User intent | Mode | Workflow |
| --- | --- | --- |
| "tiered consensus", "review team", "level 1/2/3", wants structured IT review | Tiered review | `workflows/tiered-review.md` |
| Names specific models, wants stances (for/against), ad-hoc panel | Flexible consensus | `workflows/consensus.md` |
| "refresh the model data", roster references dead models | Data refresh | `workflows/refresh-data.md` |

When the request is ambiguous, default to tiered review at level 1 (it is
nearly free) and say so.

## Engine quick reference

```bash
uv run .claude/skills/consensus/scripts/consensus_cli.py select --level 2 --domain architecture
uv run .claude/skills/consensus/scripts/consensus_cli.py estimate --level 3
uv run .claude/skills/consensus/scripts/consensus_cli.py run --prompt-file /tmp/q.txt --roster-file /tmp/roster.json
uv run .claude/skills/consensus/scripts/consensus_cli.py run --prompt-file /tmp/q.txt --models "openai/gpt-5.1,anthropic/claude-opus-4.6" --roles-file /tmp/roles.json
uv run .claude/skills/consensus/scripts/consensus_cli.py refresh
```

Domains: `code_review` (default), `security`, `architecture`, `general`.

## Levels and cost caps

| Level | Roster | Cap |
| --- | --- | --- |
| 1 | 3 free models (failover may substitute cheap paid models) | $0.50 |
| 2 | level 1 + 3 economy models (6 total) | $1.00 |
| 3 | level 2 + 2 premium models (8 total) | $10.00 |

The script refuses to run past the cap; pass `--max-cost` only after the
user explicitly approves the higher spend.

## Synthesis requirements

After `run` returns, synthesize from the raw JSON yourself:

1. Per-model summary (one line each, name the model and role).
2. Consensus points: claims at least half the models agree on.
3. Disagreements: attribute positions to specific models.
4. Your recommendation, weighing role-specific concerns.
5. Report actual `total_cost_usd` and any failed models.

Never present template text as analysis. If `failed > 0`, say which models
failed and that the synthesis covers a partial panel.
```

Note: the description field avoids colons inside the YAML value (uses
semicolons) to keep the frontmatter parseable.

- [ ] **Step 2: Write workflows/tiered-review.md**

```markdown
# Tiered Review (IT review team)

Structured multi-model review with levels and professional roles.

## Procedure

1. **Select the roster.** Pick the domain from the user's topic (security
   questions get `security`, design questions get `architecture`, code gets
   `code_review`, anything else `general`).

   ```bash
   uv run .claude/skills/consensus/scripts/consensus_cli.py select --level <N> --domain <domain> > /tmp/consensus-roster.json
   cat /tmp/consensus-roster.json
   ```

2. **Present roster and cost.** Show the user the models, roles, and
   `estimated_cost_usd`. For level 1 proceed without waiting. For level 2-3,
   confirm with the user before running unless they already approved the
   level explicitly.

3. **Write the prompt file.** Include the user's question plus any context
   they supplied. Keep it self-contained; the models see nothing else.

   ```bash
   cat > /tmp/consensus-prompt.txt << 'PROMPT'
   <the question, with context>
   PROMPT
   ```

4. **Run.**

   ```bash
   uv run .claude/skills/consensus/scripts/consensus_cli.py run \
     --prompt-file /tmp/consensus-prompt.txt \
     --roster-file /tmp/consensus-roster.json \
     --level <N>
   ```

5. **Synthesize** per the requirements in SKILL.md. Structure the output as:
   executive summary (2-3 sentences), consensus points, disagreements with
   attribution, role-specific highlights worth noting, recommendation,
   actual cost and failures.

## Failure handling

- `failed > 0` but `succeeded >= 2`: synthesize and flag the gap.
- `succeeded < 2`: do not synthesize a "consensus" from one voice. Report
  the errors and offer to rerun or escalate a level.
- Roster came back short (fewer models than the level promises): mention it;
  the live catalog validation likely dropped dead entries. Offer the
  refresh-data workflow.
```

- [ ] **Step 3: Write workflows/consensus.md**

```markdown
# Flexible Consensus

Ad-hoc multi-model consultation: any models, any roles or stances.

## Procedure

1. **Choose models.** If the user named models, use them verbatim. Otherwise
   pick 3-5 from `data/models.csv` spanning at least two providers; prefer
   high `humaneval_score` within the user's cost comfort.

2. **Assign stances or roles (optional).** Build a roles file mapping each
   model to either a role name from `data/roles.json` (for example
   `system_architect`) or a literal system prompt:

   ```bash
   cat > /tmp/consensus-roles.json << 'ROLES'
   {
     "openai/gpt-5.1": "Argue FOR the proposal. Steelman it.",
     "anthropic/claude-opus-4.6": "Argue AGAINST the proposal. Find the flaws.",
     "deepseek/deepseek-chat:free": "technical_validator"
   }
   ROLES
   ```

3. **Write the prompt file** (self-contained question plus context).

4. **Run.** Pass `--max-cost` if the user approved a budget; otherwise the
   run is uncapped only when no `--level` is given, so state the expected
   cost before running paid models.

   ```bash
   uv run .claude/skills/consensus/scripts/consensus_cli.py run \
     --prompt-file /tmp/consensus-prompt.txt \
     --models "openai/gpt-5.1,anthropic/claude-opus-4.6,deepseek/deepseek-chat:free" \
     --roles-file /tmp/consensus-roles.json \
     --max-cost 2.00
   ```

5. **Synthesize** per SKILL.md. With for/against stances, present the
   strongest case each side made before your verdict.
```

- [ ] **Step 4: Write workflows/refresh-data.md**

```markdown
# Refresh Model Data

Keep `data/models.csv` aligned with the live OpenRouter catalog. The script
never edits the dataset; benchmark scores and specializations are hand-rated.

## Procedure

1. **Generate the report.**

   ```bash
   uv run .claude/skills/consensus/scripts/consensus_cli.py refresh
   ```

2. **Remove dead rows.** For each model in `dead_in_curated`, delete its row
   from `.claude/skills/consensus/data/models.csv` (or fix the id if the
   model was renamed upstream; check https://openrouter.ai/models).

3. **Curate additions sparingly.** From `live_free_not_in_curated`, add only
   models worth consulting (recognizable provider, plausible quality). A new
   row needs: rank (append after existing), model id, provider, tier,
   status, context (like `131K`), input_cost, output_cost, org_level,
   specialization, role, strength, humaneval_score and swe_bench_score
   (estimate from public benchmarks; mark estimates honestly), openrouter
   URL, and today's date.

4. **Verify.**

   ```bash
   uv run .claude/skills/consensus/scripts/consensus_cli.py select --level 1
   uv run pytest tests/unit/test_consensus_cli.py -q --no-cov
   ```

5. **Commit** the dataset change with a `chore(consensus): refresh model data`
   message.
```

- [ ] **Step 5: Verify SKILL.md stays under 200 lines and commit**

```bash
wc -l .claude/skills/consensus/SKILL.md
git add .claude/skills/consensus/SKILL.md .claude/skills/consensus/workflows/
git commit -S -m "feat(consensus): SKILL.md router and tiered/flexible/refresh workflows"
```

Expected: line count under 200.

---

### Task 11: Registration, full gates, PR

**Files:**
- Modify: `AGENTS-AND-SKILLS.md` (add entry, alphabetical among skills)

- [ ] **Step 1: Register the skill**

Find the skills section in `AGENTS-AND-SKILLS.md` (entries are formatted as bold-linked names with a short description). Insert alphabetically (after `claude-md-improver`, before `debug-tests` if those are the neighbors):

```markdown
**[/consensus](/.claude/skills/consensus/SKILL.md)**
Multi-model consensus via OpenRouter with two modes: a tiered IT review team
(levels 1-3, professional roles per domain) and fully flexible model/stance
selection. Bundles a uv-run engine script for parallel fan-out, band-based
roster selection with live catalog validation, failover, and per-level cost
caps; Claude synthesizes the raw responses. Replaces the zen/pal MCP
consensus tools. Activates on: "consensus", "tiered review", "second
opinion", "multi-model".
```

- [ ] **Step 2: Run the full pre-commit suite**

```bash
pre-commit run --all-files
```

Expected: all hooks pass. If the front-matter validator or markdownlint flags the new skill files, fix per the error messages (skill SKILL.md files may be exempt from doc frontmatter; if flagged, match the frontmatter shape used by an existing skill like `.claude/skills/ci-fix/SKILL.md`).

- [ ] **Step 3: Run the whole unit suite to catch collateral damage**

```bash
uv run pytest tests/unit -q --no-cov
```

Expected: all pass.

- [ ] **Step 4: Commit and open the PR**

```bash
git add AGENTS-AND-SKILLS.md
git commit -S -m "docs(skills): register consensus skill"
git push -u origin feat/consensus-skill
gh pr create --title "feat(consensus): multi-model consensus skill replacing zen-mcp consensus suite" --body "$(cat <<'EOF'
## Summary
- New umbrella skill `consensus` with two modes: tiered IT review team (levels 1-3, roles per domain) and flexible model/stance consensus
- One PEP 723 uv-run engine script: select/estimate/run/refresh, parallel OpenRouter fan-out, retries, tier failover, live catalog validation (24h cache), per-level cost caps (L1 $0.50, L2 $1, L3 $10)
- Curated model data salvaged from zen-mcp-server (models.csv, bands_config.json, roles.json export)
- Synthesis moves from Python templates to Claude (fixes the broken synthesis layer)
- Spec: docs/superpowers/specs/2026-06-11-consensus-skill-design.md

## Test plan
- [x] 67 unit tests (band filtering, roster failover, cost caps, cache corruption/races, fan-out with MockTransport, null-content handling, gather isolation, run input validation, CLI error paths and exit codes)
- [ ] Manual level-1 smoke run (3 free models, ~$0) post-merge

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 5: Manual smoke eval (requires OPENROUTER_API_KEY; ~$0)**

```bash
uv run .claude/skills/consensus/scripts/consensus_cli.py select --level 1 > /tmp/consensus-roster.json
cat /tmp/consensus-roster.json
echo "Is SQLite a reasonable production database for a single-user web app? Answer in 3 sentences." > /tmp/consensus-prompt.txt
uv run .claude/skills/consensus/scripts/consensus_cli.py run --prompt-file /tmp/consensus-prompt.txt --roster-file /tmp/consensus-roster.json --level 1
```

Expected: roster of 3 live free models; run returns `succeeded: 3, failed: 0`, three distinct response texts, `total_cost_usd: 0.0` (or a few tenths of a cent if failover used a paid model). This is the parity scenario the MCP server failed on 2026-06-10.

---

## Execution order

Tasks are strictly sequential (each builds on the prior file state). Task 10 (docs) and Task 8 (refresh) could technically swap, but keep the order; it is not worth parallelizing a single-file build.

## Parity follow-up (not in this plan)

After the skill proves the four parity criteria in the spec, decide the zen-mcp-server fork's fate (archive vs keep) and whether to remove the pal MCP server from session config. That decision belongs to the user, not this plan.
