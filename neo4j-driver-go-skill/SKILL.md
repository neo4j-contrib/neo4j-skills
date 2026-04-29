---
name: neo4j-driver-go-skill
description: Covers the Neo4j Go Driver v6 — driver lifecycle, ExecuteQuery, managed and
  explicit transactions, session config, error handling, data type mapping, and connection
  tuning. Use when writing Go code that connects to Neo4j, setting up NewDriver or ExecuteQuery,
  debugging sessions/transactions/result handling, or working with neo4j-go-driver v5→v6 migration.
  Triggers on NewDriver, ExecuteQuery, SessionConfig, ManagedTransaction, neo4j-go-driver.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT cover driver version migration steps — use neo4j-migration-skill.
version: 1.0.0
allowed-tools: Bash WebFetch
---

## When to Use
- Writing Go code that connects to Neo4j
- Setting up `neo4j.NewDriver()`, `ExecuteQuery()`, or session/transaction patterns
- Debugging connection errors, result iteration, type assertions, causal consistency

## When NOT to Use
- **Writing/optimizing Cypher** → `neo4j-cypher-skill`
- **v5→v6 migration steps** → `neo4j-migration-skill`

---

## Installation

```bash
go get github.com/neo4j/neo4j-go-driver/v6
```

Import: `github.com/neo4j/neo4j-go-driver/v6/neo4j`

**v5→v6 rename** (deprecated aliases still compile, remove before v7):

| v5 | v6 |
|----|----|
| `neo4j.NewDriverWithContext(...)` | `neo4j.NewDriver(...)` |
| `neo4j.DriverWithContext` | `neo4j.Driver` |

---

## Environment Variables

```go
import "os"

uri      := getEnv("NEO4J_URI",      "neo4j://localhost:7687")
user     := getEnv("NEO4J_USERNAME", "neo4j")
password := getEnv("NEO4J_PASSWORD", "")
database := getEnv("NEO4J_DATABASE", "neo4j")

func getEnv(key, fallback string) string {
    if v := os.Getenv(key); v != "" { return v }
    return fallback
}
```

