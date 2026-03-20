# AGENTS.md — neo4j-skills

## Feedback Commands

- Run extraction tests: `cd skill-generation-validation-tools && uv run python3 scripts/test-extract-references.py`
- Run harness (once built): `uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/tests/harness/runner.py --cases skill-generation-validation-tools/tests/cases/ --skill neo4j-cypher-authoring-skill`
- Lint YAML: `yamllint .github/workflows/`

## Conventions

- Skill directories: `neo4j-<name>-skill/` containing `SKILL.md`, optional `references/`, `VERSION`
- L3 reference files live in `neo4j-cypher-authoring-skill/references/` organized by category:
  - `references/read/` — patterns, functions, read subqueries (COUNT/COLLECT/EXISTS/CALL), types-and-nulls
  - `references/write/` — CALL IN TRANSACTIONS, bulk writes
  - `references/schema/` — indexes, constraints, DDL (SHOW INDEXES, SHOW CONSTRAINTS, SHOW PROCEDURES)
  - `references/admin/` — database admin: users, roles, privileges, CREATE/DROP DATABASE, SHOW TRANSACTIONS, SHOW SERVERS
  - `references/` root — style-guide (cross-cutting)
- Generation/validation tools live in `skill-generation-validation-tools/` (scripts/, tests/, pyproject.toml)
- Test harness: `skill-generation-validation-tools/tests/harness/`, test cases: `skill-generation-validation-tools/tests/cases/`

## Submodule Notes

- `docs-cypher` → `git@github.com:neo4j/docs-cypher.git` pinned to `2026.01.0`
- `docs-cheat-sheet` → `git@github.com:neo4j/docs-cheat-sheet.git` pinned to `2026.02.0`
- Tag naming convention: `YYYY.MM.PATCH` (e.g. `2026.01.0`)
- After cloning: `git submodule update --init --recursive`

## Gotchas

- Both docs repos were originally plain cloned directories (untracked). Used `git submodule add --force` to convert without losing data.
- docs-cheat-sheet is on a newer tag (2026.02.0) than docs-cypher (2026.01.0) — update both together when pinning to new releases.
- GQL-excluded clauses: LET, FINISH, FILTER, NEXT, INSERT — strip these from all L3 reference files.
- SCHEMA vs ADMIN split: `schema/` = indexes/constraints/DDL/SHOW PROCEDURES; `admin/` = databases, users, roles, privileges, SHOW TRANSACTIONS, SHOW SERVERS. Don't conflate them.
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
- `CALL { ... } IN TRANSACTIONS` is only allowed in implicit transactions — not inside explicit `BEGIN`/`COMMIT` blocks. Batching applies to input rows fed *outside* the subquery; matching inside the subquery collapses to one transaction.
- `COUNT {}` vs `count()`: `COUNT { pattern }` is a subquery counting rows; `count(expr)` is an aggregating function. They are not interchangeable — `count()` must appear in a clause that has an aggregation context.
- CALL subquery scope clause (`CALL (x, y) { }`) is Cypher 25 standard; importing `WITH` as first clause inside CALL is deprecated. Use `CALL ()` for isolated, `CALL (*)` for all-vars, `CALL (x)` for specific imports.
- Type predicates: `IS :: TYPE` returns `true` for `null` by default (all types include null). Append `NOT NULL` to exclude null: `x IS :: INTEGER NOT NULL`. Negation `IS NOT ::` returns `false` for null by default.
- Closed Dynamic Unions: `val IS :: INTEGER | FLOAT` tests multiple types; all inner types must have same nullability (all nullable or all `NOT NULL`).
- Casting: base functions (`toFloat`, `toInteger`, etc.) throw on unconvertible input; `OrNull` variants (`toFloatOrNull`, etc.) return `null` instead — prefer OrNull in agent-authored queries to avoid runtime errors.
- `null = null` → `null` (not `true`); `null <> null` → `null`. Always use `IS NULL` / `IS NOT NULL`.
- Style guide keyword list (keywords.adoc) is 400 items — useless for agents. What agents need: UPPERCASE for clauses/operators, camelCase for functions, lowercase for `null`/`true`/`false`. Document this as a casing rules table, not a keyword enumeration.

## Python / uv

- All generation/validation tools live in `skill-generation-validation-tools/` — kept outside `neo4j-cypher-authoring-skill/` so they don't pollute the installed skill.
- `pyproject.toml` lives in `skill-generation-validation-tools/` (not repo root).
- Local dev: `cd skill-generation-validation-tools && uv venv && uv run python3 scripts/extract-references.py ...`
- From repo root: `uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/scripts/...`
- GH Actions: `working-directory: skill-generation-validation-tools` for `uv venv`; script calls use `uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/...`

## Scripts

