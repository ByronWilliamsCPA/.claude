---
schema_type: common
title: OpenAPI Compliance Agent Design
status: published
owner: engineering
tags: [api, openapi, postman, agents, compliance, fastapi]
purpose: Design for a multi-agent pipeline that audits internal API repos, enriches FastAPI code for full OpenAPI coverage, exports importable specs and Postman collections, runs validation via Postman CLI on docker-host, wires up CI, and integrates into the repo-compliance audit system.
---

**Date**: 2026-05-07
**Status**: Approved
**Author**: Byron Williams

---

## Background

An API scan across all 46 repos (2026-05-07) confirmed ten repos that serve real internal
API endpoints, all using FastAPI (with two Flask services in `homelab-infra`). None of
these repos currently export an OpenAPI specification or a Postman collection. As a
result, Postman cannot import or test them, API contracts are undocumented, and there is
no automated gate to catch regressions in endpoint behavior.

This design specifies a multi-agent pipeline that:

- Enriches FastAPI route code to achieve full OpenAPI coverage (response models,
  summaries, tags, error responses)
- Exports `openapi.yaml` and a Postman Collection v2.1 JSON per repo
- Designs test scripts and validates them via Postman CLI (newman) on docker-host
- Adds a per-repo GitHub Actions workflow for ongoing test enforcement
- Opens a per-repo PR delivering all of the above
- Integrates into the repo-compliance audit system via new `API` domain checks

---

## Confirmed Internal API Repos

Repos with `servesApi: true` that the agent targets:

| Repo | Framework | Primary entry point |
|---|---|---|
| `audio_processor` | FastAPI | `src/audio_processor/api/__init__.py` |
| `dataset_dev` | FastAPI | `src/prepare_doc/main.py` |
| `exercise_competition` | FastAPI | `src/exercise_competition/main.py` |
| `foundry_unify` | FastAPI | `src/foundry_unify/api/health.py` |
| `fragrance_rater` | FastAPI | `site/planning/backend/app/main.py` |
| `homelab-infra` | FastAPI + Flask | `services/cloudflare-auth-validator/src/main.py`, `services/ai-text-detector/app/main.py`, `services/cert-enroll/app.py` |
| `image_detection` | FastAPI | `src/image_preprocessing_detector/api/app.py` |
| `rag_processor` | FastAPI | `src/rag_processor/main.py` |
| `uml-mcp-server` | MCP | `uml_mcp_server.py` |
| `zen-mcp-server` | MCP + FastAPI | `server.py`, `plugins/promptcraft_system/api_server.py` |

MCP-only repos (`uml-mcp-server`, `zen-mcp-server` main server) expose no HTTP routes and
are exempt from OpenAPI requirements. The FastAPI plugin in `zen-mcp-server` and all
FastAPI/Flask services in `homelab-infra` are in scope.

---

## Repo Catalog Update

### `github-repos.json` -- new `api` block per entry

Every repo entry gains an inline `api` block. The initial values come from the 2026-05-07
scan. The compliance agent updates `openApiSpec`, `postmanCollection`, `lastAudited`, and
`testStatus` after each run.

**API-serving repo:**
```json
"api": {
  "servesApi": true,
  "frameworks": ["fastapi"],
  "entryPoints": ["src/audio_processor/api/__init__.py"],
  "externalClients": ["requests", "sendgrid"],
  "openApiSpec": false,
  "postmanCollection": false,
  "lastAudited": null,
  "testStatus": null
}
```

**External-caller-only repo:**
```json
"api": {
  "servesApi": false,
  "externalClients": ["anthropic", "openai", "supabase"]
}
```

Repos with no API activity omit the `api` block entirely.

### `_meta.idealEntry` addition

```json
"api": {
  "_note": "Required for servesApi=true repos only. N/A for non-API repos.",
  "openApiSpec": true,
  "postmanCollection": true,
  "lastAudited": "<within 90 days>",
  "testStatus": "passing"
}
```

### Merge conflict resolution

The existing merge conflict at line 149 of `github-repos.json` (a trivial one-liner
about `mutation-testing.yml` in the `python-app` type profile) is resolved as part of
the catalog population edit pass that precedes any agent runs.

---

## Agent Architecture

Four sequential steps per repo; three new agent files, two existing agents reused.

```text
openapi-compliance-agent (orchestrator)
    │
    ├── Invocation
    │       /openapi-audit <repo-name>     -- single repo
    │       /openapi-audit all             -- all servesApi=true repos
    │
    ├── Creates: .worktrees/openapi-<repo-slug>
    │           branch: feat/openapi-compliance-<repo-slug>
    │
    ├── [sequential within each repo]
    │       │
    │       ├── 1. openapi-code-enricher       (new specialist)
    │       │        Patches FastAPI code in worktree
    │       │
    │       ├── 2. api-development-agent       (existing, reused)
    │       │        Exports openapi.yaml + Postman collection
    │       │
    │       ├── 3. postman-test-designer        (new specialist)
    │       │        Injects test scripts into collection
    │       │        Runs newman on docker-host
    │       │        Writes .github/workflows/postman-api-tests.yml
    │       │        Fails pipeline if newman reports failures
    │       │
    │       └── 4. github-workflow-agent        (existing, reused)
    │                Opens PR with newman results in description
    │
    └── [parallel across repos for /openapi-audit all]
            Each repo's full four-step pipeline runs concurrently
```

**Files created by this design:**

| File | Purpose |
|---|---|
| `.claude/agents/openapi-compliance-agent.md` | Orchestrator |
| `.claude/agents/openapi-code-enricher.md` | FastAPI code enrichment specialist |
| `.claude/agents/postman-test-designer.md` | Test design, newman execution, CI workflow |

---

## Subagent: `openapi-code-enricher`

