# neo4j-cypher-authoring-skill

An Agent Skill that enables autonomous AI agents to write, optimize, and validate **Cypher 25** queries for **Neo4j 2025.x and 2026.x** databases.

Compatible with any Claude Code agent or system that supports the Agent Skills progressive disclosure model.

---

## What This Skill Does

Without this skill, agents produce queries that:
- Miss the `CYPHER 25` pragma, silently running as Cypher 5
- Cause full label scans and Cartesian products by skipping schema inspection
- Use incorrect quantified path expression syntax (too new for base model training)
- Omit `ON CREATE SET` / `ON MATCH SET` on `MERGE`, corrupting data on re-runs
- Inline string literals instead of `$params`, breaking plan caching and risking injection

With this skill, agents apply a mandatory schema-first protocol and produce correct, index-aware, parameterised Cypher on the first attempt.

---

## Skill Activation

This skill uses the **L1 → L2 → L3 progressive disclosure model**:

| Level | File | Size | Purpose |
|---|---|---|---|
| L1 | Skill registry metadata | ~50 tokens | Agent loads only the name + description; decides whether to invoke |
| L2 | `SKILL.md` | ~2,000 tokens | Core protocol, inline patterns, decision trees; always loaded on invocation |
| L3 | `references/*.md` | ≤2,000 tokens each | Deep reference loaded on-demand per query type |

Agents load `SKILL.md` and then selectively load L3 files based on the query construction decision tree.

---

## Scope

**In scope:**
- `MATCH`, `OPTIONAL MATCH`, `WHERE`, `WITH`, `RETURN`, `UNWIND`
- `CREATE`, `MERGE` (with `ON CREATE SET` / `ON MATCH SET`), `SET`, `REMOVE`, `DELETE`
- `CALL` subqueries, `OPTIONAL CALL`, `COUNT {}`, `COLLECT {}`, `EXISTS {}`
- `CALL { } IN TRANSACTIONS` for batch writes
- Quantified path expressions (`{m,n}`, `+`, `*`), `SHORTEST`, match modes
- `SEARCH` clause (vector index, GA in Neo4j 2026.02.1+) and `db.index.fulltext.queryNodes()`
- `FOREACH`, `LOAD CSV`, `USE` clause
- Index and constraint DDL (`CREATE INDEX`, `SHOW INDEXES`, etc.)
- Optional plugin procedures: GDS (`gds.*`), APOC (`apoc.*`), GenAI plugin (`ai.*`)

**Out of scope:**
- Driver code generation → use `neo4j-migration-skill`
- Database administration (CREATE DATABASE, ALTER USER, roles, privileges) → use `neo4j-cli-tools-skill`
- Cypher 4.x / 5.x migration → use `neo4j-cypher-skill`
- GQL-only clauses: `LET`, `FINISH`, `FILTER`, `NEXT`, `INSERT` — never emitted

---

## Key Protocols

### CYPHER 25 Pragma
Every query begins with `CYPHER 25`. No exceptions.

### Schema-First
Before writing any `MATCH` clause, inspect schema via:
```cypher
CYPHER 25 CALL db.schema.visualization() YIELD nodes, relationships RETURN nodes, relationships;
CYPHER 25 SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state WHERE state = 'ONLINE' RETURN *;
CYPHER 25 SHOW PROCEDURES WHERE name = 'apoc.meta.schema' YIELD name RETURN count(name) > 0 AS apocAvailable;
```
If schema context is injected in the prompt, use it directly — do not run inspection queries again.

### MERGE Safety
Every `MERGE` must include both `ON CREATE SET` and `ON MATCH SET`:
```cypher
CYPHER 25
MERGE (p:Person {id: $id})
ON CREATE SET p.name = $name, p.createdAt = datetime()
ON MATCH SET  p.name = $name, p.updatedAt = datetime()
```

### Self-Validation
After generating Cypher: run `EXPLAIN` to check for `AllNodesScan` and `CartesianProduct`; rewrite if found. Run `PROFILE` when performance matters.

### Parameter Discipline
All predicate values and MERGE keys use `$params`. Inline literals are only allowed for `LIMIT` and integer schema constants.

---

## Version Compatibility

| Feature | Minimum version | Notes |
|---|---|---|
| Cypher 25 pragma | 2025.01 | Required prefix |
| Quantified path expressions (`{m,n}`) | 2025.01 | Use `{1,}` not `+` for compatibility |
| `SHORTEST` keyword | 2025.01 | Replaces `shortestPath()` |
| `COLLECT {}` / `COUNT {}` subqueries | 2025.01 | |
| `WHEN` conditional | 2025.06 | |
| `REPEATABLE ELEMENTS` / `DIFFERENT RELATIONSHIPS` | 2025.06 | Must follow `MATCH` keyword directly |
| `vector()` function | 2025.10 | |
| `SEARCH` clause (vector index) | 2026.02.1 | Not available on demo.neo4jlabs.com (2026.01) |
| GRAPH TYPE DDL | 2026.02 | Enterprise Preview only |

Cross-reference `references/version-matrix.md` before using any version-gated feature.

---

## Optional Plugin Capabilities

Plugins are gated — only use when the schema context declares them available:

