# Settings and Permissions

## Five-scope hierarchy (precedence order, lowest to highest)

1. `~/.claude/settings.json` (global user settings; lowest)
2. `.claude/settings.json` (project-committed shared settings)
3. `.claude/settings.local.json` (gitignored per-machine overrides)
4. Claude Code CLI args (`--allowedTools`, `--disallowedTools`)
5. Managed policy (server-enforced; cannot be overridden; highest)

When the same key appears at multiple scopes, the highest scope wins.
Managed policy at scope 5 is the ceiling: no other scope overrides it.

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
- `permissions.ask` contains 30 entries covering destructive bash commands.
  See `~/.claude/settings.json` for the full list.

## Authorization failure modes

Two principles not captured by the permissions schema that apply at runtime:

- **Questions are not consent.** Asking the user whether to proceed is not
  equivalent to being authorized. An unanswered or deflected question grants
  nothing; wait for an explicit answer before acting.
- **Silence is not consent.** User non-intervention between actions does not
  establish approval for the next action. Each significant action requires
  its own authorization basis.

These apply regardless of `permissions.allow` entries. A permission entry
grants capability; it does not grant blanket authorization for all uses of
that capability in a single session.

## Sources

- Claude Code settings: <https://code.claude.com/docs/en/settings>
- Permissions and sandbox: <https://code.claude.com/docs/en/permissions>
- Settings JSON schema: <https://json.schemastore.org/claude-code-settings.json>
