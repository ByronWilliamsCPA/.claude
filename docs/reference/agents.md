---
title: "Agents Catalog"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Index of all 43 agents in .claude/agents/ with domain, purpose, and invocation notes."
tags:
  - reference
  - agents
  - technical
---

Agents are invoked explicitly via the `Agent` tool with `subagent_type`. Each runs in an isolated context with its own tool restrictions. See [Agent Dispatch](../architecture/agent-dispatch.md) for how invocation works and [ADR-004](../architecture/adr/ADR-004-skill-vs-agent-boundary.md) for the classification rubric.

All agent files live in `.claude/agents/` (symlinked to `~/.claude/agents/`). The `subagent_type` value is the `name:` field in the agent's frontmatter: not necessarily the filename.

## Code Quality

| Agent (`subagent_type`) | File | Purpose |
| --- | --- | --- |
| `code-reviewer` | `code-reviewer.md` | Automated code review focused on quality, standards compliance, and best practices |
| `code-simplifier` | `code-simplifier.md` | Simplifies recently written code for clarity and maintainability without altering behavior |
| `comment-analyzer` | `comment-analyzer.md` | Analyzes code comments for accuracy, completeness, and long-term maintainability |
| `silent-failure-hunter` | `silent-failure-hunter.md` | Identifies silent failures, inadequate error handling, and inappropriate fallback behavior |
| `modularization-assistant` | `modularization-assistant.md` | Breaks down monolithic code, configs, and documentation into maintainable components |
| `type-design-analyzer` | `type-design-analyzer.md` | Reviews type design for encapsulation, invariant expression, and enforcement quality |

## Testing

| Agent (`subagent_type`) | File | Purpose |
| --- | --- | --- |
| `test-engineer` | `test-engineer.md` | Test strategy, generation, and quality assurance targeting 80%+ coverage |
| `test-writer` | `test-writer.md` | Coverage-driven iterative test generation with run-fix loop for pytest |
| `test-reviewer` | `test-reviewer.md` | Senior test quality review with OWASP and ISO 25010 coverage |
| `pr-test-analyzer` | `pr-test-analyzer.md` | Reviews pull request test coverage quality and completeness |
| `ui-testing-agent` | `ui-testing-agent.md` | End-to-end testing, user interaction validation, and Playwright test authoring |

## Security and OWASP

| Agent (`subagent_type`) | File | Purpose |
| --- | --- | --- |
| `security-auditor` | `security-auditor.md` | Vulnerability detection, threat assessment, and compliance validation |
| `owasp-dispatch` | `owasp-dispatch.md` | Routes security testing to the correct OWASP specialist based on project type |
| `owasp-web` | `owasp-web.md` | OWASP Top 10 for Web Applications (2025): reviews A01–A10 vulnerabilities |
| `owasp-api` | `owasp-api.md` | OWASP API Security Top 10 (2023): REST, GraphQL, gRPC, WebSocket |
| `owasp-llm` | `owasp-llm.md` | OWASP Top 10 for LLM Applications (2025): LLM01–LLM10 |
| `owasp-agent` | `owasp-agent.md` | OWASP Top 10 for Agentic Applications (2026): AG01–AG10 |
| `owasp-ml` | `owasp-ml.md` | OWASP ML Security Top 10 (v0.3, 2023): ML01–ML10 for training pipelines |
| `owasp-citizen` | `owasp-citizen.md` | OWASP Citizen Developer Top 10 (2025): AI-assisted and low-code/no-code |

## Planning and Architecture

| Agent (`subagent_type`) | File | Purpose |
| --- | --- | --- |
| `project-plan-synthesizer` | `project-plan-synthesizer.md` | Synthesizes planning documents into a PROJECT-PLAN.md with phase branches and quality gates |
| `scope-analyzer` | `scope-analyzer.md` | Produces a scope boundary document for a project phase (internal: phase-gate skill) |
| `plan-validator` | `plan-validator.md` | Validates an action plan against scope boundaries to detect creep (internal: phase-gate skill) |
| `phase-reviewer` | `phase-reviewer.md` | Executes quality gates to determine if a phase is complete (internal: phase-gate skill) |

## API and Backend

| Agent (`subagent_type`) | File | Purpose |
| --- | --- | --- |
| `api-development-agent` | `api-development-agent.md` | REST/GraphQL APIs, OpenAPI specifications, contract testing, and API versioning |
| `database-operations-agent` | `database-operations-agent.md` | Query optimization, schema management, migration handling, and data integrity |
| `ai-engineer` | `ai-engineer.md` | LLM applications, RAG pipelines, multi-agent systems, and prompt optimization |

## DevOps and Git

| Agent (`subagent_type`) | File | Purpose |
| --- | --- | --- |
| `devops-deployment-agent` | `devops-deployment-agent.md` | CI/CD pipelines, infrastructure automation, deployment orchestration, monitoring |
| `git-workflow-agent` | `git-workflow-agent.md` | Repository management, branch operations, conventional commits, and release management |
| `github-workflow-agent` | `github-workflow-agent.md` | Pull requests, issues, project boards, repository settings, and GitHub Actions |

## Frontend

| Agent (`subagent_type`) | File | Purpose |
| --- | --- | --- |
| `frontend-designer` | `frontend-designer.md` | UI/UX design, accessible components, React performance, and anti-generic-AI aesthetics |

## Research

| Agent (`subagent_type`) | File | Purpose |
| --- | --- | --- |
| `research-agent` | `research-agent.md` | Deep research, multi-source verification, and technology comparison |

## Documentation and Diagrams

| Agent (`subagent_type`) | File | Purpose |
| --- | --- | --- |
| `documentation-writer` | `documentation-writer.md` | API docs, user guides, architecture documentation, and documentation standards |
| `diagram-maintenance-agent` | `diagram-maintenance-agent.md` | PlantUML diagram maintenance, source traceability, and consistency enforcement |
| `diagram-specialist` | `diagram-specialist.md` | Technical diagrams (PlantUML, Mermaid) for network engineering documentation |
| `visual-content-generator` | `visual-content-generator.md` | Professional visual content (diagrams, blueprints, illustrations) for business documents |

## Writing Pipeline

A three-stage writing quality pipeline: draft → validate → style edit.

| Agent (`subagent_type`) | File | Stage | Purpose |
| --- | --- | --- | --- |
| `document-drafter` | `document-drafter.md` | Pre-pipeline | Produces first drafts from outlines or bullet points, calibrated to the author's voice |
| `document-validator` | `document-validator.md` | Stage 2 | Verifies claims, detects hallucinations, checks for bias, and flags reasoning errors |
| `grammar-composition-editor` | `grammar-composition-editor.md` | Stage 1 | Grammar, composition, plain language, and AI-mechanical pattern checks |
| `writing-style-editor` | `writing-style-editor.md` | Stage 3 | Persona fidelity and AI pattern detection: ensures documents sound human |
| `tone-rewriter` | `tone-rewriter.md` | Pre-pipeline | Rewrites a document for a different audience or register |
| `audience-reaction-analyzer` | `audience-reaction-analyzer.md` | Post-pipeline | Predicts how a target audience will interpret and react to a finished document |
| `style-analyzer` | `style-analyzer.md` | Setup | Analyzes writing samples to build a personalized style profile |

## See Also

- [Skills Catalog](skills.md): the 40+ skills and their triggers
- [Architecture → Agent Dispatch](../architecture/agent-dispatch.md): how agents are invoked at runtime
- [Contributing → Adding an Agent](../contributing/adding-agents.md): how to add a new agent
