#!/usr/bin/env python3
"""Populate docs/reusable-workflow-jobs.yaml from a local clone of an org repo.

Walks <clone-path>/.github/workflows/*.yml, extracts check names produced
by each workflow using the same parser as check-required-checks.py, and
writes a YAML registry file. Re-run when reusable workflows change.
"""

from __future__ import annotations

import argparse
import importlib.abc
import importlib.util
import sys
from datetime import date
from pathlib import Path

from ruamel.yaml import YAML

_SELF_DIR = Path(__file__).resolve().parent
_VALIDATOR_PATH = _SELF_DIR / "check-required-checks.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location(
        "check_required_checks",
        _VALIDATOR_PATH,
    )
    assert spec is not None, f"Validator script not found: {_VALIDATOR_PATH}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_required_checks"] = module
    assert isinstance(spec.loader, importlib.abc.Loader)
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
    for path in workflow_paths:
        produced = _validator.extract_produced_check_names(
            path.read_text(), registry={}
        )
        if not produced:
            continue
        key = f"{org_slug}/.github/workflows/{path.name}"
        registry[key] = {
            "produces": sorted(produced),
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
        default=date.today().isoformat(),  # noqa: DTZ011
    )
    args = parser.parse_args(argv)
    scan_org_repo(args.clone_path, args.org_slug, args.output, args.today)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
