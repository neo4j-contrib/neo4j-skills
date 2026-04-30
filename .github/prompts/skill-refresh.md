# Neo4j Skills Refresh

You are running inside a headless Claude Code session in the `neo4j-skills` repository.
Goal: scan Neo4j release notes and deprecation pages, then update any SKILL.md and references/ files that are stale, outdated, or missing new features. Open no PRs or commits — output only file edits. The workflow will handle git and PR creation.

---

## Step 1 — Fetch release signals

Fetch and read each source. Extract: new syntax, deprecated APIs, removed features, version bumps, new config options, new tools/libraries. Note the source URL and Neo4j version for each finding.

**Release notes / changelogs:**
- https://neo4j.com/release-notes/ — scan releases published in the last 30 days
- https://github.com/neo4j/neo4j/wiki/Neo4j-2026-changelog
- https://github.com/neo4j/neo4j/wiki/Changelog — scan entries from the last 30 days

**Deprecation and removal pages:**
- https://neo4j.com/docs/cypher-manual/current/deprecations-additions-removals-compatibility/
- https://neo4j.com/docs/operations-manual/current/deprecations/
- https://neo4j.com/docs/graphql/current/deprecations/

For each finding, note:
- What changed (new / deprecated / removed / renamed)
- Which Neo4j version introduced it
- Which skill(s) it likely affects

---

## Step 2 — Map findings to skills

Discover skills dynamically:

```bash
ls -d neo4j-*-skill/
```

For each affected skill, read its `SKILL.md` and any linked `references/` files before making changes.

---

## Step 3 — Fetch supporting docs

For each finding that affects a skill, fetch the relevant section of the actual Neo4j docs to get precise new syntax, parameter names, and examples before editing. Do not guess API shape from release note summaries alone.

Doc roots:
- Cypher manual: https://neo4j.com/docs/cypher-manual/current/
- Operations manual: https://neo4j.com/docs/operations-manual/current/
- Python driver: https://neo4j.com/docs/python-manual/current/
- JavaScript driver: https://neo4j.com/docs/javascript-manual/current/
- Java driver: https://neo4j.com/docs/java-manual/current/
- Go driver: https://neo4j.com/docs/go-manual/current/
- .NET driver: https://neo4j.com/docs/dotnet-manual/current/
- GDS: https://neo4j.com/docs/graph-data-science/current/
- GraphRAG Python client: https://neo4j.com/docs/graph-data-science-client/current/
- GraphQL: https://neo4j.com/docs/graphql/current/
- Aura: https://neo4j.com/docs/aura/current/
- Kafka connector: https://neo4j.com/docs/kafka/current/
- Spark connector: https://neo4j.com/docs/spark/current/

---

## Step 4 — Edit skills and references

Read `AGENTS.md` before editing anything. It contains the authoritative rules for skill structure, terse language, decision tables, and quality gates.

Apply changes. Read each file fully before editing.

**What to update:**
- Version numbers that are out of date (driver versions, GDS versions, product versions)
- Deprecated syntax replaced with current syntax, and add new alternative
- Removed APIs — remove examples and add migration pointer
- New features worth knowing — add to relevant section or references/ file
- Broken `Does NOT handle X — use Y-skill` pointers (if a skill was renamed or added)

**What NOT to change:**
- Content you are not confident is outdated — leave it and note it in the summary
- Architectural patterns that are still valid
- Code examples that are still correct
- **GQL syntactic synonyms** (`FOR`, `FILTER`, `LET`, `PROPERTY_EXISTS`, `IS [NOT] LABELED`, etc.) — document only as a compact alias table with a "GQL compliance only — use Cypher equivalents" note. Do not add per-alias examples, separate sections, or version-gate rows for each. One table row in the references file is sufficient.

**Quality rules (all must pass before you finish):**

1. **Line budget**: `SKILL.md` ≤ 500 lines. If a SKILL.md would exceed 500 lines after additions, move new content to a `references/` file and add a link.

2. **Terse language**: Follow caveman compression — no section intros restating headings, no hedging, no passive-voice padding. See AGENTS.md for the full rule with examples and decision tables.

3. **Cypher comments**: Use `//` only. `--` is a SQL comment and a Cypher parse error. Check every Cypher block you write or edit.

4. **Named properties**: `RETURN n.name, n.email` not `RETURN n` or `RETURN *`. Exception: diagnostic/schema queries.

5. **No placeholder text**: No `[TODO]`, `[INSERT]`, `[Your Value Here]`.

6. **Negative triggers**: Every `description:` field must end with at least one `Does NOT handle X — use Y-skill` line.

7. **Linter**: Run `python3 scripts/lint_skills.py` after all edits. Fix any failures before finishing. Only tracked files are checked — new files must be `git add`-ed first.

---

## Step 5 — Lint

```bash
git add $(git ls-files --modified --others --exclude-standard | grep -E '^neo4j-.*-skill/')
python3 scripts/lint_skills.py
```

If the linter fails, fix all violations and re-run until it passes.

---

## Step 6 — Output summary

Print a summary in this exact format (used by the workflow to populate the PR body). The sentinel line must appear exactly as shown — the workflow extracts everything after it.

```
<!-- SUMMARY_START -->
## Skills Refresh Summary

### Sources scanned
- <URL> — <date or version range covered>

### Changes made
- `<skill-dir>/<file>`: <one-line reason> [<Neo4j version>]

### Findings not acted on (uncertain or low confidence)
- <finding>: <reason not acted on>

### Linter
All N SKILL.md files passed.
```

If no changes were needed, print:
```
<!-- SUMMARY_START -->
## Skills Refresh Summary
No updates required — all skills current as of <today's date>.
```
