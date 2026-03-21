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

## When NOT to Use This Skill

- **Driver code** → use `neo4j-migration-skill`
- **DB administration** (CREATE DATABASE, ALTER USER, roles, privileges, SHOW SERVERS) → use `neo4j-cli-tools-skill`
- **Cypher 4.x / 5.x migration** → use `neo4j-cypher-skill`
- **GQL-only clauses**: never emit `LET`, `FINISH`, `FILTER`, `NEXT`, `INSERT` — use `WITH`, `RETURN`, `WHERE`, `CREATE`

---

## Autonomous Operation Protocol

Non-negotiable defaults — apply before writing any query:

1. **CYPHER 25 always** — first token of every query
2. **Schema first** — inspect schema before writing any `MATCH` clause; if schema is provided in the prompt, use it directly
3. **Output mode** — check invocation context for `interactive` (literals) or `programmatic` (parameters); default to `interactive`; always return both (see Output Mode section)
4. **Schema fidelity** — after generating Cypher, validate every label, rel-type, and property against the schema before returning (see MUST VALIDATE section)
5. **MERGE safety** — every `MERGE` must have `ON CREATE SET` and `ON MATCH SET`
6. **Validate** — `EXPLAIN` every query; `PROFILE` when performance matters
7. **Recover** — handle 0-result queries, TypeErrors, timeouts autonomously
8. **READ/WRITE/ADMIN first** — categorize, then load only the relevant L3 folder

---

## Cypher 25 Pragma + Schema-First Protocol

Every query begins with `CYPHER 25` (enables QPEs, SEARCH, CALL scope clauses, type predicates).

**If schema context is provided in the prompt** (labels, properties, indexes, constraints, vector dimensions) — use it directly. Do NOT run inspection queries; the user may lack read access, schema queries cannot be mixed with data queries in the same transaction, and the agent may never see results from a separate query turn.

**If no schema context is provided** — run these inspection queries before any `MATCH` clause:

```cypher
CYPHER 25 CALL db.schema.visualization() YIELD nodes, relationships RETURN nodes, relationships;
CYPHER 25 SHOW INDEXES YIELD name, type, labelsOrTypes, properties, options, state WHERE state = 'ONLINE' RETURN name, type, labelsOrTypes, properties, options;
CYPHER 25 SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties RETURN name, type, labelsOrTypes, properties;
-- Detect APOC:
CYPHER 25 SHOW PROCEDURES WHERE name = 'apoc.meta.schema' YIELD name RETURN count(name) > 0 AS apocAvailable;
-- If APOC available: CYPHER 25 CALL apoc.meta.schema() YIELD value RETURN value;
-- Otherwise: CYPHER 25 CALL db.schema.nodeTypeProperties() YIELD nodeLabels, propertyName, propertyTypes, mandatory RETURN nodeLabels, propertyName, propertyTypes, mandatory;
```

**Vector index dimensions**: always read from the provided schema context (the `dimensions` field on the index or property). Never introspect `options.vector.dimensions` at runtime — this requires a separate schema query the agent may not be able to execute. If dimensions are absent from the provided schema, state the assumption explicitly in a comment.

---

## Output Mode: Literals vs Parameters

**Always return both formats** as a YAML block. Default mode: `interactive` (literal values). `programmatic` mode uses `$param` for plan caching.

```yaml
query_literals: |
  CYPHER 25
  MATCH (n:Organization {name: 'Apple'}) RETURN n.name LIMIT 10
query_parametrized: |
  CYPHER 25
  MATCH (n:Organization {name: $name}) RETURN n.name LIMIT 10
parameters:
  name: "Apple"
```

