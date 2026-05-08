---
schema_type: planning
title: "OpenAPI Compliance Pipeline Implementation Plan"
status: draft
owner: core-maintainer
purpose: "Implementation plan for the OpenAPI compliance pipeline: catalog api blocks, three new agents, five API-domain manifest checks, applies_to evaluator, and compliance skill update."
component: Development-Tools
source: "docs/superpowers/specs/2026-05-07-openapi-compliance-design.md"
---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-agent pipeline that enriches FastAPI routes, exports OpenAPI specs and Postman collections, validates APIs via newman on docker-host, gates compliance via five new `API-*` manifest checks, and registers all of this in the repo catalog.

**Architecture:** A catalog-driven orchestrator (`openapi-compliance-agent`) dispatches three sequential specialists per repo (code enricher, spec exporter, test designer) and opens a PR; the `/repo-audit` system gains `API-*` checks guarded by an `applies_to` evaluator in `check-repo-compliance.py`.

**Tech Stack:** FastAPI, Pydantic, OpenAPI 3.x YAML, Postman Collection v2.1 JSON, newman (Postman CLI), GitHub Actions, `gh` CLI, `python3`, `jq`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `docs/reference/github-repos.json` | Modify | Add `idealEntry.api` + `api` block to all 46 repos |
| `docs/standards-manifest.yaml` | Modify | Append API domain with API-001..005 checks |
| `.claude/agents/openapi-compliance-agent.md` | Create | Orchestrator agent |
| `.claude/agents/openapi-code-enricher.md` | Create | FastAPI enrichment specialist |
| `.claude/agents/postman-test-designer.md` | Create | Test design, newman, CI workflow |
| `scripts/check-repo-compliance.py` | Modify | Add catalog loader + `applies_to` evaluator + API-001..005 checks |
| `.claude/skills/repo-compliance/SKILL.md` | Modify | Add API domain row + `applies_to` dispatch note |
| `AGENTS-AND-SKILLS.md` | Modify | Register 3 new agents |

---

## Task 1: Add idealEntry.api to github-repos.json

**Files:**
- Modify: `docs/reference/github-repos.json` (find `"templateDrift"` key in `idealEntry`, insert after it)

- [ ] **Step 1: Write the migration script**

Save as `/tmp/add_ideal_api.py`:

```python
#!/usr/bin/env python3
"""Inserts idealEntry.api into _meta block of github-repos.json."""
import json
from pathlib import Path

CATALOG = Path("/home/byron/dev/.claude/docs/reference/github-repos.json")

data = json.loads(CATALOG.read_text())

ideal_api = {
    "_note": "Required for servesApi=true repos only. N/A for non-API repos.",
    "openApiSpec": True,
    "postmanCollection": True,
    "lastAudited": "<within 90 days>",
    "testStatus": "passing"
}

data["_meta"]["idealEntry"]["api"] = ideal_api

CATALOG.write_text(json.dumps(data, indent=2) + "\n")
print("Done. idealEntry.api added.")
```

- [ ] **Step 2: Run the script**

```bash
python3 /tmp/add_ideal_api.py
```

Expected: `Done. idealEntry.api added.`

- [ ] **Step 3: Verify**

```bash
python3 -c "
import json
d = json.load(open('/home/byron/dev/.claude/docs/reference/github-repos.json'))
print(json.dumps(d['_meta']['idealEntry']['api'], indent=2))
"
```

Expected output:
```json
{
  "_note": "Required for servesApi=true repos only. N/A for non-API repos.",
  "openApiSpec": true,
  "postmanCollection": true,
  "lastAudited": "<within 90 days>",
  "testStatus": "passing"
}
```

---

## Task 2: Populate api blocks for all repos (Python script)

**Files:**
- Modify: `docs/reference/github-repos.json`

Note: `github-repos.json` is gitignored (local-only catalog). Commit is not required for this file; verification only.

- [ ] **Step 1: Write the population script**

Save as `/tmp/populate_api_blocks.py`:

```python
#!/usr/bin/env python3
"""Populates api blocks in github-repos.json from 2026-05-07 scan results."""
import json
from pathlib import Path

CATALOG = Path("/home/byron/dev/.claude/docs/reference/github-repos.json")

# ------------------------------------------------------------------ #
# servesApi=true repos: full block with compliance tracking fields    #
# ------------------------------------------------------------------ #
SERVES_API = {
    "audio_processor": {
        "frameworks": ["fastapi"],
        "entryPoints": ["src/audio_processor/api/__init__.py"],
        "externalClients": ["requests", "sendgrid"],
    },
    "dataset_dev": {
        "frameworks": ["fastapi"],
        "entryPoints": ["src/prepare_doc/main.py"],
        "externalClients": ["aws_boto3"],
    },
    "exercise_competition": {
        "frameworks": ["fastapi"],
        "entryPoints": ["src/exercise_competition/main.py"],
        "externalClients": ["httpx", "requests"],
    },
    "foundry_unify": {
        "frameworks": ["fastapi"],
        "entryPoints": ["src/foundry_unify/api/health.py"],
        "externalClients": ["httpx", "requests"],
    },
    "fragrance_rater": {
        "frameworks": ["fastapi"],
        "entryPoints": ["site/planning/backend/app/main.py"],
        "externalClients": ["httpx", "requests"],
    },
    "homelab-infra": {
        "frameworks": ["fastapi", "flask"],
        "entryPoints": [
            "services/cloudflare-auth-validator/src/main.py",
            "services/ai-text-detector/app/main.py",
            "services/cert-enroll/app.py",
        ],
        "externalClients": ["aws_boto3", "httpx", "requests", "urllib"],
    },
    "image_detection": {
        "frameworks": ["fastapi"],
        "entryPoints": ["src/image_preprocessing_detector/api/app.py"],
        "externalClients": [
            "aiohttp_client", "anthropic", "google_cloud", "httpx",
            "openai", "requests", "ssh_paramiko", "urllib",
        ],
    },
    "rag_processor": {
        "frameworks": ["fastapi"],
        "entryPoints": ["src/rag_processor/main.py"],
        "externalClients": ["httpx", "redis_client", "requests"],
    },
    "zen-mcp-server": {
        "frameworks": ["fastapi", "mcp"],
        "entryPoints": ["plugins/promptcraft_system/api_server.py"],
        "externalClients": ["httpx", "openai", "redis_client", "requests", "supabase"],
    },
    # williaby hyphenated equivalents of the repos above
    "exercise-competition": {
        "frameworks": ["fastapi"],
        "entryPoints": ["src/exercise_competition/main.py"],
        "externalClients": ["httpx", "requests"],
    },
    "fragrance-rater": {
        "frameworks": ["fastapi"],
        "entryPoints": ["site/planning/backend/app/main.py"],
        "externalClients": ["httpx", "requests"],
    },
    "image-preprocessing-detector": {
        "frameworks": ["fastapi"],
        "entryPoints": ["src/image_preprocessing_detector/api/app.py"],
        "externalClients": [
            "aiohttp_client", "anthropic", "google_cloud", "httpx",
            "openai", "requests", "ssh_paramiko", "urllib",
        ],
    },
    "rag-processor": {
        "frameworks": ["fastapi"],
        "entryPoints": ["src/rag_processor/main.py"],
        "externalClients": ["httpx", "redis_client", "requests"],
    },
    "audio-processor": {
        "frameworks": ["fastapi"],
        "entryPoints": ["src/audio_processor/api/__init__.py"],
        "externalClients": ["requests", "sendgrid"],
    },
}

# ------------------------------------------------------------------ #
# External-only repos: servesApi=false + externalClients only         #
# ------------------------------------------------------------------ #
EXTERNAL_ONLY = {
    "uml-mcp-server": ["requests"],
    "DeQA-Doc": ["anthropic", "google_cloud", "httpx", "openai", "requests", "supabase", "urllib"],
    "OSINT": ["dns_resolver", "httpx", "smtp_email"],
    "PromptCraft": ["aiohttp_client", "anthropic", "httpx", "openai", "requests", "ssh_paramiko", "supabase"],
    "cookiecutter-python-template": ["httpx", "requests"],
    "dna": ["requests", "urllib"],
    "gleif": ["httpx"],
    "image-generation": ["requests"],
    "library": ["requests"],
    "llc-manager": ["requests"],
    "maester_tests": ["requests", "urllib"],
    "maester-tests": ["requests", "urllib"],
    "monte_carlo": ["azure_sdk", "httpx", "smtp_email"],
    "pp-security-master": ["aiohttp_client"],
    "precision_rifle": ["aiohttp_client", "anthropic", "httpx", "openai", "requests", "supabase"],
    "python-libs": ["google_cloud", "httpx", "requests"],
    "python_libs": ["google_cloud", "requests"],
    "reference-library": ["urllib"],
    "template-sample": ["requests"],
    "xero_crypto": ["httpx", "redis_client", "requests", "supabase"],
    "xero-crypto": ["httpx", "redis_client", "requests", "supabase"],
}

# Repos with no API activity at all -- omit api block entirely.
# (These are listed here for reference; the script skips them.)
NO_API = {
    "OPNSense", "backpacking", "data_ops", "family-office-portal",
    "genealogy", "homelab-agent-configs", "klipper-octoprint-configs",
    "ostf", "taxdome", "unify", "usc",
    # config/docs-only repos not scanned locally
    ".claude", ".github", "CR-10-", "OPNS", "superslicer-configs",
    "dart-frog-paludarium",
}

data = json.loads(CATALOG.read_text())

served_count = 0
external_count = 0
skipped_count = 0

for repo in data["repos"]:
    name = repo["name"]

    if name in SERVES_API:
        info = SERVES_API[name]
        repo["api"] = {
            "servesApi": True,
            "frameworks": info["frameworks"],
            "entryPoints": info["entryPoints"],
            "externalClients": info["externalClients"],
            "openApiSpec": False,
            "postmanCollection": False,
            "lastAudited": None,
            "testStatus": None,
        }
        served_count += 1

    elif name in EXTERNAL_ONLY:
        repo["api"] = {
            "servesApi": False,
            "externalClients": EXTERNAL_ONLY[name],
        }
        external_count += 1

    elif name in NO_API:
        skipped_count += 1  # intentionally no api block

    else:
        # Repo exists in catalog but has no local scan data.
        # Flag it for manual review rather than silently skipping.
        print(f"WARNING: {name} ({repo['org']}) has no scan data -- set api block manually")

CATALOG.write_text(json.dumps(data, indent=2) + "\n")
print(f"Done. servesApi=true: {served_count}, external-only: {external_count}, no-api: {skipped_count}")
```

