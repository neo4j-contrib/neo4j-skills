---
name: neo4j-import-skill
description: Import structured data into Neo4j — LOAD CSV, CALL IN TRANSACTIONS, neo4j-admin
  database import full (offline bulk), apoc.load.csv/json, apoc.periodic.iterate, driver
  batch writes. Covers method selection, header file format, type coercion, null handling,
  ON ERROR modes, CONCURRENT TRANSACTIONS, pre-import constraint setup, and post-import
  validation. Use when importing CSV/JSON/Parquet files, migrating relational data to graph,
  or bulk-loading large datasets. Does NOT handle unstructured document/PDF/vector chunking
  pipelines — use neo4j-document-import-skill. Does NOT handle live app write patterns
  (MERGE/CREATE) — use neo4j-cypher-skill. Does NOT handle neo4j-admin backup/restore/config
  — use neo4j-cli-tools-skill.
version: 1.0.0
allowed-tools: Bash WebFetch
---

# Neo4j Import Skill

## When to Use

- Importing CSV, JSON, or Parquet files into Neo4j
- Batch-upserting nodes and relationships (UNWIND + CALL IN TRANSACTIONS)
- Migrating relational data (SQL → graph)
- Bulk-loading large datasets offline (neo4j-admin import)
- Choosing between online (Cypher) and offline (admin) import methods
- Verifying import completeness (counts, constraints, index states)

## When NOT to Use

- **Unstructured docs, PDFs, vector chunks** → `neo4j-document-import-skill`
- **Live application writes (MERGE/CREATE in app code)** → `neo4j-cypher-skill`
- **neo4j-admin backup/restore/config** → `neo4j-cli-tools-skill`
- **GDS algorithm projection from existing graph** → `neo4j-gds-skill`

---

## Method Decision Table

| Dataset size | DB state | Source | Method |
|---|---|---|---|
| Any size | Online | CSV (Aura or local) | LOAD CSV + CALL IN TRANSACTIONS |
| < 1M rows | Online | List/API response | UNWIND + CALL IN TRANSACTIONS |
| > 10M rows | **Offline** (local/self-managed) | CSV / Parquet | `neo4j-admin database import full` |
| Any size | Online | APOC available | `apoc.periodic.iterate` + `apoc.load.csv` |
| Any size | Online | JSON/API | `apoc.load.json` or driver batching |
| Incremental delta | Offline (Enterprise) | CSV | `neo4j-admin database import incremental` |

**Aura**: only `https://` URLs — no `file:///`. Use neo4j-admin import only on self-managed.

---

## Pre-Import Checklist

Run in this exact order — skipping causes hard-to-debug duplicates or missed index usage:

**Constraints BEFORE import. Additional indexes AFTER import.**
- Constraints create implicit RANGE indexes used by MERGE during load + enforce uniqueness
- Additional non-unique indexes (TEXT, RANGE on non-key props, FULLTEXT) created after load — Neo4j populates them async from the committed data; poll `populationPercent` until 100%
- Creating extra indexes before import slows every write during load with no benefit

1. **Create uniqueness constraints** (enables index used by MERGE):
   ```cypher
   CREATE CONSTRAINT IF NOT EXISTS FOR (n:Person) REQUIRE n.id IS UNIQUE;
   CREATE CONSTRAINT IF NOT EXISTS FOR (n:Movie)  REQUIRE n.movieId IS UNIQUE;
   ```

2. **Verify APOC if using apoc.* procedures**:
   ```cypher
   RETURN apoc.version();
   ```
   If fails → APOC not installed. Use plain LOAD CSV instead.

3. **Confirm target is PRIMARY** (not replica):
   ```cypher
   CALL dbms.cluster.role() YIELD role RETURN role;
   ```
   If role ≠ `PRIMARY` → stop. Redirect write to PRIMARY endpoint.

4. **Count source file rows** before import (catch encoding issues early):
   ```bash
   wc -l data/persons.csv    # Linux/macOS
   ```

5. **Verify UTF-8 encoding** — LOAD CSV requires UTF-8. Re-encode if needed:
   ```bash
   file -i persons.csv       # Check encoding
   iconv -f latin1 -t utf-8 persons.csv > persons_utf8.csv
   ```

---

## LOAD CSV Patterns

### Basic node import with type coercion and null handling

