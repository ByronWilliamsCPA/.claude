"""Unit tests for the consensus skill engine script.

The script lives under .claude/skills/ (a dot-directory), so it is loaded by
file path rather than imported as a package, matching the pattern in
tests/integration/test_scripts.py.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import httpx
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


class TestLiveCatalog:
    """Tests for the fetch_live_model_ids function."""

    def _client(self, handler):
        """Build an httpx.Client backed by a mock transport."""
        return httpx.Client(transport=httpx.MockTransport(handler))

    def test_fetch_and_cache(self, tmp_path):
        """Fetch live model ids, cache them, and serve the second call from cache."""
        calls = {"n": 0}

        def handler(request):
            calls["n"] += 1
            return httpx.Response(
                200, json={"data": [{"id": "a/x"}, {"id": "b/y:free"}]}
            )

        cache = tmp_path / "cache.json"
        ids = cli.fetch_live_model_ids(client=self._client(handler), cache_path=cache)
        assert ids == {"a/x", "b/y:free"}
        assert json.loads(cache.read_text()) == ["a/x", "b/y:free"]
        ids2 = cli.fetch_live_model_ids(client=self._client(handler), cache_path=cache)
        assert ids2 == ids
        assert calls["n"] == 1  # second call served from cache

    def test_stale_cache_used_on_network_error(self, tmp_path):
        """Fall back to a stale cache file when the network call fails."""

        def handler(request):
            raise httpx.ConnectError("boom")

        cache = tmp_path / "cache.json"
        cache.write_text(json.dumps(["old/model"]))
        two_days_ago = time.time() - 2 * 86400
        os.utime(cache, (two_days_ago, two_days_ago))
        ids = cli.fetch_live_model_ids(client=self._client(handler), cache_path=cache)
        assert ids == {"old/model"}

    def test_network_error_without_cache_raises(self, tmp_path):
        """Propagate the httpx error when the network fails and no cache exists."""

        def handler(request):
            raise httpx.ConnectError("boom")

        with pytest.raises(httpx.HTTPError):
            cli.fetch_live_model_ids(
                client=self._client(handler), cache_path=tmp_path / "missing.json"
            )

    def test_corrupted_fresh_cache_falls_through_to_fetch(self, tmp_path):
        """A fresh but unparseable cache file triggers a refetch and rewrite."""

        def handler(request):
            return httpx.Response(200, json={"data": [{"id": "a/x"}]})

        cache = tmp_path / "cache.json"
        cache.write_text("{not json")
        ids = cli.fetch_live_model_ids(client=self._client(handler), cache_path=cache)
        assert ids == {"a/x"}
        assert json.loads(cache.read_text()) == ["a/x"]  # rewritten atomically

    def test_malformed_200_body_uses_stale_cache(self, tmp_path):
        """A 200 response with an unexpected schema falls back to a stale cache."""

        def handler(request):
            return httpx.Response(200, json={"unexpected": "schema"})

        cache = tmp_path / "cache.json"
        cache.write_text(json.dumps(["old/model"]))
        two_days_ago = time.time() - 2 * 86400
        os.utime(cache, (two_days_ago, two_days_ago))
        ids = cli.fetch_live_model_ids(client=self._client(handler), cache_path=cache)
        assert ids == {"old/model"}


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
    """Tests for the select_roster function."""

    def setup_method(self):
        """Load shared fixtures before each test."""
        self.bands = cli.load_bands()
        self.roles = cli.load_roles()

    def test_level1_is_three_free_models_with_level1_roles(self):
        """Level 1 roster: three free models in humaneval order with correct roles."""
        roster = cli.select_roster(
            fake_dataset(), self.bands, self.roles, 1, "code_review"
        )
        assert [r["model"] for r in roster] == [
            "free-a:free",
            "free-b:free",
            "free-c:free",
        ]
        assert [r["role"] for r in roster] == [
            "code_reviewer",
            "security_checker",
            "technical_validator",
        ]

    def test_level2_is_additive_six_models(self):
        """Level 2 roster: three free plus three economy models, six total."""
        roster = cli.select_roster(
            fake_dataset(), self.bands, self.roles, 2, "code_review"
        )
        assert len(roster) == 6
        assert [r["model"] for r in roster][:3] == [
            "free-a:free",
            "free-b:free",
            "free-c:free",
        ]
        assert {r["model"] for r in roster[3:]} == {"econ-a", "econ-b", "econ-c"}

    def test_level3_adds_two_premium(self):
        """Level 3 roster: level 2 plus two premium models, eight total."""
        roster = cli.select_roster(
            fake_dataset(), self.bands, self.roles, 3, "architecture"
        )
        assert len(roster) == 8
        assert {r["model"] for r in roster[6:]} == {"prem-a", "prem-b"}

    def test_live_validation_skips_dead_model(self):
        """A model absent from live set is skipped; next candidate fills the slot."""
        live = {m.name for m in fake_dataset()} - {"free-a:free"}
        roster = cli.select_roster(
            fake_dataset(), self.bands, self.roles, 1, "code_review", live=live
        )
        assert [r["model"] for r in roster] == [
            "free-b:free",
            "free-c:free",
            "free-d:free",
        ]

    def test_free_exhaustion_fails_over_to_economy(self):
        """When free tier is exhausted, economy models fill remaining free slots."""
        live = {
            "free-a:free",
            "econ-a",
            "econ-b",
            "econ-c",
            "val-a",
            "prem-a",
            "prem-b",
        }
        roster = cli.select_roster(
            fake_dataset(), self.bands, self.roles, 1, "code_review", live=live
        )
        assert [r["model"] for r in roster] == ["free-a:free", "econ-a", "econ-b"]

    def test_roster_entries_carry_cost_estimates(self):
        """Every roster entry includes an est_cost_usd key."""
        roster = cli.select_roster(
            fake_dataset(), self.bands, self.roles, 1, "code_review"
        )
        assert all(r["est_cost_usd"] == 0.0 for r in roster)

    def test_level3_cross_tier_dedup_no_duplicates(self):
        """Economy models filling free slots must not also occupy economy slots."""
        live = {
            "free-a:free",
            "econ-a",
            "econ-b",
            "econ-c",
            "val-a",
            "prem-a",
            "prem-b",
        }
        roster = cli.select_roster(
            fake_dataset(), self.bands, self.roles, 3, "code_review", live=live
        )
        names = [r["model"] for r in roster]
        assert len(names) == len(set(names))
        assert names.count("econ-a") == 1
        assert names.count("econ-b") == 1

    def test_invalid_level_raises(self):
        """An out-of-range level raises ValueError."""
        with pytest.raises(ValueError, match="Invalid level"):
            cli.select_roster(fake_dataset(), self.bands, self.roles, 4, "code_review")

    def test_invalid_domain_raises(self):
        """An unrecognised domain name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid domain"):
            cli.select_roster(fake_dataset(), self.bands, self.roles, 1, "nonsense")


