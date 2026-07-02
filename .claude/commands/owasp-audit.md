# OWASP Audit

Detect the project's applicable OWASP domains and dispatch the matching
`owasp-*` specialist agents to review code and tests for vulnerabilities,
then aggregate their findings into one unified security report sorted by
severity. This command replaces the retired `owasp-dispatch` agent:
dispatch and aggregation are orchestration, which belongs at the command
layer, not behind another agent (agents invoking agents contradicts
ADR-004; see `.claude/rules/supervisor.md`).

## Arguments (optional)

- `<path>` -- target path to review; defaults to the whole project.
- `--mode review-code|review-tests|generate` -- passed through to every
  dispatched specialist; defaults to `review-code`.

## Steps

### 1. Detect project type

1. Read `pyproject.toml` (or `requirements.txt`, `package.json`) for
   dependencies.
2. Scan source imports in the target path using Grep/Glob.
3. Check for framework indicators (`.claude/`, MCP configs, `Dockerfile`,
   etc.).

### 2. Build the dispatch plan

Apply these rules to decide which specialists to invoke:

- **owasp-web**: always include. Every project needs web/AppSec review.
- **owasp-api**: include if any HTTP framework, REST endpoints, or API
  route decorators are detected.
- **owasp-llm**: include if any LLM SDK (anthropic, openai, litellm,
  langchain, openrouter, transformers with `pipeline("text-generation")`)
  is imported or configured.
- **owasp-agent**: include if agent orchestration (langchain agents,
  Claude tool_use, MCP server definitions, autogen, crewai) is detected.
- **owasp-ml**: include if ML training/serving libraries (torch,
  tensorflow, sklearn, mlflow, wandb, safetensors) are present AND the
  project trains or fine-tunes models (not just inference).
- **owasp-citizen**: include if the project was scaffolded by
  AI-assisted tools (v0, cursor-generated markers, copilot suggestions)
  OR uses low-code platform connectors.

Present the plan before invoking anything:

```text
DISPATCH PLAN
=============
Project: {project_name}
Target:  {path}
Mode:    {review-code | review-tests | generate}

Specialists to invoke:
  1. owasp-web    - [reason: HTTP framework detected, auth module present]
  2. owasp-api    - [reason: FastAPI routes in src/api/]
  3. owasp-llm    - [reason: anthropic SDK in dependencies]

Specialists skipped:
  - owasp-agent   - [reason: no agent orchestration detected]
  - owasp-ml      - [reason: inference only, no training code]
  - owasp-citizen - [reason: no low-code indicators]
```

### 3. Invoke the selected specialists

For each specialist in the plan, use the Agent tool with
`subagent_type="<specialist-name>"` (for example `owasp-web`, `owasp-api`)
and pass the target path plus the requested mode. Specialists are
independent of each other and share no state, so dispatch all selected
specialists in a single message with multiple Agent tool calls (see the
`dispatching-parallel-agents` skill) instead of invoking them one at a
time.

### 4. Aggregate findings

Merge every specialist's findings into one report sorted by severity
(CRITICAL, HIGH, MEDIUM, LOW), preserving each finding's OWASP category
ID, file path and line number(s), and recommended remediation or
generated test code.

In `generate` mode, specialist agents return generated test code rather
than writing it to disk or running it themselves (they hold no Write or
Bash tool). Write each returned test to the appropriate test file and run
the suite yourself, iterating on failures.

## Resource constraints

Set an explicit `timeout` on each Agent tool call expected to run longer
than 5 minutes. No unbounded loops or recursive agent calls.