- `skill-generation-validation-tools/scripts/extract-references.py` — extract asciidoc → Markdown for L3 reference files. Run with `--dry-run` to preview without writing.
- `skill-generation-validation-tools/scripts/test-extract-references.py` — test suite. Run from the tools dir: `uv run python3 scripts/test-extract-references.py`
- `skill-generation-validation-tools/scripts/extract-changelog.py` — parse changelog adoc → Markdown. Usage: `uv run python3 scripts/extract-changelog.py --src ../../docs-cypher/modules/ROOT/pages/deprecations-additions-removals-compatibility.adoc --out path/changelog.md [--since 2026.01]`

### extract-references.py — Hybrid Workflow

The script generates **first drafts** for L3 reference files (not final output). After generation, manually curate to improve density and accuracy. Then re-run the script only when submodule pins change.

**Key behaviors:**
- `skip_preamble=True` per source: strips everything before the first `==` section (level-2+ heading), not just the title. Critical for docs-cypher pages which have verbose intro paragraphs.
- `max_code_blocks=N` per source: limits code blocks per file (set 1–3 for docs-cypher, 0 for cheat-sheet inline files).
- `////` comment blocks stripped (test-setup CREATEs in cheat-sheet are wrapped in `////`).
- `[source, ..., role=test-setup]` blocks skipped entirely (no output).
- `[source, role="queryresult"...]` tables skipped (result output tables).
- `// tag::name[]` / `// end::name[]` markers stripped (inline tag delimiters in docs-cypher).
- `[.description]`, `[%collapsible]`, `[options=...]` annotations stripped.
- `|====` (4-sign) tables handled in addition to `|===` (3-sign).
- `include::` directives resolved locally: `{attr}/docs-cypher/.../pages/PATH` → `cypher_src/PATH`; tag-filtered sections extracted.

**Cheat-sheet files and includes:** Only ~44/101 cheat-sheet pages have inline content; the rest use `include::` that reference docs-cypher by tag. Both cases now work: inline content is extracted directly, include-based content resolves to the tagged section in docs-cypher.

**Config ordering:** Put cheat-sheet inline sources first in EXTRACTION_CONFIGS so truncation preserves the most concise content.

**GH Action update workflow:** When bumping a submodule pin (e.g., docs-cypher 2026.01.0 → 2026.02.0), run `python3 scripts/extract-references.py` to regenerate all L3 drafts, inspect `git diff` on the generated files, manually curate any sections that degraded, and commit. No diff-based update plan needed — full regeneration is idempotent and fast.

## GH Actions Notes

- `.yamllint` config in repo root with `line-length: max: 160` is needed — GH Actions `${{ expressions }}` routinely exceed 80 chars.
- Two-gate PR creation: `has_update` (tags differ) + `has_changes` (git diff non-empty). Both required to avoid spurious PRs.
- `breaking-change` label must be pre-created in the GitHub repo; the workflow won't auto-create it.
- `workflow_dispatch` `target_tag` input applies to both submodules. Use the same version tag for both unless you need independent control.
- Changelog `--since` arg should be the OLD (current) tag, not the new one, so only new-release entries appear in the PR body.
- heredoc in a GH Actions `run:` block works for VERSION file rewrite — use `<<EOF` / `EOF` with `cat >` to avoid quoting issues.
- Test workflows should handle missing harness gracefully: use a harness-availability check step + placeholder report so structural checks still run before harness tasks are complete.
- Store harness exit code as a step output, then evaluate in a separate step — ensures artifact upload runs even when harness reports failures.
- `actions/github-script@v7` is simpler than `gh pr comment` for posting multi-line dynamic content to PRs.
- Include `run_id` in artifact names to avoid collisions on concurrent workflow runs.

## Changelog Parser Notes (extract-changelog.py)

- AsciiDoc table rows are `a|` (feature cell with code) then `|` (details cell). Together they form ONE entry — do NOT flush on `|`, only on next `a|`.
- Only `[source, cypher]` and `[source, role=noheader]` blocks are extracted; `[source, csv]`, `[source, javascript]` etc. are skipped but still consumed.
- `--since VERSION` filters rendered output AND the summary count. Useful in GH Actions to report only what changed in the new submodule pin.
- Empty sections correctly render `_No entries._` (not missing or crash).

## Runner Notes (tests/harness/runner.py)

- Claude headless invocation: `claude --skill <name> --print --output-format text` with prompt on stdin.
- Cypher extraction: regex ```` ```(?:cypher|CYPHER)\s*\n(.*?)``` ```` with DOTALL — matches both casings.
- Dry-run (`--dry-run`): validates YAML structure (required fields, duplicate IDs, valid difficulty) without executing queries or invoking Claude. Exits 0 on valid YAML.
- Exit codes: 0 = all PASS, 1 = any FAIL, 2 = any WARN (no FAIL).
- TestCaseResult fields: verdict, failed_gate, warned_gate, generated_cypher, metrics, gate_details, error (runner-level), duration_s.
- pyyaml is a required dep (added to pyproject.toml) — needed in CI runner context, not just dev.
- Neo4j driver lazy-imported at runtime — dry-run and YAML validation work without the neo4j package.
- Test case YAML key: `cases:` (list); each entry needs `id`, `question`; optional `database`, `difficulty`, `tags`, `domain`, `min_results`, `max_db_hits`, `max_allocated_memory_bytes`, `max_runtime_ms`, `is_write_query`.

