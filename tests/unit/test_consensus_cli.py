"""Unit tests for the panel skill engine script (consensus_cli.py).

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
SCRIPT = REPO_ROOT / ".claude" / "skills" / "panel" / "scripts" / "consensus_cli.py"

_spec = importlib.util.spec_from_file_location("consensus_cli", SCRIPT)
assert _spec is not None
assert _spec.loader is not None
cli = importlib.util.module_from_spec(_spec)
sys.modules["consensus_cli"] = cli
_spec.loader.exec_module(cli)

# Captured immediately after exec_module, before any autouse fixture can patch
# cli._load_dotenv_keys away, so loader-specific tests can opt back into the
# real implementation deliberately (see _clean_zdr_env below).
_REAL_LOAD_DOTENV_KEYS = cli._load_dotenv_keys


@pytest.fixture(autouse=True)
def _clean_zdr_env(monkeypatch):
    """Keep OpenRouter key/ZDR env vars out of the ambient environment for every test.

    ZDR mode is env-var-triggered by design (the requirement travels with
    the key), so a leaked value from one test or the developer's shell
    would silently change another test's behavior. The two API key names are
    cleared the same way, then force-cleared again on teardown: the dotenv
    loader under test writes directly into os.environ (not via monkeypatch),
    so monkeypatch's own undo stack does not know to revert it.

    #CRITICAL: this also neutralizes cli._load_dotenv_keys to a no-op for
    every test by default, so no test can accidentally read a real .env
    from this machine (a real repo-root .env is explicitly off-limits to
    this test suite). Tests that specifically exercise the loader restore
    the real function via _REAL_LOAD_DOTENV_KEYS, captured at module import
    time above, before this fixture ever runs. #VERIFY: no test in this
    file calls the real loader without first monkeypatching cli.Path.cwd()
    and/or cli._owning_repo_root to a tmp_path fixture; grep confirms every
    _REAL_LOAD_DOTENV_KEYS() or cli._load_dotenv_keys() call site does so.
    """
    env_vars = ("OPENROUTER_ZDR", "OPENROUTER_API_KEY", "OPENROUTER__ZDR_API_KEY")
    for name in env_vars:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(cli, "_load_dotenv_keys", lambda: None)
    yield
    for name in env_vars:
        os.environ.pop(name, None)


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


class TestZdrEnvTruthy:
    """Tests for the _env_truthy helper backing OPENROUTER_ZDR."""

    @pytest.mark.parametrize("value", ["1", "true", "yes", "TRUE", "Yes", " 1 "])
    def test_truthy_values(self, monkeypatch, value):
        """Recognised truthy strings (case-insensitive, whitespace-tolerant)."""
        monkeypatch.setenv("OPENROUTER_ZDR", value)
        assert cli._env_truthy("OPENROUTER_ZDR") is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "", "on", "banana"])
    def test_falsy_values(self, monkeypatch, value):
        """Anything other than the truthy set, including empty string, is False."""
        monkeypatch.setenv("OPENROUTER_ZDR", value)
        assert cli._env_truthy("OPENROUTER_ZDR") is False

    def test_unset_is_falsy(self, monkeypatch):
        """An unset env var is False, not an error."""
        monkeypatch.delenv("OPENROUTER_ZDR", raising=False)
        assert cli._env_truthy("OPENROUTER_ZDR") is False


class TestFetchZdrModelIds:
    """Tests for fetch_zdr_model_ids, mirroring TestLiveCatalog's contract."""

    def _client(self, handler):
        """Build an httpx.Client backed by a mock transport."""
        return httpx.Client(transport=httpx.MockTransport(handler))

    def test_fetch_and_cache(self, tmp_path):
        """Fetch ZDR model ids from model_id fields, cache, and reuse the cache."""
        calls = {"n": 0}

        def handler(request):
            calls["n"] += 1
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"model_id": "z-ai/glm-5.3", "provider_name": "z-ai"},
                        {"model_id": "openai/gpt-6-sol", "provider_name": "openai"},
                    ]
                },
            )

        cache = tmp_path / "zdr-cache.json"
        ids = cli.fetch_zdr_model_ids(client=self._client(handler), cache_path=cache)
        assert ids == {"z-ai/glm-5.3", "openai/gpt-6-sol"}
        assert set(json.loads(cache.read_text())) == ids
        ids2 = cli.fetch_zdr_model_ids(client=self._client(handler), cache_path=cache)
        assert ids2 == ids
        assert calls["n"] == 1  # second call served from cache

    def test_stale_cache_used_on_network_error(self, tmp_path):
        """Fall back to a stale ZDR cache file when the network call fails."""

        def handler(request):
            raise httpx.ConnectError("boom")

        cache = tmp_path / "zdr-cache.json"
        cache.write_text(json.dumps(["old/zdr-model"]))
        two_days_ago = time.time() - 2 * 86400
        os.utime(cache, (two_days_ago, two_days_ago))
        ids = cli.fetch_zdr_model_ids(client=self._client(handler), cache_path=cache)
        assert ids == {"old/zdr-model"}

    def test_network_error_without_cache_raises(self, tmp_path):
        """Propagate the httpx error when the network fails and no cache exists."""

        def handler(request):
            raise httpx.ConnectError("boom")

        with pytest.raises(httpx.HTTPError):
            cli.fetch_zdr_model_ids(
                client=self._client(handler), cache_path=tmp_path / "missing.json"
            )

    def test_malformed_200_body_uses_stale_cache(self, tmp_path):
        """An unexpected /endpoints/zdr schema falls back to a stale cache."""

        def handler(request):
            return httpx.Response(200, json={"unexpected": "schema"})

        cache = tmp_path / "zdr-cache.json"
        cache.write_text(json.dumps(["old/zdr-model"]))
        two_days_ago = time.time() - 2 * 86400
        os.utime(cache, (two_days_ago, two_days_ago))
        ids = cli.fetch_zdr_model_ids(client=self._client(handler), cache_path=cache)
        assert ids == {"old/zdr-model"}

    def test_uses_own_cache_file_distinct_from_live_catalog(self):
        """The ZDR cache path is a sibling file, never the live-catalog cache."""
        assert cli.ZDR_CACHE_PATH != cli.CACHE_PATH
        assert cli.ZDR_CACHE_PATH.parent == cli.CACHE_PATH.parent
        assert cli.ZDR_CACHE_PATH.name == "openrouter-zdr-models.json"


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

    def test_economy_pins_lead_level2_economy_slots(self):
        """Economy pins fill the first economy slots even from the value band."""
        bands = {**self.bands, "tier_pins": {"economy": ["val-a", "prem-b"]}}
        roster = cli.select_roster(fake_dataset(), bands, self.roles, 2, "code_review")
        assert [r["model"] for r in roster][3:] == ["val-a", "prem-b", "econ-a"]

    def test_economy_pins_carry_into_level3_without_duplicates(self):
        """Level 3 inherits economy pins; a pinned premium model is not repeated."""
        bands = {**self.bands, "tier_pins": {"economy": ["val-a", "prem-b"]}}
        roster = cli.select_roster(fake_dataset(), bands, self.roles, 3, "architecture")
        names = [r["model"] for r in roster]
        assert names[3:5] == ["val-a", "prem-b"]
        assert len(names) == len(set(names))
        assert "prem-a" in names[6:]

    def test_unknown_or_dead_pins_are_skipped(self):
        """Pins absent from the dataset or the live set fall through to the band."""
        bands = {**self.bands, "tier_pins": {"economy": ["ghost/x", "val-a"]}}
        live = {m.name for m in fake_dataset()} - {"val-a"}
        roster = cli.select_roster(
            fake_dataset(), bands, self.roles, 2, "code_review", live=live
        )
        assert {r["model"] for r in roster[3:]} == {"econ-a", "econ-b", "econ-c"}

    def test_fallbacks_order_pins_ahead_of_band_within_tier(self):
        """Within a tier's fallback walk, pins come before that tier's bands.

        Tiers are still walked in LEVEL_TIER_COUNTS order, so at level 2 the
        free tier's chain precedes economy pins; the exclude set removes it.
        """
        bands = {**self.bands, "tier_pins": {"economy": ["prem-b"]}}
        exclude = {m.name for m in fake_dataset() if m.input_cost <= 1.0}
        out = cli.select_fallbacks(fake_dataset(), bands, 2, exclude)
        assert out == ["prem-b", "val-a"]

    @pytest.mark.parametrize(
        "pins",
        [
            None,
            ["x"],
            {"economy": "openai/gpt-6-sol"},
            {"economy": [1]},
            {"econmy": ["val-a"]},
        ],
    )
    def test_malformed_tier_pins_raise(self, pins):
        """A hand-edit typo in tier_pins fails loudly instead of pinning nothing."""
        bands = {**self.bands, "tier_pins": pins}
        with pytest.raises(ValueError, match="tier_pins"):
            cli.select_roster(fake_dataset(), bands, self.roles, 2, "code_review")

    def test_malformed_other_tier_pin_raises_at_level1(self):
        """A bad economy entry fails even when only the free tier is selected."""
        bands = {**self.bands, "tier_pins": {"economy": "val-a"}}
        with pytest.raises(ValueError, match=r"tier_pins\.economy"):
            cli.select_roster(fake_dataset(), bands, self.roles, 1, "code_review")

    def test_description_key_is_allowed_in_tier_pins(self):
        """The description metadata key is not treated as a tier."""
        bands = {**self.bands, "tier_pins": {"description": "note", "economy": []}}
        roster = cli.select_roster(fake_dataset(), bands, self.roles, 1, "code_review")
        assert len(roster) == 3

    def test_paid_free_pin_leads_level1_and_carries_up(self):
        """A paid model pinned under free takes the first seat at every level."""
        bands = {**self.bands, "tier_pins": {"free": ["econ-c"]}}
        level1 = cli.select_roster(fake_dataset(), bands, self.roles, 1, "code_review")
        assert [r["model"] for r in level1] == ["econ-c", "free-a:free", "free-b:free"]
        assert level1[0]["est_cost_usd"] > 0
        level3 = cli.select_roster(fake_dataset(), bands, self.roles, 3, "architecture")
        names = [r["model"] for r in level3]
        assert names[0] == "econ-c"
        assert names.count("econ-c") == 1

    def test_absent_tier_pins_keeps_benchmark_order(self):
        """Without tier_pins, economy slots follow benchmark order."""
        bands = {k: v for k, v in self.bands.items() if k != "tier_pins"}
        roster = cli.select_roster(fake_dataset(), bands, self.roles, 2, "code_review")
        assert [r["model"] for r in roster][3:] == ["econ-a", "econ-b", "econ-c"]

    def test_real_tier_pins_exist_in_dataset(self):
        """Every shipped pin is a curated row, so no pin is skipped silently."""
        names = {m.name for m in cli.load_models()}
        for tier, pins in self.bands.get("tier_pins", {}).items():
            if isinstance(pins, list):
                missing = [p for p in pins if p not in names]
                assert not missing, f"tier_pins.{tier} not in models.csv: {missing}"

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


