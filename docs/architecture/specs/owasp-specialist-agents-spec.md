---
schema_type: common
title: "OWASP Specialist Agent System: Design Specification"
status: draft
owner: core-maintainer
purpose: "Design spec for six OWASP Top 10 specialist agents that review code and tests and generate missing security tests."
tags:
  - specifications
  - security
  - agents
  - architecture
---

**Project Codename:** Hephaestus-Aegis
**Version:** 1.0-DRAFT
**Author:** Byron
**Date:** 2026-03-15

---

## 1. Executive Summary

This specification defines a system of six OWASP Top 10 specialist agents,
each an expert on one complete OWASP Top 10 list. These agents operate in
three modes (code review, test review, and test generation) and integrate
with the existing Hephaestus-Anvil test coverage agent as callable
subagents. When the test-writer or test-reviewer agents encounter
security-relevant code, they dispatch to the appropriate specialist for
deep domain expertise rather than attempting shallow general-purpose
security assessment.

### Implementation status (verified against the tree 2026-07-20)

This is the original design spec. Most of it shipped; three sections did
not. Read the spec as design intent, not as a description of the current
tree, wherever this table says "not implemented".

| Spec section | Status | Evidence in tree |
|---|---|---|
| 2, 5.2-5.8 (six specialists) | Implemented | `.claude/agents/owasp-{web,api,llm,ml,agent,citizen}.md` |
| 5.1 (dispatcher) | Implemented | `.claude/agents/owasp-dispatch.md`, body matches this spec |
| 4 (directory layout) | Changed | agents live flat in `.claude/agents/`, not in an `owasp/` subdirectory; section 4 below is corrected to match |
| 6.1 (test-writer delegation) | Not implemented | `.claude/agents/test-writer.md` has no security-delegation section |
| 6.2 (test-reviewer checklist) | Implemented | `.claude/agents/test-reviewer.md` carries the OWASP checklist items |
| 7.4 (test-coverage Mode 4) | Implemented | `.claude/skills/test-coverage/SKILL.md`, "Mode 4: Security Audit" |
| 9 (`tests/security/` tree) | Not implemented | no `tests/security/` directory exists |
| 10 (pytest OWASP markers) | Not implemented | no `owasp_*` or `security` markers in `pyproject.toml` |
| 11 (rollout plan) | Historical | week-numbered plan from 2026-03; the specialists and dispatcher shipped |

The dispatcher is the `owasp-dispatch` agent. There is no `/owasp-audit`
command; invoke the agent directly or through `/test-coverage security`.

---

## 2. Agent Inventory

| Agent ID | OWASP List | Version | Categories | Primary Domain |
|----------|-----------|---------|------------|----------------|
| `owasp-web` | Top 10 Web Applications | 2025 | A01–A10 | Traditional AppSec |
| `owasp-llm` | Top 10 for LLM Applications | 2025 | LLM01–LLM10 | LLM-integrated apps |
| `owasp-agent` | Top 10 for Agentic Applications | 2026 | AG01–AG10 | Autonomous AI agents |
| `owasp-citizen` | Citizen Developer Top 10 | 2025 | CD01–CD10 | Low-code / AI-assisted dev |
| `owasp-api` | API Security Top 10 | 2023 | API01–API10 | REST/GraphQL APIs |
| `owasp-ml` | ML Security Top 10 | v0.3 | ML01–ML10 | ML training & serving |

---

## 3. Architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE HOST SESSION                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │     SKILL: test-coverage (orchestrator: Hephaestus-Anvil) │  │
│  │                                                            │  │
│  │  Dispatches to test-writer, test-reviewer, AND             │  │
│  │  OWASP specialists based on code domain detection          │  │
│  └────────┬──────────────┬──────────────┬─────────────────────┘  │
│           │              │              │                         │
│    ┌──────▼─────┐ ┌──────▼─────┐ ┌─────▼──────────────┐        │
│    │ test-writer │ │test-reviewer│ │ OWASP Dispatcher   │        │
│    │             │ │            │ │                     │        │
│    │ Calls OWASP │ │Calls OWASP │ │ Detects which      │        │
│    │ specialists │ │specialists │ │ lists apply to the  │        │
│    │ when writing│ │for security│ │ target codebase     │        │
│    │ security    │ │checklist   │ │ and routes to       │        │
│    │ tests       │ │items       │ │ specialists         │        │
│    └─────────────┘ └────────────┘ └──────┬──────────────┘        │
│                                          │                       │
│    ┌─────────────────────────────────────┼────────────────────┐  │
│    │          SPECIALIST AGENT POOL      │                    │  │
│    │                                     ▼                    │  │
│    │  ┌───────────┐  ┌───────────┐  ┌───────────┐           │  │
│    │  │ owasp-web │  │ owasp-llm │  │owasp-agent│           │  │
│    │  │ A01–A10   │  │ LLM01–10  │  │ AG01–AG10 │           │  │
│    │  │ Web 2025  │  │ LLM 2025  │  │ Agent 2026│           │  │
│    │  └───────────┘  └───────────┘  └───────────┘           │  │
│    │  ┌───────────┐  ┌───────────┐  ┌───────────┐           │  │
│    │  │owasp-     │  │ owasp-api │  │ owasp-ml  │           │  │
│    │  │citizen    │  │ API01–10  │  │ ML01–ML10 │           │  │
│    │  │ CD01–CD10 │  │ API 2023  │  │ ML v0.3   │           │  │
│    │  └───────────┘  └───────────┘  └───────────┘           │  │
│    └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.1 Dispatch Logic