- [ ] **Step 2: Run the script**

```bash
python3 /tmp/populate_api_blocks.py
```

Expected (no errors, warnings only for truly unclassified repos):
```
Done. servesApi=true: N, external-only: N, no-api: N
```

Any `WARNING` lines indicate repos that need a manual `api` block. For each warning, inspect the repo with `gh repo view <org>/<name>` and set `api.servesApi` accordingly.

- [ ] **Step 3: Verify one servesApi=true entry and one external-only entry**

```bash
python3 -c "
import json
d = json.load(open('/home/byron/dev/.claude/docs/reference/github-repos.json'))
for r in d['repos']:
    if r['name'] == 'audio_processor':
        print('audio_processor:', json.dumps(r.get('api'), indent=2))
    if r['name'] == 'uml-mcp-server':
        print('uml-mcp-server:', json.dumps(r.get('api'), indent=2))
"
```

Expected:
```
audio_processor: {
  "servesApi": true,
  "frameworks": ["fastapi"],
  "entryPoints": ["src/audio_processor/api/__init__.py"],
  "externalClients": ["requests", "sendgrid"],
  "openApiSpec": false,
  "postmanCollection": false,
  "lastAudited": null,
  "testStatus": null
}
uml-mcp-server: {
  "servesApi": false,
  "externalClients": ["requests"]
}
```

---

## Task 3: Add API domain checks to standards-manifest.yaml

**Files:**
- Modify: `docs/standards-manifest.yaml` (append after last entry, which ends at line 737)

- [ ] **Step 1: Append the API domain block**

Open `docs/standards-manifest.yaml` and add at the end of the file (after the MKDOCS-012 entry):

```yaml

# ===========================================================================
# API Domain (applies_to: api_repos -- skipped for servesApi=false repos)
# ===========================================================================

- id: API-001
  domain: api
  severity: critical
  description: "OpenAPI spec present at docs/api/openapi.yaml"
  verify: "file_exists: docs/api/openapi.yaml"
  applies_to: api_repos
  override_eligible: false

- id: API-002
  domain: api
  severity: critical
  description: "Postman collection present at docs/api/postman-collection.json"
  verify: "file_exists: docs/api/postman-collection.json"
  applies_to: api_repos
  override_eligible: false

- id: API-003
  domain: api
  severity: important
  description: "Postman API tests CI workflow present"
  verify: "file_exists: .github/workflows/postman-api-tests.yml"
  applies_to: api_repos
  override_eligible: false

- id: API-004
  domain: api
  severity: important
  description: "OpenAPI spec audited within 90 days"
  verify: "catalog_field: api.lastAudited, within_days: 90"
  applies_to: api_repos
  override_eligible: true

- id: API-005
  domain: api
  severity: suggested
  description: "All Postman API tests passing"
  verify: "catalog_field: api.testStatus, equals: passing"
  applies_to: api_repos
  override_eligible: true
```

- [ ] **Step 2: Verify YAML is valid**

```bash
python3 -c "import yaml; yaml.safe_load(open('docs/standards-manifest.yaml'))" && echo "VALID"
```

Expected: `VALID`

- [ ] **Step 3: Verify check count increased by 5**

```bash
python3 -c "
import yaml
checks = yaml.safe_load(open('docs/standards-manifest.yaml'))
api_checks = [c for c in checks if c.get('domain') == 'api']
print(f'API checks: {len(api_checks)}')
for c in api_checks:
    print(f'  {c[\"id\"]}: {c[\"description\"][:50]}')
"
```

Expected: 5 API checks printed.

- [ ] **Step 4: Commit**

```bash
git add docs/standards-manifest.yaml
git commit -m "feat(manifest): add API domain checks API-001..005 with applies_to guard"
```

---

## Task 4: Create openapi-compliance-agent.md

**Files:**
- Create: `.claude/agents/openapi-compliance-agent.md`

- [ ] **Step 1: Create the agent file**

```markdown
---
name: openapi-compliance-agent
description: >
  OpenAPI compliance orchestrator. Reads the repo catalog to find servesApi=true
  repos, creates a per-repo worktree, then dispatches openapi-code-enricher,
  api-development-agent, postman-test-designer, and github-workflow-agent
  sequentially. Updates api.openApiSpec, api.postmanCollection, api.lastAudited,
  and api.testStatus in the catalog after a successful run. Invoke via
  /openapi-audit <repo-slug> or /openapi-audit all. Runs repos in parallel when
  "all" is specified.
model: sonnet
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Agent"]
---

OpenAPI compliance orchestrator for internal API repos.

## Invocation

```text
/openapi-audit <repo-slug>   -- single repo (e.g., /openapi-audit audio_processor)
/openapi-audit all            -- all repos with api.servesApi=true
```

## Workflow

### Step 1: Load targets from catalog

Read `/home/byron/dev/.claude/docs/reference/github-repos.json`. Extract all repo
entries where `api.servesApi == true`. If a single slug was supplied, filter to
that one repo; error if the slug is not found or `api.servesApi` is not `true`.

For each target repo, you need:
- `name`: repo slug (e.g., `audio_processor`)
- `org`: GitHub org (e.g., `ByronWilliamsCPA`)
- `api.frameworks`: list of frameworks
- `api.entryPoints`: list of entry point file paths

### Step 2: Per-repo pipeline (sequential within each repo)

For `all`, run each repo's full four-step pipeline concurrently across repos.
For a single repo, run sequentially.

#### 2a. Prepare worktree

```bash
REPO_SLUG=<name>
BRANCH="feat/openapi-compliance-${REPO_SLUG}"
WORKTREE="/home/byron/dev/${REPO_SLUG}-worktrees/openapi"