def _ok_response(model_name):
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": f"answer from {model_name}"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        },
    )


class TestRunConsensus:
    """Tests for the run_consensus async fan-out function."""

    def test_partial_failure_returns_successes_and_errors(self, monkeypatch):
        """Partial failure: successes and errors are both captured in results."""
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
                entries,
                "question?",
                "test-key",
                catalog={},
                transport=httpx.MockTransport(handler),
            )
        )
        assert out["succeeded"] == 1
        assert out["failed"] == 1
        good = next(r for r in out["results"] if r["model"] == "good/model")
        assert good["response"] == "answer from good/model"
        bad = next(r for r in out["results"] if r["model"] == "bad/model")
        assert "404" in bad["error"]

    def test_system_prompt_is_sent(self):
        """A non-None system_prompt is included as the first message."""
        seen = {}

        def handler(request):
            body = json.loads(request.content)
            seen["messages"] = body["messages"]
            return _ok_response(body["model"])

        entries = [
            {"model": "m/x", "role": "skeptic", "system_prompt": "Be skeptical."}
        ]
        asyncio.run(
            cli.run_consensus(
                entries, "q?", "k", catalog={}, transport=httpx.MockTransport(handler)
            )
        )
        assert seen["messages"][0] == {"role": "system", "content": "Be skeptical."}
        assert seen["messages"][1] == {"role": "user", "content": "q?"}

    def test_retry_on_429_then_success(self, monkeypatch):
        """A 429 on the first attempt is retried and succeeds on the second."""
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
        """Per-model cost is computed from the catalog and summed into total_cost_usd."""

        def handler(request):
            return _ok_response("m/x")

        catalog = {"m/x": make_model("m/x", 1.0, 2.0)}
        entries = [{"model": "m/x", "role": None, "system_prompt": None}]
        out = asyncio.run(
            cli.run_consensus(
                entries,
                "q?",
                "k",
                catalog=catalog,
                transport=httpx.MockTransport(handler),
            )
        )
        expected = round((1.0 * 100 + 2.0 * 50) / 1_000_000, 6)
        assert out["results"][0]["cost_usd"] == expected
        assert out["total_cost_usd"] == expected

    def test_malformed_200_body_is_isolated_error(self):
        """A 200 response with an unexpected body shape is an isolated per-model error."""

        def handler(request):
            return httpx.Response(200, json={"surprise": True})

        entries = [{"model": "m/x", "role": None, "system_prompt": None}]
        out = asyncio.run(
            cli.run_consensus(
                entries, "q?", "k", catalog={}, transport=httpx.MockTransport(handler)
            )
        )
        assert out["failed"] == 1
        assert "malformed" in out["results"][0]["error"]
