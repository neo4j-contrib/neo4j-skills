# AGENTS.md — neo4j-skills

## Feedback Commands

- Run extraction tests: `cd skill-generation-validation-tools && uv run python3 scripts/test-extract-references.py`
- Run harness (all domains, schema injected): `uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/tests/harness/runner.py --cases skill-generation-validation-tools/tests/cases/ --skill neo4j-cypher-authoring-skill --verbose`
- Run harness (single domain): `uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/tests/harness/runner.py --cases skill-generation-validation-tools/tests/cases/companies.yml --skill neo4j-cypher-authoring-skill --neo4j-uri neo4j+s://demo.neo4jlabs.com:7687 --neo4j-username companies --neo4j-password companies --verbose`
- Run harness (ucfraud, local DB): `uv run --project skill-generation-validation-tools python3 skill-generation-validation-tools/tests/harness/runner.py --cases skill-generation-validation-tools/tests/cases/ucfraud.yml --skill neo4j-cypher-authoring-skill --neo4j-uri bolt://localhost:7687 --neo4j-username neo4j --neo4j-password password --verbose`
- Schema is auto-injected from `tests/schemas/{domain}.json` when the directory exists. Use `--no-schema` to disable for ablation runs.
- Lint YAML: `yamllint .github/workflows/`
- Run harness with specific model: add `--model haiku` (or `sonnet`/`opus`) to any runner.py invocation, or `MODEL=haiku` to any Makefile target.

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
- DIFFERENT RELATIONSHIPS and REPEATABLE ELEMENTS match modes only available since Neo4j 2025.06 / Cypher 25. REPEATABLE ELEMENTS requires bounded quantifiers (no +, *, {1,}). Use REPEATABLE ELEMENTS when counting all walks (including cyclic); use DIFFERENT RELATIONSHIPS (default) for acyclic path finding.
- `+` / `*` QPE shorthands: supported on local Neo4j 2026.02.x but NOT on demo.neo4jlabs.com (2026.02) — always use `{1,}` / `{0,}` for demo/unknown targets.
- `SHORTEST` keyword replaces deprecated `shortestPath()` / `allShortestPaths()` functions in Cypher 25.
- `id()` is deprecated — prefer `elementId()` which returns a `STRING` stable only within a single transaction.
- `vector()` constructor is new in Neo4j 2025.10; `vector.similarity.cosine()` and `vector.similarity.euclidean()` existed before.
- Aggregating functions: `collect(null)` → `[]` (empty list), `count(null)` → `0`, `sum(null)` → `0`; all others → `null` when all inputs are null.
- `SEARCH` clause: **GA in Neo4j 2026.02+**. Vector-only — fulltext indexes still use `db.index.fulltext.queryNodes()` procedure. SEARCH clause does not cover fulltext indexes.
- Test case authoring rule: never use `$param` parameters in test questions for the harness — the harness does not inject runtime parameters. Use literal values or ask the model to use literals.
- **Test case question language rule (MANDATORY)**: Every `question:` field must be written as a casual, business-user question — the kind a non-technical analyst or product manager would ask. Questions MUST NOT contain: graph labels (`:Person`, `:Movie`), relationship types (`[:ACTED_IN]`), Cypher keywords (`MATCH`, `WHERE`, `MERGE`, `CALL`, `EXISTS {}`, `COUNT {}`), property dot-access syntax (`.name`, `.rating`), GDS/APOC procedure names (`gds.`, `apoc.`), or index/procedure technical names. Good: "Which companies have more than 5 subsidiaries?" Bad: "Find (:Organization)-[:HAS_SUBSIDIARY]->() with depth > 2". Violations introduced in new or modified test cases must be caught in review.
- Vector index `OPTIONS` map is **mandatory** — `vector.dimensions` and `vector.similarity_function` are required at creation time.
- `USING INDEX SEEK` forces index seek (not scan); `USING SCAN` forces label scan with no index — opposite of intent, so use `USING SCAN` only to deliberately avoid indexes.
- Index `state` values: `ONLINE` (usable), `POPULATING` (building — check `populationPercent`), `FAILED`.
- `CALL { ... } IN TRANSACTIONS` is only allowed in implicit transactions — not inside explicit `BEGIN`/`COMMIT` blocks. Batching applies to input rows fed *outside* the subquery; matching inside the subquery collapses to one transaction.
- **Harness validator CALL IN TRANSACTIONS**: `driver.execute_query()` uses explicit BEGIN/COMMIT in Neo4j Python driver 6.x / Neo4j 2026.x — this breaks CALL IN TRANSACTIONS. Use `session.run()` instead for implicit auto-commit transactions. Fix is in `validator.py` Gate 2 and Gate 4 branches.
- **Test case data verification**: Before writing path traversal test cases, verify that the starting/ending entities actually have the required relationship links (e.g., SIMILAR_TO in goodreads is very sparse — most books have 0 links). Use the dataset `notes:` field to document verified entity values and data constraints.
- **goodreads SIMILAR_TO network**: Very sparse — only 424 total edges. Most books have 0 links. 'The Berlin Stories' has 7 incoming but 0 outgoing links. Use undirected traversal for path queries. 'Name of the Wind' has 0 SIMILAR_TO links — do not use for path tests.
- `COUNT {}` vs `count()`: `COUNT { pattern }` is a subquery counting rows; `count(expr)` is an aggregating function. They are not interchangeable — `count()` must appear in a clause that has an aggregation context.
- CALL subquery scope clause (`CALL (x, y) { }`) is Cypher 25 standard; importing `WITH` as first clause inside CALL is deprecated. Use `CALL ()` for isolated, `CALL (*)` for all-vars, `CALL (x)` for specific imports.
- Type predicates: `IS :: TYPE` returns `true` for `null` by default (all types include null). Append `NOT NULL` to exclude null: `x IS :: INTEGER NOT NULL`. Negation `IS NOT ::` returns `false` for null by default.
- Closed Dynamic Unions: `val IS :: INTEGER | FLOAT` tests multiple types; all inner types must have same nullability (all nullable or all `NOT NULL`).
- Casting: base functions (`toFloat`, `toInteger`, etc.) throw on unconvertible input; `OrNull` variants (`toFloatOrNull`, etc.) return `null` instead — prefer OrNull in agent-authored queries to avoid runtime errors.
- `null = null` → `null` (not `true`); `null <> null` → `null`. Always use `IS NULL` / `IS NOT NULL`.
- `least()` / `greatest()` do NOT exist in Cypher — use `CASE WHEN a < b THEN a ELSE b END` instead.
- Style guide keyword list (keywords.adoc) is 400 items — useless for agents. What agents need: UPPERCASE for clauses/operators, camelCase for functions, lowercase for `null`/`true`/`false`. Document this as a casing rules table, not a keyword enumeration.
- GRAPH TYPE DDL (`ALTER CURRENT GRAPH TYPE`, `EXTEND GRAPH TYPE`, `SHOW GRAPH TYPES`, `CREATE GRAPH TYPE`, `DROP GRAPH TYPE`) cannot be `EXPLAIN`'d or `PROFILE`'d. Validator auto-PASSes Gates 1 and 4 for these; Gate 2 execution validates syntax. Detected via `_is_graph_type_ddl()` in validator.py.
- **--model flag**: runner.py and generator.py accept `--model sonnet|haiku|opus` (short names) or a full model ID. Makefile variable `MODEL ?= sonnet`. Mapping: sonnet→claude-sonnet-4-6, haiku→claude-haiku-4-5, opus→claude-opus-4-5.
- GDS `.stream` procedures do NOT write properties to nodes — never filter `WHERE n.louvainCommunity = x` unless schema confirms a `.write` was performed. Properties like `louvainCommunity`, `pageRank`, `betweenness` only exist if a GDS write-back ran. cypher25-gds.md Section 6 has the DO-NOT examples.
- **recommendations domain**: `Movie.released` is a STRING `'YYYY-MM-DD'` — use string comparison (`> '2000-01-01'`), not integer. `User.userId` is a STRING — always quote: `{userId: '1'}`. Movie titles use article-inversion format: `'Matrix, The'` not `'The Matrix'`. Vector index name is `moviePlotsEmbedding` (NOT `moviePlots`). Fulltext index is `movieFulltext` (covers both title AND plot).
- **goodreads domain**: `Book.publication_year` and `Author.average_rating` / `Author.ratings_count` are all stored as STRING — use `toIntegerOrNull()` / `toFloatOrNull()` before numeric comparison. `Book.language_code` is sparse (many nulls) — always use IS NOT NULL when filtering. Collaborative filtering path: `(u:User)-[:PUBLISHED]->(r:Review)-[:WRITTEN_FOR]->(b:Book)`. Write queries should be marked `is_write_query: false` here since `read_only: true` causes them to SKIP anyway.
- **legalcontracts domain**: GDS procedures forbidden for the `legalcontracts` demo user — use pure Cypher for network analysis instead. `epochDays` does NOT exist on Date type — use `duration.between(date1, date2).days` instead. `count(n WHERE condition)` filtered count syntax is invalid — use `sum(CASE WHEN condition THEN 1 ELSE 0 END)`. `apoc.text.capitalizeWords` does not exist — use `toLower()` and regex for string normalization. Vector cases with `$embedding` fail gate 2 execution (harness can't inject vectors) — set `min_results: 0` and note that Gate 1 syntax is the goal. `PARTY_TO` direction: `(Party)-[:PARTY_TO]->(Contract)`. `THE VÄRDE FUND VI-A, L.P.` has 23 co-signatories (all Joint Venture) — good for traversal tests.

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
- `--version-matrix` flag generates a Markdown version matrix from parsed entries (8 baseline features, hand-coded; changelog scan augments but doesn't override). Run: `python3 scripts/extract-changelog.py --src ... --out ... --version-matrix`

## Version-Conditional Test Cases (min_version field)

- `min_version` field in test case YAML (YYYY.MM or YYYY.MM.PATCH) skips the case when server < required version.
- `--neo4j-version VERSION` flag provides version explicitly; otherwise auto-detected via `dbms.components()`.
- Auto-detection only runs when at least one test case has `min_version` set (avoids extra DB call on most runs).
- SKIPPED cases appear in reporter per-difficulty table (only when skips exist) and in a dedicated Skipped Cases section.
- Pass rate denominator excludes SKIPPED cases — only runnable cases are counted.
- `detect_server_version()` tries `database_="system"` first, then default DB as fallback (handles Aura/cloud).
- Version comparison is prefix-match: `"2026.02"` required against `"2026.02.1"` detected → satisfies (only compares up to required's component count).
- Dry-run validates `min_version` format without DB connection (`_validate_min_version_format()`).

## Domain YAML Structure (task-045: dataset: + database: split)

Domain YAML files now have two top-level keys:
- `database:` — connection info and version: `uri`, `username`, `database`, `neo4j_version` (YYYY.MM.PATCH), `cypher_version`, `read_only` (bool, optional)
- `dataset:` — schema for prompt injection: `name`, `description`, `schema` (nodes/relationships/indexes), `notes`

`load_dataset_schemas()` returns a `(schemas_dict, db_blocks_dict)` tuple — not a single dict.
`_format_dataset_schema(dataset, db_block=...)` injects `Database version: Neo4j X.Y / Cypher 25` when db_block provided.
Version resolution order in `run_all()`: CLI `--neo4j-version` → `database.neo4j_version` in YAML → `dbms.components()` auto-detect.
`read_only: true` in `database:` block → all `is_write_query: true` cases for that domain SKIP (verdict=SKIPPED, skip_reason="write query on read-only database"). Currently set on `companies` and `recommendations` (demo.neo4jlabs.com). Does not apply to `ucfraud` (localhost, writeable).
Backwards compatibility: old `dataset.connection` format still works as fallback in `_build_domain_drivers()`.

## Runner Notes (tests/harness/runner.py)

- Claude headless invocation: `claude --skill <name>` does NOT exist in claude 2.1.80. Runner uses `--append-system-prompt` with SKILL.md content loaded via `_load_skill_content()`. The `--skill` flag is a fallback for future CLI versions.
- `_load_skill_content(skill_name)` searches: cwd/skill_name/SKILL.md, repo_root/skill_name/SKILL.md, repo_root/neo4j-{name}-skill/SKILL.md, one level up from _REPO_ROOT (which is the skill-generation-validation-tools dir). `_REPO_ROOT.parent` is the actual git repo root.
- Schema injection: `--schema-dir PATH` loads `{domain}.json` from PATH and injects a compact schema block into every Claude prompt. Auto-detects `tests/schemas/` if it exists. Disable with `--no-schema`. Schema files: `tests/schemas/{domain}.json` with keys: `labels`, `relationship_types`, `indexes`, `node_properties`, `rel_properties`, `_notes`.
- Schema is formatted by `_format_schema_text()` into a compact `=== DATABASE SCHEMA ===` block and prepended to each prompt so the model uses exact label/rel-type/property names.
- Cypher extraction: handles two output formats: (1) raw ```` ```cypher ``` ```` block; (2) ```` ```yaml ``` ```` dual-format block with `query_literals` and `query_parametrized` keys. Prefers `query_literals` for harness execution (no parameter injection needed).
- Dry-run (`--dry-run`): validates YAML structure (required fields, duplicate IDs, valid difficulty) without executing queries or invoking Claude. Exits 0 on valid YAML.
- Exit codes: 0 = all PASS, 1 = any FAIL, 2 = any WARN (no FAIL).
- TestCaseResult fields: verdict, failed_gate, warned_gate, generated_cypher, metrics, gate_details, error (runner-level), duration_s.
- pyyaml is a required dep (added to pyproject.toml) — needed in CI runner context, not just dev.
- neo4j driver is a required dep (added to pyproject.toml) — `neo4j>=6.0.0` for the harness.
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

## to_jsonl.py Notes (scripts/to_jsonl.py)

- CLI: `uv run python3 scripts/to_jsonl.py --input tests/dataset/companies.yml --output out.jsonl [--difficulty basic] [--tags search,vector]`
- Smoke tests: direct invocation with no args (`uv run python3 scripts/to_jsonl.py`).
- System message is a fixed constant (not read from SKILL.md) — keeps the dataset self-contained and reproducible.
- Tags filter uses OR semantics: record is included if it has ANY of the specified tags (comma-separated).
- Directory mode skips `*-generated.yml` files (those require human promotion via exporter.py first).
- Schema context formatter sorts labels, rel types, and property names for deterministic output.

## analyze-results.py Notes (scripts/analyze-results.py)

- CLI: `uv run python3 scripts/analyze-results.py --input tests/results/ --output report.md`; or `--input file1.json file2.json` for multiple files.
- Smoke tests: direct invocation with no args (`uv run python3 scripts/analyze-results.py`).
- Pattern detection split: `match_cypher` = plain substring (case-insensitive `in` check); `match_cypher_regex` = `re.search()`. Keep them separate — mixing regex syntax chars like `(` in `match_cypher` causes `re.PatternError`.
- Pattern library has 13 built-in entries. Each maps to a SKILL.md section and includes a before/after Cypher example + recommendation text.
- Section 5 (Unclassified) catches cases that didn't match any pattern — always include it so novel failures are surfaced for manual review.
- Multi-file deduplication: last-wins by `case_id` when the same case appears in multiple run files.
- Generates report to stdout when `--output` is omitted — useful for quick CLI review.
- Run across latest result files (not oldest) — use the highest-timestamp JSON files per domain for the most current baseline.
- Result JSON structure: top-level keys are `run_id`, `started_at`, `completed_at`, `skill`, `summary`, `cases`. Per-case fields include `case_id`, `difficulty`, `verdict`, `failed_gate`, `generated_cypher`, `metrics`, `gate_details`.
- Baseline pass rates (after task-028 improvements): basic 95.5%, intermediate 86.4%, advanced 81.8%, complex 76.9%, expert 50.0%. Basic+intermediate combined: 90.9% (target ≥85%).

## Exporter Notes (tests/harness/exporter.py)

- CLI: `uv run python3 tests/harness/exporter.py --input run.json --domain companies --output-dir tests/dataset/ [--schema schema.json] [--dry-run]`
- Smoke tests: direct invocation with no args (`uv run python3 tests/harness/exporter.py`).
- WARN cases with all four gate_details present ARE exported — WARN ≠ FAIL; the query is valid but slow.
- `--schema` accepts a JSON file with keys: `labels`, `relationship_types`, `indexes`, `property_samples`. Optional — fields are `null` if absent.
- `property_samples` strips raw sample values on export — only `inferred_semantic` and `non_null_count` are written (keeps dataset compact, avoids leaking PII values).
- Dedup: loads existing record IDs into a set before appending. Safe for sequential re-runs; does not lock the file.
- `tests/dataset/{domain}.yml` uses a top-level `records:` key (list of record dicts).
- `passed_gates` field is a sorted list of gate numbers (e.g. `[1, 2, 3, 4]`).

## Test Case Question Authoring

Questions in domain YAML files must use **business language only** — as if asked by a fraud analyst, product manager, or data steward with no graph database knowledge.

### Question Validation Checklist

Before writing or accepting a `question` field, verify:

```
FAIL if the question contains any Cypher keyword: MATCH, RETURN, WITH, WHERE,
  OPTIONAL, CALL, COLLECT, COUNT, EXISTS, UNION, SET, CYPHER, LIMIT, ORDER
FAIL if it names a specific index ('moviePlots', 'entity', 'news', 'customerNames')
FAIL if it references a graph procedure (db.index.*, db.index.vector.*)
FAIL if it mentions node labels (Transaction, Customer, Movie, Organization)
FAIL if it mentions relationship type names (ACTED_IN, HAS_SUBSIDIARY, SHARED_IDENTIFIERS)
FAIL if it says "hops", "path expression", "quantified path", "traversal"
FAIL if it mentions algorithm names (betweenness, Louvain — but "network influence score" OK)
FAIL if it says "batch", "transactions of N rows", "CALL IN TRANSACTIONS"
FAIL if it embeds a coding constraint ("use a literal string match")
FAIL if it references internal field names (fraudFlag, louvainCommunity, pagerank as field)
PASS if it could be asked verbatim by a business user with no DB knowledge
PASS if thresholds are expressed in plain English ("at least 5", "more than 3")
PASS if the output format is implied naturally ("show", "list", "how many", "rank")
```

### Domain Glossary

**Fraud (`ucfraud`):** Transaction node → transaction; Account node → account; SHARED_IDENTIFIERS → shared personal details; `fraudFlag='True'` → flagged for fraud; `betweenness` → centrality / connections passing through; `louvainCommunity` → fraud network cluster; `pagerank` → network influence score; QPE `{2,4}` → two to four intermediate links; CALL IN TRANSACTIONS → process in small batches.

**Recommendations (`recommendations`):** Movie node → movie/film; Person node → actor/director; ACTED_IN → appeared in; RATED → rated/reviewed; plotEmbedding → storyline; vector similarity → similar storylines; collaborative filtering → users with similar taste; QPE through co-stars → connected through shared cast members.

**Companies (`companies`):** Organization node → company/firm; Article node → news article; Chunk node → article segment; HAS_SUBSIDIARY → owns/is parent of; MENTIONS → mentions/covers; `sentiment` → tone/coverage sentiment; fulltext index `entity` → company name search; QPE `{1,}` → at any depth in the ownership chain.

**Goodreads (`goodreads`):** Book node → book; Author node → author; Review node → review; User node → reader; AUTHORED=(Author→Book); PUBLISHED=(User→Review) (not User→Book); WRITTEN_FOR=(Review→Book); SIMILAR_TO=(Book→Book); `average_rating` on Author stored as STRING — use toFloat(); `publication_year` also STRING; book-descriptions and review-text vector indexes (1536-dim, cosine).

**Northwind (`northwind`):** Product node → product; Category node → category; Supplier node → supplier; Customer node → customer; Order node → order; ORDERS=(Order→Product); PURCHASED=(Customer→Order); PART_OF=(Product→Category); SUPPLIES=(Supplier→Product); `freight` and `orderDate` stored as STRING — use toFloat()/string comparison.

**Twitter (`twitter`):** User node → user/account; Tweet node → tweet; Hashtag node → topic; Me node → central account (neo4j, screen_name='neo4j'); FOLLOWS=(User→User); POSTS=(User→Tweet); TAGS=(Tweet→Hashtag); RETWEETS=(Tweet→Tweet); Hashtag names are lowercase without #; `betweenness` is sparse.

**Legal Contracts (`legalcontracts`):** Contract node → contract; Party node → signatory/company; Clause node → clause; Location node → jurisdiction; PARTY_TO=(Party→Contract) NOT (Contract→Party); HAS_CLAUSE=(Contract→Clause); HAS_GOVERNING_LAW=(Contract→Location); Party names in UPPER CASE; `effective_date` is DATE type; `total_amount` is sparse; contractSummary vector index (1536-dim, cosine).

**Retail (`retail`):** Product node → product type; Article node → specific variant (colour/style); Department node → store department; Customer node → customer; PURCHASED=(Customer→Article) with properties tDat (DATE), price (normalised 0-1), salesChannelId (1=store, 2=online); VARIANT_OF=(Article→Product); FROM_DEPARTMENT=(Article→Department); product_text_embeddings (1536-dim) and article_graph_embeddings (128-dim) vector indexes.

**UCNetwork (`ucnetwork`):** Client/AccessPoint/WIFIBridge all have :Device label; SSID node → WiFi network; Snapshot node → time-series observation; FIRST/LAST=(Device→Snapshot) for first/last observation; NEXT=(Snapshot→Snapshot) for linked list; SIGNAL/PERFORMANCE/MOBILITY/SECURITY_POSTURE=(Snapshot→metric_node); CONNECTED_TO=(Snapshot→Snapshot) for direct communication; signalstr is negative dBm (closer to 0 is stronger); timestamps are Unix epoch integers.

### Difficulty ↔ Question Complexity

| Difficulty | What the user asks | Cypher implication |
|---|---|---|
| basic | Simple lookups, counts, filters on one entity | Single MATCH, simple WHERE/RETURN |
| intermediate | Cross-entity, comparisons, aggregations | 2-hop traversal, WITH + aggregation |
| advanced | Pattern-based, "what if not", ranking within groups | OPTIONAL MATCH, COUNT/COLLECT subquery, fulltext |
| complex | Multi-faceted, 3+ dimensions | CALL subquery, UNION, multi-step WITH |
| expert | Deep network, similarity, path-finding | QPE, SHORTEST, ALL SHORTEST, vector index, CALL IN TRANSACTIONS |

- Expert tier was already accepted in `_VALID_DIFFICULTIES` (runner.py) and `DIFFICULTY_ORDER` (reporter.py) from the start. Only data (test cases) needed adding.
- Expert write cases (CALL IN TRANSACTIONS) on `read_only: true` domains are automatically SKIPPED — not FAIL.
- Avoid the word "batch" in question text — use "groups of N at a time" instead.
- "Full-text search" as a concept (not index name) is acceptable business language; "db.index.fulltext.queryNodes()" is not.

## Value-Grounded and Casual-Language Test Case Authoring

- Use a `notes:` field on casual-language cases to document the expected value translation (e.g. `"casual 'bad press' → a.sentiment < -0.3"`). This helps human reviewers verify the case without running the harness.
- Watch out for temporal questions that reference relative periods ("last year", "this month") when the dataset has a fixed date range. If the dataset only covers 2025, "last year" in 2026 → 0 rows. Either drop the temporal constraint or use a fixed year.
- Casual-language enum cases: always verify the exact case of enum values against the `values:` field in the domain YAML schema.

## SKILL.md Critical Syntax Notes (verified on Neo4j 2026.02.1)

- `CASE WHEN ... THEN ... ELSE ... END` is correct; standalone `WHEN ... THEN ... END` (without CASE) is NOT supported in Neo4j 2026.02.1 — syntax error.
- `CALL IN TRANSACTIONS` syntax: `MATCH ... CALL (x) { ... } IN TRANSACTIONS OF N ROWS` — `IN TRANSACTIONS` comes AFTER the `{ }` block. Never `CALL (x) IN TRANSACTIONS { }`.
- `CALL IN TRANSACTIONS` is for **write batching only** — never use for read queries; Neo4j rejects it in the implicit transaction context the harness uses for reads.
- `SHORTEST 1 (a)-[:REL]+` fails — wrap: `SHORTEST 1 (a)(()-[:REL]->()){1,}(b)`.

## Schema Data Quality (Injected Schema Accuracy)

When schema JSON files (`tests/schemas/{domain}.json`) contain wrong data, Claude generates queries with those wrong values — the model trusts the schema context over its training knowledge. Always verify schema files against live DB before running harness:
- Index names (vector/fulltext) are commonly wrong — verify with `SHOW INDEXES YIELD name, type WHERE state = 'ONLINE'`
- Relationship type endpoints — verify with `MATCH (a)-[:REL]->(b) RETURN labels(a), labels(b) LIMIT 3`
- Relationship type existence — verify with `CALL db.relationshipTypes()`
- Property types (String vs DateTime vs Boolean vs Integer) — critical for WHERE predicate generation


## Negative Example Patterns (Stale Training Data)

Three QPE/subquery patterns the model persistently generates wrong despite guidance:
1. **QPE bare quantifier**: `(a)-[:REL]-{2,4}-(b)` is a SYNTAX ERROR — must use group: `(a) (()-[:REL]-(){2,4}) (b)`
2. **CALL IN TRANSACTIONS order**: `CALL (o) IN TRANSACTIONS OF 5 ROWS { }` is SYNTAX ERROR — `{}` always comes BEFORE `IN TRANSACTIONS`
3. **SHORTEST with bare rel**: `SHORTEST 1 (a)-[:REL]+(b)` fails — wrap: `SHORTEST 1 (a)(()-[:REL]->()){1,}(b)`

DO-NOT blocks for all three are now in: SKILL.md (QPE section), cypher25-patterns.md (top), cypher25-call-in-transactions.md (top).

## GDS / Optional Plugin Capabilities

- `gds: true` in `database:` block signals GDS availability; runner.py injects it into schema context automatically via `_format_dataset_schema()`.
- GDS L3 reference is in `write/` folder (GDS procedures mutate in-memory graphs — conceptually WRITE).
- Always drop GDS projections after use (`CALL gds.graph.drop('name')`) — projections consume JVM heap.
- `gds.util.asNode(nodeId)` is required to convert GDS internal integer nodeIds back to Neo4j nodes in RETURN.
- GDS is NOT on demo.neo4jlabs.com — never use `gds.*` unless schema context explicitly states `gds: true`.

## APOC Capabilities

- `capabilities: [apoc, apoc-extended]` in `database:` block — runner.py injects this as a line in the schema context block.
- `apoc-core` is bundled with Neo4j 5+ and always available in Aura. `apoc-extended` is NOT in Aura (load/export procedures).
- APOC L3 reference is in `read/cypher25-apoc.md` (utility functions are read-only conceptually). Sections: map, coll, text, date/temporal, path traversal, load/export, availability check.
- `apoc.path.*` relationship filter syntax: `'REL_TYPE>'` = outgoing, `'<REL_TYPE'` = incoming, `'REL_TYPE'` = either. Combine with `|`.
- `apoc.date.*` operates on epoch ms/seconds — NOT Neo4j temporal types. Use `apoc.temporal.*` for Neo4j `date()`/`datetime()`.
- `capabilities` is a list field (distinct from the boolean `gds: true`) — more extensible for future plugins (genai, etc.).

## SKILL.md Authoring Notes

- SKILL.md line budget is 300 lines (not 300 non-blank lines). Inline `CYPHER 25` on the same line as each query to save ~10 lines in the Schema-First Protocol section.
- Autonomous Operation Protocol: Version step (step 3) uses 3-tier resolution: injected schema → dbms.components() → conservative defaults. Aura caveat and inline comment instruction must both appear in the same step to stay within budget.
- Verified with: `wc -l SKILL.md` (lines) + `python3 -c "words=len(text.split()); print(int(words*1.3))"` (token estimate).
- task-020 (WebFetch proactive framing) was folded into task-010's SKILL.md — the proactive framing is already present. task-020 can be marked as superseded or trivially completed.
- SEARCH clause: **GA in Neo4j 2026.02.1+** (was Preview in 2026.01). Vector-only — fulltext still uses `db.index.fulltext.queryNodes()`. demo.neo4jlabs.com upgraded to 2026.02.x — SEARCH clause is available there.

## Companies Dataset — Fulltext Index Distinction (task-054)

The `companies` DB has **two** fulltext indexes with distinct scopes:
- `entity` — on `Organization(name)` and `Person(name)`. Use for company/person name lookup. `WHERE node:Article` after this call **always returns 0 rows** — Articles are not indexed here.
- `news_fulltext` — on `Chunk(text)`. Use for keyword/topic search in article content (e.g. "renewable energy", "mergers"). Returns `Chunk` nodes; traverse back to `Article` with `MATCH (a:Article)-[:HAS_CHUNK]->(chunk)`.

**Pattern for article content search** (not name search):
```cypher
CALL db.index.fulltext.queryNodes('news_fulltext', 'renewable energy')
YIELD node AS chunk, score
MATCH (a:Article)-[:HAS_CHUNK]->(chunk)
OPTIONAL MATCH (a)-[:MENTIONS]->(org:Organization)
RETURN a.title, score, collect(DISTINCT org.name) AS companies
ORDER BY score DESC LIMIT 10
```

When a test question asks to "search articles/news for topic X" — always use `news_fulltext`, never `entity`.
