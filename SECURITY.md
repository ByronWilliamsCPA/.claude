# Security Guide for Claude Global Configuration

## Reporting Security Vulnerabilities

Report vulnerabilities privately via GitHub Security Advisories. Navigate to
the Security tab of this repository and click "Report a vulnerability". Do not
file public issues for security vulnerabilities; public disclosure before a
fix is available puts all users at risk.

Report a new vulnerability at:
[GitHub Security Advisories](https://github.com/ByronWilliamsCPA/.claude/security/advisories/new)

The full Security Advisories tab is at:
[GitHub Security Advisories](https://github.com/ByronWilliamsCPA/.claude/security/advisories)

We will acknowledge your report within 14 days of receipt. The maximum initial
response time is 14 days. After acknowledgment, we will provide a timeline for
a fix and coordinate disclosure with you before any public announcement.

For questions about the scope of this policy, contact the maintainer directly
via the GitHub Security Advisories channel above.

---

## API Key Management

### Overview
This configuration uses environment variables to securely manage API keys for MCP servers. **NEVER commit actual API keys to Git repositories**.

### Security Architecture

```text
~/.claude/
├── .env                  # LOCAL ONLY - Contains actual API keys (git-ignored)
├── .env.example          # COMMITTED - Template showing required variables
└── mcp/
    ├── common-servers.json     # Uses ${VARIABLE} references
    ├── github-server.json      # Uses ${GITHUB_PERSONAL_ACCESS_TOKEN}
    └── dev-tools-servers.json  # Uses ${GIT_REPO_PATH}
```

### Initial Setup

1. **Clone the repository**:
   ```bash
   cd ~
   git clone https://github.com/your-username/.claude.git
   ```

2. **Run the environment setup script**:
   ```bash
   ~/.claude/scripts/setup-env.sh
   ```
   This script:
   - Creates `.env` from `.env.example`
   - Sets secure permissions (600 - owner read/write only)
   - Provides instructions for adding API keys

3. **Add your API keys**:
   ```bash
   # Edit with your preferred editor
   nano ~/.claude/.env
   # or
   vim ~/.claude/.env
   ```

### Required API Keys

| Variable | Service | How to Obtain |
|----------|---------|---------------|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub MCP Server | [Create at github.com/settings/tokens](https://github.com/settings/tokens) |
| `PERPLEXITY_API_KEY` | Perplexity Search | [Get from Perplexity settings](https://www.perplexity.ai/settings/api) |
| `TAVILY_API_KEY` | Tavily Search | [Sign up at tavily.com](https://tavily.com) |
| `UPSTASH_REDIS_REST_URL` | Context7 | [Create at upstash.com](https://upstash.com) |
| `UPSTASH_REDIS_REST_TOKEN` | Context7 | From Upstash dashboard |
| `SENTRY_AUTH_TOKEN` | Sentry | [Create at sentry.io](https://sentry.io/settings/auth-tokens/) |
| `ZAPIER_API_KEY` | Zapier | [Get from Zapier settings](https://zapier.com/app/settings/integrations) |

### Security Best Practices

#### 1. **File Permissions**
```bash
# Verify .env has secure permissions
ls -la ~/.claude/.env
# Should show: -rw------- (600)

# Fix permissions if needed
chmod 600 ~/.claude/.env
```

#### 2. **Git Safety**
- `.env` is in `.gitignore` - never remove this
- Always use `git status` before committing to verify
- If you accidentally commit secrets:
  1. Immediately rotate the exposed keys
  2. Use `git filter-branch` or BFG to remove from history
  3. Force push to update remote

#### 3. **Key Rotation**
- Rotate API keys every 90 days
- Use minimal permissions for each key
- Monitor key usage in respective services

#### 4. **Backup Strategy**
```bash
# Secure backup with encryption
gpg -c ~/.claude/.env
# Creates ~/.claude/.env.gpg

# Restore from backup
gpg -d ~/.claude/.env.gpg > ~/.claude/.env
chmod 600 ~/.claude/.env
```

### MCP Server Configuration

MCP servers reference environment variables using `${VARIABLE_NAME}` syntax:

```json
{
  "mcpServers": {
    "github": {
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

Claude Code automatically:
1. Reads the MCP configuration
2. Substitutes `${VARIABLE_NAME}` with values from environment
3. Passes the actual values to the MCP servers

### Troubleshooting

#### Missing Environment Variables
If an MCP server fails to start:
1. Check if the variable is defined: `grep VARIABLE_NAME ~/.claude/.env`
2. Ensure no typos in variable names
3. Verify the .env file is in the correct location

#### Permission Errors
```bash
# Fix ownership
chown $USER:$USER ~/.claude/.env

# Fix permissions
chmod 600 ~/.claude/.env
```

#### Variable Not Loading
1. Restart Claude Code after modifying .env
2. Check for syntax errors in .env file
3. Ensure no spaces around `=` in assignments

### Security Checklist

Before using the configuration:
- [ ] `.env` file exists and has 600 permissions
- [ ] All required API keys are added to `.env`
- [ ] No API keys in any `.json` files (only `${VARIABLE}` references)
- [ ] `.gitignore` includes `.env` and `.env.*`
- [ ] Backup of `.env` is encrypted and stored securely
- [ ] API keys have minimal required permissions
- [ ] Key rotation schedule is documented

### Emergency Response

If API keys are exposed:
1. **Immediately revoke** the exposed keys in their respective services
2. **Generate new keys** with minimal permissions
3. **Update** your local `.env` file
4. **Audit** access logs in affected services
5. **Notify** team members if using shared services
6. **Review** how the exposure occurred and update procedures

### Additional Resources

- [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [Best practices for API key safety](https://cloud.google.com/docs/authentication/api-keys#securing_an_api_key)
- [12 Factor App: Config](https://12factor.net/config)
