"""Unit tests for the consensus skill engine script.

The script lives under .claude/skills/ (a dot-directory), so it is loaded by
file path rather than imported as a package, matching the pattern in
tests/integration/test_scripts.py.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / ".claude" / "skills" / "consensus" / "scripts" / "consensus_cli.py"

_spec = importlib.util.spec_from_file_location("consensus_cli", SCRIPT)
assert _spec is not None
assert _spec.loader is not None
cli = importlib.util.module_from_spec(_spec)
sys.modules["consensus_cli"] = cli
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
    """Tests for the parse_context helper function."""

    def test_k_suffix(self):
        """Parse a context string with K suffix."""
        assert cli.parse_context("131K") == 131_000

    def test_m_suffix(self):
        """Parse a context string with M suffix."""
        assert cli.parse_context("1M") == 1_000_000

    def test_plain_number(self):
        """Parse a plain numeric string."""
        assert cli.parse_context("200000") == 200_000

    def test_numeric_passthrough(self):
        """Pass through an integer directly."""
        assert cli.parse_context(65000) == 65_000

    def test_garbage_returns_zero(self):
        """Return zero for unparseable context strings."""
        assert cli.parse_context("unknown") == 0


class TestLoadData:
    """Tests for the data loading functions."""

    def test_load_models_returns_rows(self):
        """Load models CSV and verify every row has a non-empty name."""
        models = cli.load_models()
        assert len(models) > 20
        assert all(m.name for m in models)

    def test_load_bands_has_cost_tiers(self):
        """Load bands config and verify cost tier names are present."""
        bands = cli.load_bands()
        assert set(bands["cost_tier_bands"]) >= {"free", "economy", "value", "premium"}

    def test_load_roles_has_domains(self):
        """Load roles config and verify domain_roles structural integrity."""
        roles = cli.load_roles()
        assert set(roles["domain_roles"]) == {
            "code_review",
            "security",
            "architecture",
            "general",
        }
        referenced = {
            r
            for levels in roles["domain_roles"].values()
            for lst in levels.values()
            for r in lst
        }
        assert referenced <= set(roles["role_definitions"])


class TestCostTierFilter:
    """Tests for the models_in_cost_tier filter function."""

    def test_free_requires_zero_input_and_output(self):
        """Free tier requires both input and output costs to be exactly zero."""
        bands = cli.load_bands()
        models = [make_model("a:free", 0.0, 0.0), make_model("b", 0.0, 0.5)]
        free = cli.models_in_cost_tier(models, "free", bands)
        assert [m.name for m in free] == ["a:free"]

    def test_sorted_by_humaneval_descending(self):
        """Results are sorted by humaneval score descending."""
        bands = cli.load_bands()
        models = [
            make_model("low:free", 0, 0, he=70),
            make_model("high:free", 0, 0, he=90),
        ]
        free = cli.models_in_cost_tier(models, "free", bands)
        assert [m.name for m in free] == ["high:free", "low:free"]

    def test_swe_bench_tiebreak(self):
        """Equal humaneval scores fall back to swe_bench descending."""
        bands = cli.load_bands()
        models = [
            make_model("low-swe:free", 0, 0, he=80, swe=50),
            make_model("high-swe:free", 0, 0, he=80, swe=75),
        ]
        free = cli.models_in_cost_tier(models, "free", bands)
        assert [m.name for m in free] == ["high-swe:free", "low-swe:free"]

    def test_economy_band_range(self):
        """Economy tier includes low-cost models but excludes expensive ones."""
        bands = cli.load_bands()
        models = [make_model("cheap", 0.5, 0.9), make_model("expensive", 5.0, 20.0)]
        econ = cli.models_in_cost_tier(models, "economy", bands)
        assert [m.name for m in econ] == ["cheap"]


class TestRolePrompts:
    """Tests for the role_system_prompt function."""

    def test_known_role_renders_definition(self):
        """A known role key expands into a structured system prompt."""
        roles = cli.load_roles()
        prompt = cli.role_system_prompt("code_reviewer", roles)
        assert "code reviewer" in prompt
        assert "Code quality, standards, maintainability" in prompt
        assert "Security vulnerabilities?" in prompt

    def test_unknown_role_passes_through_as_literal_prompt(self):
        """An unrecognised role string is returned verbatim as a literal prompt."""
        roles = cli.load_roles()
        literal = "Argue against this proposal as a skeptic."
        assert cli.role_system_prompt(literal, roles) == literal


class TestCost:
    """Tests for cost estimation and cap enforcement."""

    def test_estimate_model_cost(self):
        """Estimate cost using assumed token counts and per-million pricing."""
        m = make_model("m", 1.0, 10.0)
        expected = round(
            (1.0 * cli.EST_INPUT_TOKENS + 10.0 * cli.EST_OUTPUT_TOKENS) / 1_000_000, 6
        )
        assert cli.estimate_model_cost(m) == expected

    def test_level1_cap_is_fifty_cents(self):
        """Level 1 default cost cap is exactly $0.50."""
        assert cli.LEVEL_COST_CAPS_USD[1] == 0.50

    def test_cap_exceeded_raises_system_exit(self):
        """enforce_cost_cap raises SystemExit when estimated cost exceeds the cap."""
        with pytest.raises(SystemExit) as exc_info:
            cli.enforce_cost_cap(0.60, level=1, max_cost=None)
        assert exc_info.value.code == 2

    def test_cap_at_exact_limit_passes(self):
        """enforce_cost_cap does not raise when cost equals the cap exactly."""
        cli.enforce_cost_cap(0.50, level=1, max_cost=None)

    def test_under_cap_passes(self):
        """enforce_cost_cap does not raise when cost is within the cap."""
        cli.enforce_cost_cap(0.40, level=1, max_cost=None)

    def test_max_cost_overrides_level_cap(self):
        """An explicit --max-cost flag overrides the per-level default cap."""
        cli.enforce_cost_cap(5.0, level=1, max_cost=10.0)
