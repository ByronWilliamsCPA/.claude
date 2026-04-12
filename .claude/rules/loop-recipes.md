# Loop Recipes

`/loop` runs a skill repeatedly on a scheduled interval. Use for babysit-style
automation that benefits from repeated lightweight passes.

## Approved recipes

### `/loop 6h /doc-audit`

Audits documentation for drift every 6 hours. The `doc-audit` skill checks that
docs still match code.

```text
/loop 6h /doc-audit
```

### `/loop 30m /sonarcloud`

Polls SonarQube for new issues every 30 minutes during active development.

```text
/loop 30m /sonarcloud
```

## Required safeguards

Before running any loop unattended:

1. **Cost circuit breaker:** Set a hard-stop timer. Do not leave a loop running
   for more than 4 hours without checking the API cost. Claude Code currently has
   no built-in cost cap for `/loop`.
2. **Token budget:** Monitor `~/.claude/logs/` for context-window growth. A
   malformed loop prompt can inflate context without useful work.
3. **Self-termination:** The `/loop` 7-day auto-expiry is the backstop, not the
   primary cost control.

## When NOT to use `/loop`

- Do not use `/loop` for workflows that depend on external state that changes
  on a different cadence (API rate limits, external service uptime).
- Do not run more than one loop unattended overnight without a cost alert.

## Sources

- Boris Cherny, Jan 3 2026 (13 tips): <https://x.com/bcherny/status/2007179832300581177>