# Clone if not already present locally
REPO_PATH="/home/byron/dev/${REPO_SLUG}"
if [ ! -d "$REPO_PATH" ]; then
    gh repo clone "${ORG}/${REPO_SLUG}" "$REPO_PATH"
fi

cd "$REPO_PATH"
git worktree add "$WORKTREE" -b "$BRANCH" HEAD 2>/dev/null || \
    git worktree add "$WORKTREE" "$BRANCH"
```

#### 2b. Dispatch openapi-code-enricher

Dispatch with:
```
Target repo: <WORKTREE absolute path>
Entry points: <api.entryPoints list>
Frameworks: <api.frameworks list>
```

Wait for completion. If it exits with an error, log the failure, remove the worktree,
and stop the pipeline for this repo.

#### 2c. Dispatch api-development-agent

Dispatch with:
```
Mode: openapi-export
Target repo: <WORKTREE absolute path>
Frameworks: <api.frameworks list>
Entry points: <api.entryPoints list>
Output: docs/api/openapi.yaml and docs/api/postman-collection.json
```

The agent must generate both files in the worktree under `docs/api/`. Wait for
completion. If either file is absent after the run, log the failure and stop.

#### 2d. Dispatch postman-test-designer

Dispatch with:
```
Target repo: <WORKTREE absolute path>
Postman collection: docs/api/postman-collection.json
Repo slug: <name>
Org: <org>
```

The agent will inject test scripts, run newman on docker-host, write the CI workflow,
and return a JSON status:
```json
{"status": "pass|fail", "newman_report_path": "<path>", "failures": []}
```

If `status == "fail"`, log failures, leave worktree intact for inspection, update
`api.testStatus = "failing"` in the catalog, and stop.

#### 2e. Dispatch github-workflow-agent

Dispatch with:
```
Action: open-pr
Worktree: <WORKTREE absolute path>
Repo: <ORG>/<REPO_SLUG>
Branch: <BRANCH>
Base: main
Title: "docs(api): add OpenAPI spec, Postman collection, and API tests"
Body: |
  ## Summary
  - Enriched FastAPI routes for full OpenAPI coverage
  - Generated docs/api/openapi.yaml
  - Generated docs/api/postman-collection.json
  - Added .github/workflows/postman-api-tests.yml
  - Newman validation passed on docker-host

  ## Newman results
  <embed newman_report_path contents or link>
```

#### 2f. Update catalog

After a successful PR is opened, update the repo's entry in
`/home/byron/dev/.claude/docs/reference/github-repos.json`:

```json
"api": {
  "servesApi": true,
  "frameworks": [...],
  "entryPoints": [...],
  "externalClients": [...],
  "openApiSpec": true,
  "postmanCollection": true,
  "lastAudited": "<today's date YYYY-MM-DD>",
  "testStatus": "passing"
}
```

### Step 3: Summary

After all repos are processed, print a summary table:

```
Repo                  | Status  | PR
----------------------|---------|----
audio_processor       | PASS    | #42
rag_processor         | PASS    | #17
homelab-infra         | FAIL    | --  (newman: 2 assertion failures)
```

## Error handling

- If `api.servesApi` is absent or false: skip with `SKIP (servesApi: false)`.
- If the worktree already exists from a prior run: reuse it; do not recreate.
- If any subagent returns an error: stop that repo's pipeline, log the error,
  continue with remaining repos.
- Never open a PR if newman reported failures.
```

- [ ] **Step 2: Verify frontmatter parses cleanly**

```bash
python3 -c "
import re
content = open('/home/byron/dev/.claude/.claude/agents/openapi-compliance-agent.md').read()
fm = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
import yaml; print(yaml.safe_load(fm.group(1)))
"
```

Expected: dict with name, description, model, tools keys; no errors.

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/openapi-compliance-agent.md
git commit -m "feat(agents): add openapi-compliance-agent orchestrator"
```

---

## Task 5: Create openapi-code-enricher.md

**Files:**
- Create: `.claude/agents/openapi-code-enricher.md`

- [ ] **Step 1: Create the agent file**

```markdown
---
name: openapi-code-enricher
description: >
  FastAPI OpenAPI enrichment specialist. Works in a repo worktree. Reads all
  FastAPI route files (app.get/post/put/delete/patch, APIRouter decorators) and
  applies a defined set of enrichments: app-level metadata in the FastAPI()
  constructor, per-route summary/docstring/response_model/status_code/responses/
  tags. Creates Pydantic models for untyped request bodies. Does NOT touch
  business logic, database calls, authentication implementations, or complete
  type annotations. Commits with message "docs(openapi): enrich FastAPI routes".
model: sonnet
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
---

FastAPI OpenAPI enrichment specialist. Operates entirely within the provided worktree.

## Inputs (from orchestrator prompt)

```
Target repo: <absolute path to worktree>
Entry points: <list of FastAPI app entry point file paths relative to worktree>
Frameworks: <list, e.g. ["fastapi"]>
```