Wrap `query_literals` in a ` ```cypher ` block too for direct rendering in interactive mode.

---

## MUST VALIDATE: Schema Fidelity

**After generating any Cypher query, before returning, verify every schema element against the provided schema. This is mandatory when a schema context is present in the prompt.**

### Validation checklist

| Element | Check | Action on failure |
|---|---|---|
| Node label `(n:Label)` | Label exists in schema's Node Labels | Replace with correct label from schema |
| **Label-free node** `(n)` | **Never emit unless strictly required** | **Add the correct label from schema** |
| Relationship type `-[:TYPE]->` | Type exists in schema's Relationship Types | Replace with nearest match from schema |
| Property `n.propName` | `propName` listed for that label in Node Properties | Remove or replace with a valid property |
| Index name in procedure call | Index name exists in schema's Indexes | Use correct index name from schema |
| **MERGE pattern** | Single-node with key only; rel MERGE has pre-bound endpoints; both `ON CREATE SET` and `ON MATCH SET` present | Refactor per MERGE Safety rules |

**Label-free `MATCH (n)` is forbidden** except in two narrow cases: (1) re-referencing a variable already bound with a label earlier in the same query; (2) inside a QPE group variable where the label is implied by the path pattern. In every other case, always specify the label. A label-free MATCH causes an `AllNodesScan` and will scan the entire graph.

### Vocabulary discipline

Business questions use domain vocabulary that does **not** match schema labels:

| Business term | Do NOT use | MUST use (from schema) |
|---|---|---|
| "company", "companies", "firm" | `:Company` | Use the label from the provided schema (e.g., `:Organization`) |
| "movie", "film" | `:Film` | Use label from schema (e.g., `:Movie`) |
| "user", "customer" | `:Member` | Use label from schema |
| ownership, "owns" | `:OWNS` | Use rel type from schema (e.g., `:HAS_SUBSIDIARY`) |
| "sends money" | `:TRANSFERS` | Use rel type from schema (e.g., `:SENT`) |

**Rule**: Never infer label or relationship type names from the business question wording. Always look them up in the provided schema. If no schema is provided, run the Schema-First Protocol before writing any MATCH clause.

### QPE quantifier compatibility

| Database | `+` quantifier | `{1,}` equivalent |
|---|---|---|
| Local Neo4j 2026.x | ✓ supported | ✓ supported |
| demo.neo4jlabs.com | ✗ NOT supported | ✓ use this |

**Default to `{1,}` form** unless you have confirmed the target DB supports `+`. Same for `*` → use `{0,}`.

---

## Value Normalization and Domain Translation

**When schema provides `values:` (enum) or `sample:` data, map user language to stored values before writing any query.**

> **Output format is internal.** Never mention `$param` placeholders or YAML keys in user-facing comments or responses.

**Rules:**
1. **Schema enum match** — map "active customers" → `'ACTIVE'` from schema `values`; "The Matrix" → `'Matrix, The'` if samples show article-inversion. Comment: `-- Translated: user said "active" → 'ACTIVE' (stored enum value)`
2. **Range validation** — if user value is outside schema `min`/`max` by 10×, surface a ⚠ concern and ask before proceeding
3. **ID pattern normalization** — `"txn 234"` → `"TXN-00234"` when samples show `"TXN-00001"` format
4. **No schema values?** — apply common-sense transformation (trim, uppercase, expand abbreviations); only elicit when genuinely insufficient

---

## Core Pattern Cheat Sheet

### MERGE Safety

**Rules:**
1. **Key property only** — `MERGE` on constrained key property(ies) only; set other properties in `ON CREATE SET` / `ON MATCH SET`
2. **Pre-bind endpoints** — for relationship MERGE, `MATCH` or `MERGE` both nodes first; never MERGE a full path
3. **Both sub-clauses** — every MERGE must have `ON CREATE SET` and `ON MATCH SET`

```cypher
-- DO: CYPHER 25 MATCH (a:Person {id:$a}) MATCH (b:Person {id:$b}) MERGE (a)-[r:KNOWS]->(b) ON CREATE SET r.since=date() ON MATCH SET r.lastSeen=date();
-- DON'T: MERGE (p:Person {id:$id, name:$name}) -- multi-property = duplicates
-- DON'T: MERGE (:Person {id:$a})-[:KNOWS]->(:Person {id:$b}) -- unbound = ghost nodes
```

### Quantified Path Expressions (QPEs)

**ALWAYS prefer `{1,}` over `+` and `{0,}` over `*`** — `+`/`*` shorthands fail on some servers (e.g. demo.neo4jlabs.com). Use `+`/`*` only after confirming server support.

```cypher
-- {m,n} fixed range — universal, works everywhere
CYPHER 25 MATCH (a:Person)-[:KNOWS]-{1,3}(b:Person {name: $name}) RETURN a.name;

