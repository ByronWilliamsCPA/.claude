# Diagram Maintenance Skill

> **Triggers**: "update diagram", "add diagram", "diagram audit", "PUML", "plantuml",
> "architecture diagram", "traceability check", "regenerate SVG", "diagram gaps",
> "diagram consistency", "stale diagram", "diagram index"

Orchestrates diagram maintenance tasks by delegating to the `diagram-maintenance-agent`.
Supports four modes depending on the request.

---

## Mode Detection

Determine the mode from the user's request:

| Mode | Keywords / Intent |
|------|------------------|
| **audit** | "diagram audit", "check diagrams", "stale", "gaps", "traceability check" |
| **update** | "update diagram", "diagram is outdated", "reflect changes in diagram", "rename in diagram" |
| **create** | "add diagram", "new diagram", "create PUML", "document this workflow" |
| **svg** | "regenerate SVG", "SVG out of date", "rebuild diagrams" |

---

## Mode: audit

Scan all diagrams for quality issues and report findings.

1. Read `docs/architecture/diagrams/INDEX.md` (or `DIAGRAM_INDEX.md`)
2. Delegate to `diagram-maintenance-agent` with this prompt:

```
Perform a traceability audit of all diagrams in docs/architecture/diagrams/.

Report:
1. Source files referenced in PUML notes that no longer exist
2. Source files in monitored directories that are NOT referenced in any diagram
3. Diagrams missing traceability notes entirely
4. Index entries that don't match existing PUML files
5. SVG files that are older than their corresponding PUML file

Format findings as:
- STALE REFERENCES: [list]
- UNDOCUMENTED SOURCE FILES: [list]
- MISSING TRACEABILITY: [list]
- INDEX MISMATCHES: [list]
- SVGs NEEDING REGENERATION: [list]
```

3. Present findings grouped by severity

---

## Mode: update

Update one or more diagrams to reflect code changes.

1. Identify which diagrams are affected (ask if unclear)
2. Delegate to `diagram-maintenance-agent` with this prompt:

```
Update the following diagrams to reflect these changes: [USER_CHANGES]

Steps:
1. Read the current PUML file(s)
2. Apply the changes (renamed files, new components, removed components, scope adjustments)
3. Update traceability notes with correct source file paths
4. Update INDEX.md / DIAGRAM_INDEX.md entries
5. List which SVG files need regeneration

Apply project color conventions from docs/architecture/STYLE_GUIDE.md if it exists.
```

3. After agent completes, offer to run SVG regeneration

---

## Mode: create

Create a new diagram for an undocumented component or workflow.

1. Clarify: what component/workflow, which hierarchy level, which parent diagram
2. Delegate to `diagram-maintenance-agent` with this prompt:

```
Create a new [LEVEL] diagram for [COMPONENT/WORKFLOW].

Requirements:
1. Follow the file reference pattern appropriate for this level
2. Apply project color conventions from STYLE_GUIDE.md
3. Include traceability notes linking to all relevant source files
4. Add a cross-reference link in the parent diagram
5. Add an entry to INDEX.md / DIAGRAM_INDEX.md
6. Use abbreviated path notation in notes

Parent diagram to update: [PARENT_DIAGRAM_PATH]
New diagram location: docs/architecture/diagrams/[LEVEL]/[FILENAME].puml
```

3. After agent creates the file, offer SVG generation and optional AI visual

---

## Mode: svg

Regenerate SVG files for changed PUML files.

```bash
# Check which files need regeneration
python3 tools/generate_diagram_svgs.py --check

# Regenerate all changed files
python3 tools/generate_diagram_svgs.py

# Force all
python3 tools/generate_diagram_svgs.py --all
```

If `tools/generate_diagram_svgs.py` does not exist, inform the user that the SVG generation
tool is not set up for this project and point them to the image_detection project as a
reference implementation.

---

## Post-Task Checklist

After any diagram operation, verify:

- [ ] PUML syntax is valid (no unclosed blocks, invalid arrows)
- [ ] SVG regenerated for modified PUML files
- [ ] INDEX.md / DIAGRAM_INDEX.md updated
- [ ] No broken documentation links (`[[...]]` references)
- [ ] Color conventions consistent with STYLE_GUIDE.md
- [ ] Traceability notes present on all modified components
