#!/usr/bin/env python3
"""Path-invoked shim. Logic lives in claude_config.compliance.log_render.

Kept under scripts/ with its original name so hooks, the settings.json
allowlist, and sibling-path RENDERER_SCRIPT references keep resolving. The
sys.path bootstrap follows the ~/.claude/scripts symlink to the real src/
without requiring the package to be installed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from claude_config.compliance.log_render import main

if __name__ == "__main__":
    raise SystemExit(main())