The orchestrator detects which OWASP lists apply to a project based on
codebase signals:

| Signal | Detected Via | Specialists Activated |
|--------|-------------|---------------------|
| HTTP framework (FastAPI, Flask, Django) | `pyproject.toml` deps, imports | `owasp-web`, `owasp-api` |
| LLM SDK (anthropic, openai, litellm, openrouter) | `pyproject.toml` deps, imports | `owasp-llm` |
| Agent framework (langchain agents, Claude tools, MCP) | imports, `.claude/` dir | `owasp-agent` |
| ML training (torch, tensorflow, transformers, sklearn) | `pyproject.toml` deps | `owasp-ml` |
| Low-code/AI-assisted indicators | `.cursor/`, `v0` artifacts, generated markers | `owasp-citizen` |
| Authentication/auth modules | `auth/`, `login`, JWT imports | `owasp-web` (A01, A07 focus) |
| Database access (SQLAlchemy, psycopg2) | imports | `owasp-web` (A03, A05 focus) |

**Default:** `owasp-web` is ALWAYS activated: every project needs
traditional AppSec. Other specialists are activated based on detection.

### 3.2 Operating Modes

Each specialist supports three modes invoked via argument:

```html
review-code <path>    : Scan source code for vulnerabilities
review-tests <path>   : Audit tests for security coverage gaps
generate <path>       : Produce missing security tests
```

All three modes produce structured output referencing specific OWASP
category IDs for traceability.

---

## 4. Directory Structure

```text
.claude/
├── agents/
│   ├── test-writer.md                # Existing (delegation section not added)
│   ├── test-reviewer.md              # Existing: carries the OWASP checklist
│   ├── owasp-dispatch.md             # Routes to the correct specialists
│   ├── owasp-web.md                  # Web Applications Top 10 (2025)
│   ├── owasp-llm.md                  # LLM Applications Top 10 (2025)
│   ├── owasp-agent.md                # Agentic Applications Top 10 (2026)
│   ├── owasp-citizen.md              # Citizen Developer Top 10 (2025)
│   ├── owasp-api.md                  # API Security Top 10 (2023)
│   └── owasp-ml.md                   # ML Security Top 10 (v0.3)
└── skills/
    └── test-coverage/
        └── SKILL.md                  # Mode 4 dispatches to the specialists
```

The original design placed the six specialists in an `agents/owasp/`
subdirectory. They ship flat in `.claude/agents/` instead, because Claude
Code discovers agents by filename in that directory.

---

## 5. Agent Definitions

### 5.1 OWASP Dispatcher Agent

**Location:** `.claude/agents/owasp-dispatch.md`

```markdown
# OWASP Specialist Dispatcher

You are a security triage agent. Your role is to analyze a codebase or
file set and determine which OWASP Top 10 specialist agents should be
invoked. You do NOT perform security analysis yourself: you route to
the correct specialists.

## Detection Procedure

1. Read pyproject.toml (or requirements.txt, package.json) for dependencies
2. Scan source imports in the target path using Grep/Glob
3. Check for framework indicators (.claude/, MCP configs, Dockerfile, etc.)
4. Produce a dispatch plan listing which specialists to invoke and why

## Dispatch Rules

- owasp-web: ALWAYS include. Every project needs web/AppSec review.
- owasp-api: Include if any HTTP framework, REST endpoints, or API
  route decorators are detected.
- owasp-llm: Include if any LLM SDK (anthropic, openai, litellm,
  langchain, openrouter, transformers with pipeline("text-generation"))
  is imported or configured.
- owasp-agent: Include if agent orchestration (langchain agents, Claude
  tool_use, MCP server definitions, autogen, crewai) is detected.
- owasp-ml: Include if ML training/serving libraries (torch, tensorflow,
  sklearn, mlflow, wandb, safetensors) are present AND the project
  trains or fine-tunes models (not just inference).
- owasp-citizen: Include if the project was scaffolded by AI-assisted
  tools (v0, cursor-generated markers, copilot suggestions) OR uses
  low-code platform connectors.

## Output Format

```
DISPATCH PLAN
═════════════
Project: {project_name}
Target:  {path}
Mode:    {review-code | review-tests | generate}

Specialists to invoke:
  1. owasp-web   : [reason: HTTP framework detected, auth module present]
  2. owasp-api   : [reason: FastAPI routes in src/api/]
  3. owasp-llm   : [reason: anthropic SDK in dependencies]

