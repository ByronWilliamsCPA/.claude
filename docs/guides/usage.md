---
title: "Usage"
schema_type: common
status: published
owner: core-maintainer
purpose: "Usage guide for Claude Code Configuration."
tags:
  - guide
  - usage
---

This guide covers common usage patterns for Claude Code Configuration.

## Installation

### From PyPI

```bash
pip install claude-config
```

### From Source

```bash
git clone https://github.com/ByronWilliamsCPA/.claude
cd claude_config
uv sync --all-extras
```

## Library Usage

### Basic Import

```python
from claude_config import __version__

print(f"Version: {__version__}")
```

### Logging

```python
from claude_config.utils.logging import get_logger, setup_logging

# Setup logging
setup_logging(level="DEBUG", json_logs=False)

# Get a logger
logger = get_logger(__name__)
logger.info("Hello from Claude Code Configuration")
```