-- {1,} one-or-more (prefer over +); {0,} zero-or-more (prefer over *)
CYPHER 25 MATCH (root:Category) (()-[:HAS_SUBCATEGORY]->(){1,}) (leaf:Category) RETURN root.name, leaf.name;

-- Full QPE with group variable (parentheses required around the hop pattern)
CYPHER 25 MATCH ((a:Stop)-[r:NEXT]->(b:Stop)){1,5} RETURN a, b, r;
```

**NEVER write `SHORTEST 1 (a)-[:REL]+`** — wrap in group: `SHORTEST 1 (a)(()-[:REL]->()){1,}(b)`.

**REPEATABLE ELEMENTS** requires bounded quantifier — no `+` or `*`.

### WITH Cardinality Reset

`WITH` closes the row stream; use it to filter aggregated results before further traversal: `MATCH (p:Person)-[:ACTED_IN]->(m:Movie) WITH p, count(m) AS mc WHERE mc > 5 MATCH (p)-[:KNOWS]->(f:Person) RETURN p.name, f.name;`

### CASE WHEN Conditional

```cypher
CYPHER 25
MATCH (n:Event)
RETURN n.name,
  CASE WHEN n.type = 'A' THEN 'Alpha'
       WHEN n.type = 'B' THEN 'Beta'
  ELSE 'Other' END AS category;
