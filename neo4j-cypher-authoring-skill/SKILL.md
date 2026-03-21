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

## Cypher 25 Version Pragma

Every generated query must begin with `CYPHER 25`. Selects the Cypher 25 parser; enables QPEs, WHEN, SEARCH, CALL scope clauses, type predicates. Without it, Neo4j defaults to Cypher 5 — new syntax causes parse errors.

```cypher
CYPHER 25
MATCH (n:Person) RETURN n.name LIMIT 10
```

**Compat**: to target a Cypher 5–only server, omit the pragma and document the constraint.

---

## Schema-First Protocol

**If schema context is provided in the prompt** (labels, properties, indexes, constraints, vector dimensions) — use it directly. Do NOT run inspection queries; the user may lack read access, schema queries cannot be mixed with data queries in the same transaction, and the agent may never see results from a separate query turn.

**If no schema context is provided** — run the five inspection queries below before writing any `MATCH` clause:

```cypher
-- 1. Graph topology
CYPHER 25 CALL db.schema.visualization() YIELD nodes, relationships RETURN nodes, relationships;

-- 2. Online indexes (includes vector dimensions in options map)
CYPHER 25 SHOW INDEXES YIELD name, type, labelsOrTypes, properties, options, state
WHERE state = 'ONLINE' RETURN name, type, labelsOrTypes, properties, options;

-- 3. Constraints
CYPHER 25 SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties
RETURN name, type, labelsOrTypes, properties;

-- 4. Detect APOC (never throws)
CYPHER 25 SHOW PROCEDURES WHERE name = 'apoc.meta.schema'
YIELD name RETURN count(name) > 0 AS apocAvailable;

-- 5a. Property schema — APOC preferred (fast)
CYPHER 25 CALL apoc.meta.schema() YIELD value RETURN value;

-- 5b. Property schema — fallback when APOC absent (slow on large graphs)
CYPHER 25 CALL db.schema.nodeTypeProperties()
YIELD nodeLabels, propertyName, propertyTypes, mandatory
RETURN nodeLabels, propertyName, propertyTypes, mandatory;
CYPHER 25 CALL db.schema.relTypeProperties()
YIELD relType, propertyName, propertyTypes, mandatory
RETURN relType, propertyName, propertyTypes, mandatory;
```

Run 5a when `apocAvailable = true`; run 5b otherwise.

**Vector index dimensions**: always read from the provided schema context (the `dimensions` field on the index or property). Never introspect `options.vector.dimensions` at runtime — this requires a separate schema query the agent may not be able to execute. If dimensions are absent from the provided schema, state the assumption explicitly in a comment.

---

## Output Mode: Literals vs Parameters

**Interactive mode** (human running queries directly): use literal values. Immediately executable, no runtime config needed.

**Programmatic mode** (queries used in application code): use `$param` placeholders. Enables plan caching; prevents injection. Pass via `.execute_query(query, name="Alice")`.

**Always return both formats** as a YAML block, plus a parameter resolution section:

```yaml
query_literals: |
  CYPHER 25
  MATCH (n:Organization {name: 'Apple'})
  RETURN n.name, n.description LIMIT 10

query_parametrized: |
  CYPHER 25
  MATCH (n:Organization {name: $name})
  RETURN n.name, n.description LIMIT 10

parameters:
  name: "Apple"
```