## Validator Notes (tests/harness/validator.py)

- Gate 3 source checks (GQL-excluded clauses, deprecated syntax regexes) run BEFORE any DB execution. GQL-excluded clause FAIL exits early without touching the DB.
- Write query test isolation: `driver.session().begin_transaction()` → always `tx.rollback()`. NOT `CALL IN TRANSACTIONS` (that requires implicit txn scope, not allowed inside explicit BEGIN).
- PROFILE metrics are extracted recursively from the plan tree (`_sum_plan_attr()`). The `GlobalMemory` value for `totalAllocatedMemory` lives in `plan.arguments['GlobalMemory']` on the root plan node only.
- `extract_profile_metrics()` accepts: neo4j driver ProfiledPlan object, plain dict (for mocks), or raw PROFILE text string (heuristic parse). Supports all three for flexibility in tests.
- CYPHER 25 pragma is preserved when prepending EXPLAIN/PROFILE: pragma stays as the first token, EXPLAIN/PROFILE is inserted on the next line.
- `_prepend_explain()` / `_prepend_profile()` handle both `CYPHER 25\nQUERY` and plain `QUERY` forms.
- Smoke tests run with: `uv run python3 tests/harness/validator.py` (no DB connection needed).

## Reporter Notes (tests/harness/reporter.py)

- CLI: `reporter.py --input run.json --output run.md`; direct invocation (`python3 reporter.py` no args) runs smoke tests.
- Standalone — no imports from runner.py or validator.py; defines its own PASS/WARN/FAIL constants for use in isolation (e.g. CI steps with only the JSON artifact).
- Uses `statistics.median()` from stdlib; no extra deps.
- Failure Analysis groups FAIL cases by `failed_gate` and WARN cases by `warned_gate` separately.
- Cypher excerpts in failure blocks capped at 10 lines for readability.
- `_truncate()` escapes `|` chars in question text to prevent Markdown table breakage.
- Smoke tests: `uv run python3 tests/harness/reporter.py` (no DB or Claude needed).

## Generator Notes (tests/harness/generator.py)

- CLI: `uv run python3 tests/harness/generator.py --domain companies --database companies --output-dir tests/cases/ [--dry-run]`
- Property sampling uses `COLLECT { MATCH (m:\`Label\`) WHERE m.\`prop\` IS NOT NULL RETURN DISTINCT m.\`prop\` LIMIT 100 } AS samples` — this is the correct Cypher 25 form (not `collect()[..N]`).
- Semantic inference priority: sparse check first (runs before empty-samples check) → uuid (regex) → freetext (long text) → score (float in [-1,1]) → range (high-cardinality numeric) → name-based hinting (freetext/score keywords before enum fallback) → enum (low-cardinality) → unknown.
- Name-based hinting runs BEFORE enum fallback — properties named `summary`, `description`, `sentiment` get correct semantics regardless of sample cardinality. Only `id`/`key` name hints come after enum to avoid false positives.
- `inferred_semantics` written as a structured dict field (not YAML comments) — pyyaml cannot write per-key comments; the field achieves the same goal for human reviewers.
- Output: `tests/cases/{domain}-generated.yml` — never `{domain}.yml`. Requires explicit human promotion step.
- Tolerance multipliers: `max_db_hits = observed × 3`, `max_allocated_memory_bytes = observed × 3`, `max_runtime_ms = observed × 5` (runtime has 5× because CI timing variability is high).
- Dry-run skips Claude calls and all file writes. Use it to verify schema connectivity and inspect what would be generated.
- Generator imports `extract_profile_metrics` from validator.py at runtime (not at module level) so it works from both `tests/harness/` and repo root paths.

## SKILL.md Authoring Notes

- SKILL.md line budget is 300 lines (not 300 non-blank lines). Inline `CYPHER 25` on the same line as each query to save ~10 lines in the Schema-First Protocol section.
- Verified with: `wc -l SKILL.md` (lines) + `python3 -c "words=len(text.split()); print(int(words*1.3))"` (token estimate).
- task-020 (WebFetch proactive framing) was folded into task-010's SKILL.md — the proactive framing is already present. task-020 can be marked as superseded or trivially completed.
- SEARCH clause (Neo4j 2026.01 Preview) is **vector-only** — always document the fulltext procedure fallback alongside it.
