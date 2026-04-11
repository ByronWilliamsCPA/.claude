# Settings and Permissions

## Five-scope hierarchy (precedence order, lowest to highest)

1. Managed policy (server-enforced; cannot be overridden)
2. Claude Code CLI args (`--allowedTools`, `--disallowedTools`)
3. `.claude/settings.local.json` (gitignored per-machine overrides)
4. `.claude/settings.json` (project-committed shared settings)
5. `~/.claude/settings.json` (global user settings)

When the same key appears at multiple scopes, the highest scope wins.

## Evaluation order for `permissions.*`

Within a single settings file:

1. `deny` -- if matched, the operation is blocked unconditionally
2. `ask` -- if matched, Claude pauses for human confirmation
3. `allow` -- if matched and not denied, runs without interruption

`deny` is the floor. No `allow` entry overrides a `deny` entry at the same scope.

Path prefix syntax: `Bash(rm:*)` matches any Bash call starting with `rm`.
Tool + path form: `Read(/etc/passwd)` restricts a specific path.

## Sandbox architectural layer

`sandbox.filesystem` and `sandbox.network` are OS-level isolation controls that
operate beneath the `permissions.*` evaluation. A `deny` entry stops Claude from
attempting the operation; sandbox contains the blast radius if it runs anyway.

When `sandbox.enabled: true`, filesystem writes are restricted to the project
directory tree, and network calls go through a filtering proxy.

## Our current posture

- `sandbox.enabled: false` in `~/.claude/settings.json` -- appropriate for trusted
  local development.
- `permissions.ask` contains 22 entries covering destructive bash commands.
  See `~/.claude/settings.json` for the full list.

## Sources

- Claude Code settings: <https://code.claude.com/docs/en/settings>
- Permissions and sandbox: <https://code.claude.com/docs/en/permissions>
- Settings JSON schema: <https://json.schemastore.org/claude-code-settings.json>
