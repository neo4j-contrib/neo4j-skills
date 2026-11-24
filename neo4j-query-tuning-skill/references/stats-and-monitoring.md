# Stats and Monitoring — Reference

## Long-Running Queries (via SHOW TRANSACTIONS)

`SHOW QUERIES` and `TERMINATE QUERY` do not exist (syntax error). Running queries appear as the `currentQuery*` columns of `SHOW TRANSACTIONS` (needs `SHOW TRANSACTION` privilege for other users' transactions).

```cypher
SHOW TRANSACTIONS
YIELD transactionId, database, username, currentQuery, currentQueryElapsedTime,
      currentQueryAllocatedBytes, currentQueryStatus, activeLockCount,
      currentQueryPageHits, currentQueryPageFaults
WHERE currentQueryElapsedTime > duration('PT5S')
RETURN transactionId, username, currentQueryElapsedTime, currentQueryAllocatedBytes, currentQuery
ORDER BY currentQueryElapsedTime DESC
```

Key fields:
- `transactionId` — use with `TERMINATE TRANSACTION`
- `currentQueryElapsedTime` — wall time since the current query started (`DURATION`)
- `currentQueryAllocatedBytes` — heap allocated; high = memory pressure
- `currentQueryStatus` — `parsing`, `planning`, `planned`, `running`, `waiting`
- `activeLockCount` — >0 means write transaction holding locks
- `currentQueryPageHits` / `currentQueryPageFaults` — cache hit/miss counts for this query

Kill a running query → terminate its transaction:
```cypher
TERMINATE TRANSACTION "neo4j-transaction-123"
YIELD transactionId, username, message
```

---

## SHOW TRANSACTIONS

Lists all currently open transactions.

```cypher
SHOW TRANSACTIONS
YIELD transactionId, database, username, currentQuery, elapsedTime,
      status, cpuTime, waitTime, idleTime, activeLockCount,
      pageHits, pageFaults, currentQueryId
WHERE status <> 'Terminated'
RETURN transactionId, username, status, elapsedTime, activeLockCount, currentQuery
ORDER BY elapsedTime DESC
```

Key fields:
- `transactionId` — use with `TERMINATE TRANSACTION`
- `status` — `Running`, `Blocked`, `Closing`, `Terminated`
- `activeLockCount` — transactions blocking others will have high counts
- `currentQuery` — the Cypher string currently executing (or last executed)
- `elapsedTime` — duration since transaction opened

Terminate a transaction:
```cypher
TERMINATE TRANSACTION "neo4j-transaction-123"
YIELD transactionId, username, message
```

Terminate multiple:
```cypher
TERMINATE TRANSACTIONS "tx-1", "tx-2"
YIELD transactionId, message
```

---

## Database Statistics

### Graph Counts
Node/relationship counts by label and type — the data the planner uses for cardinality estimation.

```cypher
CALL db.stats.retrieve('GRAPH COUNTS')
YIELD section, data
RETURN section, data
```

`data` map keys: `nodes`, `relationships`, `indexes`, `constraints`.
- `data.nodes` — list: `[{count: 15200}, {count: 5000, label: 'Person'}, …]` (entry without `label` = total)
- `data.relationships` — list of `{count, relationshipType, startLabel, endLabel}` entries (selectivity data)
- No `nodesByLabel` / `relsByType*` keys

### Token Stats
```cypher
CALL db.stats.retrieve('TOKENS')
YIELD section, data
RETURN section, data
```

Returns internal token ID mappings for labels, property keys, and relationship types.

### Retrieve All Stats
```cypher
CALL db.stats.retrieveAllAnonymized('GRAPH COUNTS')
YIELD section, data
RETURN section, data
```
Anonymized version for sharing without exposing property names.

---

## Statistics and Replanning

### Config
`dbms.cypher.statistics_divergence_threshold` (default: `0.75`)

Formula: `abs(a - b) / max(a, b)`. At 0.75, plan invalidated when statistics change by 75% (~4× growth/shrink). Lower to replan more aggressively on growing databases.

### Force Replanning
```cypher
// Recalculate all statistics immediately (blocks until complete):
CALL db.prepareForReplanning()

// Resample a specific index asynchronously:
CALL db.resampleIndex("index-name")

// Resample all outdated indexes asynchronously:
CALL db.resampleOutdatedIndexes()
```

Force replanning of a single query without changing stats:
```cypher
CYPHER replan=force
MATCH (p:Person {email: $email}) RETURN p.name
```

Skip replanning (use cached plan even if stale — useful during high-load bursts):
```cypher
CYPHER replan=skip
MATCH (p:Person {email: $email}) RETURN p.name
```

---

## Index Health Check

```cypher
// Indexes not yet ONLINE (still populating or failed):
SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state
WHERE state <> 'ONLINE'
RETURN name, type, labelsOrTypes, properties, state

// All online indexes:
SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state, populationPercent
WHERE state = 'ONLINE'
RETURN name, type, labelsOrTypes, properties
ORDER BY type, labelsOrTypes
```

Index types and supported predicates:
| Type | `=` | `<>` | `<` `>` | `IN` | `STARTS WITH` | `CONTAINS` | `ENDS WITH` | `POINT` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| RANGE | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| TEXT | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ |
| POINT | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| FULLTEXT | — | — | — | — | — | ✗ | — | — |
| LOOKUP | node/rel by ID | — | — | — | — | — | — | — |

FULLTEXT is never used for `WHERE … CONTAINS` (plans as `NodeByLabelScan` + `Filter`) — query it with `SEARCH … FULLTEXT INDEX` [2026.09] or `db.index.fulltext.queryNodes`.

---

## Query Log (server-side)

Enterprise Edition only (Community query log stays empty). On self-managed Enterprise, queries log to `query.log`:

Config options (`neo4j.conf`):
```
db.logs.query.enabled=INFO          # OFF | INFO (only queries over threshold, at end) | VERBOSE (all queries, start + end; default)
db.logs.query.threshold=2s          # INFO logs queries taking longer than this
db.logs.query.parameter_logging_enabled=true
```

Each log entry includes: `{elapsedMs} ms: {query}` with optional params, allocated bytes, page hits/misses.

Format set in `server-logs.xml`: PLAIN default today; new installs default to JSON after 2026 LTS (upgrades keeping existing `server-logs.xml` stay PLAIN). Parse JSON field names, not PLAIN line layout, in new tooling.

`LIMIT`/`SKIP` integer literals and `LOAD CSV ... FIELDTERMINATOR` strings appear unobfuscated [2026.08]; earlier releases masked them as sensitive literals.

---

## Page Cache Sizing

Small page cache → high `pageFaults` → disk I/O → slow queries.

Measure with `PROFILE` (page cache hits/misses per operator) or `SHOW TRANSACTIONS` (`dbms.queryJmx` has no Neo4j page cache bean — returns zero rows):
```cypher
SHOW TRANSACTIONS
YIELD transactionId, pageHits, pageFaults, currentQuery
RETURN transactionId, pageHits, pageFaults, currentQuery
```

From SHOW TRANSACTIONS:
- `pageHits` high, `pageFaults` low → cache is sufficient
- `pageFaults` > 1% of pageHits → increase `server.memory.pagecache.size` in `neo4j.conf`

Set page cache to hold the entire graph store (`graph.db/` directory size).

[2026.09] Page cache reserves its full configured size at startup and never exceeds `server.memory.pagecache.size` — heap + page cache + OS headroom must fit host RAM from startup, not just under load [derived].
