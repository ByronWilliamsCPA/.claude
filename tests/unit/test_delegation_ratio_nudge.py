"""Tests for scripts/hooks/delegation-ratio-nudge.py.

The hook counts main-thread (non-sidechain) file mutations against subagent
dispatches and nudges when the orchestrator is doing implementation work
itself. These tests pin the two properties that make it safe to run on every
file edit: it never counts subagent work against the root thread, and it
fails open on every malformed input.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING

import pytest

from tests.unit._load_delegation_ratio_nudge import load_module

if TYPE_CHECKING:
    from pathlib import Path

nudge = load_module()


def _assistant(tools: list[str], *, sidechain: bool = False) -> str:
    """Build one assistant transcript line carrying the named tool_use blocks."""
    return json.dumps(
        {
            "type": "assistant",
            "isSidechain": sidechain,
            "message": {"content": [{"type": "tool_use", "name": t} for t in tools]},
        }
    )


def _transcript(tmp_path: Path, lines: list[str]) -> Path:
    """Write transcript lines to a JSONL file and return its path."""
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _fresh() -> dict[str, int]:
    """Return a zeroed scan state."""
    return {"offset": 0, "mutations": 0, "dispatches": 0, "last_band": -1}


class TestScan:
    """Transcript scanning and root/subagent attribution."""

    def test_counts_root_mutations(self, tmp_path: Path) -> None:
        """Every mutating tool in the hook's matcher must be counted."""
        tools = ["Edit", "Write", "MultiEdit", "NotebookEdit"]
        t = _transcript(tmp_path, [_assistant(tools)])
        state = nudge.scan(t, _fresh())
        assert state["mutations"] == len(tools)

    def test_ignores_sidechain_mutations(self, tmp_path: Path) -> None:
        """A subagent editing files must never count against the root thread."""
        t = _transcript(
            tmp_path,
            [
                _assistant(["Edit"]),
                _assistant(["Edit", "Edit", "Write"], sidechain=True),
            ],
        )
        state = nudge.scan(t, _fresh())
        assert state["mutations"] == 1

    def test_counts_root_dispatches(self, tmp_path: Path) -> None:
        t = _transcript(tmp_path, [_assistant(["Agent", "Agent"])])
        state = nudge.scan(t, _fresh())
        assert state["dispatches"] == 2

    def test_ignores_sidechain_dispatches(self, tmp_path: Path) -> None:
        t = _transcript(tmp_path, [_assistant(["Agent"], sidechain=True)])
        state = nudge.scan(t, _fresh())
        assert state["dispatches"] == 0

    def test_ignores_unrelated_tools_and_records(self, tmp_path: Path) -> None:
        t = _transcript(
            tmp_path,
            [_assistant(["Bash", "Read", "Grep"]), json.dumps({"type": "user"})],
        )
        state = nudge.scan(t, _fresh())
        assert state["mutations"] == 0
        assert state["dispatches"] == 0

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        t = _transcript(tmp_path, ["{not json", _assistant(["Edit"]), ""])
        state = nudge.scan(t, _fresh())
        assert state["mutations"] == 1

    def test_incremental_scan_does_not_double_count(self, tmp_path: Path) -> None:
        """Second scan reads only appended bytes, so counts accumulate once."""
        t = _transcript(tmp_path, [_assistant(["Edit"])])
        state = nudge.scan(t, _fresh())
        assert state["mutations"] == 1
        first_offset = state["offset"]

        with t.open("a", encoding="utf-8") as fh:
            fh.write(_assistant(["Edit"]) + "\n")

        state = nudge.scan(t, state)
        assert state["mutations"] == 2
        assert state["offset"] > first_offset

    def test_resets_when_transcript_shrinks(self, tmp_path: Path) -> None:
        """A rotated or compacted transcript must recount, not trust the offset."""
        t = _transcript(tmp_path, [_assistant(["Edit"]) for _ in range(5)])
        state = nudge.scan(t, _fresh())
        assert state["mutations"] == 5

        _transcript(tmp_path, [_assistant(["Edit"])])
        state = nudge.scan(t, state)
        assert state["mutations"] == 1
        assert state["offset"] > 0

    def test_missing_transcript_returns_state_unchanged(self, tmp_path: Path) -> None:
        state = _fresh()
        result = nudge.scan(tmp_path / "absent.jsonl", state)
        assert result == state