class TestZdrRosterFiltering:
    """ZDR restricts roster and fallback candidates to a given id set."""

    def setup_method(self):
        """Load shared fixtures before each test."""
        self.bands = cli.load_bands()
        self.roles = cli.load_roles()

    def test_zdr_free_tier_without_zdr_endpoint_falls_over_to_economy(self):
        """A free tier with no ZDR-compliant candidate fills from economy instead.

        This fixture's free models happen to have no ZDR endpoint, so the
        free tier empties and the existing free->economy fallback chain
        (TIER_FALLBACK_ORDER) fills the level-1 roster with cheap paid ZDR
        models instead. This is not a claim that every free model lacks a
        ZDR endpoint: the live catalog does include some (e.g.
        qwen/qwen3.8-27b:free); the fallback only engages for the ones that
        do not.
        """
        zdr_ids = {"econ-a", "econ-b", "econ-c", "val-a", "prem-a", "prem-b"}
        roster = cli.select_roster(
            fake_dataset(), self.bands, self.roles, 1, "code_review", zdr=zdr_ids
        )
        assert [r["model"] for r in roster] == ["econ-a", "econ-b", "econ-c"]

    def test_zdr_roster_stays_under_level1_cap(self):
        """A ZDR-filled level-1 roster (no free seats) still fits the $0.50 cap."""
        zdr_ids = {"econ-a", "econ-b", "econ-c"}
        roster = cli.select_roster(
            fake_dataset(), self.bands, self.roles, 1, "code_review", zdr=zdr_ids
        )
        total = sum(r["est_cost_usd"] for r in roster)
        assert total < cli.LEVEL_COST_CAPS_USD[1]
        assert total > 0  # sanity: these are paid, not free, models

    def test_zdr_and_live_combine(self):
        """A model must pass both live validation and the ZDR filter."""
        live = {m.name for m in fake_dataset()}
        zdr_ids = {"free-a:free", "econ-a", "econ-b"}
        roster = cli.select_roster(
            fake_dataset(),
            self.bands,
            self.roles,
            1,
            "code_review",
            live=live,
            zdr=zdr_ids,
        )
        assert [r["model"] for r in roster] == ["free-a:free", "econ-a", "econ-b"]

    def test_zdr_none_leaves_selection_unfiltered(self):
        """zdr=None (the default) is a no-op, matching pre-ZDR behavior."""
        roster = cli.select_roster(
            fake_dataset(), self.bands, self.roles, 1, "code_review"
        )
        assert [r["model"] for r in roster] == [
            "free-a:free",
            "free-b:free",
            "free-c:free",
        ]

    def test_zdr_filters_fallbacks_too(self):
        """select_fallbacks skips candidates missing from the ZDR set.

        Level 1's only tier ("free") falls back through free then economy
        (TIER_FALLBACK_ORDER); with every free model off-ZDR, only the
        ZDR-listed economy model survives the walk.
        """
        zdr_ids = {"econ-b"}
        fallbacks = cli.select_fallbacks(
            fake_dataset(), self.bands, 1, exclude=set(), zdr=zdr_ids
        )
        assert fallbacks == ["econ-b"]


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

    def test_all_models_failing_aggregates_to_zero(self):
        """A fully failed run reports zero successes and zero cost."""

        def handler(request):
            return httpx.Response(404, json={"error": "not found"})

        entries = [
            {"model": "a/x", "role": None, "system_prompt": None},
            {"model": "b/y", "role": None, "system_prompt": None},
        ]
        out = asyncio.run(
            cli.run_consensus(
                entries, "q?", "k", catalog={}, transport=httpx.MockTransport(handler)
            )
        )
        assert out["succeeded"] == 0
        assert out["failed"] == 2
        assert out["total_cost_usd"] == 0.0
        assert all(r["error"] for r in out["results"])

    def test_zdr_true_adds_provider_preference_to_every_request(self):
        """zdr=True on run_consensus reaches call_model and every request body."""
        seen_bodies = []

        def handler(request):
            seen_bodies.append(json.loads(request.content))
            return _ok_response(json.loads(request.content)["model"])

        entries = [
            {"model": "a/x", "role": None, "system_prompt": None},
            {"model": "b/y", "role": None, "system_prompt": None},
        ]
        asyncio.run(
            cli.run_consensus(
                entries,
                "q?",
                "k",
                catalog={},
                transport=httpx.MockTransport(handler),
                zdr=True,
            )
        )
        assert len(seen_bodies) == 2
        assert all(body["provider"] == {"zdr": True} for body in seen_bodies)

    def test_zdr_false_omits_provider_key(self):
        """zdr=False (the default) never adds a provider key; unchanged behavior."""
        seen_bodies = []

        def handler(request):
            seen_bodies.append(json.loads(request.content))
            return _ok_response("m/x")

        entries = [{"model": "m/x", "role": None, "system_prompt": None}]
        asyncio.run(
            cli.run_consensus(
                entries, "q?", "k", catalog={}, transport=httpx.MockTransport(handler)
            )
        )
        assert "provider" not in seen_bodies[0]


