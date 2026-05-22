#!/usr/bin/env python3
"""Populate docs/reusable-workflow-jobs.yaml from a local clone of an org repo.

Walks <clone-path>/.github/workflows/*.yml, extracts check names produced
by each workflow using the same parser as check-required-checks.py, and
writes a YAML registry file. Re-run when reusable workflows change.

The registry stores UNPREFIXED check names; the validator applies the
caller-job-name prefix at compare time. This makes a single registry entry
portable across repos that call the same reusable workflow with different
job names.
"""

from __future__ import annotations

import argparse
import importlib.abc
import importlib.util
import sys
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

if TYPE_CHECKING:
    from types import ModuleType

_SELF_DIR = Path(__file__).resolve().parent
_VALIDATOR_PATH = _SELF_DIR / "check-required-checks.py"


def _load_validator() -> ModuleType:
    """Load check-required-checks.py via importlib (filename has hyphens).

    Uses explicit raise statements rather than `assert` because asserts are
    stripped under `python -O`, which would let a missing or malformed
    validator slip through and surface as opaque AttributeError downstream.
    """
    spec = importlib.util.spec_from_file_location(
        "check_required_checks",
        _VALIDATOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise FileNotFoundError(
            f"Validator script not found or unloadable: {_VALIDATOR_PATH}"
        )
    if not isinstance(spec.loader, importlib.abc.Loader):
        raise RuntimeError(
            f"Validator spec loader is not a Loader instance: {type(spec.loader).__name__}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_required_checks"] = module
    spec.loader.exec_module(module)
    return module


_validator = _load_validator()


def scan_org_repo(
    clone_path: Path,
    org_slug: str,
    output_path: Path,
    today: str,
) -> None:
    """Walk clone_path/.github/workflows/*.yml and write a registry YAML.

    Args:
        clone_path: Local clone of the org repo (e.g., ByronWilliamsCPA/.github).
        org_slug: Org repo slug used as the prefix in registry keys.
        output_path: Where to write the YAML registry.
        today: ISO date string used for last_verified timestamps.

    Raises:
        FileNotFoundError: If the workflow directory does not exist.
    """
    workflow_dir = clone_path / ".github" / "workflows"
    if not workflow_dir.is_dir():
        raise FileNotFoundError(f"No workflow directory at {workflow_dir}")

    registry: dict[str, dict[str, object]] = {}
    workflow_paths = sorted(
        list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))
    )
    unregistered_prefix = _validator._UNREGISTERED_PREFIX  # noqa: SLF001 -- module constant; no public alias.
    for path in workflow_paths:
        produced = _validator.extract_produced_check_names(
            path.read_text(), registry={}
        )
        # Skip the UNREGISTERED sentinels so reusable workflows that
        # themselves call other reusables do not pollute the registry with
        # placeholder entries. The unresolved names will surface as
        # CI-022 findings if they're ever required.
        cleaned = {p for p in produced if not p.startswith(unregistered_prefix)}
        if not cleaned:
            continue
        key = f"{org_slug}/.github/workflows/{path.name}"
        registry[key] = {
            "produces": sorted(cleaned),
            "source_repo": org_slug,
            "last_verified": today,
        }

    yaml = YAML()
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    with output_path.open("w") as fh:
        yaml.dump(registry, fh)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the seed script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clone-path",
        type=Path,
        required=True,
        help="Local clone of the org repo (e.g., ByronWilliamsCPA/.github)",
    )
    parser.add_argument(
        "--org-slug",
        required=True,
        help="Org repo slug (e.g., ByronWilliamsCPA/.github)",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--today",
        default=date.today().isoformat(),
    )
    args = parser.parse_args(argv)
    scan_org_repo(args.clone_path, args.org_slug, args.output, args.today)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
