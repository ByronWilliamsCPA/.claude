# Global Claude Development Standards

> **Status**: ✅ Active | Core Standard
> **Version**: 1.0.0
> **Last Updated**: 2025-01-16
>
> Universal development standards and practices for Claude Code across all projects.
>
> **Token Optimized**: This streamlined file references detailed specifications in `/standards/` 
> and `/commands/` directories for maximum efficiency while maintaining comprehensive coverage.

## Core Development Standards

> **Detailed Specifications**: See `/standards/python.md`, `/standards/security.md`, `/standards/git-workflow.md`, `/standards/git-worktree.md`, `/standards/linting.md`

### Essential Requirements
- **Code Quality**: Ruff formatting & linting (88 chars, PyStrict-aligned), BasedPyright type checking (strict mode)
- **Security**: GPG/SSH key validation, dependency scanning, encrypted secrets
- **Testing**: Minimum 80% coverage, tiered testing approach
- **Git**: Conventional commits, signed commits, feature branch workflow
- **Response-Aware Development**: Assumption tagging and verification (see `/docs/response-aware-development.md`)

## Response-Aware Development (RAD)

> **Full Documentation**: See `/docs/response-aware-development.md` for complete rationale and evaluation metrics

### Assumption Tagging Standards

When writing code, ALWAYS tag assumptions that could cause production failures:

```javascript
// #CRITICAL: [category]: [assumption that could cause outages/data loss]
// #VERIFY: [defensive code required]
// Example: Payment processing, auth flows, concurrent writes

// #ASSUME: [category]: [assumption that could cause bugs]  
// #VERIFY: [validation needed]
// Example: UI state, form validation, API responses

// #EDGE: [category]: [assumption about uncommon scenarios]
// #VERIFY: [optional improvement]  
// Example: Browser compatibility, slow networks
```

### Critical Assumption Categories (MANDATORY tagging)
- **Timing Dependencies**: State updates, async operations, race conditions
- **External Resources**: API availability, file existence, network connectivity
- **Data Integrity**: Type safety at boundaries, null/undefined handling
- **Concurrency**: Shared state, transaction isolation, deadlock potential
- **Security**: Authentication, authorization, input validation
- **Payment/Financial**: Transaction integrity, retry logic, rollback handling

### Verification Workflow (AUTOMATED with Agent Integration)
1. **During Development**: Claude tags assumptions inline with risk level
2. **On File Save**: Hook triggers assumption-verification-agent scan automatically
3. **Agent Processing**: Agent categorizes, verifies, and suggests defensive fixes
4. **Before Commit**: Agent validates critical assumptions are addressed
5. **Mark Verified**: Agent adds verification timestamps automatically

### File-Type Standards
- **Python**: 88-char line length, comprehensive rule compliance
- **Markdown**: 120-char line length, consistent formatting
- **YAML**: 2-space indentation, 120-char line length
- **Validation**: Pre-commit hooks enforce all standards

### Type Checking with BasedPyright
BasedPyright replaces MyPy as the standard type checker (3-5x faster, stricter analysis):
- **Mode**: `strict` (recommended) - enables all strict type checking without excessive noise
- **Strict Inference**: `strictListInference`, `strictDictionaryInference`, `strictSetInference` enabled
- **Configuration**: In `pyproject.toml` under `[tool.basedpyright]`
- **Reference**: https://docs.basedpyright.com

### PyStrict-Aligned Ruff Rules
Ruff configuration includes PyStrict-aligned rules for ultra-strict code quality:
- **BLE**: Blind except detection (no bare `except:` or `except Exception:`)
- **EM**: Error message best practices
- **SLF**: Private member access violations
- **INP**: Require `__init__.py` in packages
- **ISC**: Implicit string concatenation
- **PGH**: Deprecated type comments, blanket ignores
- **RSE**: Raise statement best practices
- **TID**: Banned imports, relative import rules
- **YTT**: Python version checks
- **FA**: Future annotations
- **T10**: Debugger statements (no `breakpoint()`, `pdb`)
- **G**: Logging format strings

## Code Generation Principles (MANDATORY)

