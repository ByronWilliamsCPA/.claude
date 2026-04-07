# Canonical Package Registry

> **Status**: ✅ Active | Core Standard | **Version**: 1.1.0 | **Last Updated**: 2026-04-07
>
> Authoritative package choices across all Python projects. When Claude suggests a package,
> it must come from the **Canonical** column. Deviations require explicit justification in
> the project's `CLAUDE.md` under a `## Package Overrides` section.

## Google Assured OSS Policy

**Prefer packages available in Google Assured Open Source Software (AOSS).** When two
packages satisfy the same requirement, choose the one included in AOSS. AOSS packages are
scanned, patched, and distributed by Google through Artifact Registry.

Packages marked **✓ AOSS** below are confirmed present in the program per
[the supported packages list](https://cloud.google.com/assured-open-source-software/docs/supported-packages).
Verify the current list with:

```bash
# Requires gcloud auth
gcloud artifacts packages list \
  --repository=cloud-aoss-python \
  --location=us \
  --project=cloud-aoss \
  --format="value(name)"
```

Or via REST (requires an access token):

```bash
curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://artifactregistry.googleapis.com/v1/projects/cloud-aoss/locations/us/repositories/cloud-aoss-python/pythonPackages"
```

## Override Policy

Projects may override a canonical choice only when:

1. The project existed before this standard (legacy projects retain grandfathered packages)
2. A specific technical constraint makes the canonical choice impossible (document why)
3. The project is an explicit evaluation of an alternative package

Document the override in the project `CLAUDE.md`:

```markdown
## Package Overrides
- **HTTP**: Using `requests` instead of `httpx` — legacy service client, pre-dates standard
```

## Quality Toolchain

**qlty** is the unified quality runner across all projects. It is a standalone CLI (not a
Python package) configured via `.qlty/qlty.toml`. Always invoke quality checks through
qlty rather than calling ruff, basedpyright, or other tools directly.

```bash
qlty check          # Run all enabled checks
qlty check --fix    # Run with auto-fix where supported
qlty smells         # Show complexity/maintainability issues
qlty plugins list   # Show active plugins
```

ruff remains a Python dev dependency (configured in `pyproject.toml`) because qlty reads
its configuration from there. Security tools (bandit, detect-secrets) run via pre-commit
hooks rather than qlty plugins.

---

## Package Management

| Category | Canonical | Avoid | Notes |
| --- | --- | --- | --- |
| Dependency/env manager | `uv` | pip, virtualenv, pipenv | New projects only |
| Build backend | `hatchling` ✓ AOSS | `setuptools` ✓ AOSS | For uv projects |
| Build backend (poetry) | `poetry-core` | — | Existing poetry projects only |
| Template scaffolding | `cookiecutter` ✓ AOSS | — | |
| Template sync | `cruft` | — | Keeps projects in sync with template |

---

## Web & HTTP

| Category | Canonical | Avoid | Notes |
| --- | --- | --- | --- |
| HTTP client | `httpx` ✓ AOSS | `requests` ✓ AOSS, `aiohttp` ✓ AOSS | httpx handles sync and async; replaces both |
| Web framework | `fastapi` ✓ AOSS | flask, django | For REST/async APIs |
| ASGI server | `uvicorn[standard]` ✓ AOSS | gunicorn (WSGI) | Pair with fastapi |
| Rate limiting | `slowapi` | — | FastAPI-compatible; not in AOSS |
| File uploads | `python-multipart` ✓ AOSS | — | Required for FastAPI form/file endpoints |
| Async file I/O | `aiofiles` ✓ AOSS | — | Non-blocking file reads |
| Retry logic | `tenacity` ✓ AOSS | urllib3 retry, custom loops | Exponential backoff with jitter |
| HTML parsing | `beautifulsoup4` + `lxml` ✓ AOSS | html.parser | Use `lxml` parser for speed; bs4 not in AOSS |
| Safe XML parsing | `defusedxml` ✓ AOSS | stdlib `xml.etree` | Required for untrusted XML input |

---

## Data Validation & Configuration

| Category | Canonical | Avoid | Notes |
| --- | --- | --- | --- |
| Data validation / models | `pydantic` v2 ✓ AOSS | marshmallow, attrs | Required; v2 only |
| Settings / env loading | `pydantic-settings` | `python-dotenv` ✓ AOSS standalone | pydantic-settings not in AOSS; wraps dotenv |
| Template engine | `jinja2` ✓ AOSS | mako, chameleon | |

---

## Database

| Category | Canonical | Avoid | Notes |
| --- | --- | --- | --- |
| ORM | `sqlalchemy[asyncio]` v2 ✓ AOSS | tortoise-orm, peewee | Async mode; sync allowed for scripts |
| Migrations | `alembic` ✓ AOSS | yoyo, liquibase | Pair with SQLAlchemy |
| Async Postgres driver | `asyncpg` ✓ AOSS | `psycopg2-binary` ✓ AOSS | asyncpg is preferred for async |
| Sync Postgres driver | `psycopg[binary]` | `psycopg2-binary` ✓ AOSS | psycopg3; use only when sync required |
| Redis client | `redis` ✓ AOSS | aioredis (merged into redis) | Includes async support |
| Analytical SQL | `duckdb` | — | Not in AOSS |

---

## Task Queues & Scheduling

| Category | Canonical | Avoid | Notes |
| --- | --- | --- | --- |
| Async task queue | `arq` ✓ AOSS | `rq`, `celery` ✓ AOSS (for new projects) | Redis-backed, async-native |
| Complex workflows | `celery` ✓ AOSS | — | Only when arq lacks required features (beat, canvas, etc.) |
| Scheduled jobs | arq scheduled jobs or cron | `APScheduler` | Avoid APScheduler in new projects |

---

## Testing

| Category | Canonical | Avoid | Notes |
| --- | --- | --- | --- |
| Test runner | `pytest` ✓ AOSS | unittest | |
| Coverage | `pytest-cov` ✓ AOSS | coverage standalone | |
| Async tests | `pytest-asyncio` | anyio | Not in AOSS |
| Parallel execution | `pytest-xdist` ✓ AOSS | — | |
| Mocking | `pytest-mock` ✓ AOSS | `unittest.mock` directly | Cleaner fixtures |
| Property-based testing | `hypothesis` ✓ AOSS | — | |
| Test factories | `factory-boy` ✓ AOSS | — | |
| Fake data | `faker` ✓ AOSS | mimesis | |
| Time mocking | `freezegun` | — | Not in AOSS |
| Random test ordering | `pytest-randomly` | — | Not in AOSS |
| Benchmarks | `pytest-benchmark` | timeit in tests | Not in AOSS |
| Mutation testing | `mutmut` | — | Optional; critical modules only; not in AOSS |
| HTTP mocking (httpx) | `respx` | `responses` ✓ AOSS | `responses` is for `requests` only; respx not in AOSS |
| Redis mocking | `fakeredis` ✓ AOSS | — | |
| Browser testing | `playwright` + `pytest-playwright` | `selenium` ✓ AOSS | playwright not in AOSS; prefer over selenium |

---

## Code Quality

> **Runner**: All quality checks are invoked through **qlty** (`qlty check`), a standalone
> CLI configured via `.qlty/qlty.toml`. Do not invoke ruff, basedpyright, or other tools
> directly — use qlty. Security tools (bandit, detect-secrets) run via pre-commit hooks.

| Category | Canonical | Avoid | Notes |
| --- | --- | --- | --- |
| Quality runner | `qlty` CLI | direct tool invocations | Standalone CLI; not a Python package |
| Linting + formatting | `ruff` | `black`, `isort`, `flake8`, `pylint` | Not in AOSS; qlty reads config from pyproject.toml |
| Type checking | `basedpyright` | `mypy` ✓ AOSS | basedpyright not in AOSS but faster and stricter |
| Docstring coverage | `interrogate` ✓ AOSS | — | |
| Dead code | `vulture` | — | Not in AOSS |
| Pre-commit framework | `pre-commit` ✓ AOSS | manual hooks | |
| Task automation (new projects) | `tox` ✓ AOSS + `tox-uv` | `nox`, `Makefile` | tox 4 + pyproject.toml + tox-uv; see note below |
| Task automation (existing projects) | `nox` (grandfathered) | — | Do not migrate; nox stays until project is rewritten |
| nox + uv integration (legacy) | `nox-uv` | — | Existing nox projects only |

> **tox setup for new projects**: Install via `uv tool install tox --with tox-uv`. Configure
> in `pyproject.toml` under `[tool.tox]`. Use `runner = "uv-venv-lock-runner"` and
> `dependency_groups = ["dev"]` to read from `uv.lock`. Run with `tox -p auto` for parallel
> execution. Do **not** add tox or tox-uv to `[dependency-groups]` — tox is a system tool,
> not a project dependency.
>
> **Existing nox projects**: Do not migrate. nox stays in place until a project is rebuilt
> from the cookiecutter template. The compliance/SBOM sessions rely on Python function calls
> between sessions that tox cannot replicate without helper scripts — migration cost outweighs
> AOSS benefit for dev tooling.

---

## Security

| Category | Canonical | Avoid | Notes |
| --- | --- | --- | --- |
| Dependency vulnerabilities | `pip-audit` | `safety` | Neither in AOSS; exit code 64 = advisory found |
| SAST | `bandit[toml]` ✓ AOSS | — | Runs via pre-commit hook; `[toml]` extra required to read `[tool.bandit]` config from pyproject.toml |
| Secrets detection | `detect-secrets` ✓ AOSS | truffleHog | Runs via pre-commit hook |
| Cryptography primitives | `cryptography` ✓ AOSS | `pycryptodome` | |
| JWT | `pyjwt` | `python-jose` | Not in AOSS |
| GPG | `python-gnupg` ✓ AOSS | — | |

---

## Logging & Observability

| Category | Canonical | Avoid | Notes |
| --- | --- | --- | --- |
| Structured logging | `structlog` ✓ AOSS | `python-json-logger`, stdlib logging direct | |
| Error tracking | `sentry-sdk` ✓ AOSS | rollbar | Production services |
| Metrics | `prometheus-client` ✓ AOSS | statsd | |
| Tracing | `opentelemetry-api` ✓ AOSS + `opentelemetry-sdk` ✓ AOSS | — | Use when distributed tracing required |

---

## CLI & Terminal

| Category | Canonical | Avoid | Notes |
| --- | --- | --- | --- |
| CLI framework | `typer` ✓ AOSS | `click` ✓ AOSS (for new code) | Typer wraps click; prefer for new CLIs |
| Terminal output / formatting | `rich` ✓ AOSS | colorama, termcolor | Tables, panels, progress bars |

---

## Documentation

| Category | Canonical | Avoid | Notes |
| --- | --- | --- | --- |
| Docs site | `mkdocs-material` | `sphinx` (new projects) | Neither mkdocs nor mkdocs-material in AOSS |
| API autodocs | `mkdocstrings[python]` | — | Not in AOSS |
| Pydantic model docs | `griffe-pydantic` | — | Not in AOSS |

---

## Data & Science

| Category | Canonical | Avoid | Notes |
| --- | --- | --- | --- |
| Tabular data | `pandas` ✓ AOSS | — | |
| Numerical computing | `numpy` ✓ AOSS | — | |
| High-perf DataFrames | `polars` | — | Allowed for perf-sensitive paths; not in AOSS |
| Statistical modeling | `scipy` ✓ AOSS, `statsmodels` ✓ AOSS | — | |
| ML | `scikit-learn` ✓ AOSS | — | |
| YAML | `pyyaml` ✓ AOSS | ruamel.yaml | |
| Excel | `openpyxl` ✓ AOSS | `xlrd` (read-only legacy), `xlsxwriter` | openpyxl handles both read and write |
| Date parsing | `python-dateutil` ✓ AOSS | pendulum | stdlib `datetime` + dateutil covers most cases |
| In-memory caching | `cachetools` ✓ AOSS | — | |
| Frontmatter parsing | `python-frontmatter` | — | Not in AOSS |

---

## AI / LLM

| Category | Canonical | Avoid | Notes |
| --- | --- | --- | --- |
| Claude / Anthropic | `anthropic` | — | Primary LLM SDK; not in AOSS |
| OpenAI | `openai` ✓ AOSS | — | When OpenAI-specific features required |
| Google Gemini | `google-genai` | `google-generativeai` (deprecated) | Not in AOSS |
| Embeddings | `sentence-transformers` ✓ AOSS | — | Local embedding models |
| Vector store client | `qdrant-client` | — | Not in AOSS; external Qdrant at 192.168.1.16:6333 |
| Token counting | `tiktoken` | — | Not in AOSS; OpenAI tokenizer |
| MCP server SDK | `mcp` | — | Not in AOSS; Model Context Protocol |

---

## Infrastructure & Cloud

| Category | Canonical | Avoid | Notes |
| --- | --- | --- | --- |
| Google Cloud Storage | `google-cloud-storage` ✓ AOSS | — | |
| Google Auth | `google-auth` ✓ AOSS | — | |
| AWS | `boto3` ✓ AOSS | — | |
| Cloudflare | `cloudflare` | — | Not in AOSS |
| Docker SDK | `docker` ✓ AOSS | subprocess docker calls | |
| DNS | `dnspython` ✓ AOSS | — | |
| IaC scanning | `checkov` ✓ AOSS | — | |
| Git automation | `gitpython` ✓ AOSS | subprocess git calls | |

---

## Packages to Actively Replace

When touching existing code that uses these, migrate to the canonical alternative if the
change is in scope. Do not migrate as a drive-by.

| Package | Replace With | Reason |
| --- | --- | --- |
| `requests` | `httpx` | httpx handles async; drop-in for sync usage |
| `aiohttp` | `httpx` | httpx handles async natively with cleaner API |
| `black` | `ruff format` via qlty | ruff replaces black |
| `isort` | ruff `I` rules via qlty | ruff replaces isort |
| `flake8` | ruff via qlty | ruff replaces flake8 |
| `pylint` | ruff `PL` rules via qlty | ruff replaces pylint |
| `mypy` | `basedpyright` | faster, stricter, active development |
| `python-dotenv` (standalone) | `pydantic-settings` | settings already uses pydantic |
| `psycopg2-binary` | `asyncpg` / `psycopg[binary]` | asyncpg for async, psycopg3 for sync |
| `selenium` | `playwright` | modern, faster, better async support |
| `rq` | `arq` | async-native task queue |
| `APScheduler` | arq scheduled jobs | avoid extra scheduler in new services |
| `marshmallow` | `pydantic` v2 | pydantic covers same use cases |
| `responses` | `respx` | `responses` mocks `requests`; use `respx` for `httpx` |
| `sphinx` | `mkdocs-material` | simpler, better theme, markdown-native |
| `safety` | `pip-audit` | pip-audit is more actively maintained |
