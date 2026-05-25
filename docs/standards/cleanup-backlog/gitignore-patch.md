---
title: "Gitignore patch for homelab-infra"
schema_type: common
status: published
owner: core-maintainer
purpose: "Gitignore entries homelab-infra must add to keep cleanup-backlog runtime files local-only."
tags:
  - reference
  - infrastructure
  - automation
---

Add the following block to `~/dev/homelab-infra/.gitignore`. Suggested location:
near the existing `tmp_cleanup/` entries (around line 193 in the current file)
or at the end of the file in a clearly labeled section.

```gitignore
# Cleanup backlog runtime directory: schema and spec live in
# ~/dev/.claude/docs/standards/cleanup-backlog/. Backlog state and per-task
# files are local-only to avoid triggering CI on every backlog edit.
cleanup-backlog/
```

## Why the directory is fully ignored

An earlier draft considered committing `_schema.md` and `README.md` inside the
backlog directory while ignoring the status subdirectories. That approach was
rejected because:

1. The schema doc already lives in the .claude repo (this directory). Storing
   it in two places risks drift.
2. Every commit to homelab-infra triggers CI. Even schema doc updates would
   incur CI cost for content that is not part of the homelab-infra project.
3. A single-line gitignore entry is simpler than a multi-line allow/ignore
   pattern with per-status-dir negations.

## Applying the patch

Wait until you are on `main` (or a clean branch where this addition makes
sense), then apply:

```bash
cd ~/dev/homelab-infra
echo '' >> .gitignore
echo '# Cleanup backlog runtime directory: schema lives in ~/dev/.claude/docs/standards/cleanup-backlog/' >> .gitignore
echo 'cleanup-backlog/' >> .gitignore
git add .gitignore
git commit -m "chore: ignore cleanup-backlog runtime directory"
```

Do not apply this while on the active `fix/newman-stack-env` branch unless you
want the change bundled with that feature. The runtime directory works fine
without the gitignore entry; the only risk is accidentally committing task
files in a future `git add .`. Until the patch is applied, prefer
`git add <specific-file>` over `git add .` in homelab-infra.
