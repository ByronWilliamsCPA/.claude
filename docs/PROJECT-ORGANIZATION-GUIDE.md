---
title: "Project Organization Guide"
schema_type: common
status: published
owner: core-maintainer
purpose: "Configuration and documentation guide for organizing Claude Code setups."
tags:
  - guide
  - documentation
  - architecture
---

> **Reference guide for organizing Claude Code configurations, tools, and documentation**

## 🎯 Purpose

This guide outlines **what should live where** in the `$HOME/.claude/` git-trackable configuration to maintain consistency, avoid duplication, and ensure team collaboration.

## 📁 Directory Structure & Ownership

### Core Configuration Files
```text
$HOME/.claude/
├── .claude.json              # 🎯 Main config: MCP servers, user settings
├── settings.json             # 🎯 Project settings: permissions, hooks
├── .gitignore               # 🎯 Git exclusions: credentials, cache, backups
└── start-claude.sh          # 🎯 Startup script: environment setup
```

**What belongs here:**
- **MCP server definitions** (user-level, global)
- **Tool permissions** and allowed commands
- **Hooks configuration** (TDD enforcement, MCP tracking)
- **Git-trackable settings** only (no credentials!)

---

### Documentation Hub
```text
├── README.md                     # 🎯 Main project overview
├── CLAUDE.md                     # 🎯 Global development standards
├── PROJECT-ORGANIZATION-GUIDE.md # 🎯 This file - what goes where
├── README-git-trackable-config.md # 🎯 Setup and configuration guide
├── SECURITY.md                   # 🎯 Security guidelines
└── CHANGELOG.md                  # 🎯 Version history and updates
```

**What belongs here:**
- **High-level overviews** and getting started guides
- **Universal development standards** that apply to all projects
- **Security requirements** and best practices
- **Configuration setup** and troubleshooting guides

**What does NOT belong here:**
- Project-specific documentation (goes in project repos)
- Implementation details (goes in `/docs/`)
- Temporary notes or drafts

---

### MCP Server Configurations
```text
mcp/
├── zen-server.json           # 🎯 Active: Smart consensus + core tools
├── github-server.json        # 🎯 Active: GitHub integration
├── playwright-server.json    # 🎯 Active: Browser automation
├── disabled/                 # 🎯 Inactive configurations
├── examples/                 # 🎯 Example/template configurations
└── README.md                # 🎯 MCP server documentation
```

**What belongs here:**
- **Active MCP server configurations** (tracked in git)
- **Disabled configurations** for reference (ignored in git)
- **Example configurations** for team templates
- **Server-specific documentation** and setup guides

**Naming Convention:**
- Active servers: `{server-name}.json`
- Disabled servers: `{server-name}.json.disabled` → moved to `disabled/`
- Examples: `{server-name}.json.example` → moved to `examples/`

---

### Custom Agents
```text
agents/
├── README.md                 # 🎯 Agent overview and usage
├── security-auditor.md       # 🎯 Security analysis specialist
├── code-reviewer.md          # 🎯 Code quality and standards
├── test-writer.md            # 🎯 Testing and coverage specialist
├── api-development-agent.md  # 🎯 API development specialist
└── [25+ other agents]        # 🎯 Specialized domain experts
```

**What belongs here:**
- **Reusable agent definitions** for specialized tasks
- **Agent documentation** with usage examples
- **Domain-specific agents** (security, testing, API, etc.)

**Agent Naming Convention:**
- Domain-based: `{domain}-{role}.md` (e.g., `security-auditor.md`)
- Function-based: `{function}-agent.md` (e.g., `api-development-agent.md`)

---

### Custom Commands
```text
commands/
├── _README.md               # 🎯 Command overview and categories
├── quality-*.md             # 🎯 Code quality and formatting
├── security-*.md            # 🎯 Security validation and checks
├── workflow-*.md            # 🎯 Development workflow helpers
├── meta-*.md               # 🎯 Command management utilities
└── test-*.md               # 🎯 Testing and validation commands
```

**What belongs here:**
- **Reusable slash commands** that work across projects
- **Quality automation** (formatting, linting, validation)
- **Security tools** (key validation, environment checks)
- **Workflow helpers** (git operations, branch management)

**Command Naming Convention:**
```text
{category}-{action}-{object}.md
```

**Categories:**
- `quality-*`: Code formatting, linting, standards (< 5 min)
- `security-*`: Security validation, environment checks (< 5 min)
- `workflow-*`: Git operations, branch management (5-15 min)
- `test-*`: Testing, coverage, validation (variable time)
- `meta-*`: Command management, help utilities (< 2 min)

---

### Scripts & Automation
```text
scripts/
├── setup-env.sh             # 🎯 Environment setup and validation
├── mcp-manager.sh           # 🎯 MCP server installation
├── check-mcp-env.sh         # 🎯 MCP environment validation
├── tdd-enforcement-hook.sh  # 🎯 Pre-tool-use TDD enforcement
├── track-mcp-usage.sh       # 🎯 Post-tool-use MCP tracking
└── session-health-check.sh  # 🎯 Session startup validation
```

**What belongs here:**
- **Environment setup** and validation scripts
- **Hook implementations** for Claude Code events
- **MCP server management** utilities
- **Automation helpers** for development workflow

**Script Categories:**
- Setup: Initial environment configuration
- Hooks: Claude Code event handlers
- Validation: Environment and tool checking
- Management: MCP server and tool management

---

