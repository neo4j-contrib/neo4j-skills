# L3 Reference Files — Folder Structure and Routing

This README documents the four-folder structure of the `references/` directory, defines the READ/WRITE/SCHEMA/ADMIN categories, lists current files and their load conditions, and provides guidance for adding new L3 files.

Agents should consult SKILL.md §"Query Construction Decision Tree" to select the correct folder. This README is the companion reference for humans and agents adding new L3 files.

---

## Category Definitions

| Category | Definition | Primary clauses |
|---|---|---|
| **READ** | Queries that only read data; never modify the graph. Safe to run without a write transaction. | `MATCH`, `OPTIONAL MATCH`, `WITH`, `RETURN`, `CALL` subquery, `COUNT{}`, `COLLECT{}`, `EXISTS{}`, `SEARCH` |
| **WRITE** | Queries that modify nodes, relationships, or properties. Must run in a write transaction; can be rolled back in tests. | `CREATE`, `MERGE`, `SET`, `REMOVE`, `DELETE`, `DETACH DELETE`, `CALL IN TRANSACTIONS`, `FOREACH`, `LOAD CSV` |
| **SCHEMA** | DDL statements that create or alter graph indexes and constraints, or inspect schema metadata. Structural changes; not data changes. | `CREATE INDEX`, `DROP INDEX`, `CREATE CONSTRAINT`, `DROP CONSTRAINT`, `SHOW INDEXES`, `SHOW CONSTRAINTS`, `SHOW PROCEDURES` |
| **ADMIN** | Database lifecycle and access-control commands. Require admin privileges; separate from schema DDL. | `CREATE DATABASE`, `DROP DATABASE`, `ALTER USER`, roles/privileges, `SHOW TRANSACTIONS`, `SHOW SERVERS`, `KILL TRANSACTION` |

---

## Folder Inventory

### `read/` — READ queries

| File | Load when |
|---|---|
| `cypher25-patterns.md` | Variable-length paths, QPEs (`{m,n}`, `+`, `*`), `SHORTEST`, match modes (`DIFFERENT RELATIONSHIPS`, `REPEATABLE ELEMENTS`), non-linear patterns, path pattern expressions |
| `cypher25-functions.md` | Aggregating functions (`count`, `collect`, `avg`, `sum`, `stdev`), list functions, string functions, scalar functions, predicate functions, math/trig, temporal, spatial, vector functions |
| `cypher25-subqueries.md` | `CALL { }` subqueries, `OPTIONAL CALL`, `COUNT { }` / `COLLECT { }` / `EXISTS { }` subquery forms, correlated subquery scope rules |
| `cypher25-types-and-nulls.md` | Type errors, null propagation, `IS NULL` / `IS NOT NULL` guards, `coalesce()`, type casting functions, type predicate expressions (`IS :: TYPE`) |
| `cypher25-runtime.md` | Runtime hints (`CYPHER runtime=parallel`, `pipelined`, `slotted`, `interpreted`), when to use parallel runtime, when NOT to use it (OLTP, writes), EXPLAIN/PROFILE plan verification, version availability |

### `write/` — WRITE queries

| File | Load when |
|---|---|
| `cypher25-call-in-transactions.md` | Batch writes, `CALL { } IN TRANSACTIONS OF N ROWS`, `ON ERROR` options, `REPORT STATUS AS`, `CONCURRENT` transactions, large-scale `LOAD CSV` |

### `schema/` — SCHEMA DDL

| File | Load when |
|---|---|
| `cypher25-indexes.md` | Creating or dropping indexes or constraints, `SHOW INDEXES`, `SHOW CONSTRAINTS`, `SEARCH` clause (vector index queries), `db.index.fulltext.queryNodes()` (fulltext), `USING INDEX` hints, index type selection |

### `admin/` — ADMIN (currently empty)

No L3 files yet. ADMIN queries (database lifecycle, users, roles, privileges, SHOW TRANSACTIONS, SHOW SERVERS) are covered by `neo4j-cli-tools-skill`. If this skill is extended to cover admin in future, add files here. Do **not** add schema DDL or index commands here.

### `references/` root — cross-cutting

| File | Load when |
|---|---|
| `cypher-style-guide.md` | Naming conventions (labels, relationship types, properties), keyword casing rules, indentation, spacing, pattern authoring best practices; applies to ALL categories |

---

## Split Rationale

### CALL subquery (`read/`) vs CALL IN TRANSACTIONS (`write/`)

These share the `CALL { }` syntax but differ fundamentally:

- **`CALL { }` subquery** (`read/cypher25-subqueries.md`) — a read subquery executed once per outer row, within the same transaction. Can be used in any read or write query. The result rows flow back into the outer query. No batching.
- **`CALL { } IN TRANSACTIONS`** (`write/cypher25-call-in-transactions.md`) — a batch-write mechanism. Executes the inner subquery in separate, committed transactions of N input rows. Only allowed in implicit transactions (not inside explicit `BEGIN`/`COMMIT`). Cannot be used for reads where you need results back in the outer query. Violating this distinction causes runtime errors.

Load `read/cypher25-subqueries.md` for any `CALL {}` that returns results to the outer query or is used in a read context. Load `write/cypher25-call-in-transactions.md` only for batch-write patterns where committed batches are required.

### SCHEMA (`schema/`) vs ADMIN (`admin/`)

These are often conflated but are distinct privilege domains in Neo4j:

- **SCHEMA** (`schema/`) — index and constraint DDL; requires `CREATE INDEX` / `DROP INDEX` privilege (not full admin). Covers structural graph schema: what indexes exist, what constraints are enforced, what procedures are available. Read with `SHOW INDEXES`, `SHOW CONSTRAINTS`, `SHOW PROCEDURES`.
- **ADMIN** (`admin/`) — database lifecycle (`CREATE DATABASE`, `DROP DATABASE`), user management (`ALTER USER`, `CREATE USER`, `SHOW USERS`), role and privilege management (`GRANT`, `DENY`, `REVOKE`), transaction management (`SHOW TRANSACTIONS`, `KILL TRANSACTION`), and server/cluster management (`SHOW SERVERS`). Requires admin or the specific system privilege.

An agent that can query indexes may not have admin rights. Never load admin-category files for schema-inspection queries, and never load schema-category files for database lifecycle commands.

---

## Adding New L3 Files

1. **Determine category** using the definitions above. If the file covers clauses in more than one category, it must be split — do not create cross-category files.
2. **Place in the correct folder** (`read/`, `write/`, `schema/`, or `admin/`). Cross-cutting files (like `cypher-style-guide.md`) go at the `references/` root.
3. **Update `SKILL.md`** — add a row to the "Step 2" routing table in §"Query Construction Decision Tree" so agents know when to load the new file.
4. **Update this README** — add the file to the folder inventory table above with a clear "Load when" condition.
5. **File budget**: every L3 file must be ≤ 2,000 tokens. Files that hit the token budget before covering all required content must be further split into narrower topic files.