## Enrichment pass

### Step 1: Discover all route files

Starting from each entry point, find:
1. Files containing `FastAPI(` -- the app constructor
2. Files containing `APIRouter(` -- sub-routers
3. Files containing `@<var>.(get|post|put|delete|patch|options|head)(` -- route decorators

Use `grep -rn` on the worktree `src/` and `services/` directories.

### Step 2: App-level metadata

In each file containing `FastAPI(`, update the constructor call to include these
keyword arguments if absent:

```python
app = FastAPI(
    title="<Human-readable app name from directory or pyproject.toml>",
    description="<One-paragraph description of what this API does>",
    version="<read from pyproject.toml [project].version, else '0.1.0'>",
    contact={"name": "Byron Williams", "email": "byronawilliams@gmail.com"},
    openapi_tags=[],  # populate after discovering all route tags (Step 5)
)
```

Read `pyproject.toml` at the repo root if it exists. Extract `[project].version` or
`[tool.poetry.version]`.

Read `LICENSE` at the repo root if it exists. Add:
```python
    license_info={"name": "<first line of LICENSE file that names the license>"},
```

### Step 3: Per-route enrichment

For each route decorator (`@app.get`, `@router.post`, etc.), inspect the decorated
function and apply these enrichments only when the field is absent:

| Missing element | Action |
|-----------------|--------|
| `summary` | Add to decorator: `summary="<function name in Title Case>"` |
| `status_code` | GET/DELETE: `200`; void DELETE/POST: `204`; POST creating: `201`; default: `200` |
| `responses` | Add `{422: {"description": "Validation error"}, 500: {"description": "Internal server error"}}` |
| `tags` | Derive from route prefix (e.g., `/health/...` -> `["health"]`) or file name |
| Function docstring | Add one describing params, return value, and side effects |
| `response_model` | See Step 4 |

### Step 4: response_model and Pydantic models

For each route function:
- If return type is already a Pydantic model class: add `response_model=<ClassName>` to decorator.
- If return type is `dict`, `Any`, or absent: create a named Pydantic model.

When creating a model, inspect the function body to infer field names and types.
Place the model in a `models.py` file in the same directory as the route file.
Import it at the top of the route file.

Example: for a function `get_health()` returning `{"status": str, "version": str}`:

```python
# models.py
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    version: str
```

```python
# routes file
from .models import HealthResponse

@app.get("/health", response_model=HealthResponse, status_code=200, ...)
def get_health() -> HealthResponse:
    ...
```

### Step 5: Populate openapi_tags

After processing all routes, collect the unique tags used across all route files.
Update the `openapi_tags=[]` list in the `FastAPI()` constructor:

```python
openapi_tags=[
    {"name": "health", "description": "Service health and readiness endpoints"},
    {"name": "inference", "description": "Model inference endpoints"},
    # one entry per unique tag
]
```

### Step 6: Commit

```bash
cd <worktree path>
git add -A
git commit -m "docs(openapi): enrich FastAPI routes for OpenAPI coverage"
```

## What this agent does NOT touch

- Business logic, database calls, authentication implementations
- Type annotations that are already complete and correct
- Any file not containing FastAPI route definitions
- Flask routes (handled separately if present)
```

- [ ] **Step 2: Verify frontmatter**

```bash
python3 -c "
import re
content = open('/home/byron/dev/.claude/.claude/agents/openapi-code-enricher.md').read()
fm = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
import yaml; print(yaml.safe_load(fm.group(1)))
"
```

Expected: dict with name, description, model, tools; no errors.

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/openapi-code-enricher.md
git commit -m "feat(agents): add openapi-code-enricher FastAPI enrichment specialist"
```

---

## Task 6: Create postman-test-designer.md

**Files:**
- Create: `.claude/agents/postman-test-designer.md`

- [ ] **Step 1: Create the agent file**

```markdown
---
name: postman-test-designer
description: >
  Postman test design, newman execution on docker-host, and CI workflow specialist.
  Reads docs/api/postman-collection.json in the worktree, injects pre-request
  scripts and test assertions into each request, adds negative test cases,
  runs newman on docker-host, writes .github/workflows/postman-api-tests.yml,
  and returns a JSON status object. Requires docs/api/postman-collection.json
  to already exist. Stops the pipeline without opening a PR if any newman
  assertion fails.
model: sonnet
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
---

Postman test design, newman execution, and CI workflow agent.

## Inputs (from orchestrator prompt)

```
Target repo: <absolute path to worktree>
Postman collection: docs/api/postman-collection.json
Repo slug: <name>
Org: <org>
```

## Step 1: Test script injection

Read `<worktree>/docs/api/postman-collection.json`. For every request item in the
collection, inject the following scripts into the `event` array.

### Pre-request script (inject into each request)

```javascript
// Set base URL from environment or default to localhost
pm.environment.set("base_url", pm.environment.get("base_url") || "http://localhost:8000");

// Set auth token if the route description contains "auth" or "bearer"
if (pm.request.headers.has("Authorization")) {
    pm.environment.set("auth_token", pm.environment.get("auth_token") || "test-token");
    pm.request.headers.upsert({key: "Authorization", value: "Bearer {{auth_token}}"});
}
```

### Test assertions (inject into each request)

Derive the expected status code from the request's `response` array in the collection,
or from the route decorator `status_code` field found in the OpenAPI spec.
Fall back to 200 for GET, 201 for POST, 204 for DELETE.

```javascript
// Status code
pm.test("Status code is {{expected_status}}", function () {
    pm.response.to.have.status({{expected_status}});
});