Use [godotenv](https://github.com/joho/godotenv) to load `.env` in dev: `godotenv.Load()`. `.env` in `.gitignore`.

---

## Driver Lifecycle

One `Driver` per application. Goroutine-safe, connection-pooled, expensive to create.

```go
func NewNeo4jDriver(uri, user, password string) (neo4j.Driver, error) {
    driver, err := neo4j.NewDriver(
        uri, // "neo4j+s://xxx.databases.neo4j.io" for Aura
        neo4j.BasicAuth(user, password, ""),
    )
    if err != nil {
        return nil, fmt.Errorf("create driver: %w", err)
    }
    ctx := context.Background()
    if err := driver.VerifyConnectivity(ctx); err != nil {
        driver.Close(ctx)
        return nil, fmt.Errorf("verify connectivity: %w", err)
    }
    return driver, nil
}

// In main / app teardown:
defer driver.Close(ctx)
```

❌ Never create driver per-request. Create once at startup; share across goroutines.

URI schemes: `neo4j+s://` (Aura/TLS+routing), `neo4j://` (plain+routing), `bolt+s://` (TLS+single), `bolt://` (plain+single).

---

## Choosing the Right API

| API | Use when | Auto-retry | Lazy results |
|-----|----------|:----------:|:------------:|
| `neo4j.ExecuteQuery()` | Most queries — simple default | ✅ | ❌ eager |
| `session.ExecuteRead/Write()` | Large result sets / streaming | ✅ | ✅ |
| `session.BeginTransaction()` | Spans multiple functions / ext coordination | ❌ | ✅ |
| `session.Run()` | `CALL IN TRANSACTIONS` / auto-commit only | ❌ | ✅ |

`CALL { … } IN TRANSACTIONS` and `USING PERIODIC COMMIT` manage their own transactions — use `session.Run()`. They fail inside managed transactions.

---

## ExecuteQuery (Recommended Default)

Manages sessions, transactions, retries, and bookmarks automatically.

```go
result, err := neo4j.ExecuteQuery(ctx, driver,
    `MATCH (p:Person {name: $name})-[:KNOWS]->(friend)
     RETURN friend.name AS name`,
    map[string]any{"name": "Alice"},
    neo4j.EagerResultTransformer,
    neo4j.ExecuteQueryWithDatabase("neo4j"),       // always specify
    neo4j.ExecuteQueryWithReadersRouting(),         // for read queries
)
if err != nil {
    return fmt.Errorf("query people: %w", err)
}

for _, record := range result.Records {
    name, _ := record.Get("name")
    fmt.Println(name)
}
fmt.Println(result.Summary.Counters().NodesCreated())
```

Key options:
```go
neo4j.ExecuteQueryWithDatabase("mydb")          // required for performance
neo4j.ExecuteQueryWithReadersRouting()           // route reads to replicas
neo4j.ExecuteQueryWithImpersonatedUser("jane")  // impersonate
neo4j.ExecuteQueryWithoutBookmarkManager()       // opt out of causal consistency
```

❌ Never concatenate user input into query strings. Always use `map[string]any` parameters.

---

## Managed Transactions (Session-Based)

Use for lazy streaming (large result sets) or callback-level control.

```go
session := driver.NewSession(ctx, neo4j.SessionConfig{
    DatabaseName: "neo4j", // always specify
    AccessMode:   neo4j.AccessModeRead,
})
defer session.Close(ctx)

result, err := session.ExecuteRead(ctx,
    func(tx neo4j.ManagedTransaction) (any, error) {
        res, err := tx.Run(ctx,
            `MATCH (p:Person) RETURN p.name AS name LIMIT $limit`,
            map[string]any{"limit": 100},
        )
        if err != nil {
            return nil, err
        }
        var names []string
        for res.Next(ctx) { // lazy — don't Collect() on large sets
            name, _ := res.Record().Get("name")
            names = append(names, name.(string))
        }
        return names, res.Err()
    },
)
```

❌ No side effects in callback — retried on transient failures.
`ExecuteRead` → replicas. `ExecuteWrite` → cluster leader.

---

## Explicit Transactions

Use when transaction work spans multiple functions or requires external coordination.

```go
session := driver.NewSession(ctx, neo4j.SessionConfig{DatabaseName: "neo4j"})
defer session.Close(ctx)

tx, err := session.BeginTransaction(ctx)
if err != nil {
    return err
}
if err := doPartA(ctx, tx); err != nil {
    tx.Rollback(ctx)
    return err
}
if err := doPartB(ctx, tx); err != nil {
    tx.Rollback(ctx)
    return err
}
return tx.Commit(ctx)
```

❌ Not auto-retried. Caller handles retry. Prefer managed transactions unless you need explicit control.

---

## Error Handling

```go
result, err := neo4j.ExecuteQuery(...)
if err != nil {
    var neo4jErr *neo4j.Neo4jError
    if errors.As(err, &neo4jErr) {
        slog.Error("database error", "code", neo4jErr.Code, "msg", neo4jErr.Msg)
    }
    var connErr *neo4j.ConnectivityError
    if errors.As(err, &connErr) {
        slog.Error("connectivity error", "err", connErr)
    }
    return fmt.Errorf("execute query: %w", err)
}
```

Helpers:
```go
neo4j.IsNeo4jError(err)                // server-side Cypher/database error
neo4j.IsTransactionExecutionLimit(err) // managed tx retries exhausted
```

In managed tx callback: return error → driver retries if transient.
`ConnectivityError` at startup: check URI scheme, credentials, firewall.

---

## Data Types

| Cypher | Go |
|--------|----|
| `Integer` | `int64` |
| `Float` | `float64` |
| `String` | `string` |
| `Boolean` | `bool` |
| `List` | `[]any` |
| `Map` | `map[string]any` |
| `Node` | `neo4j.Node` |
| `Relationship` | `neo4j.Relationship` |
| `Path` | `neo4j.Path` |
| `Date` | `neo4j.Date` |
| `DateTime` | `neo4j.Time` |
| `Duration` | `neo4j.Duration` |
| `null` | `nil` |

```go
// Typed extraction (v6+, preferred):
neo4j.GetRecordValue[string](record, "name")

// Manual extraction:
rawAge, ok := record.Get("age")
if !ok { return errors.New("missing 'age' field") }
age := rawAge.(int64) // Neo4j integers → int64

// Node access:
rawNode, _ := record.Get("p")
node := rawNode.(neo4j.Node)
name := node.Props["name"].(string)
labels := node.Labels // []string
```

❌ Always check `ok` from `record.Get()` before type-asserting — panics on missing key.
❌ After lazy `for res.Next(ctx)` loop, always check `res.Err()`.

---

## Key Patterns

### Context — always propagate

```go
ctx, cancel := context.WithTimeout(parentCtx, 5*time.Second)
defer cancel()
// pass ctx to all driver calls
```

`context.Background()` has no deadline — slow queries block indefinitely.

### Batching Writes

```go
// Bad: one transaction per record
for _, item := range items {
    neo4j.ExecuteQuery(ctx, driver, writeQuery, item, ...)
}

// Good: UNWIND batch in one transaction
neo4j.ExecuteQuery(ctx, driver,
    `UNWIND $items AS item
     MERGE (n:Node {id: item.id})
     SET n += item`,
    map[string]any{"items": items},
    neo4j.EagerResultTransformer,
    neo4j.ExecuteQueryWithDatabase("neo4j"),
)
```

### Generic Helpers (v6+)

Prefer type-safe helpers over manual assertions:

```go
// GetRecordValue[T] — extract + cast in one call
name, isNil, err := neo4j.GetRecordValue[string](record, "name")
// isNil=true when OPTIONAL MATCH returned null; err != nil when key absent or wrong type

// CollectTWithContext — map all records to a slice
people, err := neo4j.CollectTWithContext(ctx, result, func(record *neo4j.Record) (Person, error) {
    name, _, err := neo4j.GetRecordValue[string](record, "name")
    age, _, _   := neo4j.GetRecordValue[int64](record, "age")
    return Person{Name: name, Age: int(age)}, err
})

// SingleTWithContext — expect exactly one record (error if 0 or 2+)
person, err := neo4j.SingleTWithContext(ctx, result, func(record *neo4j.Record) (Person, error) {
    name, _, _ := neo4j.GetRecordValue[string](record, "name")
    return Person{Name: name}, nil
})

// GetProperty — typed property from Node or Relationship
node, _, _ := neo4j.GetRecordValue[neo4j.Node](record, "p")
nameVal, err := neo4j.GetProperty[string](node, "name")
```

### Spatial Types

```go
// 2D Cartesian (SRID 7203), 3D Cartesian (SRID 9157)
pt2d := neo4j.Point2D{X: 1.23, Y: 4.56, SpatialRefId: 7203}
pt3d := neo4j.Point3D{X: 1.23, Y: 4.56, Z: 7.89, SpatialRefId: 9157}

// 2D WGS-84 (SRID 4326), 3D WGS-84 (SRID 4979)
london := neo4j.Point2D{X: -0.118092, Y: 51.509865, SpatialRefId: 4326}
shard  := neo4j.Point3D{X: -0.0865, Y: 51.5045, Z: 310, SpatialRefId: 4979}

// Pass as parameter
result, err := neo4j.ExecuteQuery(ctx, driver,
    "CREATE (p:Place {location: $loc})",
    map[string]any{"loc": london},
    neo4j.EagerResultTransformer,
    neo4j.ExecuteQueryWithDatabase("neo4j"),
)

// Read from result — assert to Point2D or Point3D
raw, _ := record.Get("location")
if p2d, ok := raw.(neo4j.Point2D); ok {
    fmt.Printf("lon=%f lat=%f srid=%d\n", p2d.X, p2d.Y, p2d.SpatialRefId)
}

// Distance (same SRID only)
result, _ = neo4j.ExecuteQuery(ctx, driver,
    "RETURN point.distance($p1, $p2) AS distance",
    map[string]any{"p1": pt2d, "p2": neo4j.Point2D{X: 10, Y: 10, SpatialRefId: 7203}},
    neo4j.EagerResultTransformer, neo4j.ExecuteQueryWithDatabase("neo4j"),
)
dist, _ := result.Records[0].Get("distance")
fmt.Println(dist.(float64))
```

### Always Specify Database

```go
neo4j.ExecuteQueryWithDatabase("neo4j")    // in ExecuteQuery
neo4j.SessionConfig{DatabaseName: "neo4j"} // in sessions
```

Omitting costs a network round-trip per call to resolve home database.

### Causal Consistency

`ExecuteQuery` manages bookmarks automatically — no action needed for sequential calls.
Cross-session (parallel workers): combine bookmarks explicitly — see [references/repository-pattern.md](references/repository-pattern.md).

---

## Common Errors

| Error / Symptom | Cause | Fix |
|-----------------|-------|-----|
| `ConnectivityError` at startup | URI wrong / TLS mismatch / firewall | Check scheme (`neo4j+s://` for Aura), credentials, port 7687 |
| `ConnectivityError` mid-run | Pool exhausted | Increase `MaxConnectionPoolSize`; check for leaked sessions |
| Panic on type assertion | `record.Get()` returned nil/wrong type | Use `neo4j.GetRecordValue[T]()` or check `ok` first |
| `res.Err()` non-nil after loop | Network error mid-stream | Handle error; re-run transaction |
| Callback retried unexpectedly | Side effect inside managed tx | Move side effects outside callback |
| Context deadline exceeded | No timeout on context | Use `context.WithTimeout` |
| 0 results, query looks correct | Wrong `DatabaseName` | Always set `DatabaseName` in config |
| `CALL IN TRANSACTIONS` fails | Run inside managed tx | Use `session.Run()` (auto-commit) |

---

## References

Load on demand:
Load on demand:
- [references/advanced-config.md](references/advanced-config.md) — connection pool tuning, custom address resolver, notification config, Bolt logging, auth options, URI scheme table
- [references/repository-pattern.md](references/repository-pattern.md) — repository wrapper pattern, cross-session causal consistency with bookmarks

## WebFetch

| Need | URL |
|------|-----|
| Go driver manual | `https://neo4j.com/docs/go-manual/current/` |
| API reference | `https://pkg.go.dev/github.com/neo4j/neo4j-go-driver/v6/neo4j` |

---

## Checklist
- [ ] One driver created at startup; shared across goroutines; `defer driver.Close(ctx)`
- [ ] `driver.VerifyConnectivity(ctx)` called at startup
- [ ] `DatabaseName` set in all `SessionConfig` / `ExecuteQueryWithDatabase`
- [ ] `context.WithTimeout` used for production queries
- [ ] `map[string]any` parameters used — no string interpolation
- [ ] `ExecuteQueryWithReadersRouting()` on read-only `ExecuteQuery` calls
- [ ] `res.Err()` checked after lazy `for result.Next(ctx)` loop
- [ ] Type assertions guarded (use `GetRecordValue[T]` or check `ok`)
- [ ] No side effects inside managed transaction callbacks
- [ ] `session.Run()` used for `CALL IN TRANSACTIONS` / auto-commit queries
- [ ] Sessions closed with `defer session.Close(ctx)`
