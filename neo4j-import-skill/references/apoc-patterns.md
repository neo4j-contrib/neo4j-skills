# APOC Patterns

Moved from SKILL.md to keep it under the 500-line budget.

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

`apoc.load.csv` is **APOC Extended**, not APOC core ("no such procedure" on core-only installs). Prefer `LOAD CSV`. File URLs for `apoc.load.*` need `apoc.import.file.enabled=true` in `apoc.conf` (off by default).

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