// Response time
pm.test("Response time under 2000ms", function () {
    pm.expect(pm.response.responseTime).to.be.below(2000);
});

// Content-Type (skip for 204 No Content)
if ({{expected_status}} !== 204) {
    pm.test("Content-Type is application/json", function () {
        pm.expect(pm.response.headers.get("Content-Type")).to.include("application/json");
    });
}

// Response structure (check top-level keys from response_model schema)
pm.test("Response body has expected structure", function () {
    const body = pm.response.json();
    // Validate against expected fields from OpenAPI response_model
    {{expected_field_assertions}}
});
```

Replace `{{expected_field_assertions}}` with actual field checks derived from the
OpenAPI spec's `response_model` schema. Example for a `HealthResponse` model:
```javascript
    pm.expect(body).to.have.property("status");
    pm.expect(body).to.have.property("version");
```

### Negative test cases

For each request that accepts a request body, add a sibling request with suffix
`(invalid payload)`:
- Method: same as original
- URL: same
- Body: `{}` (empty object, will fail Pydantic validation)
- Test assertion: `pm.response.to.have.status(422);`

## Step 2: Newman execution on docker-host

### 2a. Locate the service configuration

Read `<worktree>/docker-compose.yml` if present. Extract:
- `services.<service>.image` -- Docker image name
- `services.<service>.ports` -- port mapping

Read `<worktree>/.env.example` if present. Extract `DOCKER_HOST` or `API_HOST` if set.

If neither file specifies the docker-host address, emit:
```
BLOCK: docker-host address unknown.
Set DOCKER_HOST in .env.example or docker-compose.yml before proceeding.
Return to orchestrator with status=blocked.
```

### 2b. Start the API container on docker-host

```bash
DOCKER_HOST="ssh://byron@docker-host"
IMAGE="<image name from docker-compose.yml>"

# Pull latest image
docker -H "$DOCKER_HOST" pull "$IMAGE"

# Start container on a random host port to avoid conflicts
CONTAINER_ID=$(docker -H "$DOCKER_HOST" run -d \
    --name "newman-test-$(date +%s)" \
    -p 0:8000 \
    "$IMAGE")

# Get the assigned host port
HOST_PORT=$(docker -H "$DOCKER_HOST" inspect "$CONTAINER_ID" \
    --format '{{(index (index .NetworkSettings.Ports "8000/tcp") 0).HostPort}}')

echo "API running at docker-host:${HOST_PORT}"
```

Wait up to 15 seconds for the container to be ready:
```bash
for i in $(seq 1 15); do
    curl -sf "http://docker-host:${HOST_PORT}/health" && break
    sleep 1
done
```

### 2c. Run newman

```bash
newman run <worktree>/docs/api/postman-collection.json \
    --env-var "base_url=http://docker-host:${HOST_PORT}" \
    --reporters cli,json \
    --reporter-json-export /tmp/newman-results-<repo-slug>.json \
    --bail
```

### 2d. Tear down the test container

```bash
docker -H "$DOCKER_HOST" rm -f "$CONTAINER_ID"
```

### 2e. Evaluate results

Read `/tmp/newman-results-<repo-slug>.json`. Check `run.stats.assertions.failed`.

If `failed > 0`:
- Print each failing assertion: collection item name, test name, error message
- Return to orchestrator:
  ```json
  {"status": "fail", "newman_report_path": "/tmp/newman-results-<repo-slug>.json",
   "failures": ["<item>: <test>: <error>", ...]}
  ```
- Do NOT proceed to Step 3.

If `failed == 0`: proceed to Step 3.

## Step 3: Write the CI workflow

Write the following to `<worktree>/.github/workflows/postman-api-tests.yml`:

```yaml
name: Postman API Tests

on:
  pull_request:
    paths:
      - "src/**"
      - "docs/api/**"
  push:
    branches: [main]
    paths:
      - "src/**"
      - "docs/api/**"

jobs:
  api-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build API image
        run: docker build -t api-test-image .

      - name: Start API container
        run: |
          docker run -d --name api-test -p 8000:8000 api-test-image
          sleep 5

      - name: Install newman
        run: npm install -g newman newman-reporter-html

      - name: Run Postman API tests
        run: |
          newman run docs/api/postman-collection.json \
            --env-var "base_url=http://localhost:8000" \
            --reporters cli,html \
            --reporter-html-export newman-report.html \
            --bail

      - name: Upload newman report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: newman-report
          path: newman-report.html

      - name: Stop API container
        if: always()
        run: docker rm -f api-test
```

## Step 4: Commit and return status

```bash
cd <worktree path>
git add docs/api/postman-collection.json .github/workflows/postman-api-tests.yml
git commit -m "test(api): add Postman test scripts and CI workflow"
```

Return to orchestrator:
```json
{
  "status": "pass",
  "newman_report_path": "/tmp/newman-results-<repo-slug>.json",
  "failures": []
}
```
```

- [ ] **Step 2: Verify frontmatter**