Works entirely within the worktree. Reads all FastAPI route files and applies enrichments
in a defined order. Commits with message `docs(openapi): enrich FastAPI routes for
OpenAPI coverage`.

### App-level metadata (in the `FastAPI()` constructor file)

Adds or updates if absent:
- `title` -- human-readable app name
- `description` -- one-paragraph description of what the API does
- `version` -- reads from `pyproject.toml` if available, else `"0.1.0"`
- `contact` -- `{"name": "Byron Williams", "email": "byronawilliams@gmail.com"}`
- `license_info` -- reads `LICENSE` at repo root if present
- `openapi_tags` -- list built from tags discovered across all routes

### Per-route enrichment

For every `@app.get`, `@router.post`, and equivalents:

| Missing element | Action |
|---|---|
| `summary` | Inferred from function name (snake_case to Title Case) |
| Function docstring | Added describing inputs, outputs, and side effects |
| `response_model` | Inferred from return annotation; Pydantic model created if needed |
| `status_code` | 200 for GET/DELETE, 201 for POST, 204 for void POST/DELETE |
| `responses` | Adds 422 (validation error) and 500 (internal error) at minimum |
| `tags` | Grouping tag applied by route prefix or file name |

### Pydantic model creation

If a request body currently uses `dict`, `Any`, or has no type annotation, the enricher
creates a named Pydantic model in a `models.py` alongside the route file and replaces the
untyped parameter.

### What the enricher does NOT touch

Business logic, database calls, authentication implementations, or any type annotation
that is already complete and correct.

---

## Subagent: `api-development-agent` (reused)

After enrichment, this existing agent:

1. Generates `openapi.yaml` by importing the FastAPI app and calling `app.openapi()`, or
   by starting the app and fetching `/openapi.json` if static import is not possible
2. Converts the spec to `docs/api/postman-collection.json` (Postman Collection v2.1)
3. Saves both files under `docs/api/` in the worktree

---

## Subagent: `postman-test-designer`

### Step 1 -- Test script injection

For each request in the Postman collection:

**Pre-request script:**
- Sets `base_url` environment variable
- Sets `auth_token` from environment if the route requires authentication

**Test assertions per request:**
- Status code matches the route's documented `status_code`
- Response body JSON structure matches the `response_model` schema
- Response time under 2000ms
- `Content-Type: application/json` header present

**Negative test cases:**
- One additional request per route with an intentionally invalid payload
- Asserts 422 Unprocessable Entity is returned

### Step 2 -- Newman execution on docker-host

The subagent:

1. Reads docker-host SSH target from the repo's `.env.example` or `docker-compose.yml`;
   if neither specifies it, the orchestrator surfaces a prompt to the user before
   proceeding
2. Reads the Docker image name from `docker-compose.yml` or `Dockerfile`
3. SSHes to docker-host, starts the FastAPI app as a short-lived container
4. Runs newman against the enriched Postman collection
5. Captures the newman JSON results report
6. Tears down the test container
7. If any assertion fails: reports failures to the orchestrator, leaves the worktree
   intact for manual inspection, sets `testStatus: failing` in the catalog, and halts
   the pipeline (the PR does not open)
8. If all pass: proceeds to CI workflow generation

### Step 3 -- CI workflow

Writes `.github/workflows/postman-api-tests.yml` to the worktree:

- Triggers on PRs that touch `src/` or `docs/api/`
- Starts the API in a Docker container using the repo's image
- Runs newman against `docs/api/postman-collection.json`
- Fails the PR if any assertion fails
- Uploads the newman HTML report as a workflow artifact

The workflow uses the same Docker image and environment configuration as the local newman
run, ensuring local and CI results are consistent.

---

## Compliance Integration

### New `API` domain in `standards-manifest.yaml`

Five new checks gated by `applies_to: api_repos`. The compliance agent skips all
`API-*` checks silently for repos where `api.servesApi` is `false` or absent.

```yaml
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

### Supporting code changes

**`check-repo-compliance.py`:** Gains an `applies_to` evaluator. When a check specifies
`applies_to: api_repos`, the script reads `api.servesApi` from the repo's catalog entry
before running the check. Non-API repos skip `API-*` checks with no finding.

**`repo-compliance` skill:** Description updated to note it covers the `API` domain for
repos where `api.servesApi: true`.

### Post-run catalog update (on successful pipeline)

```json
"api": {
  "openApiSpec": true,
  "postmanCollection": true,
  "lastAudited": "<run date>",
  "testStatus": "passing"
}
```

This means the next compliance audit immediately shows the repo as green on
`API-001` through `API-005`.

---

## Deliverables Summary

| Deliverable | Type | Notes |
|---|---|---|
| `github-repos.json` catalog update | One-time edit | Populates `api` blocks from 2026-05-07 scan; resolves merge conflict |
| `openapi-compliance-agent.md` | New agent | Orchestrator |
| `openapi-code-enricher.md` | New agent | FastAPI enrichment specialist |
| `postman-test-designer.md` | New agent | Tests, newman, CI workflow |
| `standards-manifest.yaml` update | Standards edit | Adds `API` domain, 5 checks, `applies_to` field |
| `check-repo-compliance.py` update | Script edit | `applies_to` evaluator |
| Per-repo PRs (up to 10) | Agent output | One PR per API repo |

---

## Out of Scope

- MCP-only repos (`uml-mcp-server` main server, `zen-mcp-server` MCP layer) -- no HTTP
  routes, no OpenAPI requirement
- Repos where `servesApi: false` -- not touched by the compliance agent
- API authentication design -- the enricher documents existing auth, does not redesign it
- Breaking API changes -- the enricher only adds documentation, not new or changed behavior
- GraphQL APIs -- none present in the confirmed API repos