class TestRefresh:
    def test_reports_dead_and_new_free_models(self):
        """Refresh report lists curated rows gone upstream and new free models."""
        curated = [make_model("alive/x", 0, 0), make_model("dead/y", 1.0, 2.0)]
        live = {"alive/x", "brand/new:free", "paid/other"}
        report = cli.refresh_report(curated, live)
        assert report["dead_in_curated"] == ["dead/y"]
        assert report["live_free_not_in_curated"] == ["brand/new:free"]
        assert report["curated_count"] == 2

    def test_curated_without_zdr_endpoint_lists_missing_ids(self):
        """When a zdr set is given, curated ids missing from it are reported."""
        curated = [
            make_model("has-zdr/x", 0.01, 0.02),
            make_model("no-zdr/y", 0.01, 0.02),
        ]
        live = {"has-zdr/x", "no-zdr/y"}
        zdr = {"has-zdr/x"}
        report = cli.refresh_report(curated, live, zdr=zdr)
        assert report["curated_without_zdr_endpoint"] == ["no-zdr/y"]
        assert "zdr_error" not in report

    def test_zdr_error_reports_null_list_without_failing_refresh(self):
        """A ZDR fetch failure reports zdr_error and a null list, not a crash."""
        curated = [make_model("alive/x", 0, 0)]
        live = {"alive/x"}
        report = cli.refresh_report(curated, live, zdr_error="ConnectError: no network")
        assert report["curated_without_zdr_endpoint"] is None
        assert report["zdr_error"] == "ConnectError: no network"
        # dead_in_curated / live_free_not_in_curated are unaffected by ZDR failure.
        assert report["dead_in_curated"] == []

    def test_neither_zdr_nor_zdr_error_omits_the_key_entirely(self):
        """Calling refresh_report with neither zdr arg leaves the key absent."""
        curated = [make_model("alive/x", 0, 0)]
        report = cli.refresh_report(curated, {"alive/x"})
        assert "curated_without_zdr_endpoint" not in report
        assert "zdr_error" not in report