```bash
python3 -c "
import re
content = open('/home/byron/dev/.claude/.claude/agents/postman-test-designer.md').read()
fm = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
import yaml; print(yaml.safe_load(fm.group(1)))
"
```

Expected: dict with name, description, model, tools; no errors.

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/postman-test-designer.md
git commit -m "feat(agents): add postman-test-designer for test injection, newman, and CI"
```

---

## Task 7: Add applies_to evaluator and API checks to check-repo-compliance.py

**Files:**
- Modify: `scripts/check-repo-compliance.py` (currently 213 lines)

The script currently hardcodes five GitHub API drift checks (CI-020, CI-021, BP-4, BP-5, BP-6).
This task adds:
1. A `load_catalog()` helper that reads `github-repos.json`
2. An `applies_to_api_repos(org, repo, catalog)` guard
3. Five new API-* checks in the `RepoResult` dataclass and `check_repo()` function

- [ ] **Step 1: Read the current file to understand the exact structure**

```bash
head -60 /home/byron/dev/.claude/scripts/check-repo-compliance.py
```

Note the existing `RepoResult` dataclass fields and the structure of `check_repo()`.

- [ ] **Step 2: Add catalog loader and applies_to guard**

After the existing import block (around line 15), add:

```python
import datetime
from pathlib import Path

CATALOG_PATH = Path(__file__).parent.parent / "docs/reference/github-repos.json"


def load_catalog() -> dict:
    """Load github-repos.json. Returns empty dict if file absent."""
    if not CATALOG_PATH.exists():
        return {}
    with CATALOG_PATH.open() as f:
        data = json.load(f)
    return {f"{r['org']}/{r['name']}": r for r in data.get("repos", [])}


def applies_to_api_repos(org: str, repo: str, catalog: dict) -> bool:
    """Return True if the repo serves an API (api.servesApi == true)."""
    entry = catalog.get(f"{org}/{repo}", {})
    return bool(entry.get("api", {}).get("servesApi", False))
```

- [ ] **Step 3: Add five new fields to RepoResult dataclass**

Find the `@dataclass` definition for `RepoResult` and add these fields:

```python
    api_001_openapi_spec: str = "N/A"       # docs/api/openapi.yaml present
    api_002_postman_collection: str = "N/A" # docs/api/postman-collection.json present
    api_003_ci_workflow: str = "N/A"        # .github/workflows/postman-api-tests.yml present
    api_004_last_audited: str = "N/A"       # api.lastAudited within 90 days
    api_005_test_status: str = "N/A"        # api.testStatus == "passing"
```

- [ ] **Step 4: Add API check logic inside check_repo()**

At the end of the `check_repo()` function body, before the `return result` line, add:

```python
    # API-001..005: only run for repos with api.servesApi=true
    if applies_to_api_repos(org, repo, catalog):
        slug = f"{org}/{repo}"
        catalog_entry = catalog.get(slug, {})
        api_info = catalog_entry.get("api", {})

        # API-001: openapi.yaml present
        result.api_001_openapi_spec = (
            "PASS" if file_exists(org, repo, "docs/api/openapi.yaml") else "FAIL"
        )

        # API-002: postman-collection.json present
        result.api_002_postman_collection = (
            "PASS" if file_exists(org, repo, "docs/api/postman-collection.json") else "FAIL"
        )

        # API-003: CI workflow present
        result.api_003_ci_workflow = (
            "PASS"
            if file_exists(org, repo, ".github/workflows/postman-api-tests.yml")
            else "FAIL"
        )

        # API-004: lastAudited within 90 days
        last_audited = api_info.get("lastAudited")
        if last_audited is None:
            result.api_004_last_audited = "FAIL"
        else:
            try:
                audited_date = datetime.date.fromisoformat(last_audited)
                days_ago = (datetime.date.today() - audited_date).days
                result.api_004_last_audited = "PASS" if days_ago <= 90 else "FAIL"
            except ValueError:
                result.api_004_last_audited = "FAIL"

        # API-005: testStatus == "passing"
        test_status = api_info.get("testStatus")
        result.api_005_test_status = "PASS" if test_status == "passing" else "FAIL"
```

- [ ] **Step 5: Pass catalog to check_repo()**

Update the `check_repo` signature to accept catalog:

```python
def check_repo(org: str, repo: str, catalog: dict) -> RepoResult:
```

In `main()` (or wherever `check_repo` is called), load the catalog once and pass it:

```python
catalog = load_catalog()
# ... for each repo:
result = check_repo(org, repo, catalog)
```

- [ ] **Step 6: Run pre-commit to validate**

```bash
cd /home/byron/dev/.claude
pre-commit run ruff --files scripts/check-repo-compliance.py
pre-commit run ruff-format --files scripts/check-repo-compliance.py
```

Fix any lint errors before continuing.

- [ ] **Step 7: Smoke test the script**

```bash
python3 scripts/check-repo-compliance.py --help 2>&1 | head -5
# or run a quick syntax check:
python3 -m py_compile scripts/check-repo-compliance.py && echo "SYNTAX OK"
```

Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add scripts/check-repo-compliance.py
git commit -m "feat(compliance): add applies_to evaluator and API-001..005 checks"
```

---

## Task 8: Update repo-compliance SKILL.md

**Files:**
- Modify: `.claude/skills/repo-compliance/SKILL.md`

Two changes:
1. Add `api` row to the Domain Agents table (line ~84).
2. Add `applies_to` dispatch note below the table.
3. Update the skill's description frontmatter to mention API domain.

