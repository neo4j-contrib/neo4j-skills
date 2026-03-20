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
2. **Schema first** — inspect schema before writing any `MATCH` clause
3. **Params always** — `$param` for all predicates and MERGE keys; never inline literals (exception: `LIMIT N`)
4. **MERGE safety** — every `MERGE` must have `ON CREATE SET` and `ON MATCH SET`
5. **Validate** — `EXPLAIN` every query; `PROFILE` when performance matters
6. **Recover** — handle 0-result queries, TypeErrors, timeouts autonomously
7. **READ/WRITE/ADMIN first** — categorize, then load only the relevant L3 folder

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

Run all five inspection queries before writing any `MATCH` clause:

```cypher
-- 1. Graph topology
CYPHER 25 CALL db.schema.visualization() YIELD nodes, relationships RETURN nodes, relationships;

-- 2. Online indexes
CYPHER 25 SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state
WHERE state = 'ONLINE' RETURN name, type, labelsOrTypes, properties;

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

---

## Parameter Discipline

```cypher
-- Correct
CYPHER 25 MATCH (n:Person {name: $name}) RETURN n;

-- Never do this
CYPHER 25 MATCH (n:Person {name: 'Alice'}) RETURN n;
```

Use `$param` for: WHERE predicates, MERGE keys and property maps, SET values. Enables plan caching; prevents injection. Pass via `.execute_query(query, name="Alice")`.

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

### SEARCH Clause (Vector — Neo4j 2026.01+, Preview)

```cypher
-- SEARCH clause (vector only in 2026.01)
CYPHER 25
MATCH (c:Chunk) SEARCH (c) USING VECTOR INDEX news
  WITH QUERY VECTOR $embedding
WHERE score > 0.8
RETURN c.text, score LIMIT 10;

-- Fulltext always via procedure in 2026.01
CYPHER 25
CALL db.index.fulltext.queryNodes('entity', $query) YIELD node, score
RETURN node.name, score LIMIT 20;
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
| `AllNodesScan` | Missing index | Add `USING INDEX` hint or create index |
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