```cypher
CYPHER 25
LOAD CSV WITH HEADERS FROM 'file:///persons.csv' AS row
CALL (row) {
  MERGE (p:Person {id: row.id})
  ON CREATE SET
    p.name       = row.name,
    p.age        = toIntegerOrNull(row.age),
    p.score      = toFloatOrNull(row.score),
    p.active     = toBoolean(row.active),
    p.born       = CASE WHEN row.born IS NOT NULL AND row.born <> '' THEN date(row.born) ELSE null END,
    p.createdAt  = datetime()
  ON MATCH SET
    p.updatedAt  = datetime()
} IN TRANSACTIONS OF 10000 ROWS
  ON ERROR CONTINUE
  REPORT STATUS AS s
RETURN s.transactionId, s.committed, s.errorMessage
```

Null/empty-string rules:
- CSV missing column → `null` (safe)
- CSV empty string `""` → stored as `""` **not** `null` — use `nullIf(row.x, '')` to convert
- `toInteger(null)` throws → always use `toIntegerOrNull()`
- `toFloat(null)` throws → always use `toFloatOrNull()`
- Neo4j never stores `null` properties — they are silently dropped on SET

### Relationship import (nodes must exist first)

```cypher
CYPHER 25
LOAD CSV WITH HEADERS FROM 'file:///knows.csv' AS row
CALL (row) {
  MATCH (a:Person {id: row.fromId})
  MATCH (b:Person {id: row.toId})
  MERGE (a)-[:KNOWS {since: toIntegerOrNull(row.year)}]->(b)
} IN TRANSACTIONS OF 5000 ROWS
  ON ERROR CONTINUE
  REPORT STATUS AS s
```

Always import ALL nodes before ANY relationships — MATCH fails on missing nodes.

### Tab-separated or custom delimiter

```cypher
CYPHER 25
LOAD CSV WITH HEADERS FROM 'file:///data.tsv' AS row FIELDTERMINATOR '\t'
CALL (row) { MERGE (p:Person {id: row.id}) }
IN TRANSACTIONS OF 10000 ROWS ON ERROR CONTINUE
```

### Compressed files (ZIP / gzip — local files only)

```cypher
LOAD CSV WITH HEADERS FROM 'file:///archive.csv.gz' AS row ...
```

### Cloud storage (Enterprise Edition)

| Scheme | Example |
|---|---|
| AWS S3 | `s3://my-bucket/data/persons.csv` |
| Google Cloud Storage | `gs://my-bucket/persons.csv` |
| Azure Blob | `azb://account/container/persons.csv` |

### Useful built-in functions inside LOAD CSV

```cypher
linenumber()   // current line number — use as fallback ID
file()         // absolute path of file being loaded
```

---

## CALL IN TRANSACTIONS — Full Reference

### Syntax

```cypher
CALL (row) {
  // write logic
} IN [n CONCURRENT] TRANSACTIONS
  [OF batchSize ROW[S]]
  [ON ERROR {CONTINUE | BREAK | FAIL | RETRY [FOR duration SECONDS] [THEN {CONTINUE|BREAK|FAIL}]}]
  [REPORT STATUS AS statusVar]
```

### ON ERROR modes

| Mode | Behavior | Use when |
|---|---|---|
| `ON ERROR FAIL` | Default. Rolls back entire outer tx on first error | All-or-nothing strict import |
| `ON ERROR CONTINUE` | Skips failed batch, continues remaining batches | Resilient bulk load — track errors via REPORT STATUS |
| `ON ERROR BREAK` | Stops after first failed batch; keeps completed work | Semi-strict: stop early, keep successful batches |
| `ON ERROR RETRY` | Exponential backoff retry (default 30s) + fallback | Concurrent writes with deadlock risk |

`ON ERROR CONTINUE/BREAK` → outer transaction **succeeds** even if inner batches fail.
`ON ERROR FAIL` → cannot be combined with `REPORT STATUS AS`.

### CONCURRENT TRANSACTIONS (parallel batches)

```cypher
CYPHER 25
LOAD CSV WITH HEADERS FROM 'file:///large.csv' AS row
CALL (row) {
  MERGE (p:Person {id: row.id}) SET p.name = row.name
} IN 4 CONCURRENT TRANSACTIONS OF 5000 ROWS
  ON ERROR RETRY FOR 30 SECONDS THEN CONTINUE
  REPORT STATUS AS s
```

Use CONCURRENT for read-heavy MERGE on non-overlapping key spaces. Risk: deadlocks on overlapping writes → combine with `ON ERROR RETRY`.