class TestShouldFire:
    """Threshold, ratio, and band re-arm logic."""

    @pytest.mark.parametrize(
        ("mutations", "dispatches", "expected"),
        [
            (9, 0, False),  # below the floor, however bad the ratio
            (10, 0, True),  # floor reached with no delegation at all
            (10, 4, False),  # 2.5:1 is within tolerance
            (30, 8, True),  # 3.75:1 trips the threshold
            (12, 32, False),  # heavily delegated, stays quiet
        ],
    )
    def test_threshold_matrix(
        self, mutations: int, dispatches: int, expected: bool
    ) -> None:
        state = {"mutations": mutations, "dispatches": dispatches, "last_fire_at": -1}
        assert nudge.should_fire(state) is expected

    def test_does_not_refire_before_rearm_distance(self) -> None:
        """A fire at edit 24 must not be followed by another at 25."""
        state = {"mutations": 25, "dispatches": 0, "last_fire_at": 24}
        assert nudge.should_fire(state) is False

    def test_refires_once_rearm_distance_is_reached(self) -> None:
        state = {"mutations": 39, "dispatches": 0, "last_fire_at": 24}
        assert nudge.should_fire(state) is True

    def test_goes_quiet_once_ratio_recovers(self) -> None:
        """Dispatching a subagent must silence the nudge without a reset."""
        state = {"mutations": 30, "dispatches": 15, "last_fire_at": 10}
        assert nudge.should_fire(state) is False

    def test_caps_total_fires_per_session(self) -> None:
        """Past the cap the reader has been told; repeating trains them out."""
        state = {
            "mutations": 500,
            "dispatches": 0,
            "last_fire_at": 10,
            "fires": nudge.MAX_FIRES,
        }
        assert nudge.should_fire(state) is False


class TestStateFile:
    """Session-id handling for the per-session state file."""

    def test_rejects_empty_id(self) -> None:
        assert nudge.state_file("") is None

    def test_sanitises_path_traversal(self) -> None:
        path = nudge.state_file("../../etc/passwd")
        assert path is not None
        assert nudge.STATE_DIR in path.parents
        assert ".." not in path.parts


class TestMain:
    """End-to-end hook contract: emit JSON, never raise, never block."""

    def _run(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        payload: str,
        state_dir: Path,
    ) -> dict[str, object]:
        monkeypatch.setattr(nudge, "STATE_DIR", state_dir)
        monkeypatch.setattr("sys.stdin", io.StringIO(payload))
        nudge.main()
        return json.loads(capsys.readouterr().out)

    def test_malformed_stdin_fails_open(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        assert self._run(monkeypatch, capsys, "not json", tmp_path) == {}

    def test_missing_transcript_is_silent(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        payload = json.dumps(
            {"session_id": "abc", "transcript_path": str(tmp_path / "nope.jsonl")}
        )
        assert self._run(monkeypatch, capsys, payload, tmp_path) == {}

    def test_disabled_by_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        monkeypatch.setenv("DELEGATION_NUDGE_DISABLED", "1")
        t = _transcript(tmp_path, [_assistant(["Edit"]) for _ in range(20)])
        payload = json.dumps({"session_id": "abc", "transcript_path": str(t)})
        assert self._run(monkeypatch, capsys, payload, tmp_path) == {}

    def test_emits_additional_context_when_ratio_is_bad(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        t = _transcript(tmp_path, [_assistant(["Edit"]) for _ in range(20)])
        payload = json.dumps({"session_id": "abc", "transcript_path": str(t)})
        out = self._run(monkeypatch, capsys, payload, tmp_path / "state")
        hook_out = out["hookSpecificOutput"]
        assert isinstance(hook_out, dict)
        assert hook_out["hookEventName"] == "PostToolUse"
        assert "20 main-thread file edits" in str(hook_out["additionalContext"])

    def test_stays_silent_when_delegating(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        lines = [_assistant(["Edit"]) for _ in range(12)]
        lines += [_assistant(["Agent"]) for _ in range(32)]
        t = _transcript(tmp_path, lines)
        payload = json.dumps({"session_id": "abc", "transcript_path": str(t)})
        assert self._run(monkeypatch, capsys, payload, tmp_path / "state") == {}

    def test_persists_band_across_invocations(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        """Firing once must not fire again until the next band."""
        t = _transcript(tmp_path, [_assistant(["Edit"]) for _ in range(20)])
        payload = json.dumps({"session_id": "abc", "transcript_path": str(t)})
        state_dir = tmp_path / "state"
        assert self._run(monkeypatch, capsys, payload, state_dir) != {}
        assert self._run(monkeypatch, capsys, payload, state_dir) == {}