### Technical Documentation
```text
docs/
├── response-aware-development.md  # 🎯 RAD methodology and practices
├── tdd-enforcement-system.md      # 🎯 TDD hook implementation
├── hybrid-mcp-conversion-goals.md # 🎯 MCP architecture strategy
├── agent-context-analysis.md      # 🎯 Agent system documentation
└── [other technical docs]         # 🎯 Implementation details
```

**What belongs here:**
- **Technical implementation** details and architecture
- **Methodology documentation** (RAD, TDD, etc.)
- **System analysis** and design decisions
- **Integration guides** and technical references

**What does NOT belong here:**
- User-facing guides (goes in root `.md` files)
- Quick reference materials (goes in root)

---

### Context & Standards
```text
context/
├── development-standards.md  # 🎯 Coding standards and practices
├── integration-patterns.md   # 🎯 Common integration patterns
└── shared-architecture.md    # 🎯 Architectural guidelines
```

**What belongs here:**
- **Shared development context** across projects
- **Architectural patterns** and guidelines
- **Integration standards** and best practices

---

### Data & Configuration Storage
```text
data/
├── promptcraft/             # 🎯 PromptCraft integration data
│   ├── channel_config.json
│   └── performance_metrics.json
└── [other data stores]      # 🎯 Tool-specific data
```

**What belongs here:**
- **Tool-specific configuration** data
- **Performance metrics** and analytics
- **Integration data** for external tools

**⚠️ Important:** Add sensitive data paths to `.gitignore`

---

### Temporary & Generated Files (IGNORED)
```markdown
# These should be in .gitignore
.mypy_cache/                 # 🚫 MyPy type checking cache
__pycache__/                 # 🚫 Python bytecode cache
node_modules/                # 🚫 Node.js dependencies
*.backup                     # 🚫 Backup files
.credentials.json            # 🚫 Sensitive credentials
.env                        # 🚫 Environment variables
```

---

## 🎯 Decision Matrix: Where Does It Go?

### Configuration

| Item | Location | Reason |
|------|----------|---------|
| MCP server definitions | `mcp/{name}.json` | Version control, team sharing |
| Tool permissions | `settings.json` | Project-specific settings |
| Credentials/API keys | `.env` (ignored) | Security - never commit |
| Hook scripts | `scripts/` | Automation, reusable |

### Documentation

| Item | Location | Reason |
|------|----------|---------|
| Getting started | `README.md` | First thing users see |
| Development standards | `CLAUDE.md` | Auto-loaded by Claude Code |
| Organization guide | `PROJECT-ORGANIZATION-GUIDE.md` | Reference for maintenance |
| Technical details | `docs/` | Implementation specifics |

### Tools & Automation

| Item | Location | Reason |
|------|----------|---------|
| Slash commands | `commands/` | Claude Code auto-discovery |
| Custom agents | `agents/` | Reusable specialists |
| Setup scripts | `scripts/` | Environment automation |
| Hooks | `scripts/` | Event-driven automation |

### Data & Temporary

| Item | Location | Reason |
|------|----------|---------|
| Tool data | `data/` | Organized storage |
| Cache files | `.gitignore` | Never commit |
| Backups | `.gitignore` | Temporary files |

---

## ✅ Quality Gates

### Before Adding New Content

**Ask these questions:**

1. **Is it reusable?** → `commands/` or `agents/`
2. **Is it configuration?** → `mcp/` or `settings.json`
3. **Is it documentation?** → Root level or `docs/`
4. **Is it project-specific?** → Belongs in project repo, not here
5. **Is it sensitive?** → Add to `.gitignore`

### File Naming Standards

**Documentation:**
- `UPPER-CASE.md` for main documentation
- `lowercase-with-hyphens.md` for supporting docs

**Configuration:**
- `kebab-case.json` for MCP servers
- `snake_case.json` for data files

**Scripts:**
- `kebab-case.sh` with descriptive names
- Include file extension always

**Commands:**
- `{category}-{action}-{object}.md`
- Use hyphens, not underscores

---

## 🔄 Maintenance Workflow

### Adding New Content

1. **Identify Category** using decision matrix above
2. **Check Naming Convention** for the target directory
3. **Update Documentation** (this guide, README.md, or CLAUDE.md)
4. **Test Integration** with Claude Code
5. **Commit with Clear Message** describing the addition

### Removing Content

1. **Check Dependencies** - what references this content?
2. **Update Documentation** to remove references
3. **Move to Archive** instead of deleting (if valuable)
4. **Update .gitignore** if removing entire categories

### Reorganizing

1. **Follow This Guide** for new organization
2. **Update All References** in documentation
3. **Test All Functionality** after reorganization
4. **Update Team** on changes via commit messages

---

## 🚀 Benefits of This Organization

### For Development
- **Clear Structure**: Know exactly where to find/add content
- **Consistent Naming**: Predictable file and directory names
- **Separation of Concerns**: Configuration, documentation, and tools are separated
- **Version Control**: Only meaningful content is tracked

### For Team Collaboration
- **Shared Standards**: Everyone follows the same organization
- **Easy Onboarding**: New team members know where everything is
- **Reduced Conflicts**: Clear ownership and organization reduces merge conflicts
- **Documentation**: Self-documenting structure

### For Maintenance
- **Scalable**: Structure works as the project grows
- **Searchable**: Organized content is easier to find
- **Updatable**: Clear boundaries make updates easier
- **Debuggable**: Organized configuration is easier to troubleshoot

---

> **Next Steps**: Review this guide when adding new content and reference it in `CLAUDE.md` for team visibility.