| Plugin | Flag | Procedures | Availability |
|---|---|---|---|
| Graph Data Science | `gds: true` | `gds.*` | Self-managed (installed); Aura (always on) |
| APOC Core | `capabilities: [apoc]` | `apoc.*` | Self-managed (installed); Aura (always on) |
| APOC Extended | `capabilities: [apoc-extended]` | additional `apoc.*` | Self-managed only; NOT on Aura |
| GenAI plugin | `capabilities: [genai]` | `ai.similarity.*`, `ai.embedding.*` | Self-managed; `ai.embedding.*` is Aura-only |

Detection query (for schema tooling):
```cypher
SHOW PROCEDURES YIELD name WHERE name STARTS WITH 'gds.' RETURN count(*) AS cnt
SHOW PROCEDURES YIELD name WHERE name STARTS WITH 'apoc.' RETURN count(*) AS cnt
SHOW PROCEDURES YIELD name WHERE name STARTS WITH 'ai.' RETURN count(*) AS cnt
```

---

## File Structure

```
neo4j-cypher-authoring-skill/
├── SKILL.md                          # L2: core skill — always loaded
├── VERSION                           # Pinned doc versions (neo4j, cypher tags + SHAs)
└── references/
    ├── README.md                     # L3 folder guide for humans and agents adding files
    ├── cypher-style-guide.md         # Naming, casing, formatting conventions (all categories)
    ├── version-matrix.md             # Feature availability by Neo4j version
    ├── read/
    │   ├── cypher25-patterns.md      # QPEs, SHORTEST, match modes, path expressions
    │   ├── cypher25-functions.md     # Aggregation, list, string, temporal, spatial, vector functions
    │   ├── cypher25-subqueries.md    # CALL {}, OPTIONAL CALL, COUNT{}, COLLECT{}, EXISTS{}
    │   ├── cypher25-types-and-nulls.md  # Type errors, null propagation, casting, type predicates
    │   └── cypher25-apoc.md          # APOC Core/Extended procedures (capability-gated)
    ├── write/
    │   ├── cypher25-call-in-transactions.md  # Batch writes, CALL IN TRANSACTIONS
    │   └── cypher25-gds.md           # GDS algorithms (capability-gated: gds: true)
    └── schema/
        ├── cypher25-indexes.md       # Index/constraint DDL, SEARCH clause, fulltext, hints
        ├── cypher25-graph-types.md   # GRAPH TYPE DDL (Enterprise Preview)
        └── cypher25-genai.md         # GenAI plugin: ai.similarity.*, ai.embedding.* (capability-gated)
```

### L3 Loading Decision Tree (from SKILL.md)

| Query type | Load |
|---|---|
| Variable-length paths, QPEs, match modes | `read/cypher25-patterns.md` |
| Aggregation, list, string, temporal, spatial, vector functions | `read/cypher25-functions.md` |
| CALL subquery, COUNT{}, COLLECT{}, EXISTS{} | `read/cypher25-subqueries.md` |
| Type errors, null propagation, casting, type predicates | `read/cypher25-types-and-nulls.md` |
| APOC procedures (`apoc.*`) — only when `apoc` in capabilities | `read/cypher25-apoc.md` |
| Batch writes, CALL IN TRANSACTIONS | `write/cypher25-call-in-transactions.md` |
| GDS algorithms (`gds.*`) — only when `gds: true` in schema | `write/cypher25-gds.md` |
| Index creation, SEARCH, fulltext, vector, hints | `schema/cypher25-indexes.md` |
| GRAPH TYPE DDL (Enterprise Preview — 2026.02+) | `schema/cypher25-graph-types.md` |
| GenAI plugin (`ai.*`) — only when `genai` in capabilities | `schema/cypher25-genai.md` |
| Naming, casing, formatting (all categories) | `cypher-style-guide.md` |

---

## Common Failure Patterns (and Fixes)

| Error | Fix |
|---|---|
| `MATCH (pattern) REPEATABLE ELEMENTS` — syntax error | Move mode after MATCH: `MATCH REPEATABLE ELEMENTS (pattern)` |
| `ORDER BY x DESC NULLS LAST` — syntax error | Remove `NULLS LAST` — not valid Cypher; NULLs sort last in DESC by default |
| `SEARCH (c) USING VECTOR INDEX...` — syntax error | Use: `SEARCH c IN (VECTOR INDEX name FOR $vec LIMIT N) SCORE AS score` |
| 0 results | Check label/rel-type spelling; verify property exists; check WHERE predicates |
| `AllNodesScan` in EXPLAIN | Add label to MATCH or add an index |
| `CartesianProduct` | Add a join condition or restructure with WITH |
| TypeError on property | Add `IS NOT NULL` guard; use `coalesce()` |
| Timeout | Add LIMIT; use QPE bounded `{m,n}` not unbounded `+`; check GDS availability for analytics |

---

## Maintaining L3 Files

L3 reference files are generated from upstream Neo4j asciidoc sources. To regenerate after a Neo4j release:

```bash
# From repo root
uv run python3 skill-generation-validation-tools/scripts/extract-references.py \
  --docs-dir docs-cypher/ \
  --cheat-sheet docs-cheat-sheet/ \
  --output neo4j-cypher-authoring-skill/references/
```

See `skill-generation-validation-tools/scripts/extract-references.py --help` for options. After regeneration, run the full test harness to verify pass rates before committing.

Token budget per L3 file: **≤ 2,000 tokens**. Files exceeding this must be split.

---

## Related Skills

- `neo4j-migration-skill` — Bolt driver code generation and version migration
- `neo4j-cli-tools-skill` — Database administration, users, roles, server management
- `neo4j-cypher-skill` — Cypher 4.x / 5.x migration to 2025.x