```

**Note**: Use `CASE WHEN ... THEN ... ELSE ... END`. The standalone `WHEN ... THEN ... END` form (without `CASE`) is not yet supported in Neo4j 2026.x.

### CALL IN TRANSACTIONS

```cypher
-- CORRECT: CYPHER 25 MATCH (c:Customer) CALL (c) { SET c.flag = 'done' } IN TRANSACTIONS OF 100 ROWS RETURN count(c);
```
**NEVER write** `CALL (x) IN TRANSACTIONS { }` — `IN TRANSACTIONS` comes AFTER the `{ }` block.

---

### SEARCH Clause (Vector — GA in Neo4j 2026.02.1+)

> **SEARCH is vector-only** — fulltext always uses `db.index.fulltext.queryNodes()`. **Version check required**: SEARCH clause is GA in Neo4j **2026.02.1+**; use the procedure fallback for older versions (including demo.neo4jlabs.com which pre-dates 2026.02).

```cypher
-- Vector 2026.02.1+: CYPHER 25 MATCH (c:Chunk) SEARCH (c) USING VECTOR INDEX news WITH QUERY VECTOR $embedding WHERE score > 0.8 RETURN c.text, score LIMIT 10;
-- Vector <2026.02 (procedure fallback): CYPHER 25 CALL db.index.vector.queryNodes('news', 5, $embedding) YIELD node, score RETURN node.text, score;
-- Fulltext (all versions): CYPHER 25 CALL db.index.fulltext.queryNodes('entity', $query) YIELD node, score RETURN node.name, score LIMIT 20;
```

---

## Deprecated Syntax → Cypher 25 Preferred

| Deprecated | Cypher 25 |
|---|---|
| `[:REL*1..5]` | `-[:REL]-{1,5}` |
| `[:REL*]` | `-[:REL]*` |
| `shortestPath((a)-[*]->(b))` | `SHORTEST 1 (a)(()-[]->()){1,}(b)` |
| `allShortestPaths((a)-[*]->(b))` | `ALL SHORTEST (a)(()-[]->()){1,}(b)` |
| `CALL { WITH x ... }` | `CALL (x) { ... }` |
| `id(n)` | `elementId(n)` |
| `collect()[..N]` | `COLLECT { MATCH ... RETURN ... LIMIT N }` |

---

## FOREACH vs UNWIND

| Use | When |
|---|---|
| `FOREACH (x IN list \| clause)` | Side-effect only — no RETURN value needed |
| `UNWIND list AS x` | Need to inspect, filter, or return list items |

`FOREACH` cannot be followed by `RETURN`. When in doubt, use `UNWIND`.

---

## USE Clause (Multi-Database)

```cypher
CYPHER 25 USE myDatabase MATCH (n:Person) RETURN n.name LIMIT 5;
```

`USE` before query body. Omit when the driver connection already targets the correct database.

---

## Query Construction Decision Tree

**Step 1 — Categorize:**

| Category | Clauses | L3 Folder |
|---|---|---|
| **READ** | MATCH, OPTIONAL MATCH, CALL subquery, WITH, RETURN, COUNT{}/COLLECT{}/EXISTS{}, SEARCH | `references/read/` |
| **WRITE** | CREATE, MERGE, SET, REMOVE, DELETE, DETACH DELETE, CALL IN TRANSACTIONS, FOREACH, LOAD CSV | `references/write/` |
| **SCHEMA** | CREATE/DROP INDEX, CREATE/DROP CONSTRAINT, SHOW INDEXES, SHOW CONSTRAINTS, SHOW PROCEDURES | `references/schema/` |
| **ADMIN** | CREATE/DROP DATABASE, ALTER USER, roles/privileges, SHOW TRANSACTIONS, SHOW SERVERS | `references/admin/` |

**Step 2 — Load only the relevant L3 file(s):**

| Query type | Load |
|---|---|
| Variable-length paths, QPEs, match modes | `read/cypher25-patterns.md` |
| Aggregation, list, string, temporal, spatial, vector functions | `read/cypher25-functions.md` |
| CALL subquery, COUNT{}, COLLECT{}, EXISTS{} | `read/cypher25-subqueries.md` |
| Type errors, null propagation, casting, type predicates | `read/cypher25-types-and-nulls.md` |
| Batch writes, CALL IN TRANSACTIONS | `write/cypher25-call-in-transactions.md` |
| Index creation, SEARCH, fulltext, vector, hints | `schema/cypher25-indexes.md` |
| Naming, casing, formatting (all categories) | `cypher-style-guide.md` |

Do **not** load all files — select only what the current query type requires.

---

## EXPLAIN / PROFILE Validation Loop

`CYPHER 25 EXPLAIN <query>` — red flags: `AllNodesScan` (missing index or label-free MATCH), `CartesianProduct` (missing join predicate), `NodeByLabelScan` (no property filter index).

`CYPHER 25 PROFILE <query>` — check: `dbHits` (warn: > expected; fail: > expected × 10), `rows` (fail if < min_results), `allocatedMemory` (warn: > 100 MB; fail: > expected × 5), `elapsedTimeMs` (guidance only). Rewrite until `dbHits` and `allocatedMemory` are within bounds.

---

## Failure Recovery Patterns

**0-Result Queries:** (1) verify params non-null and correctly typed; (2) remove `WHERE` predicates one at a time to isolate; (3) check label/rel-type spelling against schema; (4) EXPLAIN to confirm index used.

**TypeErrors:** prefer `toIntegerOrNull`/`toFloatOrNull` over base casting; guard with `IS NOT NULL` before coercion.

**DateTime vs date() mismatch** — `DateTime >= date('2025-01-01')` returns 0 rows: use `.year` accessor (`t.date.year = 2025`) or `datetime()` literals for DateTime-typed properties.

**Timeouts:** EXPLAIN → fix AllNodesScan/CartesianProduct → add LIMIT → switch to `CALL IN TRANSACTIONS OF 1000 ROWS`.

---

## WebFetch Escalation

**WebFetch is always available for online agents.** Do not wait until L3 reference files are insufficient — fetch Neo4j docs pages proactively whenever a query involves syntax you are not fully certain about. L3 reference files are token-budget-truncated (≤ 2,000 tokens each); the full docs pages contain the complete picture. Use WebFetch as a **proactive, first-class** knowledge source.

| Trigger | URL |
|---|---|
| Specific clause semantics | `https://neo4j.com/docs/cypher-manual/25/clauses/{clause}/` |
| Function signatures | `https://neo4j.com/docs/cypher-manual/25/functions/{type}/` |
| Path / QPE edge cases | `https://neo4j.com/docs/cypher-manual/25/patterns/` |
| Full syntax overview | `https://neo4j.com/docs/cypher-cheat-sheet/25/all/` |

High-priority pages: `merge/`, `with/`, `call-subquery/`, `search/`, `aggregating/`, `use/`