When `interactive` is the mode (default), wrap `query_literals` in a ` ```cypher ` block too so it renders properly. When `programmatic` is the mode, highlight `query_parametrized` as the primary output.

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

**When a schema context with sample, enum, or range data is provided, apply these rules before writing any query.**

> **Output format is an internal detail.** When communicating concerns or translated values to the user (comments, ⚠ notices), never mention `$param` placeholders, YAML keys, or dual-format output — those are implementation details of the query output, invisible to the end user.

### 1 — Translate user-supplied values to schema domain values

Users speak in business language; the database stores domain-specific codes or formats. If the schema supplies `values:` (enum) or `sample:` entries for a property, map the user's input to the nearest matching stored value.

| User says | Schema sample / values | Use in query |
|---|---|---|
| "Chicago" | Airport codes: `["ORD", "MDW", "CHI"]` | `"ORD"` (primary airport) |
| "bolt 134" | Transaction IDs: `["BOLT-001-INV", "BOLT-134-INV"]` | `"BOLT-134-INV"` |
| "active customers" | status values: `["ACTIVE", "INACTIVE", "SUSPENDED"]` | `"ACTIVE"` |
| "last year" | year range 1990–2024 | `datetime().year - 1` |

**Rule**: When you infer a translation, state it explicitly in a comment above the query:
```cypher
-- Translated: user said "Chicago" → using "ORD" (primary IATA code in this dataset)
CYPHER 25
MATCH (f:Flight)-[:DEPARTS_FROM]->(a:Airport {code: "ORD"}) RETURN f;
```

### 2 — Validate numeric values against observed ranges

If the schema provides `min:` / `max:` for a property and the user's value is outside that range by more than an order of magnitude, **surface a concern before writing the query**:

```
⚠ Value concern: You asked for age = -5. Schema shows Customer.age range 18–95.
  Negative age is outside the observed domain. Proceeding with age = 5 (assuming typo).
  If you meant a different field, please clarify.
```

**Triggers that require explicit elicitation (do not silently guess)**:
- Negative value where schema `min` ≥ 0 (e.g. negative age, negative amount)
- Value > 10× schema `max` (e.g. temperature 50,000 K when range is 200–400 K)
- ID/code format mismatch when `values:` or `sample:` are provided and none match the input
- Date/year outside the observed range by more than 5 years

### 3 — ID pattern recognition

When schema samples reveal a structured ID format, infer the pattern and apply it:

| Observed samples | Inferred pattern | User input → stored value |
|---|---|---|
| `"TXN-00001"`, `"TXN-00234"` | `TXN-{5d}` zero-padded | `"txn 234"` → `"TXN-00234"` |
| `"ACC-ABC123"`, `"ACC-XYZ789"` | `ACC-{alphanum}` uppercase | `"acc-abc123"` → `"ACC-ABC123"` |

Always state the inferred pattern in a comment and offer the normalized value to the user for confirmation when there is ambiguity.

### 4 — When values are NOT provided in schema

If `values:` and `sample:` are absent for a property, apply common-sense transformations to the user's input (normalise case to match the property type, trim whitespace, expand obvious abbreviations, infer standard formats) and use the result. Elicit clarification only when the information provided is genuinely insufficient to generate a query at all — not as a default.

---

## Core Pattern Cheat Sheet

### MERGE Safety

```cypher
CYPHER 25
MERGE (p:Person {id: $id})
ON CREATE SET p.name = $name, p.createdAt = datetime()
ON MATCH SET p.updatedAt = datetime()
RETURN p;
```

### Quantified Path Expressions (QPEs)

```cypher
-- {m,n} fixed range
CYPHER 25 MATCH (a:Person)-[:KNOWS]-{1,3}(b:Person {name: $name}) RETURN a.name;

-- + one or more
CYPHER 25 MATCH (root:Category)-[:HAS_SUBCATEGORY]+->(leaf:Category) RETURN root.name, leaf.name;

-- * zero or more
CYPHER 25 MATCH (n:Person)-[:KNOWS]*(m:Person) RETURN n, m;

-- Full QPE with group variable
CYPHER 25 MATCH ((a:Stop)-[r:NEXT]->(b:Stop)){1,5} RETURN a, b, r;
```

**REPEATABLE ELEMENTS** requires bounded quantifier — no `+` or `*`.

### WITH Cardinality Reset

```cypher
CYPHER 25
MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
WITH p, count(m) AS movieCount
WHERE movieCount > 5
MATCH (p)-[:KNOWS]->(friend:Person)
RETURN p.name, friend.name;
```

`WITH` closes the row stream; use it to filter before expensive traversals.

### WHEN Conditional

```cypher
CYPHER 25
MATCH (n:Event)
RETURN n.name,
  WHEN n.type = 'A' THEN 'Alpha'
       n.type = 'B' THEN 'Beta'
  ELSE 'Other' END AS category;
