---
schema_type: common
title: "Per-repo ruleset bodies"
status: published
owner: core-maintainer
purpose: "JSON bodies for repo-level GitHub rulesets, applied via setup_repo_rulesets.py."
tags:
  - automation
---

JSON files in this directory follow the same schema as `../org-rulesets/`. Filename
convention: `<org>__<repo>.json`. Apply via:

```bash
uv run python scripts/setup_repo_rulesets.py \
  --repo <org>/<repo> \
  --body docs/reference/repo-rulesets/<org>__<repo>.json \
  --enforcement active
```

The org-level rulesets in `../org-rulesets/` define the universal baseline.
Per-repo rulesets are additive: a repo's effective protection is the union of
every ruleset that targets its default branch (org + repo level).
