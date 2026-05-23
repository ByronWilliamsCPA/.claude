"""Load scripts/populate-github-repos.py as a Python module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.unit._importlib_loader import load_script

if TYPE_CHECKING:
    from types import ModuleType


def load_module() -> ModuleType:
    return load_script("populate-github-repos.py", "populate_github_repos")