> **Tooling Enforcement**: Complexity limits enforced via Ruff (C901, PLR0912, PLR0915). See `pyproject.toml`.

When generating code, Claude MUST follow these structural principles:

### Function Structure
- **Length**: Prefer **20-60 statements**; hard limit **100 statements** (PLR0915)
- **Single Responsibility**: Each function performs ONE conceptual task—if you need "and" to describe it, split it
- **Early Returns**: Exit early on error conditions; avoid deep else branches
- **Nesting Depth**: Maximum **3 levels** of indentation inside function body

### Complexity Controls
- **Cyclomatic Complexity**: Target **≤10** (C901 enforced); refactor if approaching 15
- **Branches**: Maximum **12 branches** per function (PLR0912)
- **Cognitive Load**: If a function requires extensive comments to understand, it's too complex

### Code Duplication
- **Zero Tolerance**: Never duplicate logic; extract to shared functions immediately
- **Rule of Three**: If you write similar code three times, refactor into a reusable function
- **Template Patterns**: Use decorators, context managers, or base classes for repeated patterns

### Data & State Design
- **Immutability First**: Prefer immutable structures; use `frozen=True` dataclasses
- **Pure Functions**: Minimize side effects; same inputs → same outputs
- **No Global State**: Pass dependencies explicitly; avoid module-level mutable state
- **Parameter Grouping**: When a function exceeds 4 parameters, group into a dataclass:

```python
# ❌ Too many parameters
def create_user(name: str, email: str, age: int, role: str, dept: str, manager: str) -> User:
    ...

# ✅ Grouped into dataclass
@dataclass(frozen=True)
class UserCreationRequest:
    name: str
    email: str
    age: int
    role: str
    department: str
    manager_id: str

def create_user(request: UserCreationRequest) -> User:
    ...
```

### Naming Standards
- **Variables**: Descriptive, **≥3 characters**, no abbreviations unless domain-standard
- **Functions**: Verb-based names that describe behavior (`calculate_total`, not `total`)
- **Booleans**: Use `is_`, `has_`, `can_`, `should_` prefixes
- **Constants**: SCREAMING_SNAKE_CASE

### Documentation Requirements
- **Docstrings**: REQUIRED for all public functions—include purpose, args, returns, raises
- **Inline Comments**: Only for non-obvious logic; never narrate what code does
- **Type Hints**: Required on all function signatures (enforced by BasedPyright strict)

## Essential Commands

> **Complete Command Reference**: See `/commands/quality.md`, `/commands/testing.md`, `/commands/security.md`

### Code Quality & Formatting
```bash
# Format and lint (see /commands/quality.md for full details)
ruff format .                 # Format code (replaces black)
ruff check --fix .            # Lint and auto-fix
basedpyright src              # Strict mode type checking
markdownlint **/*.md
yamllint **/*.{yml,yaml}
```

### Security Validation
```bash
# Key validation (see /commands/security.md for full details)
gpg --list-secret-keys  # Must show GPG key for .env encryption
ssh-add -l              # Must show SSH key for signed commits
git config --get user.signingkey  # Must be configured for signed commits
poetry run safety check
poetry run bandit -r src
```

### Testing Standards
```bash
# Testing commands (see /commands/testing.md for full details)
poetry run pytest -v --cov=src --cov-report=html --cov-report=term-missing
poetry run pre-commit run --all-files
```

### Assumption Verification (Automated via Agent)
```bash
# Simplified assumption verification commands (replaces complex tooling)
/verify-assumptions              # Agent scans and verifies automatically
/critical-assumptions           # Agent focuses on critical assumptions only  
/apply-assumption-fixes         # Agent applies safe defensive patterns
/assumption-report             # Generate comprehensive assumption analysis report
```

**Agent-Driven Verification Process:**
- **Automatic Detection**: Scans for #CRITICAL, #ASSUME, #EDGE tags in code
- **Risk Categorization**: Routes to appropriate verification strategies
- **Defensive Code Generation**: Creates validation and error handling patterns
- **Hook Integration**: Triggers verification on file save and pre-commit

## OpenSSF Best Practices Compliance

> **Token Optimized**: Existing standards already satisfy most OpenSSF requirements. This section documents compliance mapping and additional requirements.