### REPORT STATUS columns

| Column | Type | Meaning |
|---|---|---|
| `s.started` | BOOLEAN | Batch transaction started |
| `s.committed` | BOOLEAN | Batch committed successfully |
| `s.transactionId` | STRING | Transaction ID |
| `s.errorMessage` | STRING or null | Error detail if batch failed |

### Batch size guidance

| Row count | Recommended batch size | Notes |
|---|---|---|
| < 100k | 10 000 | Default is fine |
| 100k – 1M | 10 000 – 50 000 | Monitor heap; increase if fast |
| 1M – 10M | 50 000 – 100 000 | Enable CONCURRENT if CPUs available |
| > 10M online | 50 000 | Consider neo4j-admin import instead |
| Relationship import | 5 000 | Lower — each batch does 2x MATCH |

---

## neo4j-admin import (Offline Bulk Load)

Fastest method: ~3 min for 31M nodes / 78M rels on SSD. DB must be stopped or non-existent.

### Command structure

```bash
neo4j-admin database import full \
  --nodes=Person="persons_header.csv,persons.csv" \
  --nodes=Movie="movies_header.csv,movies.csv" \
  --relationships=ACTED_IN="acted_in_header.csv,acted_in.csv" \
  --relationships=DIRECTED="directed_header.csv,directed.csv" \
  --delimiter=, \
  --id-type=STRING \
  --bad-tolerance=0 \
  --threads=$(nproc) \
  --high-parallel-io=on \
  neo4j
```

For SSDs: always set `--high-parallel-io=on`. For large graphs (>34B nodes/rels): `--format=block`.

**Dry run** (2026.02+) — validate without writing:
```bash
neo4j-admin database import full --dry-run ...
```

### Node header file format

```
# persons_header.csv
personId:ID,name,born:int,score:float,active:boolean,:LABEL
```

```
# persons.csv (data file — no header row)
p001,Alice,1985,9.2,true,Person
p002,Bob,1990,7.1,false,Person
```

| Field | Meaning |
|---|---|
| `:ID` | Unique ID for relationship wiring (not stored as property by default) |
| `:ID(Group)` | Scoped ID space — use when node types share IDs |
| `:LABEL` | One or more labels; semicolon-separated: `Person;Employee` |
| `prop:int` | Typed property; types: `int long float double boolean byte short string` |
| `prop:date` | Temporal: `date localtime time localdatetime datetime duration` |
| `prop:int[]` | Array — semicolon-separated values in cell: `1;2;3` |
| `prop:vector` | Float vector (2025.10+) — semicolon-separated coordinates |

### Relationship header file format

```
# acted_in_header.csv
:START_ID(Person),:END_ID(Movie),role,:TYPE
```

```
# acted_in.csv
p001,tt0133093,Neo,ACTED_IN
p002,tt0133093,Morpheus,ACTED_IN
```

`:START_ID` / `:END_ID` must reference the same `:ID` group as the node files.

### Key flags

| Flag | Default | Notes |
|---|---|---|
| `--delimiter` | `,` | Single char or `TAB` |
| `--id-type` | `STRING` | `STRING \| INTEGER \| ACTUAL` |
| `--bad-tolerance` | `-1` (unlimited, changed 2025.12) | Set `0` for strict prod imports |
| `--threads` | CPU count | Set explicitly on shared hosts |
| `--max-off-heap-memory` | 90% RAM | Reduce if other services share host |
| `--high-parallel-io` | `off` | Set `on` for SSD/NVMe |
| `--format` | `standard` | `block` for >34B nodes/rels |
| `--overwrite-destination` | false | Required if DB already exists |
| `--dry-run` | false | 2026.02+ — validate without writing |

### Schema file (--schema) [Enterprise, block format]

Pass a Cypher file with `CREATE CONSTRAINT` / `CREATE INDEX` statements; executed automatically after import completes. Constraints are created first (correct order enforced). File paths can be local or remote (`s3://`, `gs://`, `https://`).

```bash
neo4j-admin database import full \
  --format=block \
  --schema=schema.cypher \
  --nodes=Person="persons_header.csv,persons.csv" \
  neo4j
```

```cypher
// schema.cypher
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (n:Person) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT movie_id  IF NOT EXISTS FOR (n:Movie)  REQUIRE n.id IS UNIQUE;
CREATE RANGE INDEX person_email IF NOT EXISTS FOR (n:Person) ON (n.email);
CREATE TEXT  INDEX movie_title  IF NOT EXISTS FOR (n:Movie)  ON (n.title);
```