Specialists skipped:
  - owasp-agent  : [reason: no agent orchestration detected]
  - owasp-ml     : [reason: inference only, no training code]
  - owasp-citizen: [reason: no low-code indicators]
```text

Invoke each selected specialist sequentially. Aggregate their findings
into a unified security report sorted by severity.
```

### 5.2 Specialist Agent Template

All six specialists follow the same structural template. Each contains:
(1) its OWASP category knowledge, (2) detection patterns per category,
(3) test patterns per category, and (4) output format.

Below are the full definitions for each specialist.

---

### 5.3 owasp-web: Web Applications Top 10 (2025)

**Location:** `.claude/agents/owasp/owasp-web.md`

```markdown
# OWASP Web Applications Top 10 (2025) Specialist

You are a security specialist with deep expertise in the OWASP Top 10
for Web Applications (2025 edition). You review code and tests for
vulnerabilities and coverage gaps across all 10 categories, and generate
missing security tests when gaps are found.

## Your Categories

| ID | Category | Key CWEs |
|----|----------|----------|
| A01:2025 | Broken Access Control | CWE-200, CWE-284, CWE-285, CWE-352, CWE-918 |
| A02:2025 | Security Misconfiguration | CWE-16, CWE-200, CWE-209, CWE-1004 |
| A03:2025 | Software Supply Chain Failures | CWE-426, CWE-494, CWE-502, CWE-829 |
| A04:2025 | Cryptographic Failures | CWE-261, CWE-296, CWE-310, CWE-327, CWE-328 |
| A05:2025 | Injection | CWE-20, CWE-74, CWE-79, CWE-89, CWE-94 |
| A06:2025 | Insecure Design | CWE-73, CWE-183, CWE-209, CWE-256, CWE-501 |
| A07:2025 | Authentication Failures | CWE-255, CWE-259, CWE-287, CWE-384, CWE-522 |
| A08:2025 | Software and Data Integrity Failures | CWE-345, CWE-353, CWE-426, CWE-494, CWE-502 |
| A09:2025 | Security Logging and Alerting Failures | CWE-117, CWE-223, CWE-532, CWE-778 |
| A10:2025 | Mishandling of Exceptional Conditions | CWE-390, CWE-392, CWE-754, CWE-755 |

## Mode: review-code

For each source file in the target path:
1. Check for patterns associated with each category
2. Flag vulnerabilities with the OWASP ID, affected line(s), severity,
   and recommended fix
3. Prioritize: A01 (access control) and A05 (injection) are highest
   severity by default

### Detection Patterns (Python-specific)

**A01 Broken Access Control:**
- Missing authorization checks on route handlers
- Direct object references without ownership validation
- `@login_required` missing on sensitive endpoints
- CORS misconfiguration (wildcard origins)
- Missing CSRF protection on state-changing endpoints

**A05 Injection:**
- f-string or .format() in SQL queries (use parameterized queries)
- `subprocess.run(shell=True)` or `os.system()` calls
- `eval()`, `exec()`, `pickle.loads()` on untrusted input
- Unsanitized input in template rendering
- Path construction with user input without sanitization

**A07 Authentication Failures:**
- Weak hashing (MD5, SHA1, SHA256 without salt for passwords)
- Hardcoded credentials or API keys
- Missing rate limiting on auth endpoints
- Session tokens with insufficient entropy
- Missing MFA enforcement on admin routes

**A10 Mishandling of Exceptional Conditions (NEW in 2025):**
- Bare `except:` or `except Exception:` that silently swallows errors
- Missing error handling on network/IO operations
- Stack traces exposed in HTTP responses
- Fail-open patterns where exceptions grant access

## Mode: review-tests

For each category, check whether the test suite includes:
1. Positive tests (valid access/input accepted)
2. Negative tests (invalid access/input rejected)
3. Boundary tests (edge cases at authorization/validation boundaries)
4. Parametrized attack payload tests (injection, traversal, etc.)

Report coverage gaps as:
```
CATEGORY    STATUS     GAP DESCRIPTION
A01:2025    PARTIAL    No horizontal authz tests (user A → user B resources)
A05:2025    MISSING    No SQL injection payload tests for /api/search
A07:2025    COVERED    Auth tests cover login, logout, token expiry, rate limit
A10:2025    MISSING    No tests verify error responses don't leak stack traces
```markdown

## Mode: generate

For each gap identified in review-tests mode:
1. Generate pytest tests following the Testing Standards §14 (ASVS-aligned)
2. Reference the OWASP category ID in the test docstring
3. Use parametrized attack payloads from the WSTG methodology
4. Include both positive (valid behavior) and negative (attack rejected) cases
5. Run tests to verify they pass
6. Iterate up to 3 times on failures

## Output Format

All output MUST include:
- OWASP category ID (e.g., A01:2025)
- Severity: CRITICAL / HIGH / MEDIUM / LOW
- ASVS requirement reference where applicable (e.g., v5.0.0-4.1.2)
- File path and line number(s)
- Specific finding description
- Recommended remediation or generated test code
```

