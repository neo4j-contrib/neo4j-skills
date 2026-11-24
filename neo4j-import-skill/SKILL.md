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
version: 1.0.12
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
| Any size | Online | APOC available | `apoc.periodic.iterate` (+ `apoc.load.csv` — APOC Extended only) |
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
   > **Neo4j 2026.06+ (Enterprise/Aura, GA):** `ALTER CURRENT GRAPH TYPE SET { … }` replaces all individual constraint statements with a single declarative block. See `neo4j-cypher-skill/references/graph-type.md`. Use individual `CREATE CONSTRAINT` on Community Edition or pre-2026.02.

2. **Verify APOC if using apoc.* procedures**:
   ```cypher
   RETURN apoc.version();
   ```
   If fails → APOC not installed. Use plain LOAD CSV instead.

3. **Confirm target accepts writes** (not a secondary/replica):
   ```cypher
   SHOW DATABASE neo4j YIELD name, role, writer, currentStatus;
   ```
   `writer = true` on standalone servers and on the cluster's writer. If no row has `writer = true` → stop; redirect the write to the writer endpoint (`neo4j://` routing URI). Don't use `dbms.cluster.role()` — fails with "no such procedure" on 2026.x standalone.

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
RETURN s.committed, s.errorMessage
```

`REPORT STATUS` makes the `CALL` return rows → query must end with `RETURN` (or `FINISH`), else syntax error "incomplete query".

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
| `ON ERROR FAIL` | Default. Stops the query on first error; failed batch rolls back, **earlier batches stay committed** | Fail-fast import. Not all-or-nothing — for that use one batch (`OF <n> ROWS` above row count) or a single transaction |
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
RETURN s.committed, s.errorMessage
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
  --nodes=Person="./persons_header.csv,./persons.csv" \
  --nodes=Movie="./movies_header.csv,./movies.csv" \
  --relationships=ACTED_IN="./acted_in_header.csv,./acted_in.csv" \
  --relationships=DIRECTED="./directed_header.csv,./directed.csv" \
  --delimiter=, \
  --id-type=STRING \
  --bad-tolerance=0 \
  --threads=$(nproc) \
  --high-parallel-io=on \
  neo4j
```

File paths need a directory part (`./file.csv`, `import/file.csv` or absolute) — bare names fail: "Unable to find the parent of the path". Database name goes last, after a single-value flag (as above) — placed right after `--nodes=`/`--relationships=` it is parsed as one more file.

**Dry run** (2026.02+) — validate without writing:
```bash
neo4j-admin database import full --dry-run ...
```

### Node header file format

```
# persons_header.csv
personId:ID(Person),name,born:int,score:float,active:boolean,:LABEL
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
| `prop:date` | Temporal: `date localtime time localdatetime datetime duration`; Parquet `INTERVAL` columns import as `DURATION` [2026.07+] |
| `prop:int[]` | Array — semicolon-separated values in cell: `1;2;3` |
| `"prop:vector{coordinateType:float,dimensions:3}"` | Vector (2025.10+) — map must give `coordinateType` (`byte short int long float double`) and `dimensions` (1-4096); quote the header field (contains `,`). Coordinates semicolon-separated in CSV; imports directly from native Parquet list types [2026.06+]. Storing `VECTOR` needs `block` format (Enterprise); Community fails |

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
| `--delimiter` | `,` | Single-byte UTF-8 char, `TAB`, `\ID`, or `U+XXXX`; newline chars rejected [2026.07+] |
| `--vector-delimiter` | `;` | Separates `prop:vector` coordinates; must differ from `--delimiter` and `--quote` [enforced 2026.06+] |
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
  --nodes=Person="./persons_header.csv,./persons.csv" \
  --format=block \
  --schema=./schema.cypher \
  neo4j
```

Community rejects `--schema` ("Record format batch import does not support schema changes").

```cypher
// schema.cypher
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (n:Person) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT movie_id  IF NOT EXISTS FOR (n:Movie)  REQUIRE n.id IS UNIQUE;
CREATE RANGE INDEX person_email IF NOT EXISTS FOR (n:Person) ON (n.email);
CREATE TEXT  INDEX movie_title  IF NOT EXISTS FOR (n:Movie)  ON (n.title);
```

For incremental import, `DROP CONSTRAINT` / `DROP INDEX` are also supported [2025.02+] — used to remove indexes before the merge phase and recreate them after for faster writes. `--schema` also accepts graph-type DDL: `ALTER CURRENT GRAPH TYPE SET {…}` for `full` [2026.05+], `ALTER CURRENT GRAPH TYPE ADD/DROP/ALTER {…}` for `incremental` [2026.06+] — see `neo4j-cypher-skill/references/graph-type.md`.

---

### Incremental import (Enterprise only)

Three-stage process — limits downtime to `prepare` and `merge` (or `--stage=all` on a stopped DB):

```bash
# Back up first: a failed or aborted merge may corrupt the database

# Stage 1: prepare — DB stopped (STOP DATABASE neo4j WAIT)
neo4j-admin database import incremental --stage=prepare --force \
  --nodes=Person=./persons_header.csv,./delta.csv neo4j

# Stage 2: build — imports, deduplicates, validates; DB may be online in read-only mode
# (ALTER DATABASE neo4j SET ACCESS READ ONLY). Repeat --nodes/--relationships
neo4j-admin database import incremental --stage=build --force \
  --nodes=Person=./persons_header.csv,./delta.csv neo4j

# Stage 3: merge — DB stopped; updates indexes and constraints. No --nodes needed
neo4j-admin database import incremental --stage=merge --force neo4j
```

Enterprise only (Community has only `import full`). Uniqueness constraints must exist on the key label/property pairs of imported nodes, else the command errors. `block` format needed only for CSV update/delete actions.

---

## APOC Patterns (when APOC is available)

Read [references/apoc-patterns.md](references/apoc-patterns.md#apoc-patterns-when-apoc-is-available) when you need this.

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

MCP tools take only `{"query": "...", "params": {...}}` — no `database` argument. Database comes from server config: `NEO4J_MCP_DATABASE` (STDIO) or the `/db/{db}/mcp` URL path (HTTP).

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Couldn't load the external resource` | `file:///` path not in Neo4j import dir | Move file to `$NEO4J_HOME/import/`; check `dbms.security.allow_csv_import_from_file_urls=true` |
| `Cannot merge node using null property value` | MERGE key resolved to null | Validate `row.id IS NOT NULL` before MERGE; add `WHERE row.id IS NOT NULL` |
| `toInteger() called on null` | Null column fed to non-null-safe fn | Replace `toInteger()` → `toIntegerOrNull()`, `toFloat()` → `toFloatOrNull()` |
| `Node N already exists` / constraint violation mid-import | Duplicate source IDs | Dedup source CSV; use `MERGE` not `CREATE`; add `IF NOT EXISTS` to constraint |
| Heap overflow / OutOfMemoryError | Batch too large or file too large | Reduce batch size; switch to `CALL IN TRANSACTIONS`; neo4j-admin for offline |
| `TransactionStartFailed … can only be executed in an implicit transaction` | `CALL { … } IN TRANSACTIONS` run inside `session.execute_write` / explicit tx | Run it with `session.run` (auto-commit). `driver.execute_query` uses a managed transaction and fails the same way. Inside `execute_write`, use `UNWIND` batches instead |
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
- [ ] Target confirmed writable (`SHOW DATABASE … YIELD writer` = true)
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