For incremental import, `DROP CONSTRAINT` / `DROP INDEX` are also supported [2025.02+] — used to remove indexes before the merge phase and recreate them after for faster writes.

---

### Incremental import (Enterprise only)

Three-phase process — use when DB must stay online during import preparation:

```bash
# Phase 1: Prepare staging area
neo4j-admin database import incremental --stage=prepare \
  --nodes=Person=persons_header.csv,delta.csv --force neo4j

# Phase 2: Build indexes (DB can be read-only during this phase)
neo4j-admin database import incremental --stage=build neo4j

# Phase 3: Merge into live database (brief write-lock)
neo4j-admin database import incremental --stage=merge neo4j
```

Requires Enterprise Edition + `block` store format.

---

## APOC Patterns (when APOC is available)

Verify first: `RETURN apoc.version()` — if fails, use LOAD CSV or driver instead.

### apoc.periodic.iterate — batch-process existing graph data

```cypher
CALL apoc.periodic.iterate(
  "MATCH (p:Person) WHERE NOT (p)-[:HAS_ACCOUNT]->() RETURN p",
  "CREATE (p)-[:HAS_ACCOUNT]->(a:Account {id: randomUUID()})",
  {batchSize: 10000, parallel: false, retries: 2}
) YIELD batches, total, errorMessages
RETURN batches, total, errorMessages
```

| Config key | Default | Notes |
|---|---|---|
| `batchSize` | 10000 | Rows per inner transaction |
| `parallel` | false | Enable for non-overlapping writes; risk: deadlocks |
| `retries` | 0 | Retry failed batches N times with 100ms delay |

Prefer `CALL IN TRANSACTIONS` (native Cypher) over `apoc.periodic.iterate` for new code — it has `REPORT STATUS`, `CONCURRENT`, and `RETRY` built in without APOC dependency.

### apoc.load.csv — load with config options

```cypher
CALL apoc.load.csv('file:///persons.csv', {
  header: true,
  sep: ',',
  skip: 1,
  limit: 1000000
}) YIELD lineNo, map, list
CALL (map) {
  MERGE (p:Person {id: map.id}) SET p.name = map.name
} IN TRANSACTIONS OF 10000 ROWS ON ERROR CONTINUE
```

### apoc.load.json — load JSON from file or URL

```cypher
CALL apoc.load.json('https://api.example.com/persons') YIELD value
CALL (value) {
  MERGE (p:Person {id: value.id}) SET p.name = value.name
} IN TRANSACTIONS OF 1000 ROWS ON ERROR CONTINUE
```

---

## Driver Batch Write Pattern

Use when source is not a file (API responses, DB migrations). Collect into `BATCH_SIZE` (10 000) lists, call `UNWIND $rows AS row MERGE ...` per batch. ~10x faster than row-at-a-time. → [Python + JS examples](references/driver-batch-write.md)

---

## MCP Tool Usage

| Operation | MCP tool | Notes |
|---|---|---|
| `SHOW CONSTRAINTS`, `SHOW INDEXES` | `read-cypher` | Always inspect before import |
| `CREATE CONSTRAINT`, `CREATE INDEX` | `write-cypher` | Gate: show planned constraint, confirm |
| LOAD CSV / CALL IN TRANSACTIONS | `write-cypher` | Gate: show row count + Cypher, confirm |
| Verify counts | `read-cypher` | Post-import: `MATCH (n:Label) RETURN count(n)` |
| Poll index state | `read-cypher` | Poll until all `state = 'ONLINE'` |

Write gate — before any bulk write via MCP, show:
1. Query + affected labels
2. Estimated row count from source
3. `EXPLAIN` plan

Wait for user confirmation. Never auto-execute `CALL IN TRANSACTIONS` or `CREATE CONSTRAINT` without confirmation.