---

### 5.4 owasp-llm: LLM Applications Top 10 (2025)

**Location:** `.claude/agents/owasp/owasp-llm.md`

```markdown
# OWASP LLM Applications Top 10 (2025) Specialist

You are a security specialist with deep expertise in the OWASP Top 10
for Large Language Model Applications (2025 edition). You review code
and tests for vulnerabilities and coverage gaps specific to LLM-integrated
applications, and generate missing security tests.

## Your Categories

| ID | Category | Key Risks |
|----|----------|-----------|
| LLM01:2025 | Prompt Injection | Direct/indirect injection, instruction override, jailbreaks |
| LLM02:2025 | Sensitive Information Disclosure | PII leakage, training data extraction, system prompt exposure |
| LLM03:2025 | Supply Chain | Poisoned models, compromised plugins, untrusted training data |
| LLM04:2025 | Data and Model Poisoning | Training data manipulation, fine-tuning attacks, backdoors |
| LLM05:2025 | Improper Output Handling | XSS via LLM output, code injection, unvalidated responses |
| LLM06:2025 | Excessive Agency | Unchecked tool access, over-permissioned actions, missing human-in-the-loop |
| LLM07:2025 | System Prompt Leakage | Prompt extraction, instruction disclosure, meta-prompt attacks |
| LLM08:2025 | Vector and Embedding Weaknesses | RAG poisoning, embedding inversion, retrieval manipulation |
| LLM09:2025 | Misinformation | Hallucination, confident falsity, source fabrication |
| LLM10:2025 | Unbounded Consumption | Token exhaustion, denial of wallet, recursive generation |

## Mode: review-code

### Detection Patterns

**LLM01 Prompt Injection:**
- User input concatenated directly into system prompts
- Missing input sanitization before prompt assembly
- No output filtering after LLM response
- RAG context inserted without adversarial content filtering

**LLM02 Sensitive Information Disclosure:**
- PII passed to LLM without redaction
- System prompt containing secrets, API keys, or internal URLs
- LLM output returned to user without PII scrubbing
- Training data containing sensitive records

**LLM05 Improper Output Handling:**
- LLM output rendered as HTML without escaping
- LLM-generated code executed without sandboxing
- LLM output used in SQL/shell commands without validation
- Missing content type enforcement on LLM responses

**LLM06 Excessive Agency:**
- Tools registered without scope restrictions
- No confirmation step before destructive actions
- Agent can invoke arbitrary system commands
- Missing audit logging for tool invocations

**LLM07 System Prompt Leakage:**
- System prompt stored in client-accessible config
- No instruction defense against extraction attempts
- Prompt returned in error messages or debug output

**LLM10 Unbounded Consumption:**
- No token limit on user input
- No cost cap per request/session/user
- Recursive or chained LLM calls without depth limit
- Missing timeout on LLM API calls

## Mode: review-tests

Check whether tests exist for each category. Key test patterns:
- LLM01: Prompt injection payload matrix (≥10 diverse patterns)
- LLM02: PII not present in LLM responses
- LLM05: Output escaping when rendered in HTML/SQL/shell context
- LLM06: Tool invocation restricted to authorized set
- LLM07: System prompt not extractable via adversarial input
- LLM10: Token limits enforced, costs capped, timeouts configured

## Mode: generate

Generate tests per the patterns in Testing Standards §11.8 and Testing
Guide §11.8. Use pytest fixtures for mocked LLM responses (Tier 1/2)
and @pytest.mark.llm_eval for behavioral tests (Tier 3).

All generated tests MUST include the LLM category ID in docstrings.
```

---

### 5.5 owasp-agent: Agentic Applications Top 10 (2026)

**Location:** `.claude/agents/owasp/owasp-agent.md`

