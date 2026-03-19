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
- Asciidoc `[source, role=noheader]` has no language tag — guard against capturing `role` as the language identifier.
- Asciidoc source block language tracking: set `pending_source_lang` when `[source, lang]` is seen, consume it when `----` is encountered (not via lookback into output_lines).
- Submodule SHA detection: `docs-cypher/modules/ROOT/pages` is 3 parents up from the submodule root (`pages` → `ROOT` → `modules` → `docs-cypher`).
- Token budget: reserve ~20 tokens headroom for the truncation notice itself.
- L3 reference files for docs-cypher are better authored manually, not auto-extracted: source docs are verbose (setup graphs, narrative prose) and hit the token budget before covering all required content. The extraction script is better suited for docs-cheat-sheet which is already concise.
- DIFFERENT RELATIONSHIPS and REPEATABLE ELEMENTS match modes only available since Neo4j 2025.06 / Cypher 25. REPEATABLE ELEMENTS requires bounded quantifiers (no +, *, {1,}).
- `SHORTEST` keyword replaces deprecated `shortestPath()` / `allShortestPaths()` functions in Cypher 25.
- `id()` is deprecated — prefer `elementId()` which returns a `STRING` stable only within a single transaction.
- `vector()` constructor is new in Neo4j 2025.10; `vector.similarity.cosine()` and `vector.similarity.euclidean()` existed before.
- Aggregating functions: `collect(null)` → `[]` (empty list), `count(null)` → `0`, `sum(null)` → `0`; all others → `null` when all inputs are null.
- `SEARCH` clause (Neo4j 2026.01+, Preview) is **vector-only** — fulltext indexes still use `db.index.fulltext.queryNodes()` procedure. The SEARCH clause does not cover fulltext indexes.
- Vector index `OPTIONS` map is **mandatory** — `vector.dimensions` and `vector.similarity_function` are required at creation time.
- `USING INDEX SEEK` forces index seek (not scan); `USING SCAN` forces label scan with no index — opposite of intent, so use `USING SCAN` only to deliberately avoid indexes.
- Index `state` values: `ONLINE` (usable), `POPULATING` (building — check `populationPercent`), `FAILED`.

## Scripts

- `scripts/extract-references.py` — extract asciidoc → Markdown for L3 reference files. Run with `--dry-run` to preview without writing.
- `scripts/test-extract-references.py` — test suite for extract-references.py. Run from repo root: `python3 scripts/test-extract-references.py`
