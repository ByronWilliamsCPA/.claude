"""Loader so test_sync_org_pins can import scripts/sync_org_pins.py."""

import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "sync_org_pins",
    Path(__file__).parents[2] / "scripts" / "sync_org_pins.py",
)
module = importlib.util.module_from_spec(spec)
sys.modules["sync_org_pins"] = module
spec.loader.exec_module(module)
