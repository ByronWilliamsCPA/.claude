"""Unit tests for scripts/sync_org_pins.py."""

import textwrap
from datetime import date

import pytest
import yaml
from sync_org_pins import (
    build_updated_registry,
    load_registry,
    needs_update,
)

import tests.unit._load_sync_org_pins  # noqa: F401

REGISTRY_YAML = textwrap.dedent("""\
    sources:
      ByronWilliamsCPA/.github:
        current_tag: v1.0.0
        current_sha: ea8e19054eac195e6ab7bc93e9c2319632560b77
        last_synced: '2026-05-21'
      williaby/.github:
        current_tag: v1.0.0
        current_sha: ea8e19054eac195e6ab7bc93e9c2319632560b77
        last_synced: '2026-05-21'
""")


class TestLoadRegistry:
    def test_parses_sources(self, tmp_path):
        reg_file = tmp_path / "org-workflow-pins.yaml"
        reg_file.write_text(REGISTRY_YAML)
        registry = load_registry(reg_file)
        assert "ByronWilliamsCPA/.github" in registry["sources"]
        assert (
            registry["sources"]["ByronWilliamsCPA/.github"]["current_tag"] == "v1.0.0"
        )

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_registry(tmp_path / "nonexistent.yaml")

    def test_raises_on_invalid_yaml(self, tmp_path):
        bad = tmp_path / "org-workflow-pins.yaml"
        bad.write_text("sources: [not: a: mapping]")
        with pytest.raises(yaml.YAMLError):
            load_registry(bad)


class TestNeedsUpdate:
    def test_returns_true_when_sha_differs(self):
        entry = {
            "current_tag": "v1.0.0",
            "current_sha": "abc123",
            "last_synced": "2026-05-21",
        }
        assert needs_update(entry, tag="v1.1.0", sha="def456") is True

    def test_returns_true_when_tag_only_differs(self):
        entry = {
            "current_tag": "v1.0.0",
            "current_sha": "abc123",
            "last_synced": "2026-05-21",
        }
        assert needs_update(entry, tag="v1.0.1", sha="abc123") is True

    def test_returns_false_when_both_match(self):
        entry = {
            "current_tag": "v1.0.0",
            "current_sha": "abc123",
            "last_synced": "2026-05-21",
        }
        assert needs_update(entry, tag="v1.0.0", sha="abc123") is False


class TestBuildUpdatedRegistry:
    def test_updates_tag_sha_and_date(self):
        registry = yaml.safe_load(REGISTRY_YAML)
        today = date(2026, 5, 22)
        updated = build_updated_registry(
            registry,
            repo="ByronWilliamsCPA/.github",
            new_tag="v1.1.0",
            new_sha="deadbeef" * 5,
            sync_date=today,
        )
        src = updated["sources"]["ByronWilliamsCPA/.github"]
        assert src["current_tag"] == "v1.1.0"
        assert src["current_sha"] == "deadbeef" * 5
        assert src["last_synced"] == "2026-05-22"

    def test_does_not_mutate_other_entries(self):
        registry = yaml.safe_load(REGISTRY_YAML)
        today = date(2026, 5, 22)
        updated = build_updated_registry(
            registry,
            repo="ByronWilliamsCPA/.github",
            new_tag="v1.1.0",
            new_sha="deadbeef" * 5,
            sync_date=today,
        )
        src = updated["sources"]["williaby/.github"]
        assert src["current_tag"] == "v1.0.0"
        expected_sha = (
            "ea8e19054eac195e6ab7bc93e9c2319632560b77"  # pragma: allowlist secret
        )
        assert src["current_sha"] == expected_sha