```

### SEARCH Clause (Vector — GA in Neo4j 2026.02.1+)

```cypher
-- SEARCH clause (vector only; GA in Neo4j 2026.02.1 on local instances)
-- NOT available on demo.neo4jlabs.com — use db.index.vector.queryNodes() there
CYPHER 25
MATCH (c:Chunk) SEARCH (c) USING VECTOR INDEX news
  WITH QUERY VECTOR $embedding
WHERE score > 0.8
RETURN c.text, score LIMIT 10;

-- Fulltext: always via procedure (all Neo4j versions including demo)
CYPHER 25
CALL db.index.fulltext.queryNodes('entity', $query) YIELD node, score
RETURN node.name, score LIMIT 20;

-- Vector search on demo.neo4jlabs.com (no SEARCH clause):
CYPHER 25
CALL db.index.vector.queryNodes('news', 5, $embedding) YIELD node, score
RETURN node.text, score;
```

---

## Deprecated Syntax → Cypher 25 Preferred

| Deprecated | Cypher 25 |
|---|---|
| `[:REL*1..5]` | `-[:REL]-{1,5}` |
| `[:REL*]` | `-[:REL]*` |
| `shortestPath((a)-[*]->(b))` | `SHORTEST 1 (a)-[]-+(b)` |
| `allShortestPaths((a)-[*]->(b))` | `ALL SHORTEST (a)-[]-+(b)` |
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

**Step 1: Run EXPLAIN** — look for red-flag operators:

```cypher
CYPHER 25 EXPLAIN MATCH (n:Person {name: $name}) RETURN n;
```

| Operator | Problem | Fix |
|---|---|---|
| `AllNodesScan` | Missing index **or label-free `MATCH (n)`** | Add label + `USING INDEX` hint, or create index |
| `CartesianProduct` | Unconstrained cross-join | Add join predicate via `WHERE` |
| `NodeByLabelScan` (large label) | No property index | Use index or filter earlier with `WITH` |

**Step 2: If plan is clean, run PROFILE:**

```cypher
CYPHER 25 PROFILE MATCH (n:Person {name: $name}) RETURN n;
```

**Metrics:**

| Metric | Warning threshold | Hard fail |
|---|---|---|
| `dbHits` | > expected | > expected × 10 |
| `rows` | — | < `min_results` |
| `allocatedMemory` | > 100 MB | > expected × 5 |
| `elapsedTimeMs` | > expected | guidance only (CI varies) |

Rewrite until `dbHits` and `allocatedMemory` are within bounds.

---

## Failure Recovery Patterns

**0-Result Queries:**
1. Verify params are non-null and correctly typed
2. Remove `WHERE` predicates one at a time to isolate
3. Re-run `db.schema.visualization()` — label / rel type may be misspelled
4. Check `EXPLAIN` plan — confirm an index is used, not `AllNodesScan`
5. Return empty result; do not retry indefinitely

**TypeErrors** (`Cannot coerce STRING to INTEGER`):
1. Check property type from schema inspection
2. Cast: prefer `OrNull` variants (`toIntegerOrNull`, `toFloatOrNull`) to avoid runtime errors
3. Guard: `WHERE n.prop IS NOT NULL` before coercion

**Query Timeouts:**
1. Run `EXPLAIN` — look for `AllNodesScan` or `CartesianProduct`
2. Add or hint the correct index
3. Add `LIMIT`; for batch ops switch to `CALL IN TRANSACTIONS OF 1000 ROWS`
4. Report timeout with the plan; do not silently retry

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
