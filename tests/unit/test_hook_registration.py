"""No hook script may be registered in more than one committed source."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ["hooks.json", "settings.json", ".claude/settings.json"]

# A command's identity is the script it runs, not its last token. Guarded
# bash -c wrappers (Task 8) end in shared shell syntax like >&2', which made
# a last-token key collide across distinct plugin entries.
SCRIPT_PATH_RE = re.compile(r"[^\s\"']+/[^\s\"']+\.(?:sh|py)\b")


def script_key(cmd: str) -> str:
    """Return the basename of the first script path in cmd, or cmd itself."""
    match = SCRIPT_PATH_RE.search(cmd)
    return Path(match.group(0)).name if match else cmd


def iter_commands(config):
    hooks = config.get("hooks", config)
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                if cmd:
                    yield event, cmd


def test_no_duplicate_script_registration():
    seen = {}
    for source in SOURCES:
        path = ROOT / source
        if not path.exists():
            continue
        for event, cmd in iter_commands(json.loads(path.read_text())):
            key = (event, script_key(cmd))
            assert key not in seen, (
                f"{key} registered in {seen[key]} and {source}"
            )
            seen[key] = source


def test_registered_scripts_exist():
    for source in SOURCES:
        path = ROOT / source
        if not path.exists():
            continue
        for _event, cmd in iter_commands(json.loads(path.read_text())):
            match = SCRIPT_PATH_RE.search(cmd)
            if match is None or "/scripts/" not in match.group(0):
                continue  # plugin-hook paths are covered by their guards
            assert (ROOT / "scripts" / Path(match.group(0)).name).exists(), (
                f"{source} registers missing script {match.group(0)}"
            )