Always pass `database` param if not default: `{"code": "...", "database": "neo4j"}`.

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Couldn't load the external resource` | `file:///` path not in Neo4j import dir | Move file to `$NEO4J_HOME/import/`; check `dbms.security.allow_csv_import_from_file_urls=true` |
| `Cannot merge node using null property value` | MERGE key resolved to null | Validate `row.id IS NOT NULL` before MERGE; add `WHERE row.id IS NOT NULL` |
| `toInteger() called on null` | Null column fed to non-null-safe fn | Replace `toInteger()` → `toIntegerOrNull()`, `toFloat()` → `toFloatOrNull()` |
| `Node N already exists` / constraint violation mid-import | Duplicate source IDs | Dedup source CSV; use `MERGE` not `CREATE`; add `IF NOT EXISTS` to constraint |
| Heap overflow / OutOfMemoryError | Batch too large or file too large | Reduce batch size; switch to `CALL IN TRANSACTIONS`; neo4j-admin for offline |
| `Invalid input 'IN': expected...'` | `PERIODIC COMMIT` used | Replace `USING PERIODIC COMMIT` → `CALL IN TRANSACTIONS` — PERIODIC COMMIT removed in Cypher 25 |
| neo4j-admin: `Bad input data` | Wrong header format or type mismatch | Check `:ID`, `:START_ID`, `:END_ID` present; check typed columns parse correctly |
| neo4j-admin: import fails silently | `--bad-tolerance` default was unlimited pre-2025.12 | Set `--bad-tolerance=0` to surface all errors |
| Index not used during MERGE | Constraint not created before import | Drop data, create constraint, re-import |
| Relationship import missing nodes | Relationships imported before nodes | Always import ALL node files before ANY relationship files |

---

## Post-Import Validation

After import completes — run all:

```cypher
// Row counts per label
MATCH (n:Person) RETURN count(n) AS persons;
MATCH ()-[:KNOWS]->() RETURN count(*) AS knows_rels;

// After import: create additional non-unique indexes (populated async)
CREATE TEXT INDEX movie_title IF NOT EXISTS FOR (n:Movie) ON (n.title);
CREATE RANGE INDEX person_born IF NOT EXISTS FOR (n:Person) ON (n.born);

// Poll population — wait until populationPercent = 100 before opening to queries
SHOW INDEXES YIELD name, state, populationPercent
WHERE state <> 'ONLINE' OR populationPercent < 100
RETURN name, state, populationPercent
ORDER BY populationPercent;

// Spot check: null keys = import bug
MATCH (p:Person) WHERE p.id IS NULL RETURN count(p) AS missing_id;
```

Do NOT run production queries until all indexes are ONLINE.

---

## References

- [LOAD CSV — Cypher Manual 25](https://neo4j.com/docs/cypher-manual/25/clauses/load-csv/)
- [CALL IN TRANSACTIONS — Cypher Manual](https://neo4j.com/docs/cypher-manual/current/subqueries/subqueries-in-transactions/)
- [neo4j-admin database import](https://neo4j.com/docs/operations-manual/current/tools/neo4j-admin/neo4j-admin-import/)
- [APOC periodic execution](https://neo4j.com/docs/apoc/current/graph-updates/periodic-execution/)
- [APOC load procedures](https://neo4j.com/docs/apoc/current/import/)
- [GraphAcademy: Importing CSV Data](https://graphacademy.neo4j.com/courses/importing-cypher/)
- [Indexes and constraints — types, MERGE lock semantics, import pre-flight](../neo4j-cypher-skill/references/indexes.md)
- [Data Importer GUI — when to use, Aura access, multi-pass, gotchas](references/data-importer-gui.md)
- [Post-import refactoring — split lists, extract nodes, add labels, FK validation](references/post-import-refactoring.md)

---

## Checklist

- [ ] Uniqueness constraints created before any MERGE-based import
- [ ] APOC availability verified if using `apoc.*` procedures
- [ ] Target confirmed as PRIMARY (not replica)
- [ ] Source files validated: UTF-8 encoding, expected row count, no BOM
- [ ] LOAD CSV uses `toIntegerOrNull()` / `toFloatOrNull()` — never bare `toInteger()`/`toFloat()`
- [ ] `nullIf(row.x, '')` applied where empty string ≠ null
- [ ] `CALL IN TRANSACTIONS` used (not `USING PERIODIC COMMIT`)
- [ ] `ON ERROR CONTINUE` + `REPORT STATUS` for production loads
- [ ] Node import completed before relationship import
- [ ] neo4j-admin: `--bad-tolerance=0` set; `--high-parallel-io=on` for SSD
- [ ] Post-import: row counts match source; all indexes ONLINE
- [ ] Write execution gate applied (MCP): showed query + estimate, got confirmation
- [ ] Credentials in `.env`; `.env` in `.gitignore`
