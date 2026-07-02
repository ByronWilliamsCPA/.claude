"""No hook script may be registered in more than one committed source."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ["hooks.json", "settings.json", ".claude/settings.json"]


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
            script = Path(cmd.split()[-1]).name
            key = (event, script)
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
            token = cmd.split()[-1]
            if "/scripts/" not in token:
                continue  # plugin/submodule paths are Task 8's concern
            rel = token.split("/.claude/", 1)[-1].replace("$HOME/", "")
            assert (ROOT / "scripts" / Path(rel).name).exists(), (
                f"{source} registers missing script {token}"
            )
