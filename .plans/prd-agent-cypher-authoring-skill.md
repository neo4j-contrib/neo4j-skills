# PRD: neo4j-cypher-authoring-skill

**Status**: Draft
**Author**: Design session 2026-03-19
**Target**: Autonomous AI agents writing Cypher for Neo4j 2025.x / 2026.x

---

## Overview

A new Agent Skill that enables autonomous AI agents to write, optimize, and validate Cypher 25 queries for Neo4j 2025.x and 2026.x databases. No such skill currently exists — the existing `neo4j-cypher-skill` covers only migration (upgrading 4.x/5.x queries).

Without this skill agents produce:
- Queries missing the `CYPHER 25` version pragma, causing unintended Cypher 5 execution
- Full label scans and Cartesian products from skipping schema inspection
- Incorrect quantified path expression syntax (too new for model training data)
- `MERGE` without `ON CREATE SET` / `ON MATCH SET`, corrupting data on re-runs
- Inline literals instead of `$params`, breaking plan caching and introducing injection risk
- Silent failures on 0-result queries with no recovery logic

The skill follows the Agent Skills progressive disclosure model (L1 metadata → L2 SKILL.md → L3 reference files → WebFetch escalation) and includes a companion test harness that validates output against real Neo4j databases.

---

## Goals

1. Produce correct, index-aware Cypher 25 queries on first attempt for the common 80% case
2. Self-validate via `EXPLAIN` / `PROFILE` and recover from performance issues without human input
3. Apply schema-first discipline (inspect before writing) as a mandatory, non-skippable protocol
4. Cover all Cypher 25 syntax: SEARCH, MATCH modes, WHEN, quantified path expressions, subqueries
5. Enforce `$param` discipline (never inline literals) for plan caching and injection safety
6. Provide 5-tier knowledge escalation: training data → L2 inline → L3 references → manual clause pages → full cheat sheet
7. Stay maintainable: L3 reference files auto-regenerated from upstream asciidoc on each Neo4j release via GH Action
8. Be testable: a companion test harness validates skill output against real Neo4j databases
9. Generate a reusable training dataset from validated queries: human-readable YAML records pairing questions with verified Cypher, schema context, and performance metadata — usable for fine-tuning, few-shot prompting, and as an example store
10. WebFetch to Neo4j Cypher docs is always available to online agents — SKILL.md must frame it as a proactive first-class option, not a last resort, especially when L3 reference files are token-budget-truncated
11. Enable early pre-filtering: SKILL.md must categorize query patterns into READ / WRITE / ADMIN buckets so agents can determine at L2 which L3 folder is relevant, loading only the files they need rather than all of them

---

## Non-Goals

- Driver code generation → covered by `neo4j-migration-skill`
- Database administration (SHOW DATABASES, ALTER USER, privileges) → covered by `neo4j-cli-tools-skill`
- Cypher 4.x / 5.x migration → covered by `neo4j-cypher-skill`

### Excluded GQL Clauses

The following GQL-influenced clauses are excluded from all skill content — they are syntactic rewrites that add confusion without value:

| Excluded | Pure Cypher Equivalent |
|---|---|
| `INSERT` | `CREATE` |
| `FILTER` | `WHERE` |
| `FINISH` | `RETURN` (without output) |
| `LET` | `WITH` (variable assignment) |
| `NEXT` | Sequential composed queries |

Kept GQL-origin features (add real value, not just renames): `WHEN` (conditional dispatch), `SEARCH` clause (vector/fulltext), MATCH modes (`DIFFERENT RELATIONSHIPS`, `REPEATABLE ELEMENTS`, `ANY`, `ALL`), quantified path expressions (`{m,n}`, `+`, `*`).

---

## Requirements

### Functional Requirements