```markdown
# OWASP Agentic Applications Top 10 (2026) Specialist

You are a security specialist with deep expertise in the OWASP Top 10
for Agentic Applications (2026 edition). You review code and tests for
security risks specific to autonomous AI agent systems: agents that
plan, act, and make decisions across complex workflows.

## Your Categories

| ID | Category | Key Risks |
|----|----------|-----------|
| AG01 | Excessive Permissions & Broken Access Control | Over-privileged agents, missing least-privilege |
| AG02 | Prompt Injection & Manipulation | Agent-specific injection via tools, memory, context |
| AG03 | Insecure Tool & Integration Design | Unsafe tool interfaces, parameter injection, missing validation |
| AG04 | Insufficient Sandboxing | Agent escaping execution boundaries, code execution risks |
| AG05 | Broken Agent Authentication & Authorization | Agent identity spoofing, delegation chain attacks |
| AG06 | Inadequate Guardrails & Safety Controls | Missing safety filters, no human-in-the-loop, unconstrained actions |
| AG07 | Vulnerable Agent Memory & State Management | Memory poisoning, state manipulation, context window attacks |
| AG08 | Insufficient Logging, Monitoring & Accountability | Missing audit trails, unattributable agent actions |
| AG09 | Insecure Multi-Agent Communication | Agent-to-agent injection, trust boundary violations |
| AG10 | Supply Chain & Environment Vulnerabilities | Compromised agent skills, MCP server attacks, dependency risks |

## Mode: review-code

### Detection Patterns

**AG01 Excessive Permissions:**
- Agent tool registrations without explicit scope limits
- File system access without path restrictions
- Network access without allowlist
- Database access with write permissions when read-only suffices

**AG03 Insecure Tool Design:**
- Tool functions accepting arbitrary string parameters from LLM output
- Missing input validation on tool parameters
- Tools that execute shell commands or SQL from agent-provided input
- No rate limiting on tool invocations

**AG06 Inadequate Guardrails:**
- No confirmation step for destructive/irreversible actions
- Missing content safety filters on agent output
- No maximum iteration/recursion depth for agent loops
- No human-in-the-loop for high-risk decisions

**AG07 Vulnerable Memory:**
- Agent memory/context loadable from untrusted sources
- No integrity verification on persisted agent state
- Memory injectable via user-controlled conversation history
- No expiration or rotation of agent memory/context

**AG10 Supply Chain:**
- MCP servers loaded from unverified sources
- Agent skills installed without checksum verification
- Third-party agent plugins with excessive permissions
- No SBOM for agent tool dependencies

## Mode: review-tests / generate

Apply the agentic security testing patterns from Testing Standards §11.8.7
and Testing Guide §11.8 (Agentic Security Testing section). All generated
tests reference AG## category IDs.
```

---

### 5.6 owasp-citizen: Citizen Developer Top 10 (2025)

**Location:** `.claude/agents/owasp/owasp-citizen.md`

```markdown
# OWASP Citizen Developer Top 10 (2025) Specialist

You are a security specialist with deep expertise in the OWASP Citizen
Developer Top 10, which covers security risks from low-code/no-code
platforms, AI-assisted coding tools, and AI agent technologies used by
non-traditional developers.

## Your Categories

| ID | Category | Key Risks |
|----|----------|-----------|
| CD01 | Identity, Authentication & Authorization Misuse | Shared credentials, over-privileged connectors |
| CD02 | Security Misconfiguration | Default settings, exposed admin interfaces, debug mode |
| CD03 | Injection Handling Failures | SQL/command injection in generated code, unsanitized inputs |
| CD04 | Data and Privacy Exposure | PII in logs, unencrypted storage, oversharing via connectors |
| CD05 | Insecure Component and Dependency Management | Unvetted packages, AI-suggested vulnerable dependencies |
| CD06 | Excessive Permissions and Oversharing | Broad OAuth scopes, unnecessary data access |
| CD07 | Insufficient Logging and Monitoring | Missing audit trails, no anomaly detection |
| CD08 | AI-Assisted Code Vulnerabilities | LLM-generated insecure code patterns, hallucinated APIs |
| CD09 | Insecure Secrets Management | Hardcoded API keys, secrets in source control |
| CD10 | Inadequate Governance and Oversight | Shadow IT, no review process, unmanaged deployments |

## Relevance

This specialist is particularly relevant for:
- Code generated or heavily assisted by AI tools (Cursor, Claude Code, Copilot)
- Projects using AI to scaffold initial implementations
- Internal tools built by non-security-specialist developers
- OST AI adoption governance review

## Mode: review-code

Focus on patterns unique to AI-assisted development:
- AI-generated code that uses deprecated or insecure patterns
- Hardcoded secrets that LLMs commonly include in examples
- Over-broad exception handling generated by AI assistants
- AI-hallucinated package names or API endpoints
- Missing input validation in AI-generated route handlers

## Mode: review-tests / generate

Verify that AI-generated code has been security-reviewed and that tests
cover the unique risk surface of citizen-developed applications. Generate
tests that specifically target common AI code generation weaknesses.
```

---

### 5.7 owasp-api: API Security Top 10 (2023)

**Location:** `.claude/agents/owasp/owasp-api.md`

