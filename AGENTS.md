# AGENTS.md — neo4j-skills

## Feedback Commands

No build/test system exists yet (test harness is a future task). Once tests/harness/ is built:
- Run tests: `python tests/harness/runner.py --cases tests/cases/ --skill neo4j-cypher-authoring-skill`
- Lint YAML: `yamllint .github/workflows/`

## Conventions

- Skill directories: `neo4j-<name>-skill/` containing `SKILL.md`, optional `references/`, `VERSION`
- L3 reference files live in `neo4j-cypher-authoring-skill/references/`
- Scripts live in `scripts/`
- Test harness lives in `tests/harness/`, test cases in `tests/cases/`

## Submodule Notes

- `docs-cypher` → `git@github.com:neo4j/docs-cypher.git` pinned to `2026.01.0`
- `docs-cheat-sheet` → `git@github.com:neo4j/docs-cheat-sheet.git` pinned to `2026.02.0`
- Tag naming convention: `YYYY.MM.PATCH` (e.g. `2026.01.0`)
- After cloning: `git submodule update --init --recursive`

## Gotchas

- Both docs repos were originally plain cloned directories (untracked). Used `git submodule add --force` to convert without losing data.
- docs-cheat-sheet is on a newer tag (2026.02.0) than docs-cypher (2026.01.0) — update both together when pinning to new releases.
- GQL-excluded clauses: LET, FINISH, FILTER, NEXT, INSERT — strip these from all L3 reference files.
- CYPHER 25 pragma: every generated query must begin with `CYPHER 25`.