- REQ-F-001: SKILL.md must always instruct agents to emit `CYPHER 25` as the first token of every generated query
- REQ-F-002: SKILL.md must define a mandatory schema-first protocol — agents must inspect schema before writing any MATCH clause using: `db.schema.visualization()`, `SHOW INDEXES`, `SHOW CONSTRAINTS`, and either `apoc.meta.schema()` (preferred, fast) or `db.schema.nodeTypeProperties()` + `db.schema.relTypeProperties()` (fallback when APOC absent); APOC availability detected via `SHOW PROCEDURES WHERE name = 'apoc.meta.schema'`
- REQ-F-003: SKILL.md must enforce `$param` syntax for all predicates and MERGE keys — never inline string or integer literals (exception: LIMIT with literal integer)
- REQ-F-004: SKILL.md must define a self-validation loop: generate → `EXPLAIN` (check for AllNodesScan / CartesianProduct) → rewrite if needed → `PROFILE` (record dbHits, rows, allocatedMemory, elapsedTimeMs)
- REQ-F-005: SKILL.md must define failure recovery decision trees for: 0-result queries, TypeErrors, and query timeouts — no human escalation required
- REQ-F-006: SKILL.md must include inline core patterns for: MERGE safety (`ON CREATE SET` / `ON MATCH SET`), quantified path expressions, WITH cardinality reset, WHEN conditional queries, SEARCH clause (vector + fulltext)
- REQ-F-007: SKILL.md must include a deprecated syntax → Cypher 25 preferred mapping table covering: old variable-length paths (`[:REL*1..5]` → `{1,5}`), `shortestPath()` → `SHORTEST 1`, `allShortestPaths()` → `ALL SHORTEST`
- REQ-F-008: SKILL.md must include a query construction decision tree that selects the correct L3 reference file based on query type
- REQ-F-009: SKILL.md must include WebFetch escalation logic with specific manual page URL patterns and the cheat sheet URL
- REQ-F-010: SKILL.md must include `FOREACH` vs `UNWIND` decision rule and brief `USE` clause guidance for multi-database routing
- REQ-F-011: Six L3 reference files must be created, each generated from upstream asciidoc sources: `cypher25-patterns.md`, `cypher25-functions.md`, `cypher25-indexes.md`, `cypher25-subqueries.md`, `cypher25-types-and-nulls.md`, `cypher-style-guide.md`
- REQ-F-012: `cypher25-indexes.md` must include an index type selection table mapping query predicates to required index types (RANGE, TEXT, POINT, FULLTEXT, VECTOR)
- REQ-F-013: `cypher25-types-and-nulls.md` must cover null propagation rules, explicit null guards, type casting functions, and type predicate expressions
- REQ-F-014: An extraction script (`skill-generation-validation-tools/scripts/extract-references.py`) must generate all L3 files from `docs-cypher/` and `docs-cheat-sheet/` with configurable GQL exclusion list, max-tokens enforcement per file, and detection of missing expected sections
- REQ-F-015: `docs-cypher/` and `docs-cheat-sheet/` must be converted from plain directories to git submodules, pinned to the current Neo4j 25 / 2026.x release tag
- REQ-F-016: A GH Action (`.github/workflows/update-cypher-skill.yml`) must run monthly, detect upstream doc changes, regenerate L3 files, update the `VERSION` file, and create a PR with diff stat, changelog summary, and a `breaking-change` label when expected sections are missing
- REQ-F-017: A test harness (`skill-generation-validation-tools/tests/harness/`) must validate skill output against real Neo4j databases with four gates: syntax (EXPLAIN), correctness (row count), quality (deprecated operator / syntax detection), and performance (PROFILE metrics)
- REQ-F-018: A question generator (`skill-generation-validation-tools/tests/harness/generator.py`) must sample property values using `COLLECT { MATCH ... RETURN DISTINCT ... LIMIT 100 }` subqueries (not `collect()[..N]`), infer property semantics, generate questions via Claude API, auto-execute candidate Cypher to capture observed baselines, and produce YAML test stubs with tolerance-multiplied thresholds for human review
- REQ-F-019: A `VERSION` file at the skill root must record neo4j version, cypher version, submodule commit SHAs, and generation date; updated by the GH Action on each release
- REQ-F-020: SKILL.md must explicitly instruct online agents that WebFetch to Neo4j Cypher docs is always available and should be used proactively — not just as a last resort — framing it as a first-class knowledge source at the same level as L3 reference files; the instruction must note that L3 files may be token-budget-truncated and WebFetch fills the gap
- REQ-F-021: A training dataset exporter (`skill-generation-validation-tools/tests/harness/exporter.py`) must write YAML records for every test case that passes all four validation gates; each record must include: `id`, `question`, `database`, `neo4j_version`, `schema_context` (full schema inspection output), `property_samples` (sampled values per label/property), `cypher` (the validated query), and `metadata` (difficulty, tags, db_hits, allocated_memory_bytes, runtime_ms, passed_gates)
- REQ-F-022: A converter script (`skill-generation-validation-tools/scripts/to_jsonl.py`) must transform the YAML training dataset into JSONL format compatible with Anthropic and OpenAI fine-tuning APIs, with each line containing a system/user/assistant message triple where: system = skill instructions, user = question + schema context, assistant = validated Cypher query
- REQ-F-023: SKILL.md must include an explicit READ / WRITE / SCHEMA / ADMIN query categorization section in the Query Construction Decision Tree, defining: READ (MATCH, OPTIONAL MATCH, CALL subqueries, WITH, RETURN, aggregations, COLLECT/COUNT/EXISTS subquery expressions, SEARCH), WRITE (CREATE, MERGE, SET, REMOVE, DELETE, DETACH DELETE, CALL IN TRANSACTIONS, FOREACH, LOAD CSV), SCHEMA (CREATE/DROP INDEX, CREATE/DROP CONSTRAINT, SHOW INDEXES, SHOW CONSTRAINTS, SHOW PROCEDURES), ADMIN (CREATE/DROP DATABASE, ALTER USER, roles/privileges, SHOW TRANSACTIONS, SHOW SERVERS). The section must instruct agents to determine the category first and then load only the relevant L3 references folder, not all files
- REQ-F-024: The L3 reference file folder structure must enforce the four-way split: `references/read/` for read-only query constructs, `references/write/` for write/mutation constructs, `references/schema/` for index/constraint/DDL schema operations, `references/admin/` for database administration (users, roles, databases, transactions), and `references/` root for cross-cutting guides (e.g. style-guide). When a topic spans categories (e.g. CALL subquery for reads vs CALL IN TRANSACTIONS for writes), files must be split and placed in the correct folder. This structure must be documented in `references/README.md`
- REQ-F-025: A harness result analysis script (`skill-generation-validation-tools/scripts/analyze-results.py`) must read one or more harness JSON result files and produce a structured Markdown improvement report containing: (a) failure summary grouped by gate, difficulty tier, and tag cluster; (b) inferred SKILL.md sections most likely responsible for each failure pattern (schema-first, QPE, MERGE safety, null handling, subquery scope, type casting, etc.); (c) concrete recommended edits with before/after Cypher examples where possible. Output is for human review — the script does not patch SKILL.md automatically.
- REQ-F-026: Test cases for the `recommendations` domain (`demo.neo4jlabs.com`, credentials: `recommendations/recommendations`, database: `recommendations`) must cover ≥ 25 cases across basic, intermediate, advanced, complex, and expert difficulty tiers, exercising: bipartite graph traversal (User→Movie rating patterns), top-N recommendation queries (ORDER BY rating DESC, LIMIT), collaborative filtering via common neighbor counting, rating aggregation (avg, count, stddev), COLLECT subquery for genre/actor collections, OPTIONAL MATCH for sparse rating graphs, and vector similarity via any vector index present in the schema.
- REQ-F-027: Test cases for the `ucfraud` domain must cover ≥ 25 cases across basic, intermediate, advanced, complex, and expert difficulty tiers. The primary target database is a local Neo4j 2026.02.1 instance (`bolt://localhost`, credentials: `neo4j/password`, database: `ucfraud`) which is writeable and runs the full feature set including the GA `SEARCH` clause. Cases must exercise: fraud ring detection via quantified path expressions (QPE `{2,5}`), transaction graph traversal (Account→Transaction→Merchant multi-hop), temporal fraud patterns using date/datetime functions and duration comparisons, SHORTEST path variants for tracing money flow, multi-hop relationship traversal for ring detection, SEARCH clause with fulltext and/or vector indexes, and CALL IN TRANSACTIONS batch flagging patterns (write queries marked `is_write_query: true` — valid on the local writable instance).
- REQ-F-028: An "expert" difficulty tier must be defined in the test harness above "complex". Expert cases must exercise: multi-database `USE` clause routing, hybrid fulltext+vector re-ranking in a single query pipeline using the GA `SEARCH` clause (available in Neo4j 2026.02.1), CALL IN TRANSACTIONS with ON ERROR CONTINUE/BREAK for batch operations, ALL SHORTEST / SHORTEST k path enumeration, and deeply nested QPEs with bounded quantifiers (`{m,n}` not `+`). At least 5 expert cases must be added to each domain case file (companies, recommendations, ucfraud).
- REQ-F-029: The `SEARCH` clause (GA in Neo4j 2026.02.1, no longer Preview) must be exercised in test cases against the local 2026.02.1 instance. The ucfraud domain case file must include at least 2 cases using `SEARCH ... USING FULLTEXT INDEX` or `SEARCH ... USING VECTOR INDEX` syntax. SKILL.md must be updated to note that the SEARCH clause is GA as of Neo4j 2026.02.1 (was Preview in 2026.01) and that the fulltext procedure fallback (`db.index.fulltext.queryNodes`) remains necessary only for pre-2026.02 databases.
- REQ-F-030: A structured `dataset:` section must be present at the top of every domain YAML case file (companies.yml, recommendations.yml, ucfraud.yml). It must include: `name`, `database`, `connection` (uri, username), `description` (business-language summary of the dataset), `schema` (nodes with typed properties including optional min/max/sample/values fields, relationships with from/to direction and optional properties, indexes with type and call example), and `notes` (key constraints and caveats). This is the canonical schema source — agents and the harness use this directly, no separate schema files required.
- REQ-F-031: SKILL.md must include a mandatory "MUST VALIDATE: Schema Fidelity" section instructing agents to verify every label, relationship type, property name, and index name in a generated query against the provided schema before returning. It must include a validation checklist table and a vocabulary discipline table mapping common business terms to their correct schema counterparts. Schema validation is mandatory when schema context is present in the prompt.
- REQ-F-032: SKILL.md must define a dual output format: every generated query must be returned as a `\`\`\`yaml` block containing `query_literals` (with literal values, directly executable), `query_parametrized` (with `$param` placeholders), and `parameters` (map of param name → value). A `\`\`\`cypher` block with the literal query may also be included for quick reference. The `$param` / YAML-key output format is an internal implementation detail and must never be surfaced to the end user in elicitations or explanatory comments.
- REQ-F-033: SKILL.md must include a "Value Normalization and Domain Translation" section with four rules: (1) when schema provides `values:` or `sample:` entries, translate user-supplied values to the nearest matching stored value and comment the translation; (2) validate numeric inputs against schema `min:`/`max:` ranges and elicit clarification on out-of-range values exceeding an order of magnitude; (3) recognize ID patterns from observed samples and normalize user input to match; (4) when schema provides no values/samples, apply common-sense normalization to user input and elicit only when the information is genuinely insufficient to generate a query.
- REQ-F-034: The test harness runner must inject schema context (from the `dataset:` section) and value hints (sample/enum/range data per property) into every Claude prompt. `_collect_value_hints()` must extract this data and prepend a "REPRESENTATIVE DATA VALUES" block so the model uses real entity names, IDs, and codes rather than generic placeholders. Value hint fields (`values:`, `sample:`, `min:`, `max:`) are optional — the runner must handle their absence gracefully.
- REQ-F-035: Each domain case file must include a set of value-enriched test questions that use concrete entity names, enum values, and ranges drawn from the `dataset:` schema rather than generic placeholders. A subset (≤ 30%) of questions per domain must be phrased in casual business-user language that requires the skill to perform value translation (e.g., "show me all flagged accounts" rather than "MATCH where status='flagged'"; "which high-severity alerts are still open" rather than "severity='high' AND status='open'"). These questions test the skill's value normalization and vocabulary translation capability without replacing the majority of existing technical test cases.
- REQ-F-036: The test harness runner must support parallel test case execution via a `--workers N` flag (default 1 for serial). When N > 1, cases are dispatched concurrently to up to N Claude Code processes. Each case still runs independently (no shared state). Database connections must be pooled or created per-worker. The implementation must prevent garbled stdout by buffering per-case output and flushing atomically after each case completes. Worker count should not exceed the number of available cases.
- REQ-F-037: Following each harness run, a critical skill review must be performed combining: (a) the improvement report from analyze-results.py mapping failures to SKILL.md sections; (b) general skill design principles (progressive disclosure, token budget, actionability of rules); (c) best-practice comparisons against similar AI coding agent skills. The review must produce prioritized SKILL.md edits with before/after examples and be committed as a named revision. Target: close gaps identified in the per-difficulty pass rate analysis against PRD thresholds (REQ-NF-004 through REQ-NF-011).
- REQ-F-039: SKILL.md must include a curated set of negative examples — explicit "DO NOT write" patterns with annotated explanations — to counteract stale assumptions baked into the model from training data on older Cypher versions. The evaluation must determine: (a) which patterns the model persistently generates despite contradicting SKILL.md rules (identified from harness failures across multiple runs); (b) which patterns arise from outdated Cypher training data (deprecated syntax like `[:REL*]`, `shortestPath()`, importing-WITH in CALL, label-free MATCH, multi-property MERGE); (c) how to encode negative examples most effectively (inline DO-NOT blocks, annotated bad→good rewrites, comment warnings). The output is a prioritised list of negative examples added to SKILL.md and/or L3 reference files. A follow-up harness run must confirm that the targeted failure patterns decrease.
- REQ-F-040: SKILL.md MERGE Safety guidance must enforce three rules: (1) MERGE a node using only its constrained key property(ies) in the pattern — never include non-key properties; (2) MERGE a relationship only after both its start and end nodes are already bound via a prior MATCH or MERGE — never use unbound endpoints; (3) every MERGE must include both `ON CREATE SET` and `ON MATCH SET` sub-clauses. Violations of any of these three rules are considered SKILL.md compliance failures.
- REQ-F-041: Test case data integrity — for each domain YAML, every test case that specifies a concrete entity name, ID, enum value, or exact string literal in its question or notes must be verified to produce `actual_rows >= min_results` against the live database. Cases that return 0 rows due to stale or non-existent entity references must be updated with verified values from the DB (via live query or schema sampling). Affected domains identified by validation run: goodreads (book titles), legalcontracts (party names, contract types), retail (customer IDs, article labels), northwind (product availability). Each corrected case must be re-run to confirm it passes Gate 2.
- REQ-F-042: `write/cypher25-gds.md` must document that GDS algorithm results are **streaming-only by default** — algorithm procedures like `gds.louvain.stream()` return rows for the duration of the call only; properties such as `node.louvainCommunity` do NOT exist on the node unless a write-back step (`gds.louvain.write()`) has been explicitly executed. SKILL.md must include a note in the GDS section: never assume GDS-computed properties are stored unless schema context confirms `gds_write_back: true` or equivalent. The negative example `WHERE node.louvainCommunity IS NOT NULL` (without a prior write step) must be added to the DO-NOT list.
- REQ-F-043: The Gate 1 validator (`validator.py`) must not incorrectly flag valid GRAPH TYPE DDL statements (`ALTER CURRENT GRAPH TYPE`, `SHOW GRAPH TYPES`, `CREATE GRAPH TYPE`) as syntax errors. If `ALTER CURRENT GRAPH TYPE ADD { ... }` is currently blocked by a Gate 1 regex, add a whitelist entry or adjust the check. Gate 1 should only reject GQL-only aliases (`LET`, `FINISH`, `FILTER`, `INSERT`, bare `NEXT`) — not valid Neo4j Enterprise DDL.
- REQ-F-044: Fix test case `companies-expert-002` (and any similar cases in other domains) where a fulltext index is used with an incorrect target label. The `entity` fulltext index in the companies domain is defined on `Organization(name)` — not on `Article`. Any test case or generated query that calls `db.index.fulltext.queryNodes('entity', ...)` and then filters by `WHERE node:Article` will return 0 rows. The test case must be rewritten to use the correct index for the intended label, or to use a vector search on `Chunk` for article-content queries.
- REQ-F-045: SKILL.md and a new or updated L3 reference file must document the Neo4j **parallel runtime** for compute-intensive analytics queries. Content must cover: (1) the runtime hint syntax (`CYPHER runtime=parallel MATCH ...`); (2) query types that benefit (full graph scans, aggregations, graph algorithms without GDS); (3) version availability and edition requirements; (4) when NOT to use it (OLTP queries, short-hop lookups, write queries); (5) interaction with `PROFILE` for confirming parallel plan selection. A routing entry must be added to SKILL.md's decision tree.
- REQ-F-046: The test harness runner (`runner.py`) and schema generator (`generator.py`) must support a `--model` flag accepting `sonnet`, `haiku`, or `opus` (default: `sonnet`). The flag maps to the full model ID passed via `--model <id>` to the `claude --print` subprocess. Makefile targets must expose this as a `MODEL=` variable (e.g. `make run-all MODEL=haiku`). Default behaviour is unchanged — omitting `--model` continues to use `claude-sonnet-4-6`.
- REQ-F-047: Each domain test case file must be expanded to **≥ 100 test cases** using `generator.py` to sample real property values from the live database and generate question stubs via Claude. New cases must cover a wider variety of patterns not already represented: aggregations (GROUP BY equivalents, percentiles, window-style ranking), temporal queries (date ranges, durations, recency filters), multi-hop path traversal (3+ hops, variable-length, shortest path), write operations (MERGE upsert, CREATE, DELETE/DETACH DELETE), admin/schema introspection (SHOW INDEXES, SHOW CONSTRAINTS, SHOW PROCEDURES), plugin-specific patterns (GDS streaming + write-back, APOC utilities, GenAI similarity — where the domain's `capabilities:` list supports them), and edge-case robustness (questions that intentionally produce 0 rows, questions requiring OPTIONAL MATCH, questions with large result sets requiring LIMIT). All questions must follow the business-user language rule (no graph labels, rel-types, or Cypher in the question text). All new cases must pass harness validation (Gates 1–4) at ≥ 90% per domain. Each domain is handled as a separate task (task-057 through task-066) to allow independent progress tracking.
- REQ-F-038: Test coverage must expand to 10 structurally distinct Neo4j database domains. Each new domain requires: a `dataset:` YAML section (schema, connection, description, notes), ≥ 25 test cases across all 5 difficulty tiers, and harness validation against a live database. The full list of domains must be documented in the PRD. Candidate domains from demo.neo4jlabs.com include: `northwind` (retail ERP, relational-to-graph), `stackoverflow` (Q&A tag network), `neoflix` (streaming catalogue variant), `movies` (movie cast/crew), `airports` (transportation network), `twitter` / `github` (social graph), and any additional local instances. Each new domain must demonstrate a distinct graph shape and query pattern not already covered by the existing 3 domains.

### Target Domain Catalogue (10 total)

| # | Domain | Database | Host | Graph Shape | Key Patterns |
|---|---------|----------|------|-------------|-------------|
| 1 | companies | companies | demo.neo4jlabs.com | Knowledge graph (org hierarchy + news) | Subsidiary traversal, fulltext, sentiment |
| 2 | recommendations | recommendations | demo.neo4jlabs.com | Bipartite rating graph | Collaborative filtering, vector similarity |
| 3 | ucfraud | neo4j | localhost:7687 | Transaction fraud graph | QPE fraud rings, temporal, CALL IN TRANSACTIONS |
| 4 | northwind | northwind | demo.neo4jlabs.com | Retail ERP (relational-to-graph) | Order→Product→Supplier traversal, aggregation |
| 5 | stackoverflow | stackoverflow | demo.neo4jlabs.com | Q&A tag network | Tag co-occurrence, user reputation, answer patterns |
| 6 | goodreads | goodreads | demo.neo4jlabs.com | Book recommendation graph | Author→Book, User reviews, SIMILAR_TO, vector search |
| 7 | twitter | twitter | demo.neo4jlabs.com | Social network / ego graph | FOLLOWS, retweets, hashtag co-occurrence, betweenness |
| 8 | legalcontracts | legalcontracts | demo.neo4jlabs.com | Contract party graph | Party→Contract, clause coverage, vector similarity |
| 9 | retail | retail | demo.neo4jlabs.com | Fashion retail purchase graph | Customer→Article, VARIANT_OF, temporal purchase patterns |
| 10 | ucnetwork | ucnetwork | demo.neo4jlabs.com | WiFi network monitoring | Device snapshots, signal quality, CONNECTED_TO traversal |

All 10 domains confirmed and validated against live demo.neo4jlabs.com databases. airports and movies not used (airports unavailable; movies superseded by recommendations).

- REQ-F-035: Each domain case file must include a set of value-enriched test questions that use concrete entity names, enum values, and ranges drawn from the `dataset:` schema rather than generic placeholders. A subset (≤ 30%) of questions per domain must be phrased in casual business-user language that requires the skill to perform value translation (e.g., "show me all flagged accounts" rather than "MATCH where status='flagged'"; "which high-severity alerts are still open" rather than "severity='high' AND status='open'"). These questions test the skill's value normalization and vocabulary translation capability without replacing the majority of existing technical test cases.

### Non-Functional Requirements

- REQ-NF-001: SKILL.md body must be ≤ 300 lines / ≤ 2,500 tokens (Agent Skills L2 budget)
- REQ-NF-002: Each L3 reference file must be ≤ 2,000 tokens (enforced by extraction script `--max-tokens` flag)
- REQ-NF-003: `description` frontmatter field must be ≤ 1,024 characters and follow the "what + when + keywords" third-person pattern
- REQ-NF-004: ≥ 90% of basic-difficulty test cases must pass on first attempt
- REQ-NF-005: ≥ 80% of intermediate-difficulty test cases must pass on first attempt
- REQ-NF-006: ≥ 70% of advanced-difficulty test cases must pass on first attempt
- REQ-NF-007: 0% of passing queries may use deprecated Cypher syntax (`[:REL*`, `shortestPath()`, `allShortestPaths()`)
- REQ-NF-008: 100% of generated queries must include the `CYPHER 25` version pragma
- REQ-NF-009: Performance Gate 4 hard-fail thresholds: dbHits > expected × 10, allocatedMemory > expected × 5
- REQ-NF-010: Training dataset YAML records must conform to a defined schema; each record is self-contained (no external references needed to use it for prompting or fine-tuning)
- REQ-NF-011: ≥ 60% of expert-difficulty test cases must pass on first attempt across all domains
- REQ-NF-012: The validation suite must cover ≥ 3 structurally distinct Neo4j database domains (knowledge graph, bipartite rating graph, transaction fraud graph) to verify skill generalizability across different graph shapes and query patterns

---

## Technical Considerations

### Skill Architecture (Progressive Disclosure)

```
L1  name + description (~100 tokens) — always in memory for skill selection
    ↓ triggered
L2  SKILL.md body (≤300 lines / ≤2,500 tokens) — loaded on every trigger
    ↓ conditional on query type
L3  references/*.md (≤2,000 tokens each) — loaded only when task requires it
    ↓ conditional on edge cases
L3b WebFetch: cypher-manual/25/{clause}/ — specific clause semantics
L3c WebFetch: cypher-cheat-sheet/25/all/ — full syntax overview (~12,000 words)
```

### SKILL.md Frontmatter

```yaml
---
name: neo4j-cypher-authoring-skill
description: Generates, optimizes, and validates Cypher 25 queries for Neo4j 2025.x
  and 2026.x. Use when writing new Cypher queries, optimizing slow queries, graph
  pattern matching, vector or fulltext search, subqueries, batch writes, or building
  queries for autonomous agents. Covers MATCH, MERGE, CREATE, WITH, RETURN, CALL,
  UNWIND, FOREACH, LOAD CSV, SEARCH, expressions, functions, indexes, and subqueries.
  Not for driver migration or database administration.
allowed-tools: WebFetch
compatibility: Neo4j >= 2025.01; Cypher 25
---
```

### SKILL.md Section Budget (L2)

| Section | Lines | Purpose |
|---|---|---|
| When NOT to use this skill | 5 | Disambiguation |
| Autonomous Operation Protocol | 20 | Non-negotiable defaults |
| Cypher 25 Version Pragma | 10 | Always emit; CYPHER 5 compat use case |
| Schema-First Protocol | 30 | 5 inspection queries + APOC detection |
| Parameter Discipline | 10 | $param always; why |
| Core Pattern Cheat Sheet | 80 | MERGE, QPE, WITH, WHEN, SEARCH |
| Deprecated Syntax → Preferred | 15 | Old → new mapping table |
| FOREACH vs UNWIND | 10 | Decision rule |
| USE clause | 8 | Multi-database routing |
| Query Construction Decision Tree | 25 | Drives L3 selection |
| EXPLAIN / PROFILE Validation Loop | 30 | dbHits, rows, memory, time |
| Failure Recovery Patterns | 40 | 0-results, TypeError, timeout |
| WebFetch Escalation | 20 | Which URL, when |
| **Total** | **~303** | At budget |

### Schema Inspection Protocol

```cypher
-- 1. Graph topology
CALL db.schema.visualization() YIELD nodes, relationships RETURN nodes, relationships;

-- 2. Available indexes
SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state
WHERE state = 'ONLINE' RETURN name, type, labelsOrTypes, properties;

-- 3. Constraints
SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties
RETURN name, type, labelsOrTypes, properties;

-- 4/5. Property names + types — APOC preferred (fast on large graphs)
-- Detection (never throws):
SHOW PROCEDURES WHERE name = 'apoc.meta.schema'
YIELD name RETURN count(name) > 0 AS apocAvailable;

-- Preferred (APOC available):
CALL apoc.meta.schema() YIELD value RETURN value;

-- Fallback (no APOC — slow on large graphs):
CALL db.schema.nodeTypeProperties()
YIELD nodeLabels, propertyName, propertyTypes, mandatory
RETURN nodeLabels, propertyName, propertyTypes, mandatory;

CALL db.schema.relTypeProperties()
YIELD relType, propertyName, propertyTypes, mandatory
RETURN relType, propertyName, propertyTypes, mandatory;
```

### L3 Reference Files

Files are organized by query category — agents should pre-filter at L2 to load only the relevant folder.

| Folder | File | When Loaded | Key Sources |
|---|---|---|---|
| `read/` | `cypher25-patterns.md` | Variable-length paths, QPEs, match modes | `patterns/` adocs |
| `read/` | `cypher25-functions.md` | Aggregation, list, string, temporal, spatial, vector | `functions/` adocs |
| `read/` | `cypher25-subqueries.md` | CALL subqueries, COUNT/COLLECT/EXISTS, scope rules | `subqueries/` adocs |
| `read/` | `cypher25-types-and-nulls.md` | Type errors, null propagation, casting, type predicates | `values-and-types/` adocs |
| `write/` | `cypher25-call-in-transactions.md` | CALL IN TRANSACTIONS batching, ON ERROR, concurrency | `subqueries/subqueries-in-transactions.adoc` |
| `schema/` | `cypher25-indexes.md` | SEARCH clause, vector/fulltext, index hints | `indexes/` adocs |
| (root) | `cypher-style-guide.md` | Final output formatting, naming conventions (all categories) | `styleguide.adoc`, `syntax/naming.adoc` |

The split between `read/cypher25-subqueries.md` (CALL subquery, COUNT{}, COLLECT{}, EXISTS{}) and `write/cypher25-call-in-transactions.md` (CALL { ... } IN TRANSACTIONS) is deliberate — the former is a read-pattern expression, the latter is a write batching primitive.

Index type selection table (included in `cypher25-indexes.md`):

| Query predicate | Index type |
|---|---|
| `n.prop = $val`, `IN $list` | RANGE |
| `STARTS WITH`, `CONTAINS`, `ENDS WITH` | TEXT |
| `point.distance(...)` | POINT |
| `SEARCH ... USING FULLTEXT INDEX` | FULLTEXT |
| `SEARCH ... USING VECTOR INDEX` | VECTOR |

### WebFetch Escalation

| Trigger | URL |
|---|---|
| Specific clause semantics | `https://neo4j.com/docs/cypher-manual/25/clauses/{clause}/` |
| Function signatures | `https://neo4j.com/docs/cypher-manual/25/functions/{type}/` |
| Path query edge cases | `https://neo4j.com/docs/cypher-manual/25/patterns/` |
| Full syntax overview | `https://neo4j.com/docs/cypher-cheat-sheet/25/all/` |

High-priority pages: `merge/`, `with/`, `call-subquery/`, `search/`, `aggregating/`, `use/`

### PROFILE Metrics (Gate 4)

```
dbHits            — storage engine calls (WARN > expected, FAIL > expected × 10)
rows              — actual processed rows per operator (reliable; use over EXPLAIN estimates)
allocatedMemory   — bytes (WARN > 100MB, FAIL > expected × 5)
elapsedTimeMs     — wall time (WARN > expected, guidance only — CI environments vary)
```

### Git Submodules

| Local path | Upstream (verify before adding) | Tracks |
|---|---|---|
| `docs-cypher/` | `neo4j/docs-cypher-manual` | Neo4j 25 / 2026.x tag |
| `docs-cheat-sheet/` | `neo4j/docs-cypher-cheat-sheet` | Neo4j 25 / 2026.x tag |

### GH Action Design

Trigger: monthly schedule (`cron: '0 8 1 * *'`) + manual dispatch with optional `target_tag` input.

Steps: checkout with submodules → detect latest tag → update submodules → run extraction script → detect missing sections → update VERSION → generate changelog summary → diff check → create PR with diff stat + changelog + `breaking-change` label if any WARNING notices found.

PR is created but **never auto-merged** — human must review content correctness.

### Test Harness Architecture

**Gate sequence per test case:**
```
Gate 1: Syntax       EXPLAIN {query}    → CypherSyntaxError = FAIL
Gate 2: Correctness  Execute            → rows < min_results = FAIL
Gate 3: Quality      Parse EXPLAIN plan → deprecated operators / syntax = FAIL
                                        → missing CYPHER 25 pragma = WARN
Gate 4: Performance  PROFILE            → dbHits, rows, allocatedMemory, elapsedTimeMs
                                        → WARN / FAIL per threshold
```

Write queries execute in an explicit transaction that is always rolled back for test isolation.

**Question generator property sampling** (uses COLLECT subquery with LIMIT — stops early, does not build full list before slicing):

```cypher
MATCH (n:Organization)
RETURN 'Organization' AS label, 'name' AS property,
       COLLECT { MATCH (m:Organization)
                 WHERE m.name IS NOT NULL
                 RETURN DISTINCT m.name LIMIT 100 } AS samples,
       count { (m:Organization) WHERE m.name IS NOT NULL } AS nonNullCount
```

Inferred semantics from samples drive question generation:
- UUID → equality only; integer range → range queries; float 0–1 → threshold; low-cardinality string → IN list; free text → fulltext/CONTAINS; high null rate → IS NOT NULL guards.

**Test case baselines** auto-captured at generation time via PROFILE on candidate Cypher, stored with tolerance multipliers: result count ×[0.5, 10], dbHits ×3, memory ×3, runtime ×5.

### WebFetch as First-Class Knowledge Source

SKILL.md must frame WebFetch as a proactive option, not a fallback. The instruction in the WebFetch Escalation section must read:

> **WebFetch is always available for online agents.** Do not wait until L3 reference files are insufficient — fetch Neo4j docs pages proactively whenever a query involves syntax you are not fully certain about. L3 reference files are token-budget-truncated (≤2,000 tokens each); the full docs pages contain the complete picture.

The section budget for WebFetch Escalation (20 lines) must include this framing up front before the URL table.

### Training Dataset

Every test case that passes all four validation gates is exported as a YAML training record. Format:

```yaml
# skill-generation-validation-tools/tests/dataset/companies.yml  (one file per database domain)
records:
  - id: "companies-TC001-20260319"
    question: "Find the names of the first 10 organizations in the graph"
    database: companies
    neo4j_version: "2026.02"
    schema_context:
      labels: [Organization, Article, Chunk, Person]
      relationship_types: [MENTIONS, HAS_CHUNK, ACTED_IN]
      indexes:
        - {name: entity, type: FULLTEXT, labels: [Organization], properties: [name]}
        - {name: news, type: VECTOR, labels: [Chunk], properties: [embedding]}
    property_samples:
      Organization.name:
        samples: ["Neo4j", "Google", "Microsoft"]
        inferred_semantic: freetext
        non_null_count: 4821
      Organization.id:
        samples: ["neo4j", "google", "microsoft"]
        inferred_semantic: enum
        non_null_count: 4821
    cypher: |
      CYPHER 25
      MATCH (o:Organization)
      RETURN o.name AS name
      LIMIT 10
    metadata:
      difficulty: basic
      tags: [match, labels, return, limit]
      db_hits: 42
      allocated_memory_bytes: 8192
      runtime_ms: 3
      passed_gates: [syntax, correctness, quality, performance]
      generated_at: "2026-03-19T22:45:00Z"
```

The YAML dataset serves three purposes:
1. **Fine-tuning source**: convert to JSONL via `skill-generation-validation-tools/scripts/to_jsonl.py`
2. **Few-shot example store**: retrieve by difficulty/tags for prompt augmentation
3. **Regression baseline**: re-run queries against future Neo4j versions to detect regressions

JSONL output format (per record, one line):
```json
{
  "messages": [
    {"role": "system", "content": "<skill instructions summary>"},
    {"role": "user", "content": "Database: companies\nSchema: ...\nQuestion: Find the names of the first 10 organizations"},
    {"role": "assistant", "content": "CYPHER 25\nMATCH (o:Organization)\nRETURN o.name AS name\nLIMIT 10"}
  ]
}
```

### File Layout

```
neo4j-cypher-authoring-skill/
├── SKILL.md                                   # L2: ≤300 lines
├── VERSION                                    # Version metadata
└── references/
    ├── README.md                              # Folder structure guide + category definitions
    ├── cypher-style-guide.md                  # L3: naming, casing, formatting (cross-cutting)
    ├── read/
    │   ├── cypher25-patterns.md               # L3: QPEs, paths, match modes
    │   ├── cypher25-functions.md              # L3: aggregating, list, string, temporal, spatial, vector
    │   ├── cypher25-subqueries.md             # L3: CALL subquery, COUNT{}, COLLECT{}, EXISTS{}
    │   └── cypher25-types-and-nulls.md        # L3: null propagation, casting, type predicates
    ├── write/
    │   └── cypher25-call-in-transactions.md   # L3: CALL IN TRANSACTIONS, batching, ON ERROR
    ├── schema/
    │   └── cypher25-indexes.md                # L3: fulltext/vector, index types, hints
    └── admin/                                 # L3: database admin (users, roles, databases, transactions)

skill-generation-validation-tools/        # NOT part of the installable skill
├── pyproject.toml                      # uv project descriptor (pyyaml dep)
├── README.md                           # How to use these tools
├── scripts/
│   ├── extract-references.py           # Asciidoc → Markdown L3 generation
│   ├── extract-changelog.py            # Changelog parser for PR body
│   ├── to_jsonl.py                     # YAML dataset → JSONL fine-tuning converter (REQ-F-022)
│   └── test-extract-references.py      # Test suite for extract-references.py
└── tests/
    ├── harness/
    │   ├── runner.py                   # Main test executor
    │   ├── generator.py                # Question generation + baseline capture
    │   ├── validator.py                # Cypher execution + validation rules
    │   ├── reporter.py                 # Markdown / HTML report output
    │   ├── exporter.py                 # Training dataset YAML exporter (REQ-F-021)
    │   └── deprecated_operators.json   # Maintained per Neo4j release
    ├── cases/
    │   ├── companies.yml               # Test cases for companies KG
    │   └── {domain}.yml
    ├── dataset/
    │   ├── companies.yml               # Validated training records (YAML)
    │   └── {domain}.yml
    └── results/                        # Gitignored test run outputs

.github/workflows/
├── update-cypher-skill.yml             # Monthly update + PR
└── test-cypher-skill.yml               # PR gate: run test harness

docs-cypher/                            # git submodule
docs-cheat-sheet/                       # git submodule
```

---

## Acceptance Criteria

- [ ] Autonomous agent using only this skill produces `CYPHER 25`-prefixed queries without human prompting
- [ ] Schema inspection protocol runs before any MATCH clause; falls back gracefully when no DB access
- [ ] ≥ 90% basic, ≥ 80% intermediate, ≥ 70% advanced test cases pass in the test harness
- [ ] 0% of passing queries use deprecated syntax (`[:REL*`, `shortestPath()`, `allShortestPaths()`)
- [ ] GH Action creates a valid PR with diff stat and changelog when submodule content changes; adds `breaking-change` label when expected sections are missing
- [ ] Extraction script runs with `--dry-run` and exits 0 on current submodule content
- [ ] Each L3 reference file includes `> Source:` header with version + commit SHA and is ≤ 2,000 tokens
- [ ] SKILL.md WebFetch section frames fetching as proactive and first-class, explicitly noting L3 truncation
- [ ] Training dataset exporter writes YAML records for all gate-passing test cases with required fields
- [ ] `skill-generation-validation-tools/scripts/to_jsonl.py` converts YAML dataset to valid JSONL with system/user/assistant triples
- [ ] Running the full test harness on companies DB produces ≥ 1 training record in `skill-generation-validation-tools/tests/dataset/companies.yml`
- [ ] SKILL.md query decision tree includes READ / WRITE / SCHEMA / ADMIN categorization with explicit folder routing (`references/read/`, `references/write/`, `references/schema/`, `references/admin/`)
- [ ] `references/README.md` exists documenting the folder structure, category definitions, and the CALL subquery vs CALL IN TRANSACTIONS split rationale
- [ ] `skill-generation-validation-tools/scripts/analyze-results.py` produces a structured Markdown report from harness JSON output, grouping failures by gate + difficulty + tag and mapping to SKILL.md sections
- [ ] `skill-generation-validation-tools/tests/cases/recommendations.yml` contains ≥ 25 test cases across basic through expert difficulty covering bipartite traversal, top-N, collaborative filtering, and aggregation patterns
- [ ] `skill-generation-validation-tools/tests/cases/ucfraud.yml` contains ≥ 25 test cases across basic through expert difficulty covering fraud ring QPE, transaction traversal, temporal patterns, and SHORTEST path
- [ ] Expert difficulty tier is defined and validated in the harness; ≥ 5 expert cases per domain; ≥ 60% pass rate across all domains
- [ ] Full harness run across all 3 domains (companies + recommendations + ucfraud) completes and produces an improvement report via analyze-results.py

---

## Out of Scope

| Feature | Reason |
|---|---|
| GQL clauses: LET, FINISH, FILTER, NEXT, INSERT | Syntactic rewrites — confusing without added value |
| Admin Cypher: SHOW DATABASES, ALTER USER, privileges | Covered by neo4j-cli-tools-skill |
| Driver API code | Covered by neo4j-migration-skill |
| Cypher 4.x / 5.x migration guidance | Covered by neo4j-cypher-skill |
| Auto-merging the GH Action PR | Human review gate required for content correctness |
| Full Cypher manual inlined as L2 | 291k words violates L2 token budget; use WebFetch escalation |

---

## Open Questions

1. **Upstream submodule URLs**: Verify exact GitHub org/repo for `docs-cypher` and `docs-cheat-sheet` before `git submodule add` (likely `neo4j/docs-cypher-manual` and `neo4j/docs-cypher-cheat-sheet`).
2. **Tag naming convention**: Do upstream repos tag by Neo4j version (`2026.02`), Cypher version (`25`), or branch-per-version? Determines tag-detection logic in the GH Action.
3. **GH Action secrets**: Is `GITHUB_TOKEN` sufficient for submodule access to public upstream repos, or is a PAT needed?
4. **Test database secrets**: `companies` and `recommendations` demo DBs are public (no secrets, credentials == database name). The `ucfraud` local instance (`bolt://localhost`, `neo4j`/`password`) is developer-local — not deployed to CI without additional configuration. Local tests run via environment variables; CI can use demo.neo4jlabs.com/ucfraud (read-only) for structural validation and gate 1–3 checks, with gate 4 (PROFILE) and write queries requiring the local instance.
5. **Claude Code headless invocation**: Confirm exact CLI pattern for skill-scoped execution in the test runner.
6. **`deprecated_operators.json` maintenance**: Manually updated per release, or auto-generated by `extract-changelog.py`?
7. **Extraction script language**: Python assumed — confirm vs Node.js (a `package.json` exists in `docs-cheat-sheet/`).