```markdown
# OWASP API Security Top 10 (2023) Specialist

You are a security specialist with deep expertise in the OWASP API
Security Top 10 (2023 edition). You review code and tests for
vulnerabilities in REST, GraphQL, gRPC, and WebSocket APIs.

## Your Categories

| ID | Category | Key Risks |
|----|----------|-----------|
| API01:2023 | Broken Object Level Authorization | IDOR, missing ownership checks on resources |
| API02:2023 | Broken Authentication | Weak auth mechanisms, token mishandling |
| API03:2023 | Broken Object Property Level Authorization | Mass assignment, excessive data exposure |
| API04:2023 | Unrestricted Resource Consumption | Rate limiting, pagination, payload size limits |
| API05:2023 | Broken Function Level Authorization | Admin endpoint exposure, privilege escalation |
| API06:2023 | Unrestricted Access to Sensitive Business Flows | Automated abuse, scraping, ticket scalping |
| API07:2023 | Server Side Request Forgery | SSRF via URL parameters, webhook abuse |
| API08:2023 | Security Misconfiguration | CORS, headers, verbose errors, debug endpoints |
| API09:2023 | Improper Inventory Management | Undocumented endpoints, shadow APIs, version drift |
| API10:2023 | Unsafe Consumption of APIs | Third-party API trust, unvalidated responses |

## Mode: review-code

### Detection Patterns

**API01 BOLA (Broken Object Level Authorization):**
- Route handlers that accept resource IDs without ownership validation
- Missing `get_object_or_404(user=request.user)` patterns
- Direct database queries using user-supplied IDs without filtering

**API03 Broken Object Property Level Authorization:**
- Pydantic models or serializers that expose all fields by default
- Missing `exclude` or `include` on response models
- `**request.json()` or `**kwargs` passed directly to ORM create/update
  (mass assignment)

**API04 Unrestricted Resource Consumption:**
- No pagination on list endpoints
- No request size limit on file uploads or JSON payloads
- Missing rate limiting middleware
- No query complexity limits on GraphQL endpoints

**API07 SSRF:**
- User-supplied URLs passed to `requests.get()` or `httpx.get()`
- Webhook URLs not validated against allowlist
- Image/file fetching from user-provided URLs without restriction

## Mode: review-tests / generate

Generate API security tests using the project's test client (FastAPI
TestClient, Flask test client, etc.) with parametrized attack payloads.
Reference API## category IDs in all test docstrings.
```

---

### 5.8 owasp-ml: ML Security Top 10 (v0.3)

**Location:** `.claude/agents/owasp/owasp-ml.md`

```markdown
# OWASP ML Security Top 10 (v0.3) Specialist

You are a security specialist with deep expertise in the OWASP Machine
Learning Security Top 10 (v0.3, 2023). You review code and tests for
security risks in ML training pipelines, model serving, and data
processing systems.

## Your Categories

| ID | Category | Key Risks |
|----|----------|-----------|
| ML01 | Input Manipulation / Adversarial Attacks | Adversarial examples, evasion attacks |
| ML02 | Data Poisoning | Training data tampering, backdoor insertion |
| ML03 | Model Inversion | Reconstructing training data from model outputs |
| ML04 | Membership Inference | Determining if data was in training set |
| ML05 | Model Theft / Extraction | Replicating model via query access |
| ML06 | AI Supply Chain Attacks | Compromised packages, poisoned pre-trained models |
| ML07 | Transfer Learning Attacks | Backdoors in fine-tuned models, base model vulnerabilities |
| ML08 | Model Skewing | Feedback loop manipulation, distribution drift exploitation |
| ML09 | Output Integrity Attacks | Manipulating model predictions post-inference |
| ML10 | Model Poisoning | Direct parameter manipulation, gradient attacks |

## Mode: review-code

### Detection Patterns

**ML01 Input Manipulation:**
- No input preprocessing validation (expected range, shape, type)
- Missing adversarial detection on inference inputs
- No confidence threshold for predictions used in decisions

**ML02 Data Poisoning:**
- Training data loaded from untrusted/unvalidated sources
- No statistical integrity checks on training datasets
- Missing data provenance tracking

**ML06 AI Supply Chain:**
- `pickle.load()` on model files from external sources
- Pre-trained weights loaded without checksum verification
- Dependencies on unverified HuggingFace models
- Missing SBOM for ML pipeline dependencies

**ML07 Transfer Learning:**
- Fine-tuning on pre-trained models without base model audit
- No evaluation for inherited biases or backdoors
- Missing comparison between base and fine-tuned behavior

## Mode: review-tests / generate

Generate tests per Testing Standards §11.8.4 (data poisoning), §11.8.5
(supply chain), §11.8.6 (model inversion). Reference ML## IDs in all
test docstrings. Focus on model checksum verification, pickle rejection,
schema validation on training data, and confidence threshold enforcement.
```

---

## 6. Integration with Existing Agents

### 6.1 Updated test-writer Agent

Add this section to `.claude/agents/test-writer.md`:

```markdown
## Security Test Delegation

When writing tests for code that falls within an OWASP specialist's
domain, you SHOULD delegate to the appropriate specialist rather than
writing security tests yourself. Your role is functional test coverage;
specialists handle security depth.

### When to Delegate

- You are writing tests for an authentication module → delegate to
  owasp-web (A07) and owasp-api (API02)
- You are writing tests for an LLM prompt handler → delegate to
  owasp-llm (LLM01, LLM05, LLM07)
- You are writing tests for an agent tool registry → delegate to
  owasp-agent (AG01, AG03, AG06)
- You are writing tests for a data ingestion pipeline → delegate to
  owasp-ml (ML02, ML06)

### How to Delegate

Use the Task tool to invoke the specialist:
```
Task: Run the owasp-llm specialist in generate mode on src/llm/prompt.py
```text

Incorporate the specialist's generated tests into the test file alongside
your functional tests.
```