- [ ] **Step 1: Update the frontmatter description**

Find the `description:` block at the top of `SKILL.md` and append to it:

```yaml
description: >
  Repo compliance coordinator. Audits any repository against the standards
  manifest, presents findings by severity, applies approved remediations, and
  runs the retrospective. Interactive mode: full audit-approve-remediate-PR
  flow. Scheduled mode: report-only for org-wide sweeps.
  Covers the API domain (API-001..005) for repos where api.servesApi is true;
  API checks are skipped silently for non-API repos.
  Triggers on: /repo-audit, repo audit, compliance check, standards audit.
```

- [ ] **Step 2: Add api row to the Domain Agents table**

Find the Domain Agents table (the `| Domain | Agent | Checks |` table) and add a
row after the `mkdocs` row:

```
| api | `openapi-compliance-auditor` (via check-repo-compliance.py) | API-001..005 (applies_to: api_repos; skip when api.servesApi is false) |
```

- [ ] **Step 3: Add applies_to dispatch note below the table**

After the Domain Agents table, add:

```markdown
### API Domain: applies_to Conditional

Before dispatching API-domain checks, read `api.servesApi` from the target repo's
catalog entry (`docs/reference/github-repos.json`). If absent or `false`, skip all
API-* checks without raising FINDINGs; log `SKIP (api.servesApi: false)` in the audit
summary. API-* checks run only for repos where `api.servesApi: true`.

API-001 through API-003 are evaluated by `scripts/check-repo-compliance.py` via
the GitHub Contents API. API-004 and API-005 read from the catalog directly
(fields set by the openapi-compliance-agent after a successful run).
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/repo-compliance/SKILL.md
git commit -m "feat(compliance): add API domain dispatch and applies_to conditional to repo-audit skill"
```

---

## Task 9: Register new agents and finalize

**Files:**
- Modify: `AGENTS-AND-SKILLS.md`

- [ ] **Step 1: Read the current agent catalog format**

```bash
grep -n "api-development-agent\|github-workflow-agent" AGENTS-AND-SKILLS.md | head -6
```

Note the exact format used for existing agent entries (section heading, description, tools line).

- [ ] **Step 2: Add the three new agent entries**

Find the `## Agents` section of `AGENTS-AND-SKILLS.md`. Add entries for the three
new agents following the exact format of existing entries. Example format (match the
surrounding entries exactly):

```markdown
### openapi-compliance-agent
Orchestrates the full OpenAPI compliance pipeline for API-serving repos.
Dispatches openapi-code-enricher, api-development-agent, postman-test-designer,
and github-workflow-agent sequentially per repo; runs repos in parallel for
/openapi-audit all. Updates the repo catalog on success.
**Tools:** Read, Write, Edit, Bash, Grep, Glob, Agent
**Invoke:** /openapi-audit <repo-slug> | /openapi-audit all

### openapi-code-enricher
Patches FastAPI route files for full OpenAPI coverage. Adds app-level metadata
to FastAPI() constructors, enriches route decorators (summary, tags, responses,
status_code, response_model), and creates Pydantic models for untyped request bodies.
**Tools:** Read, Write, Edit, Bash, Grep, Glob

### postman-test-designer
Injects pre-request scripts and test assertions into Postman collections, runs
newman on docker-host to validate the API, writes .github/workflows/postman-api-tests.yml,
and returns a pass/fail status to the orchestrator.
**Tools:** Read, Write, Edit, Bash, Grep, Glob
```

- [ ] **Step 3: Run pre-commit on all changed files**

```bash
pre-commit run --all-files
```

Fix any failures. The `no-em-dash` hook will catch any em-dashes in the new agent files.
The `validate-front-matter` hook will catch missing or invalid frontmatter fields.
The `markdownlint` hook will catch heading hierarchy issues.

- [ ] **Step 4: Commit**

```bash
git add AGENTS-AND-SKILLS.md
git commit -m "docs(catalog): register openapi-compliance-agent, openapi-code-enricher, postman-test-designer"
```

---

## Self-review pass

### Spec coverage check

| Spec requirement | Task |
|-----------------|------|
| `github-repos.json` catalog update -- `api` blocks | Task 1 + 2 |
| `_meta.idealEntry.api` section | Task 1 |
| `openapi-compliance-agent.md` (orchestrator) | Task 4 |
| `openapi-code-enricher.md` (enrichment specialist) | Task 5 |
| `postman-test-designer.md` (test design + newman + CI) | Task 6 |
| `standards-manifest.yaml` -- API domain, 5 checks, `applies_to` | Task 3 |
| `check-repo-compliance.py` -- `applies_to` evaluator | Task 7 |
| `repo-compliance` skill description update | Task 8 |
| Per-repo PRs (agent output, not implementation) | Produced when orchestrator runs |

All spec requirements are covered.

### Type consistency check

- `applies_to_api_repos(org, repo, catalog)` defined in Task 7, used in Task 7 only -- consistent.
- `RepoResult.api_001_openapi_spec` ... `api_005_test_status` defined and used in Task 7 -- consistent.
- Agent frontmatter `name` fields match the names used in the orchestrator dispatch calls in Task 4 -- all three names match.

### Placeholder check

No "TBD", "TODO", or "implement later" strings present in this plan.