### Automatic Compliance (Already Configured)
Our existing standards satisfy core OpenSSF requirements:
- ✅ **Testing**: 80% coverage requirement + automated test runs
- ✅ **Static Analysis**: Ruff (PyStrict-aligned), BasedPyright, Bandit already configured
- ✅ **Security Scanning**: Safety check for dependencies
- ✅ **Version Control**: Signed commits, branch protection
- ✅ **Secrets Management**: GPG-encrypted .env files

### Required Project Files (Verify Presence)
```bash
# Check OpenSSF required files exist
ls -1 LICENSE SECURITY.md CONTRIBUTING.md CHANGELOG.md README.md 2>/dev/null | wc -l
# Should output: 5
```

### Release Checklist (Manual Verification)
Before any release:
- [ ] CHANGELOG.md updated with security fixes (if any)
- [ ] No known vulnerabilities >60 days old (`poetry run safety check`)
- [ ] All tests pass with coverage >80%
- [ ] Version tag follows SemVer (vX.Y.Z)
- [ ] Release notes include CVE fixes (if applicable)

### New Feature Requirements
When implementing new functionality:
1. **Add tests first** (TDD when practical)
2. **Document security implications** in docstrings
3. **Update CHANGELOG.md** with user-facing changes
4. **Use established libraries** (don't roll your own crypto)

### Compliance Verification
```bash
# Quick compliance check (available in cookiecutter template)
./scripts/check-openssf.sh

# Weekly automated scorecard (GitHub Actions)
# See .github/workflows/openssf-scorecard.yml in project templates
```

## Project Integration

> **Project Templates**: Use `/templates/python-project.md` or `/templates/general-project.md` for new projects
>
> **Organization Guide**: See `PROJECT-ORGANIZATION-GUIDE.md` for comprehensive guidelines on what should live where in the configuration structure

### Implementation Pattern
Projects create focused `CLAUDE.md` files that **extend** (not duplicate) these global standards:

1. **Reference Pattern**: Use `> Reference: /standards/[domain].md` for detailed requirements
2. **Project Focus**: Include only project-specific configurations and deviations
3. **Inheritance**: All universal standards automatically apply unless overridden

### Example Project Structure
```markdown
# Project Development Guide

> This project extends the global CLAUDE.md standards. Only project-specific 
> configurations and deviations are documented below.

## Project-Specific Standards
> Reference: Global standards apply. Project-specific requirements below.

- **Performance**: API response p95 < 2s
- **Security**: Service account at `.gcp/service-account.json`
- **Architecture**: External Qdrant at 192.168.1.16:6333
```

## Claude Code Supervisor Role (CRITICAL)

**Claude Code acts as the SUPERVISOR for all development tasks and MUST:**

1. **Always Use TodoWrite Tool**: Create and maintain TODO lists for ALL tasks to track progress
2. **Assign Tasks to Agents**: Each TODO item should be assigned to a specialized agent via MCP Server
3. **Review Agent Work**: Validate all agent outputs before proceeding to next steps
4. **Use Temporary Reference Files**: Create `.tmp-` prefixed files in `tmp_cleanup/` folder to store detailed context that might be lost during compaction
5. **Maintain Continuity**: Use reference files to preserve TODO details across conversation compactions

### Agent Assignment Patterns

```bash
# Always assign TODO items to appropriate agents:
- Assumption verification → Assumption Verification Agent (via mcp__zen__assumption-verify)
- Security tasks → Security Agent (via mcp__zen__secaudit)
- Code reviews → Code Review Agent (via mcp__zen__codereview)  
- Testing → Test Engineer Agent (via mcp__zen__testgen)
- Documentation → Documentation Agent (via mcp__zen__docgen)
- Debugging → Debug Agent (via mcp__zen__debug)
- Analysis → Analysis Agent (via mcp__zen__analyze)
- Refactoring → Refactor Agent (via mcp__zen__refactor)
```

### Temporary Reference Files (Anti-Compaction Strategy)

**ALWAYS create temporary reference files when:**
- TODO list contains >5 items
- Complex implementation details need preservation
- Multi-step workflows span multiple conversation turns
- Agent assignments and progress need tracking

**Naming Convention**: `tmp_cleanup/.tmp-{task-type}-{timestamp}.md` (e.g., `tmp_cleanup/.tmp-auth4-implementation-20250125.md`)

## MCP Tool Loading Strategy (CRITICAL)

> **Reference**: Based on [Anthropic's Advanced Tool Use Guide](https://www.anthropic.com/engineering/advanced-tool-use)
> **Configuration**: See `/mcp/mcp_config.yaml` for full configuration

### Overview

MCP tools are loaded using a **tiered strategy** to reduce context consumption by 85-95%:
- **Before**: ~55K tokens consumed by 80+ tools at session start
- **After**: ~3K tokens (Tier 1) + context-specific loading

### Tier 1: Always Loaded (Core Tools)

These 7 tools are loaded at every session start:

| Server | Tools | Purpose |
|--------|-------|---------|
| zen | thinkdeep, codereview, tiered_consensus, chat | Deep analysis, reviews, decisions |
| context7 | resolve_library_id, get_library_docs | Library documentation |
| github | get_file_contents | Basic file access |

### Tier 2: Agent/Skill-Bundled Tools

Tools loaded automatically when specific agents are invoked via Task tool:

| Agent | MCP Tools Loaded |
|-------|------------------|
| security-auditor | `zen.secaudit`, `sentry.*`, `github.code_security`, `postgres.analyze_db_health` |
| code-reviewer | `zen.precommit`, `zen.challenge`, `github.pull_requests` |
| test-engineer | `zen.testgen`, `playwright.*` |
| documentation-writer | `zen.docgen`, `mermaid.*`, `uml-mcp-server.*` |
| database-operations-agent | `postgres.*` |
| devops-deployment-agent | `docker.*`, `github.actions`, `sentry.*` |
| debug-agent | `zen.debug`, `sentry.*`, `postgres.explain_query` |

### Tier 3: Keyword-Triggered Tools

Tools loaded when keywords detected in user prompts:

| Keywords | Tools Loaded |
|----------|--------------|
| dockerfile, container, docker, k8s | `docker.*` |
| e2e, browser test, playwright, ui test | `playwright.*` |
| database, sql, postgres, migration | `postgres.*` |
| sentry, error monitoring, exception | `sentry.*` |
| diagram, flowchart, mermaid, uml | `mermaid.*`, `uml-mcp-server.*` |

### Removed Tools

| Tool | Reason | Alternative |
|------|--------|-------------|
| sequentialthinking | Redundant with zen.thinkdeep | Use `zen.thinkdeep` |

### Hook Scripts

Tool loading is managed by these scripts in `/scripts/`:

- **mcp-tool-loader.sh**: Load tools for specific agents or check keywords
- **keyword-tool-trigger.sh**: PreToolUse hook for keyword detection
- **track-mcp-usage.sh**: PostToolUse hook for usage analytics

### Usage Commands

```bash
# Check which tools would load for an agent
./scripts/mcp-tool-loader.sh --agent security-auditor

# Check keyword triggers
./scripts/mcp-tool-loader.sh --keywords "fix the database query"

# View MCP usage report
./scripts/track-mcp-usage.sh --report

# Reset session tool state
./scripts/keyword-tool-trigger.sh --reset
```

### Agent Definition Format

Agents define their MCP tool bundles in frontmatter:

```yaml
---
name: security-auditor
mcp_tools:
  load:
    zen: [secaudit, challenge]
    sentry: [search_errors, get_issue, analyze_issue]
    github: [code_security]
    postgres: [analyze_db_health]
  defer:
    sentry: [list_projects, create_dsn]
---
```

### Supervisor Workflow Patterns (MANDATORY)

**Every development task MUST follow this pattern:**

1. **Create TODO List**: Use TodoWrite tool to break down the task into specific, actionable items
2. **Agent Assignment**: Assign each TODO item to the most appropriate specialized agent
3. **Progress Tracking**: Mark items as in_progress when assigned, completed when validated
4. **Reference File Creation**: For complex tasks, create `.tmp-` reference files immediately
5. **Agent Output Validation**: Review all agent work before marking items complete

**For complex tasks requiring multiple agents:**

1. **Sequential Dependencies**: Use TodoWrite to show dependencies between tasks
2. **Parallel Execution**: Assign independent tasks to multiple agents simultaneously
3. **Integration Points**: Create specific TODO items for integrating agent outputs
4. **Quality Gates**: Assign review tasks to appropriate agents after implementation

### PR Preparation Workflow (AUTOMATED)

**ALWAYS use `mcp__zen-core__pr_prepare` tool for PR creation:**

```bash
# Standard PR creation with What the Diff integration
mcp__zen-core__pr_prepare --include_wtd=true --target_branch=main

# Force WTD even for large PRs
mcp__zen-core__pr_prepare --include_wtd=true --force_wtd=true

# Custom parameters
mcp__zen-core__pr_prepare \
  --include_wtd=true \
  --target_branch=main \
  --change_type=feat \
  --title="Add new feature"
```

**Branch Safety and PR Creation MUST follow this pattern:**

1. **Branch Strategy Validation**: Validate current branch strategy and proper targeting
2. **Dependency Validation**: Update poetry.lock and regenerate requirements files automatically
3. **Security Scanning**: Run dependency security checks before PR creation
4. **What the Diff Integration**: Include `<!-- wtd:summary -->` shortcode in PR description
5. **GitHub Integration**: Push branch and create draft PR with comprehensive description
6. **Review Assignment**: Auto-assign reviewers based on CODEOWNERS and change patterns

**Branch Safety Checks:**
- Prevents PRs from main branch (must use feature branches)
- Validates branch naming conventions and targeting strategy
- Provides branch migration assistance for incorrect strategies
- Confirms user intent for main branch targeting

**Automatic PR Generation:**
- Analyzes git commit history and change patterns
- Generates comprehensive PR descriptions with metrics
- **ALWAYS includes What the Diff shortcode** (`<!-- wtd:summary -->`) unless `include_wtd=false`
- Applies appropriate labels based on change types and size
- Integrates with GitHub CLI for seamless workflow

**What the Diff Integration (CRITICAL):**
- **Default behavior**: `include_wtd=true` - WTD shortcode automatically included
- **Shortcode syntax**: `<!-- wtd:summary -->` (HTML comment format)
- **Placement**: Inserted in PR description where AI-generated summary is desired
- **Additional shortcodes**: `<!-- wtd:joke -->`, `<!-- wtd:poem -->` (optional)
- **Large PRs**: Use `--force_wtd=true` to override size-based exclusion
- **Disable WTD**: Set `--include_wtd=false` (rare, only for internal/draft PRs)

## Development Philosophy

**Security First** → **Quality Standards** → **Documentation** → **Testing** → **Collaboration**

### Core Principles
1. **Security First**: Always validate keys, encrypt secrets, scan dependencies
2. **Reuse First**: Check existing repositories for solutions before building new code
3. **Configure, Don't Build**: Prefer configuration and orchestration over custom implementation
4. **Quality Standards**: Maintain consistent code quality across all projects
5. **Documentation**: Keep documentation current and well-formatted
6. **Testing**: Maintain high test coverage and run tests before commits
7. **Collaboration**: Use consistent Git workflows and clear commit messages

## Git Worktree Workflow

> **Full Documentation**: See `/standards/git-worktree.md` for complete worktree patterns, commands, and best practices.

Git worktrees enable parallel development by maintaining multiple working directories from a single repository. Use for feature development, PR reviews, hotfixes, and experimentation.

**Quick Reference**:
```bash
# Create worktree for new feature
git worktree add ../{project}-worktrees/feature-name -b feature/feature-name
cd ../{project}-worktrees/feature-name && uv sync --all-extras

# Create worktree for PR review
git worktree add ../{project}-worktrees/pr-42 origin/feature/pr-branch

# List and cleanup
git worktree list
git worktree remove ../{project}-worktrees/feature-name
git worktree prune
```

**Key Points**:
- Worktrees share git history but NOT virtualenvs - run `uv sync` in each
- Use sibling directory: `../{project}-worktrees/`
- Cleanup promptly after merging

**Note**: Worktrees are for parallel branch isolation. They do NOT replace `tmp_cleanup/` which serves as development history and anti-compaction storage.

## Automated Branch Creation Strategy (CRITICAL)

> **Full Documentation**: See `/standards/git-workflow.md` and `/standards/git-worktree.md` for complete patterns and commands.

Claude Code MUST automatically create branches and worktrees during project plan execution to maintain semantic release compatibility and git hygiene.

### Branch Type Mapping (Semantic Release)

| Task Type | Branch Prefix | Commit Type | Version Impact |
|-----------|---------------|-------------|----------------|
| New feature | `feat/` | `feat:` | Minor (0.X.0) |
| Bug fix | `fix/` | `fix:` | Patch (0.0.X) |
| Breaking change | `feat/` or `fix/` | `feat!:` or `fix!:` | Major (X.0.0) |
| Documentation | `docs/` | `docs:` | No release |
| Refactoring | `refactor/` | `refactor:` | No release |
| Performance | `perf/` | `perf:` | Patch (0.0.X) |
| Testing | `test/` | `test:` | No release |
| Chore/maintenance | `chore/` | `chore:` | No release |
| Hotfix (critical) | `hotfix/` | `fix:` | Patch (0.0.X) |

### When to Create Branches (MANDATORY)

**ALWAYS create a new branch when:**

1. **Starting ANY implementation task** - Never commit directly to `main` or `develop`
2. **TODO item involves code changes** - Each feature/fix TODO should have its own branch
3. **Multiple independent features** - Create separate branches for parallel work
4. **User explicitly requests a feature/fix** - Branch immediately before coding
5. **PR review reveals issues** - Create fix branch from the PR branch

**Branch Creation Command Pattern:**
```bash
# Standard feature branch (most common)
git checkout main && git pull origin main
git checkout -b feat/{descriptive-slug}

# Bug fix branch
git checkout -b fix/{issue-or-description}

# Documentation branch
git checkout -b docs/{topic}

# Refactoring branch
git checkout -b refactor/{component-name}
```

### When to Use Worktrees vs Simple Branches

| Scenario | Use Worktree | Reason |
|----------|--------------|--------|
| Simple single task | No | Branch is sufficient |
| Long-running feature (>1 session) | **Yes** | Preserves state across sessions |
| Parallel agent work | **Yes** | Isolated environments |
| PR review while working | **Yes** | Don't disrupt current work |
| Hotfix during feature work | **Yes** | Emergency isolation |
| Multiple TODOs in same feature | No | Single branch, multiple commits |
| Experimentation/spike | **Yes** | Safe to abandon |

**Worktree Decision Rule**: Use worktree when you need to **preserve current work state** or **run parallel isolated operations**.

### Project Plan Branch Strategy

When executing a multi-step project plan:

**Single Feature Implementation:**
```bash
# 1. Create feature branch at plan start
git checkout -b feat/implement-{feature-name}

# 2. Work through TODOs with conventional commits
git commit -m "feat: add initial {component}"
git commit -m "feat: implement {sub-feature}"
git commit -m "test: add tests for {component}"
git commit -m "docs: document {feature-name} usage"

# 3. Single PR at plan completion
```

**Multi-Feature Plan (Independent TODOs):**
```bash
# 1. Create branches for each independent feature
git checkout -b feat/feature-a
# ... work on feature A ...
git checkout main
git checkout -b feat/feature-b
# ... work on feature B ...

# 2. Or use worktrees for true parallelism
git worktree add ../{project}-worktrees/feat-a -b feat/feature-a
git worktree add ../{project}-worktrees/feat-b -b feat/feature-b
```

**Phased Development (Dependent TODOs):**
```bash
# 1. Create branch for entire phase
git checkout -b feat/phase-1-{description}

# 2. Commit each step with appropriate type
git commit -m "feat: phase 1 step 1 - {description}"
git commit -m "feat: phase 1 step 2 - {description}"
# ... continue through phase ...

# 3. Single PR for complete phase
```

### Branch Naming Convention (ENFORCED)

**Format**: `{type}/{descriptive-slug}`

**Rules:**
- **Lowercase only**: `feat/user-auth` not `feat/User-Auth`
- **Hyphen-separated**: `feat/add-login-page` not `feat/add_login_page`
- **Descriptive but concise**: `feat/oauth-google` not `feat/add-oauth-integration-with-google-identity-provider`
- **No ticket numbers alone**: `feat/auth-ABC-123` not `ABC-123`

**Examples:**
```bash
# Good
feat/user-authentication
fix/null-pointer-api
docs/installation-guide
refactor/database-queries
perf/image-optimization
hotfix/critical-security-patch

# Bad
feature/UserAuthentication  # Wrong prefix, wrong case
fix_null_pointer            # Underscores
docs/update                 # Too vague
ABC-123                     # Ticket number only
```

### Supervisor Branch Workflow (MANDATORY)

**When Claude Code starts a development task:**

1. **Check current branch**:
   ```bash
   git branch --show-current
   git status
   ```

2. **If on main/develop, create appropriate branch FIRST**:
   ```bash
   git checkout -b {type}/{descriptive-slug}
   ```

3. **Update TODO list** with branch name:
   ```
   - [x] Create branch: feat/add-user-dashboard
   - [ ] Implement dashboard component
   - [ ] Add tests
   - [ ] Create PR
   ```

4. **Commit frequently** with conventional commit messages matching branch type

5. **Never merge directly** - Always use PR workflow via `mcp__zen__pr_prepare`

### Integration with TodoWrite

When creating TODO lists, include branch management:

```markdown
## TODO List: Implement User Dashboard

### Setup
- [ ] Create feature branch `feat/user-dashboard`
- [ ] Set up worktree if parallel work needed

### Implementation
- [ ] Implement DashboardComponent
- [ ] Add API endpoints
- [ ] Write unit tests

### Completion
- [ ] Run pre-commit checks
- [ ] Create PR via mcp__zen__pr_prepare
- [ ] Clean up worktree (if used)
```

### Automatic Branch Validation

Before ANY code changes, Claude Code MUST verify:

1. **Not on protected branch**: `main`, `master`, `develop` require branch creation
2. **Branch name matches work type**: `feat/` for features, `fix/` for bugs, etc.
3. **Branch is up-to-date**: `git pull origin main` before branching
4. **No uncommitted changes**: Commit or stash before switching

```bash
# Validation check pattern
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" || "$CURRENT_BRANCH" == "develop" ]]; then
    echo "ERROR: Cannot work directly on $CURRENT_BRANCH. Create a feature branch first."
    exit 1
fi
```

## Pre-Commit Linting Checklist

Before committing ANY changes, ensure:
- [ ] **Branch Validation**: Working on appropriate feature branch (not main/develop)
- [ ] **Branch Naming**: Branch follows `{type}/{descriptive-slug}` convention
- [ ] **TODO Management**: Was TodoWrite used for task tracking?
- [ ] **Agent Assignment**: Were tasks assigned to appropriate specialized agents?
- [ ] **Reference Files**: Were temporary reference files created for complex tasks?
- [ ] **Agent Validation**: Was all agent work reviewed and validated?
- [ ] **Assumption Verification**: Agent automatically verified critical assumptions
- [ ] **OpenSSF Compliance**: Required files present (LICENSE, SECURITY.md, CONTRIBUTING.md, CHANGELOG.md)
- [ ] Environment validation passes (GPG and SSH keys present)
- [ ] File-specific linter has been run and passes
- [ ] Pre-commit hooks execute successfully (includes credential leak detection)
- [ ] No linting warnings or errors remain
- [ ] Code formatting is consistent with project standards
- [ ] Commits are signed (Git signing key configured)
- [ ] **Security Scanning**: No known vulnerabilities (`poetry run safety check`)
- [ ] **Branch Safety**: PR preparation validates branch strategy if applicable
- [ ] **Dependency Safety**: Requirements files updated if dependencies changed
- [ ] **PR Creation**: If creating PR, use `mcp__zen-core__pr_prepare` with `--include_wtd=true`

---

*This modular configuration is automatically loaded by Claude Code. For detailed specifications,
see referenced files in `/standards/` and `/commands/` directories.*

*Modularization complete! All detailed specifications are now available in domain-specific files
for maximum token efficiency.*