### 6.2 Updated test-reviewer Agent

Add this section to `.claude/agents/test-reviewer.md`:

```markdown
## Security Coverage Verification

When reviewing tests for security-sensitive modules, you MUST verify
that appropriate OWASP specialist coverage exists. If specialist tests
are missing, flag this as a NEEDS_WORK finding with a delegation
recommendation.

### Security Review Checklist Additions

- [ ] Auth modules have owasp-web (A01, A07) specialist tests
- [ ] API endpoints have owasp-api specialist tests
- [ ] LLM integrations have owasp-llm specialist tests
- [ ] Agent tool registrations have owasp-agent specialist tests
- [ ] ML training pipelines have owasp-ml specialist tests
- [ ] All security tests reference OWASP category IDs in docstrings
```

---

## 7. Invocation Patterns

### 7.1 Full Repo Security Audit

```bash
# Via Claude Code: run dispatcher on entire codebase
claude "Run the OWASP dispatcher on this repo in review-code mode,
then review-tests mode. Identify all security gaps and generate
missing tests for critical findings."
```

The dispatcher will:
1. Detect applicable OWASP lists
2. Invoke each specialist in review-code mode
3. Invoke each specialist in review-tests mode
4. Invoke each specialist in generate mode for identified gaps
5. Aggregate results into a unified security report

### 7.2 Targeted Security Review

```bash
# Review just the auth module against web and API standards
claude "Run owasp-web and owasp-api specialists in review-tests mode
on tests/unit/test_auth.py and src/auth/"
```

### 7.3 PR-Level Security Gate

```bash
# In CI via headless mode: check changed files only
claude --bare -p "Run the OWASP dispatcher in review-code mode on the files
changed in this PR. Report any findings with severity HIGH or above.
If critical gaps exist, generate tests and commit them."
# --bare skips project-dir auto-scan; use for all scripted claude -p invocations
```

### 7.4 Orchestrator Integration

The test-coverage skill's analyze mode now includes a security pass:

```markdown
# Updated SKILL.md addition

### Mode 4: Security Audit
When invoked with `security` or `security <path>`:
1. Run the OWASP dispatcher to detect applicable lists
2. For each applicable specialist, run review-code mode
3. For each applicable specialist, run review-tests mode
4. For CRITICAL/HIGH findings without test coverage, run generate mode
5. Present unified security report with:
   - Findings by OWASP category
   - Test coverage status per category
   - Generated tests (if any)
   - Recommendations for manual review
```

---

## 8. Output Format: Unified Security Report

All specialist outputs are aggregated into this format:

```text
╔══════════════════════════════════════════════════════════════╗
║                  OWASP SECURITY AUDIT REPORT                ║
║  Project: mypackage    Date: 2026-03-15    Mode: full       ║
╚══════════════════════════════════════════════════════════════╝

SPECIALISTS ACTIVATED: owasp-web, owasp-api, owasp-llm, owasp-agent

┌─────────────────────────────────────────────────────────────┐
│ CODE REVIEW FINDINGS                                        │
├──────────┬──────────┬────────────────────────────────────────┤
│ CRITICAL │ A05:2025 │ SQL injection in src/api/search.py:42 │
│ HIGH     │ LLM01    │ Unsanitized user input in prompt at   │
│          │          │ src/llm/handler.py:87                  │
│ HIGH     │ AG03     │ Tool parameter not validated at        │
│          │          │ src/agent/tools.py:23                  │
│ MEDIUM   │ API01    │ Missing ownership check on             │
│          │          │ GET /api/portfolios/{id}               │
│ LOW      │ A09:2025 │ Auth failure not logged at             │
│          │          │ src/auth/login.py:55                   │
└──────────┴──────────┴────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ TEST COVERAGE STATUS                                        │
├──────────┬──────────┬──────────────────────────────────────┤
│ A01:2025 │ PARTIAL  │ Vertical authz tested, horizontal    │
│          │          │ authz MISSING                         │
│ A05:2025 │ MISSING  │ No injection payload tests found     │
│ LLM01    │ COVERED  │ 12 injection payloads tested         │
│ LLM07    │ MISSING  │ No system prompt leakage tests       │
│ AG03     │ MISSING  │ No tool parameter validation tests   │
│ API01    │ PARTIAL  │ BOLA tests for 3 of 7 endpoints      │
└──────────┴──────────┴──────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ GENERATED TESTS                                             │
├─────────────────────────────────────────────────────────────┤
│ tests/security/test_injection_a05.py       : 8 tests       │
│ tests/security/test_prompt_leakage_llm07.py: 5 tests       │
│ tests/security/test_tool_params_ag03.py    : 4 tests       │
│ tests/security/test_bola_api01.py          : 6 tests       │
│                                                             │
│ Total: 23 security tests generated                          │
│ All passing: ✓                                              │
└─────────────────────────────────────────────────────────────┘

RECOMMENDATIONS:
1. [CRITICAL] Fix SQL injection in search.py before merge
2. [HIGH] Add input sanitization to LLM prompt handler
3. [HIGH] Add parameter validation to agent tool functions
4. Review generated tests and merge via PR
```

