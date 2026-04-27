---
name: neo4j-import-skill
description: >
  Use when importing structured data into Neo4j: LOAD CSV, UNWIND + CALL IN TRANSACTIONS
  batch upserts, neo4j-admin import (offline bulk load), apoc.load.csv/json for
  relational-to-graph migrations, or verifying import counts and constraints.
  Does NOT handle unstructured document / PDF / JSON chunking pipelines — use
  neo4j-document-import-skill. Does NOT handle live application write queries —
  use neo4j-cypher-skill. Does NOT handle neo4j-admin CLI flags — use
  neo4j-cli-tools-skill.
status: draft
version: 0.1.0
allowed-tools: Bash, WebFetch
---

# Neo4j Import Skill

> **Status: Draft / WIP** — Content is a placeholder. Procedural steps and reference files to be added.

## When to Use

- Importing CSV files into Neo4j (LOAD CSV, apoc.load.csv)
- Batch-upserting nodes and relationships (UNWIND + CALL IN TRANSACTIONS)
- Migrating relational data (SQL → graph) or bulk-loading with neo4j-admin import
- Verifying import completeness (counts, constraints, indexes)
- Choosing between online (Cypher) and offline (neo4j-admin) import methods

## When NOT to Use

- **Unstructured documents, PDFs, JSON chunking** → use `neo4j-document-import-skill`
- **Live application write patterns (MERGE, CREATE)** → use `neo4j-cypher-skill`
- **neo4j-admin CLI flags and backup/restore** → use `neo4j-cli-tools-skill`

---

## MCP Tool Usage

When the Neo4j MCP server is available, use it to execute Cypher:

| Operation | MCP tool | Notes |
|---|---|---|
| Schema inspection (SHOW CONSTRAINTS, SHOW INDEXES) | `read-cypher` | Always check before import |
| CREATE CONSTRAINT, CREATE INDEX | `write-cypher` | Run before any MERGE |
| LOAD CSV / CALL IN TRANSACTIONS | `write-cypher` | Confirm row count first |
| Verify counts (MATCH + count) | `read-cypher` | Post-import validation |

Always pass `database` parameter if not using the default: `{"code": "...", "database": "neo4j"}`.

---

## Import Method Decision Tree

```
1. File < 10M rows, online DB required        → LOAD CSV + CALL IN TRANSACTIONS
2. File > 10M rows, DB can go offline         → neo4j-admin database import
3. Source is a relational DB                  → ETL to CSV first, then LOAD CSV
4. Source is JSON/API                         → apoc.load.json or Python driver + UNWIND
5. Unstructured documents / embeddings needed → use neo4j-document-import-skill
```

---

## Pre-flight Checks

Before importing:
1. Create constraints: `CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE` — MERGE is unsafe without them
2. Confirm APOC if using `apoc.load.*`: `RETURN apoc.version()` — if fails, use plain `LOAD CSV` instead
3. Confirm you are connected to a primary (not a replica): `CALL dbms.cluster.role()` — imports must target PRIMARY

---

## Error Handling Modes

`CALL IN TRANSACTIONS` error behavior:

| Mode | Behavior | Use when |
|---|---|---|
| `ON ERROR CONTINUE` | Logs batch error, continues with next batch | Resilient bulk load; track errors separately |
| `ON ERROR BREAK` | Stops at first failed batch, does not roll back previous batches | Semi-strict: stop early but keep completed work |
| `ON ERROR FAIL` | Rolls back entire transaction | All-or-nothing strict import |

Default is `ON ERROR FAIL` if omitted.

---

## File Path Rules

- `file:///persons.csv` → reads from Neo4j's `import/` directory (default: `$NEO4J_HOME/import/`)
- `https://example.com/data.csv` → remote URL (requires `dbms.security.allow_csv_import_from_file_urls=true`)
- Aura: only `https://` URLs are supported — no local filesystem access

---

## Core Patterns

### LOAD CSV (online, transactional)

```cypher
CYPHER 25
LOAD CSV WITH HEADERS FROM 'file:///persons.csv' AS row
CALL (row) {
  MERGE (p:Person {id: row.id})
  ON CREATE SET p.name = row.name, p.email = row.email, p.createdAt = datetime()
  ON MATCH  SET p.updatedAt = datetime()
} IN TRANSACTIONS OF 10000 ROWS
  ON ERROR CONTINUE
```

### Relationship import (match nodes first)

```cypher
CYPHER 25
LOAD CSV WITH HEADERS FROM 'file:///knows.csv' AS row
CALL (row) {
  MATCH (a:Person {id: row.fromId})
  MATCH (b:Person {id: row.toId})
  MERGE (a)-[:KNOWS]->(b)
} IN TRANSACTIONS OF 5000 ROWS
  ON ERROR CONTINUE
```

### neo4j-admin import (offline bulk load)

```bash
neo4j-admin database import full \
  --nodes=Person=persons_header.csv,persons.csv \
  --relationships=KNOWS=knows_header.csv,knows.csv \
  --database=neo4j \
  --overwrite-destination
```

---

## Import Checklist

- [ ] Constraints created before import (prevents duplicates, enables index on MERGE key)
- [ ] `CALL IN TRANSACTIONS` used for large files (avoids heap overflow)
- [ ] `ON ERROR CONTINUE` set with error logging for production loads
- [ ] Node import completes before relationship import
- [ ] Row counts verified: `MATCH (n:Label) RETURN count(n)`
- [ ] `.env` / credentials not hardcoded in scripts

---

## References

- [Importing CSV Data into Neo4j](https://neo4j.com/docs/cypher-manual/current/clauses/load-csv/)
- [CALL IN TRANSACTIONS](https://neo4j.com/docs/cypher-manual/current/subqueries/call-in-transactions/)
- [neo4j-admin import](https://neo4j.com/docs/operations-manual/current/tools/neo4j-admin/neo4j-admin-import/)
- [APOC load procedures](https://neo4j.com/docs/apoc/current/import/)
- [GraphAcademy: Importing CSV Data](https://graphacademy.neo4j.com/courses/importing-cypher/)
