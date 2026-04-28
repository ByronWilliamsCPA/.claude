---
description: Security validation — GPG/SSH key validation, dependency scanning, and encryption. Triggers on "security, scan, audit".
tools: ["Read", "Bash", "Grep", "Glob"]
---

# Security Skill

Security validation, vulnerability scanning, and compliance checking.

## Invocation

```text
/security [scope]
```

**Scope** (optional): `all` (default), `env`, `scan`, `deps`

## Activation

Auto-activates on keywords: security, vulnerability, audit, OWASP, encryption, GPG, SSH, signing, secrets, scan, bandit

## Workflows

### Environment Validation
- **workflows/validate-env.md**: GPG/SSH key validation

### Scanning
- **workflows/scan.md**: Security vulnerability scanning

### Encryption
- **workflows/encrypt.md**: Secret encryption and management

## Workflow

Execute in this order for a full `/security all` run:

**Step 1 — Environment validation** (`/security env`)
```bash
gpg --list-secret-keys
ssh-add -l
git config --get user.signingkey
```

**Step 2 — Code scanning** (`/security scan`)
```bash
uv run bandit -r src/ -c pyproject.toml
uv run semgrep scan --config auto src/
```

**Step 3 — Dependency audit** (`/security deps`)
```bash
uv run pip-audit
```

**Step 4 — Secrets detection**
```bash
gitleaks detect --source .
trufflehog filesystem .
```

## Security Checklist

### Pre-Commit
- [ ] No secrets in code (checked by gitleaks)
- [ ] Dependencies scanned for vulnerabilities
- [ ] Bandit security scan passes

### Pre-Release
- [ ] All known vulnerabilities addressed
- [ ] Security advisory published (if applicable)
- [ ] Dependencies updated to secure versions

## OWASP Top 10 Considerations

1. **Injection**: Use parameterized queries, validate input
2. **Broken Authentication**: Use secure session management
3. **Sensitive Data Exposure**: Encrypt sensitive data at rest and in transit
4. **XML External Entities**: Disable external entity processing
5. **Broken Access Control**: Implement proper authorization checks
6. **Security Misconfiguration**: Use secure defaults
7. **XSS**: Escape output, use Content Security Policy
8. **Insecure Deserialization**: Validate and sanitize serialized data
9. **Using Components with Known Vulnerabilities**: Keep dependencies updated
10. **Insufficient Logging**: Log security events, monitor for anomalies