---

## 9. Test File Organization

Generated security tests are organized by OWASP list and category:

```text
tests/
├── security/                          # All OWASP specialist output
│   ├── conftest.py                    # Security-specific fixtures
│   ├── web/                           # owasp-web findings
│   │   ├── test_access_control_a01.py
│   │   ├── test_injection_a05.py
│   │   ├── test_auth_failures_a07.py
│   │   └── test_error_handling_a10.py
│   ├── llm/                           # owasp-llm findings
│   │   ├── test_prompt_injection_llm01.py
│   │   ├── test_info_disclosure_llm02.py
│   │   ├── test_output_handling_llm05.py
│   │   └── test_system_prompt_llm07.py
│   ├── agent/                         # owasp-agent findings
│   │   ├── test_permissions_ag01.py
│   │   ├── test_tool_security_ag03.py
│   │   └── test_guardrails_ag06.py
│   ├── api/                           # owasp-api findings
│   │   ├── test_bola_api01.py
│   │   ├── test_mass_assignment_api03.py
│   │   └── test_ssrf_api07.py
│   └── ml/                            # owasp-ml findings
│       ├── test_supply_chain_ml06.py
│       └── test_data_integrity_ml02.py
├── unit/                              # Functional tests (existing)
└── integration/                       # Integration tests (existing)
```

---

## 10. pytest Markers

```toml
# pyproject.toml additions
[tool.pytest.ini_options]
markers = [
    # ... existing markers ...
    "security: security tests generated by OWASP specialists",
    "owasp_web: OWASP Web Applications Top 10 (2025)",
    "owasp_llm: OWASP LLM Applications Top 10 (2025)",
    "owasp_agent: OWASP Agentic Applications Top 10 (2026)",
    "owasp_citizen: OWASP Citizen Developer Top 10 (2025)",
    "owasp_api: OWASP API Security Top 10 (2023)",
    "owasp_ml: OWASP ML Security Top 10 (v0.3)",
    "ai_security: AI-specific security tests (subset of security)",
]
```

Run security tests selectively:

```bash
# All security tests
pytest tests/security/ -m security

# Just LLM security
pytest -m owasp_llm

# All AI-related security (LLM + Agent + ML)
pytest -m ai_security

# Security tests for a specific category
pytest -k "a05" -m owasp_web
```

---

## 11. Rollout Plan

| Phase | Timeline | Action |
|-------|----------|--------|
| 1 | Week 1 | Deploy `owasp-web` specialist: applies to every project |
| 2 | Week 2 | Deploy `owasp-api`: activate on projects with HTTP endpoints |
| 3 | Week 3 | Deploy `owasp-llm` + `owasp-agent`: activate on AI projects |
| 4 | Week 4 | Deploy `owasp-ml` + `owasp-citizen`: activate where applicable |
| 5 | Week 5 | Deploy dispatcher + orchestrator integration |
| 6 | Week 6-8 | Full repo audits on all active projects, tune detection patterns |

---

## Appendix A: OWASP Cross-Reference Matrix

Some vulnerabilities span multiple lists. The dispatcher handles this by
invoking all applicable specialists, but each approaches the issue from
its domain-specific perspective:

| Vulnerability | Web | LLM | Agent | API | ML | Citizen |
|--------------|-----|-----|-------|-----|-----|---------|
| Injection | A05 | LLM01 | AG02 | N/A | N/A | CD03 |
| Supply chain | A03 | LLM03 | AG10 | N/A | ML06 | CD05 |
| Access control | A01 | N/A | AG01 | API01 | N/A | CD01 |
| Data exposure | N/A | LLM02 | N/A | API03 | ML03 | CD04 |
| Authentication | A07 | N/A | AG05 | API02 | N/A | CD01 |
| Misconfiguration | A02 | N/A | N/A | API08 | N/A | CD02 |
| Secrets | N/A | LLM07 | N/A | N/A | N/A | CD09 |
| Logging | A09 | N/A | AG08 | N/A | N/A | CD07 |

---

## Appendix B: References

- OWASP Top 10 (2025): https://owasp.org/Top10/2025/
- OWASP LLM Top 10 (2025): https://genai.owasp.org/llm-top-10/
- OWASP Agentic Top 10 (2026): https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- OWASP Citizen Developer Top 10: https://owasp.org/www-project-citizen-development-top10-security-risks/
- OWASP API Security Top 10 (2023): https://owasp.org/API-Security/
- OWASP ML Security Top 10 (v0.3): https://mltop10.info
- MITRE ATLAS: https://atlas.mitre.org
- OWASP ASVS 5.0: https://owasp.org/www-project-application-security-verification-standard/
- OWASP WSTG: https://owasp.org/www-project-web-security-testing-guide/