class TestMainRefreshZdr:
    """main(["refresh"]) wiring for the ZDR fetch and its failure path."""

    def test_zdr_fetch_success_included_in_report(self, monkeypatch, capsys):
        """A successful ZDR fetch surfaces curated_without_zdr_endpoint."""
        monkeypatch.setattr(cli, "fetch_live_model_ids", lambda: {"some/model:free"})
        monkeypatch.setattr(cli, "fetch_zdr_model_ids", lambda: set())
        rc = cli.main(["refresh"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["curated_without_zdr_endpoint"] is not None

    def test_zdr_fetch_failure_does_not_fail_whole_refresh(self, monkeypatch, capsys):
        """A ZDR fetch failure reports zdr_error but refresh still exits 0."""
        monkeypatch.setattr(cli, "fetch_live_model_ids", lambda: {"some/model:free"})

        def _boom():
            raise httpx.ConnectError("no network")

        monkeypatch.setattr(cli, "fetch_zdr_model_ids", _boom)
        rc = cli.main(["refresh"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["curated_without_zdr_endpoint"] is None
        assert "zdr_error" in payload
        assert "dead_in_curated" in payload


class TestCliWiring:
    def test_select_defaults(self):
        """Select defaults to code_review domain with validation enabled."""
        args = cli.build_parser().parse_args(["select", "--level", "2"])
        assert args.domain == "code_review"
        assert args.no_validate is False

    def test_run_requires_prompt_file(self):
        """Run without --prompt-file exits via argparse error."""
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(["run"])

    def test_main_select_no_validate_emits_roster_json(self, capsys):
        """Select with --no-validate emits a roster from the curated data."""
        rc = cli.main(["select", "--level", "1", "--no-validate"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["level"] == 1
        assert len(payload["roster"]) == 3
        assert payload["cap_usd"] == 0.50

    def test_main_run_without_api_key_fails_fast(self, monkeypatch, tmp_path, capsys):
        """Run without OPENROUTER_API_KEY returns exit code 1 with a clear error."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")
        rc = cli.main(["run", "--prompt-file", str(prompt), "--models", "m/x"])
        assert rc == 1
        assert "OPENROUTER_API_KEY" in capsys.readouterr().err

    def test_run_with_roster_file_builds_role_prompts(
        self, monkeypatch, tmp_path, capsys
    ):
        """Roster-file entries get role system prompts and reach the fan-out."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")
        roster = tmp_path / "roster.json"
        roster.write_text(
            json.dumps(
                {
                    "roster": [
                        {
                            "model": "free-x:free",
                            "role": "code_reviewer",
                            "est_cost_usd": 0.0,
                        }
                    ]
                }
            )
        )

        captured = {}

        async def fake_run_consensus(
            entries, prompt_text, api_key, catalog, transport=None, zdr=False
        ):
            captured["entries"] = entries
            return {"results": [], "succeeded": 1, "failed": 0, "total_cost_usd": 0.0}

        monkeypatch.setattr(cli, "run_consensus", fake_run_consensus)
        rc = cli.main(
            ["run", "--prompt-file", str(prompt), "--roster-file", str(roster)]
        )
        assert rc == 0
        assert captured["entries"][0]["model"] == "free-x:free"
        assert "code reviewer" in captured["entries"][0]["system_prompt"]

    def test_run_exit_code_3_when_all_fail(self, monkeypatch, tmp_path):
        """Zero successes from the fan-out maps to exit code 3."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")

        async def fake_run_consensus(
            entries, prompt_text, api_key, catalog, transport=None, zdr=False
        ):
            return {
                "results": [{"model": "m/x", "error": "boom"}],
                "succeeded": 0,
                "failed": 1,
                "total_cost_usd": 0.0,
            }

        monkeypatch.setattr(cli, "run_consensus", fake_run_consensus)
        assert cli.main(["run", "--prompt-file", str(prompt), "--models", "m/x"]) == 3

    def test_run_missing_roster_file_exits_cleanly(self, monkeypatch, tmp_path, capsys):
        """A nonexistent roster file produces a JSON error, not a traceback."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")
        with pytest.raises(SystemExit) as exc_info:
            cli.main(
                [
                    "run",
                    "--prompt-file",
                    str(prompt),
                    "--roster-file",
                    str(tmp_path / "missing.json"),
                ]
            )
        assert exc_info.value.code == 2
        assert "cannot read" in capsys.readouterr().err

    def test_select_limit_trims_roster(self, capsys):
        """--limit trims the emitted roster."""
        rc = cli.main(["select", "--level", "1", "--no-validate", "--limit", "2"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert len(payload["roster"]) == 2

    def test_main_refresh_emits_report(self, monkeypatch, capsys):
        """Refresh dispatch fetches live ids and emits the report shape."""
        monkeypatch.setattr(cli, "fetch_live_model_ids", lambda: {"some/model:free"})
        monkeypatch.setattr(cli, "fetch_zdr_model_ids", lambda: {"some/model:free"})
        rc = cli.main(["refresh"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert "dead_in_curated" in payload
        assert "live_free_not_in_curated" in payload
        assert "curated_without_zdr_endpoint" in payload


class TestCliZdrSelect:
    """CLI-level --zdr and OPENROUTER_ZDR wiring for select/estimate."""

    def test_zdr_flag_filters_roster_and_marks_payload(self, monkeypatch, capsys):
        """--zdr restricts candidates to the ZDR set and flags the payload."""
        monkeypatch.setattr(cli, "fetch_zdr_model_ids", lambda: {"openai/gpt-6-sol"})
        rc = cli.main(["select", "--level", "1", "--no-validate", "--zdr"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["zdr"] is True
        assert all(r["model"] == "openai/gpt-6-sol" for r in payload["roster"])

    def test_env_var_triggers_zdr_without_flag(self, monkeypatch, capsys):
        """OPENROUTER_ZDR alone (no --zdr) enables ZDR mode."""
        monkeypatch.setenv("OPENROUTER_ZDR", "1")
        monkeypatch.setattr(cli, "fetch_zdr_model_ids", lambda: {"openai/gpt-6-sol"})
        rc = cli.main(["select", "--level", "1", "--no-validate"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["zdr"] is True

    def test_no_validate_still_applies_zdr_filter(self, monkeypatch, capsys):
        """--no-validate skips liveness but ZDR is a policy filter, not liveness."""
        monkeypatch.setattr(cli, "fetch_zdr_model_ids", lambda: {"openai/gpt-6-sol"})
        rc = cli.main(["select", "--level", "1", "--no-validate", "--zdr"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert all(r["model"] == "openai/gpt-6-sol" for r in payload["roster"])

    def test_zdr_fetch_failure_with_no_cache_exits_nonzero(self, monkeypatch, capsys):
        """A failed ZDR fetch with no usable cache is fatal, not silently ignored."""

        def _boom():
            raise httpx.ConnectError("no network")

        monkeypatch.setattr(cli, "fetch_zdr_model_ids", _boom)
        with pytest.raises(SystemExit) as exc_info:
            cli.main(["select", "--level", "1", "--no-validate", "--zdr"])
        assert exc_info.value.code == 2
        err = json.loads(capsys.readouterr().err)
        assert "error" in err

    def test_without_zdr_flag_behavior_unchanged(self, capsys):
        """Without --zdr or the env var, select emits no zdr key at all."""
        rc = cli.main(["select", "--level", "1", "--no-validate"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert "zdr" not in payload


class TestCliZdrRun:
    """CLI-level --zdr and OPENROUTER_ZDR wiring for run."""

    def test_roster_file_zdr_true_enables_zdr_without_flag(
        self, monkeypatch, tmp_path, capsys
    ):
        """A roster file carrying "zdr": true turns on ZDR mode with no CLI flag."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        monkeypatch.setenv("OPENROUTER__ZDR_API_KEY", "zdr-k")
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")
        roster = tmp_path / "roster.json"
        roster.write_text(
            json.dumps(
                {
                    "zdr": True,
                    "roster": [
                        {
                            "model": "paid/x",
                            "role": "code_reviewer",
                            "est_cost_usd": 0.01,
                        }
                    ],
                }
            )
        )

        captured = {}

        async def fake_run_consensus(
            entries, prompt_text, api_key, catalog, transport=None, zdr=False
        ):
            captured["zdr"] = zdr
            return {"results": [], "succeeded": 1, "failed": 0, "total_cost_usd": 0.0}

        monkeypatch.setattr(cli, "run_consensus", fake_run_consensus)
        rc = cli.main(
            ["run", "--prompt-file", str(prompt), "--roster-file", str(roster)]
        )
        assert rc == 0
        assert captured["zdr"] is True
        payload = json.loads(capsys.readouterr().out)
        assert payload["zdr"] is True

    def test_env_var_enables_zdr_for_run(self, monkeypatch, tmp_path, capsys):
        """OPENROUTER_ZDR alone enables ZDR mode for run and marks the output."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        monkeypatch.setenv("OPENROUTER__ZDR_API_KEY", "zdr-k")
        monkeypatch.setenv("OPENROUTER_ZDR", "1")
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")

        captured = {}

        async def fake_run_consensus(
            entries, prompt_text, api_key, catalog, transport=None, zdr=False
        ):
            captured["zdr"] = zdr
            return {"results": [], "succeeded": 1, "failed": 0, "total_cost_usd": 0.0}

        monkeypatch.setattr(cli, "run_consensus", fake_run_consensus)
        rc = cli.main(["run", "--prompt-file", str(prompt), "--models", "m/x"])
        assert rc == 0
        assert captured["zdr"] is True
        payload = json.loads(capsys.readouterr().out)
        assert payload["zdr"] is True

    def test_models_mode_zdr_warns_on_off_zdr_models_but_still_attempts(
        self, monkeypatch, tmp_path, capsys
    ):
        """--models under ZDR merges an off-ZDR warning with the uncatalogued one."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        monkeypatch.setenv("OPENROUTER__ZDR_API_KEY", "zdr-k")
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")

        monkeypatch.setattr(cli, "fetch_zdr_model_ids", lambda: {"m/other"})

        async def fake_run_consensus(
            entries, prompt_text, api_key, catalog, transport=None, zdr=False
        ):
            return {"results": [], "succeeded": 1, "failed": 0, "total_cost_usd": 0.0}

        monkeypatch.setattr(cli, "run_consensus", fake_run_consensus)
        rc = cli.main(
            [
                "run",
                "--prompt-file",
                str(prompt),
                "--models",
                "not/catalogued",
                "--zdr",
            ]
        )
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert "warning" in payload
        assert "not/catalogued" in payload["warning"]


class TestRunFailover:
    def test_select_payload_includes_fallbacks(self, capsys):
        """Select emits an ordered fallback list excluding roster models."""
        rc = cli.main(["select", "--level", "1", "--no-validate"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        roster_models = {r["model"] for r in payload["roster"]}
        assert "fallbacks" in payload
        assert roster_models.isdisjoint(set(payload["fallbacks"]))

    def test_select_fallbacks_orders_and_excludes(self):
        """select_fallbacks walks tier chains in order, skipping excluded/dead."""
        bands = cli.load_bands()
        fallbacks = cli.select_fallbacks(
            fake_dataset(), bands, 1, exclude={"free-a:free"}, live=None, limit=3
        )
        assert fallbacks == ["free-b:free", "free-c:free", "free-d:free"]

    def test_substitution_replaces_failed_entry_and_carries_role(self, monkeypatch):
        """A failed entry is re-run on the next fallback with the same role."""

        async def fake_run(
            entries, prompt, api_key, catalog, transport=None, zdr=False
        ):
            results = [
                {
                    "model": e["model"],
                    "role": e["role"],
                    "response": "ok",
                    "tokens": {},
                    "cost_usd": 0.0,
                    "error": None,
                }
                for e in entries
            ]
            return {
                "results": results,
                "succeeded": len(results),
                "failed": 0,
                "total_cost_usd": 0.0,
            }

        monkeypatch.setattr(cli, "run_consensus", fake_run)
        outcome = {
            "results": [
                {
                    "model": "dead/x",
                    "role": "code_reviewer",
                    "response": None,
                    "tokens": None,
                    "cost_usd": None,
                    "error": "HTTP 429: limited",
                },
                {
                    "model": "alive/y",
                    "role": "security_checker",
                    "response": "fine",
                    "tokens": {},
                    "cost_usd": 0.0,
                    "error": None,
                },
            ],
            "succeeded": 1,
            "failed": 1,
            "total_cost_usd": 0.0,
        }
        roles = cli.load_roles()
        new = cli._substitute_failures(outcome, ["sub/z"], roles, "q?", "k", {})
        assert new["substitutions"] == {"dead/x": "sub/z"}
        assert new["succeeded"] == 2
        sub = next(r for r in new["results"] if r["model"] == "sub/z")
        assert sub["role"] == "code_reviewer"

    def test_no_substitution_without_fallbacks(self):
        """Flexible mode (no fallbacks) returns the outcome unchanged."""
        outcome = {
            "results": [
                {
                    "model": "m/x",
                    "role": None,
                    "response": None,
                    "tokens": None,
                    "cost_usd": None,
                    "error": "boom",
                }
            ],
            "succeeded": 0,
            "failed": 1,
            "total_cost_usd": 0.0,
        }
        assert cli._substitute_failures(outcome, [], {}, "q?", "k", {}) is outcome

    def test_partial_substitution_when_pool_exhausted(self, monkeypatch):
        """With fewer fallbacks than failures, only the available swaps happen."""

        async def fake_run(
            entries, prompt, api_key, catalog, transport=None, zdr=False
        ):
            results = [
                {
                    "model": e["model"],
                    "role": e["role"],
                    "response": "ok",
                    "tokens": {},
                    "cost_usd": 0.0,
                    "error": None,
                }
                for e in entries
            ]
            return {
                "results": results,
                "succeeded": len(results),
                "failed": 0,
                "total_cost_usd": 0.0,
            }

        monkeypatch.setattr(cli, "run_consensus", fake_run)
        failed_record = {
            "model": None,
            "role": None,
            "response": None,
            "tokens": None,
            "cost_usd": None,
            "error": "HTTP 429",
        }
        outcome = {
            "results": [
                {**failed_record, "model": "dead/a", "role": "code_reviewer"},
                {**failed_record, "model": "dead/b", "role": "security_checker"},
                {**failed_record, "model": "dead/c", "role": "technical_validator"},
            ],
            "succeeded": 0,
            "failed": 3,
            "total_cost_usd": 0.0,
        }
        roles = cli.load_roles()
        new = cli._substitute_failures(
            outcome, ["sub/x", "sub/y"], roles, "q?", "k", {}
        )
        assert len(new["substitutions"]) == 2
        assert new["succeeded"] == 2
        assert new["failed"] == 3  # three originals still carry errors in results


class TestNullContentHandling:
    """A 200 response with null content is a per-model failure, not a success."""

    def test_null_content_is_per_model_error(self):
        """choices[0].message.content == null is recorded as an error, not a response."""

        def handler(request):
            return httpx.Response(
                200, json={"choices": [{"message": {"content": None}}], "usage": {}}
            )

        entries = [{"model": "m/x", "role": None, "system_prompt": None}]
        out = asyncio.run(
            cli.run_consensus(
                entries, "q?", "k", catalog={}, transport=httpx.MockTransport(handler)
            )
        )
        assert out["succeeded"] == 0
        assert out["failed"] == 1
        assert out["results"][0]["response"] is None
        assert "null content" in out["results"][0]["error"]


class TestGatherIsolation:
    """An unexpected exception escaping call_model is isolated to that model."""

    def test_unexpected_exception_does_not_cancel_panel(self, monkeypatch):
        """One model raising an unexpected error becomes its own error record."""

        async def flaky_call(client, entry, prompt, api_key, catalog, zdr=False):
            if entry["model"] == "boom/x":
                raise RuntimeError("unexpected boom")
            return {
                "model": entry["model"],
                "role": entry.get("role"),
                "response": "ok",
                "tokens": {},
                "cost_usd": None,
                "error": None,
            }

        monkeypatch.setattr(cli, "call_model", flaky_call)
        entries = [
            {"model": "boom/x", "role": None, "system_prompt": None},
            {"model": "good/y", "role": None, "system_prompt": None},
        ]

        def noop(request):
            return _ok_response("unused")

        out = asyncio.run(
            cli.run_consensus(
                entries, "q?", "k", catalog={}, transport=httpx.MockTransport(noop)
            )
        )
        assert out["succeeded"] == 1
        assert out["failed"] == 1
        boom = next(r for r in out["results"] if r["model"] == "boom/x")
        assert "RuntimeError" in boom["error"]
        good = next(r for r in out["results"] if r["model"] == "good/y")
        assert good["error"] is None


class TestCacheSchemaValidation:
    """_read_cache rejects any shape that is not a JSON list of strings."""

    def test_non_list_cache_is_treated_as_corrupt(self, tmp_path):
        """A bare string or non-string list returns None instead of garbage ids."""
        cache = tmp_path / "c.json"
        cache.write_text(json.dumps("a-single-string"))
        assert cli._read_cache(cache) is None
        cache.write_text(json.dumps([1, 2, 3]))
        assert cli._read_cache(cache) is None
        cache.write_text(json.dumps(["a/x", "b/y"]))
        assert cli._read_cache(cache) == {"a/x", "b/y"}

    def test_cache_write_uses_unique_tmp_name(self, tmp_path):
        """The atomic write does not reuse a shared '.tmp' another run may hold."""

        def handler(request):
            return httpx.Response(200, json={"data": [{"id": "a/x"}]})

        cache = tmp_path / "c.json"
        shared_tmp = cache.with_suffix(".tmp")
        shared_tmp.write_text("OTHER-RUN-SENTINEL")
        ids = cli.fetch_live_model_ids(
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            cache_path=cache,
        )
        assert ids == {"a/x"}
        # The shared .tmp is untouched because the write targets a per-pid name.
        assert shared_tmp.read_text() == "OTHER-RUN-SENTINEL"
        assert json.loads(cache.read_text()) == ["a/x"]


class TestRunInputValidation:
    """Malformed run inputs exit with code 2 instead of raising a traceback."""

    def _prompt(self, tmp_path):
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")
        return prompt

    def test_roster_dict_without_roster_key_exits_2(
        self, monkeypatch, tmp_path, capsys
    ):
        """A roster object lacking a 'roster' key exits cleanly with code 2."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        roster = tmp_path / "r.json"
        roster.write_text(json.dumps({"level": 1}))
        with pytest.raises(SystemExit) as exc_info:
            cli.main(
                [
                    "run",
                    "--prompt-file",
                    str(self._prompt(tmp_path)),
                    "--roster-file",
                    str(roster),
                ]
            )
        assert exc_info.value.code == 2
        assert "must be a list" in capsys.readouterr().err

    def test_roster_non_list_root_exits_2(self, monkeypatch, tmp_path, capsys):
        """A roster file whose JSON root is a scalar exits with code 2."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        roster = tmp_path / "r.json"
        roster.write_text(json.dumps(42))
        with pytest.raises(SystemExit) as exc_info:
            cli.main(
                [
                    "run",
                    "--prompt-file",
                    str(self._prompt(tmp_path)),
                    "--roster-file",
                    str(roster),
                ]
            )
        assert exc_info.value.code == 2

    def test_roster_entry_not_object_exits_2(self, monkeypatch, tmp_path, capsys):
        """A roster list whose entries are not objects exits with code 2."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        roster = tmp_path / "r.json"
        roster.write_text(json.dumps({"roster": ["not-an-object"]}))
        with pytest.raises(SystemExit) as exc_info:
            cli.main(
                [
                    "run",
                    "--prompt-file",
                    str(self._prompt(tmp_path)),
                    "--roster-file",
                    str(roster),
                ]
            )
        assert exc_info.value.code == 2
        assert "model" in capsys.readouterr().err

    def test_roles_file_non_object_exits_2(self, monkeypatch, tmp_path, capsys):
        """A roles file that is not a JSON object exits with code 2."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        roles = tmp_path / "roles.json"
        roles.write_text(json.dumps([1, 2]))
        with pytest.raises(SystemExit) as exc_info:
            cli.main(
                [
                    "run",
                    "--prompt-file",
                    str(self._prompt(tmp_path)),
                    "--models",
                    "m/x",
                    "--roles-file",
                    str(roles),
                ]
            )
        assert exc_info.value.code == 2
        assert "must be a JSON object" in capsys.readouterr().err

    def test_models_and_roster_file_are_mutually_exclusive(self):
        """Passing both --models and --roster-file is an argparse error."""
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(
                [
                    "run",
                    "--prompt-file",
                    "p.txt",
                    "--models",
                    "m/x",
                    "--roster-file",
                    "r.json",
                ]
            )

    def test_binary_prompt_file_exits_2(self, monkeypatch, tmp_path, capsys):
        """A prompt file that is not valid UTF-8 exits with code 2, not a traceback."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        prompt = tmp_path / "p.bin"
        prompt.write_bytes(b"\xff\xfe\x00\x80")
        rc = cli.main(["run", "--prompt-file", str(prompt), "--models", "m/x"])
        assert rc == 2
        assert "cannot read prompt file" in capsys.readouterr().err


class TestDataLoadFailure:
    """A corrupt or unreadable data file exits with code 2 instead of a traceback."""

    def test_data_load_oserror_exits_2(self, monkeypatch, capsys):
        """An OSError from a loader is reported as a clean JSON error and exit 2."""

        def boom(*args, **kwargs):
            raise OSError("disk gone")

        monkeypatch.setattr(cli, "load_models", boom)
        rc = cli.main(["select", "--level", "1", "--no-validate"])
        assert rc == 2
        assert "cannot load consensus data files" in capsys.readouterr().err


class TestSubstitutionCostCap:
    """The substitution cap is enforced against actual incurred cost."""

    def test_substitution_cap_uses_actual_incurred_cost(
        self, monkeypatch, tmp_path, capsys
    ):
        """Real first-round cost above the cap blocks substitution with exit 2.

        The pre-flight estimate for these uncatalogued models is 0, so the old
        estimate-based check would have passed; basing the cap on the actual
        total_cost_usd returned by the run is what trips it.
        """
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")
        roster = tmp_path / "r.json"
        roster.write_text(
            json.dumps(
                {
                    "roster": [{"model": "dead/x", "role": None}],
                    "fallbacks": ["sub/y"],
                }
            )
        )

        async def fake_run(
            entries, prompt_text, api_key, catalog, transport=None, zdr=False
        ):
            return {
                "results": [
                    {
                        "model": "dead/x",
                        "role": None,
                        "response": None,
                        "tokens": None,
                        "cost_usd": None,
                        "error": "HTTP 429: limited",
                    }
                ],
                "succeeded": 0,
                "failed": 1,
                "total_cost_usd": 0.50,
            }

        monkeypatch.setattr(cli, "run_consensus", fake_run)
        with pytest.raises(SystemExit) as exc_info:
            cli.main(
                [
                    "run",
                    "--prompt-file",
                    str(prompt),
                    "--roster-file",
                    str(roster),
                    "--max-cost",
                    "0.10",
                ]
            )
        assert exc_info.value.code == 2
        assert "exceeds cap" in capsys.readouterr().err


class TestRosterLevelGuard:
    """select_roster raises a clear error when a domain lacks the level key."""

    def test_missing_level_key_raises_valueerror(self):
        """A domain present but missing the requested level raises ValueError."""
        bands = cli.load_bands()
        roles = {
            "domain_roles": {"code_review": {"1": ["reviewer"], "2": ["reviewer"]}},
            "role_definitions": {},
        }
        with pytest.raises(ValueError, match="no roles configured for level 3"):
            cli.select_roster(fake_dataset(), bands, roles, 3, "code_review")


class TestLevelDefault:
    """select/estimate default to level 2 when --level is omitted."""

    def test_select_parse_args_no_level_defaults_to_two(self):
        """parse_args(["select"]) defaults to level 2 with no explicit flag."""
        args = cli.build_parser().parse_args(["select"])
        assert args.level == 2

    def test_estimate_parse_args_no_level_defaults_to_two(self):
        """parse_args(["estimate"]) defaults to level 2 with no explicit flag."""
        args = cli.build_parser().parse_args(["estimate"])
        assert args.level == 2

    def test_run_parse_args_no_level_stays_none(self):
        """run's --level has no default; it stays optional as-is."""
        args = cli.build_parser().parse_args(["run", "--prompt-file", "p.txt"])
        assert args.level is None

    def test_main_select_no_level_emits_level2_roster(self, capsys):
        """select with no --level emits the level-2 roster (6 entries)."""
        rc = cli.main(["select", "--no-validate"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["level"] == 2
        assert len(payload["roster"]) == 6
        assert payload["cap_usd"] == 1.00

    def test_main_estimate_no_level_defaults_to_two(self, capsys):
        """estimate with no --level defaults to level 2."""
        rc = cli.main(["estimate"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["level"] == 2


class TestDotenvLoader:
    """Stdlib-only .env loader: parsing, allowlist, and non-override semantics.

    Exercised only against synthetic tmp_path fixtures, never against a real
    .env file, per the security constraint that this loader must not be
    verified by reading any real .env on disk.
    """

    def test_parses_plain_key_value(self):
        assert cli._parse_dotenv_line("OPENROUTER_API_KEY=abc123") == (
            "OPENROUTER_API_KEY",
            "abc123",
        )

    def test_skips_blank_and_comment_lines(self):
        assert cli._parse_dotenv_line("") is None
        assert cli._parse_dotenv_line("   ") is None
        assert cli._parse_dotenv_line("# a comment") is None

    def test_strips_export_prefix(self):
        assert cli._parse_dotenv_line("export OPENROUTER_API_KEY=abc123") == (
            "OPENROUTER_API_KEY",
            "abc123",
        )

    def test_strips_matching_double_quotes(self):
        raw = 'OPENROUTER_API_KEY="abc 123"'  # pragma: allowlist secret
        assert cli._parse_dotenv_line(raw) == ("OPENROUTER_API_KEY", "abc 123")

    def test_strips_matching_single_quotes(self):
        raw = "OPENROUTER_API_KEY='abc123'"  # pragma: allowlist secret
        assert cli._parse_dotenv_line(raw) == ("OPENROUTER_API_KEY", "abc123")

    def test_no_equals_sign_returns_none(self):
        assert cli._parse_dotenv_line("not a valid line") is None

    def test_load_env_file_allowlist_only(self, tmp_path):
        """Only the three allowlisted names are pulled from the file."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "OPENROUTER_API_KEY=std-key\n"
            "OPENROUTER__ZDR_API_KEY=zdr-key\n"
            "OPENROUTER_ZDR=1\n"
            "SOME_OTHER_SECRET=nope\n"
        )
        cli._load_env_file(env_file)
        env = os.environ
        assert env["OPENROUTER_API_KEY"] == "std-key"  # pragma: allowlist secret
        assert env["OPENROUTER__ZDR_API_KEY"] == "zdr-key"  # pragma: allowlist secret
        assert env["OPENROUTER_ZDR"] == "1"
        assert "SOME_OTHER_SECRET" not in env

    def test_load_env_file_never_overrides_existing_env(self, monkeypatch, tmp_path):
        """An already-set env var is left untouched by the loader."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "shell-key")
        env_file = tmp_path / ".env"
        env_file.write_text("OPENROUTER_API_KEY=dotenv-key\n")
        cli._load_env_file(env_file)
        env = os.environ["OPENROUTER_API_KEY"]
        assert env == "shell-key"  # pragma: allowlist secret

    def test_load_env_file_missing_file_is_a_noop(self, tmp_path):
        """A nonexistent .env path does not raise."""
        cli._load_env_file(tmp_path / "does-not-exist" / ".env")
        assert "OPENROUTER_API_KEY" not in os.environ

    def test_owning_repo_root_lands_on_repo_root_for_matching_depth(
        self, monkeypatch, tmp_path
    ):
        """A synthetic tree with the marker directory resolves to its repo root."""
        fake_script = (
            tmp_path
            / "repo"
            / ".claude"
            / "skills"
            / "panel"
            / "scripts"
            / "consensus_cli.py"
        )
        fake_script.parent.mkdir(parents=True)
        fake_script.write_text("# placeholder\n")
        monkeypatch.setattr(cli, "__file__", str(fake_script))
        assert cli._owning_repo_root() == (tmp_path / "repo").resolve()

    def test_owning_repo_root_rejects_missing_marker(self, monkeypatch, tmp_path):
        """The same script depth without the .claude/skills/panel marker returns None."""
        fake_script = (
            tmp_path / "repo" / "some" / "other" / "nested" / "scripts" / "x.py"
        )
        fake_script.parent.mkdir(parents=True)
        fake_script.write_text("# placeholder\n")
        monkeypatch.setattr(cli, "__file__", str(fake_script))
        assert cli._owning_repo_root() is None

    def test_owning_repo_root_guards_shallow_path(self, monkeypatch):
        """A script path with 4 or fewer parents returns None instead of raising."""
        monkeypatch.setattr(cli, "__file__", "/a/b/x.py")
        assert cli._owning_repo_root() is None

    def test_load_dotenv_keys_never_reads_cwd(self, monkeypatch, tmp_path):
        """cwd's .env is never read, even with no owning repo and a key present there.

        This is a global skill installed into arbitrary project roots; trusting
        Path.cwd()/.env would let an unrelated project's .env silently supply a
        different account's key. #VERIFY: OPENROUTER_API_KEY stays absent even
        though cwd/.env defines it, because _load_dotenv_keys no longer
        consults Path.cwd() at all.
        """
        cwd_dir = tmp_path / "cwd"
        cwd_dir.mkdir()
        (cwd_dir / ".env").write_text("OPENROUTER_API_KEY=from-cwd\n")
        monkeypatch.setattr(cli.Path, "cwd", staticmethod(lambda: cwd_dir))
        monkeypatch.setattr(cli, "_owning_repo_root", lambda: None)
        _REAL_LOAD_DOTENV_KEYS()
        assert "OPENROUTER_API_KEY" not in os.environ

    def test_load_dotenv_keys_reads_owning_repo_root_only(self, monkeypatch, tmp_path):
        """Only the (mocked) owning repo root's .env is loaded; cwd is ignored."""
        cwd_dir = tmp_path / "cwd"
        cwd_dir.mkdir()
        (cwd_dir / ".env").write_text("OPENROUTER_API_KEY=from-cwd\n")
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".env").write_text(
            "OPENROUTER_API_KEY=from-repo-root\n"  # pragma: allowlist secret
            "OPENROUTER__ZDR_API_KEY=zdr-from-repo\n"  # pragma: allowlist secret
        )
        monkeypatch.setattr(cli.Path, "cwd", staticmethod(lambda: cwd_dir))
        monkeypatch.setattr(cli, "_owning_repo_root", lambda: repo_dir)
        _REAL_LOAD_DOTENV_KEYS()
        env = os.environ
        assert env["OPENROUTER_API_KEY"] == "from-repo-root"  # pragma: allowlist secret
        zdr_key = env["OPENROUTER__ZDR_API_KEY"]
        assert zdr_key == "zdr-from-repo"  # pragma: allowlist secret

    def test_load_dotenv_keys_skips_when_no_owning_repo(self, monkeypatch, tmp_path):
        """No owning repo root (marker absent) means the loader is a no-op."""
        monkeypatch.setattr(cli, "_owning_repo_root", lambda: None)
        _REAL_LOAD_DOTENV_KEYS()
        assert "OPENROUTER_API_KEY" not in os.environ
        assert "OPENROUTER__ZDR_API_KEY" not in os.environ


class TestDualApiKeySelection:
    """Key selection: standard key for non-ZDR runs, ZDR key with no fallback under ZDR."""

    def test_select_api_key_non_zdr_uses_standard_key(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "std-key")
        assert cli._select_api_key(zdr_mode=False) == "std-key"

    def test_select_api_key_zdr_uses_zdr_key(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER__ZDR_API_KEY", "zdr-key")
        assert cli._select_api_key(zdr_mode=True) == "zdr-key"

    def test_select_api_key_zdr_mode_never_falls_back_to_standard_key(
        self, monkeypatch
    ):
        """Setting only the standard key must not satisfy a ZDR-mode request."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "std-key")
        assert cli._select_api_key(zdr_mode=True) is None

    def test_select_api_key_missing_returns_none(self):
        assert cli._select_api_key(zdr_mode=False) is None
        assert cli._select_api_key(zdr_mode=True) is None

    def test_run_zdr_flag_missing_zdr_key_exits_1_naming_variable(
        self, monkeypatch, tmp_path, capsys
    ):
        """--zdr with only the standard key set fails fast, naming the ZDR var."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "std-key")
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")
        rc = cli.main(["run", "--prompt-file", str(prompt), "--models", "m/x", "--zdr"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "OPENROUTER__ZDR_API_KEY" in err
        assert "std-key" not in err

    def test_run_zdr_env_var_missing_zdr_key_exits_1(
        self, monkeypatch, tmp_path, capsys
    ):
        """OPENROUTER_ZDR=1 with only the standard key set also fails fast."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "std-key")
        monkeypatch.setenv("OPENROUTER_ZDR", "1")
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")
        rc = cli.main(["run", "--prompt-file", str(prompt), "--models", "m/x"])
        assert rc == 1
        assert "OPENROUTER__ZDR_API_KEY" in capsys.readouterr().err

    def test_run_zdr_roster_flag_missing_zdr_key_exits_1(
        self, monkeypatch, tmp_path, capsys
    ):
        """A roster file's "zdr": true also requires the ZDR key, no fallback."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "std-key")
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")
        roster = tmp_path / "roster.json"
        roster.write_text(
            json.dumps(
                {
                    "zdr": True,
                    "roster": [
                        {
                            "model": "paid/x",
                            "role": "code_reviewer",
                            "est_cost_usd": 0.01,
                        }
                    ],
                }
            )
        )
        rc = cli.main(
            ["run", "--prompt-file", str(prompt), "--roster-file", str(roster)]
        )
        assert rc == 1
        assert "OPENROUTER__ZDR_API_KEY" in capsys.readouterr().err

    def test_run_zdr_uses_zdr_key_not_standard_key(self, monkeypatch, tmp_path):
        """A successful --zdr run is fed the ZDR key, never the standard one."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "std-key")
        monkeypatch.setenv("OPENROUTER__ZDR_API_KEY", "zdr-key")
        monkeypatch.setattr(cli, "fetch_zdr_model_ids", lambda: {"m/x"})
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")

        captured = {}

        async def fake_run_consensus(
            entries, prompt_text, api_key, catalog, transport=None, zdr=False
        ):
            captured["api_key"] = api_key
            return {"results": [], "succeeded": 1, "failed": 0, "total_cost_usd": 0.0}

        monkeypatch.setattr(cli, "run_consensus", fake_run_consensus)
        rc = cli.main(["run", "--prompt-file", str(prompt), "--models", "m/x", "--zdr"])
        assert rc == 0
        assert captured["api_key"] == "zdr-key"  # pragma: allowlist secret

    def test_run_non_zdr_still_uses_standard_key(self, monkeypatch, tmp_path):
        """A non-ZDR run is fed the standard key even when a ZDR key also exists."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "std-key")
        monkeypatch.setenv("OPENROUTER__ZDR_API_KEY", "zdr-key")
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")

        captured = {}

        async def fake_run_consensus(
            entries, prompt_text, api_key, catalog, transport=None, zdr=False
        ):
            captured["api_key"] = api_key
            return {"results": [], "succeeded": 1, "failed": 0, "total_cost_usd": 0.0}

        monkeypatch.setattr(cli, "run_consensus", fake_run_consensus)
        rc = cli.main(["run", "--prompt-file", str(prompt), "--models", "m/x"])
        assert rc == 0
        assert captured["api_key"] == "std-key"  # pragma: allowlist secret

    def test_run_loads_dotenv_keys_from_owning_repo_root(self, monkeypatch, tmp_path):
        """main() loads a key from the (mocked) owning repo root .env before run.

        cwd is deliberately left unset here (no cli.Path.cwd patch, no cwd
        .env file) to confirm the key comes from the owning repo root, not
        from any cwd fallback (there is none any more).
        """
        monkeypatch.setattr(cli, "_load_dotenv_keys", _REAL_LOAD_DOTENV_KEYS)
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".env").write_text("OPENROUTER_API_KEY=from-dotenv\n")
        monkeypatch.setattr(cli, "_owning_repo_root", lambda: repo_dir)
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")

        captured = {}

        async def fake_run_consensus(
            entries, prompt_text, api_key, catalog, transport=None, zdr=False
        ):
            captured["api_key"] = api_key
            return {"results": [], "succeeded": 1, "failed": 0, "total_cost_usd": 0.0}

        monkeypatch.setattr(cli, "run_consensus", fake_run_consensus)
        rc = cli.main(["run", "--prompt-file", str(prompt), "--models", "m/x"])
        assert rc == 0
        assert captured["api_key"] == "from-dotenv"  # pragma: allowlist secret


class TestMainLoadsDotenvForEveryCommand:
    """main() loads dotenv keys once, up front, so select/estimate benefit too."""

    def test_main_select_honors_zdr_flag_from_repo_env(
        self, monkeypatch, tmp_path, capsys
    ):
        """select with no --zdr flag still honors OPENROUTER_ZDR from the repo .env."""
        monkeypatch.setattr(cli, "_load_dotenv_keys", _REAL_LOAD_DOTENV_KEYS)
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".env").write_text("OPENROUTER_ZDR=1\n")
        monkeypatch.setattr(cli, "_owning_repo_root", lambda: repo_dir)
        monkeypatch.setattr(cli, "fetch_zdr_model_ids", lambda: {"m/x"})
        rc = cli.main(["select", "--no-validate"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["zdr"] is True
        # None of the curated catalog matches the stubbed ZDR set, so the
        # roster comes back filtered down to nothing: proof the flag sourced
        # from the repo .env actually drove selection, not just parsing.
        assert payload["roster"] == []


class TestApiKeyHygiene:
    """_select_api_key rejects malformed keys; call_model redacts leaked keys."""

    def test_select_api_key_rejects_key_with_control_character(self, monkeypatch):
        """A key containing a control character (e.g. vertical tab) is rejected."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-FAKE\x0bTAIL")
        assert cli._select_api_key(zdr_mode=False) is None

    def test_select_api_key_rejects_key_with_embedded_space(self, monkeypatch):
        """A key containing plain whitespace is rejected."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or FAKE")
        assert cli._select_api_key(zdr_mode=False) is None

    def test_select_api_key_rejects_non_ascii_key(self, monkeypatch):
        """A key containing a non-ASCII character is rejected."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-faké")
        assert cli._select_api_key(zdr_mode=False) is None

    def test_select_api_key_accepts_a_clean_key(self, monkeypatch):
        """A plain ASCII, printable, whitespace-free key is accepted unchanged."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-clean123")
        assert cli._select_api_key(zdr_mode=False) == "sk-or-clean123"

    def test_run_rejects_hygiene_failing_key_naming_variable_only(
        self, monkeypatch, tmp_path, capsys
    ):
        """A key with an embedded control char exits 1 naming only the variable."""
        bad_key = "sk-or-FAKE\x0bTAIL"
        monkeypatch.setenv("OPENROUTER_API_KEY", bad_key)
        prompt = tmp_path / "p.txt"
        prompt.write_text("q?")
        rc = cli.main(["run", "--prompt-file", str(prompt), "--models", "m/x"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "OPENROUTER_API_KEY" in err
        assert bad_key not in err
        assert "FAKE" not in err

    def test_call_model_redacts_api_key_from_http_error(self, monkeypatch):
        """A 4xx body that echoes the bearer token is redacted before storage."""
        api_key = "sk-or-SECRET123"  # pragma: allowlist secret

        def handler(request):
            return httpx.Response(
                400, text=f"bad request, Authorization: Bearer {api_key}"
            )

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(handler)
            ) as client:
                return await cli.call_model(
                    client,
                    {"model": "m/x", "role": None, "system_prompt": None},
                    "q?",
                    api_key,
                    {},
                )

        record = asyncio.run(run())
        assert api_key not in record["error"]
        assert "[REDACTED]" in record["error"]

    def test_call_model_redacts_api_key_from_exception_message(self, monkeypatch):
        """An exception message that happens to include the key is redacted."""
        monkeypatch.setattr(cli, "RETRY_BACKOFF_SECONDS", 0)
        api_key = "sk-or-SECRET456"  # pragma: allowlist secret

        def handler(request):
            raise httpx.ConnectError(f"connection reset, key={api_key}")

        async def run():
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(handler)
            ) as client:
                return await cli.call_model(
                    client,
                    {"model": "m/x", "role": None, "system_prompt": None},
                    "q?",
                    api_key,
                    {},
                )

        record = asyncio.run(run())
        assert api_key not in record["error"]
        assert "[REDACTED]" in record["error"]


class TestDotenvParserEdgeCases:
    """Edge cases in _parse_dotenv_line beyond basic quote/export handling."""

    def test_empty_value_is_skipped(self):
        """A bare KEY= with nothing after the = does not resolve as real data."""
        assert cli._parse_dotenv_line("OPENROUTER_API_KEY=") is None

    def test_unquoted_trailing_comment_is_stripped(self):
        """An unquoted value's trailing ' #comment' is not part of the value."""
        assert cli._parse_dotenv_line("OPENROUTER_API_KEY=abc123 # a comment") == (
            "OPENROUTER_API_KEY",
            "abc123",
        )

    def test_quoted_value_with_trailing_comment_is_stripped(self):
        """A quoted value with a trailing comment drops both quotes and comment."""
        raw = 'OPENROUTER_API_KEY="abc 123" # a comment'  # pragma: allowlist secret
        assert cli._parse_dotenv_line(raw) == ("OPENROUTER_API_KEY", "abc 123")

    def test_export_prefix_accepts_tab_whitespace(self):
        """export followed by a tab (not just a single literal space) is stripped."""
        raw = "export\tOPENROUTER_API_KEY=abc123"  # pragma: allowlist secret
        assert cli._parse_dotenv_line(raw) == (
            "OPENROUTER_API_KEY",
            "abc123",
        )

    def test_export_prefix_accepts_multiple_spaces(self):
        """export followed by several spaces is stripped."""
        assert cli._parse_dotenv_line("export   OPENROUTER_API_KEY=abc123") == (
            "OPENROUTER_API_KEY",
            "abc123",
        )

    def test_export_without_trailing_whitespace_is_not_stripped(self):
        """A key literally named 'exportSOMETHING' is not mistaken for the prefix."""
        raw = "exportOPENROUTER_API_KEY=abc123"  # pragma: allowlist secret
        assert cli._parse_dotenv_line(raw) == (
            "exportOPENROUTER_API_KEY",
            "abc123",
        )


class TestZdrStaleCacheSurfacing:
    """A stale (>7 day) ZDR cache used as a fallback is surfaced, not silently trusted."""

    def test_fetch_zdr_ids_or_exit_flags_cache_older_than_seven_days(
        self, monkeypatch, tmp_path
    ):
        """A ZDR cache file older than 7 days is reported as stale."""
        cache = tmp_path / "zdr.json"
        cache.write_text(json.dumps(["econ/a"]))
        eight_days_ago = time.time() - (8 * 24 * 3600)
        os.utime(cache, (eight_days_ago, eight_days_ago))
        monkeypatch.setattr(cli, "ZDR_CACHE_PATH", cache)
        monkeypatch.setattr(cli, "fetch_zdr_model_ids", lambda: {"econ/a"})
        ids, cache_stale = cli._fetch_zdr_ids_or_exit()
        assert ids == {"econ/a"}
        assert cache_stale is True

    def test_fetch_zdr_ids_or_exit_fresh_cache_not_flagged(self, monkeypatch, tmp_path):
        """A ZDR cache written moments ago is not flagged as stale."""
        cache = tmp_path / "zdr.json"
        cache.write_text(json.dumps(["econ/a"]))
        monkeypatch.setattr(cli, "ZDR_CACHE_PATH", cache)
        monkeypatch.setattr(cli, "fetch_zdr_model_ids", lambda: {"econ/a"})
        ids, cache_stale = cli._fetch_zdr_ids_or_exit()
        assert ids == {"econ/a"}
        assert cache_stale is False

    def test_fetch_zdr_ids_or_exit_missing_cache_not_flagged(
        self, monkeypatch, tmp_path
    ):
        """No cache file at all (fresh live fetch, first run ever) is not stale."""
        cache = tmp_path / "does-not-exist.json"
        monkeypatch.setattr(cli, "ZDR_CACHE_PATH", cache)
        monkeypatch.setattr(cli, "fetch_zdr_model_ids", lambda: {"econ/a"})
        ids, cache_stale = cli._fetch_zdr_ids_or_exit()
        assert ids == {"econ/a"}
        assert cache_stale is False

    def test_main_select_zdr_surfaces_stale_cache_warning(
        self, monkeypatch, tmp_path, capsys
    ):
        """select --zdr adds zdr_cache_stale + warning when the fallback cache is old."""
        cache = tmp_path / "zdr.json"
        cache.write_text(json.dumps(["econ-a", "econ-b", "econ-c"]))
        eight_days_ago = time.time() - (8 * 24 * 3600)
        os.utime(cache, (eight_days_ago, eight_days_ago))
        monkeypatch.setattr(cli, "ZDR_CACHE_PATH", cache)
        monkeypatch.setattr(
            cli, "fetch_zdr_model_ids", lambda: {"econ-a", "econ-b", "econ-c"}
        )
        rc = cli.main(["select", "--zdr", "--no-validate"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["zdr_cache_stale"] is True
        assert "warning" in payload
        assert payload["warning"]

    def test_main_select_zdr_fresh_cache_omits_stale_fields(
        self, monkeypatch, tmp_path, capsys
    ):
        """A fresh ZDR fetch never adds zdr_cache_stale or warning to the payload."""
        monkeypatch.setattr(cli, "fetch_zdr_model_ids", lambda: {"econ-a"})
        rc = cli.main(["select", "--zdr", "--no-validate"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert "zdr_cache_stale" not in payload
        assert "warning" not in payload
