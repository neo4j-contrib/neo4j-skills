---
name: neo4j-driver-go-skill
description: >
  Comprehensive guide to using the official Neo4j Go Driver (v6, current stable) — covering
  installation, driver lifecycle, all three transaction APIs (ExecuteQuery, managed transactions,
  explicit transactions), error handling, data type mapping, performance tuning, causal
  consistency, and connection configuration. Use this skill whenever writing Go code that talks
  to Neo4j, whenever reviewing or debugging Neo4j driver usage in Go, or whenever questions
  arise about sessions, transactions, bookmarks, result handling, or driver configuration.
  Also triggers on neo4j-go-driver, NewDriver, ExecuteQuery, SessionConfig, ManagedTransaction,
  or any Neo4j Bolt/Aura connection work in Go.

  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.

status: draft
version: 0.1.1
allowed-tools: Bash, WebFetch
---

 
# Neo4j Go Driver
 
**Import path**: `github.com/neo4j/neo4j-go-driver/v6/neo4j`  
**Current stable**: v6  
**Docs**: https://neo4j.com/docs/go-manual/current/  
**API ref**: https://pkg.go.dev/github.com/neo4j/neo4j-go-driver/v6/neo4j
 
## Installation
 
```bash
go get github.com/neo4j/neo4j-go-driver/v6
```
 
### Migrating from v5?
 
In v6 the `WithContext` suffix was dropped — the whole API is now context-aware by default:
 
| v5 | v6 |
|----|----|
| `neo4j.NewDriverWithContext(...)` | `neo4j.NewDriver(...)` |
| `neo4j.DriverWithContext` | `neo4j.Driver` |
 
The old names still exist as **deprecated aliases** (removed in v7), so v5 code compiles unchanged — but new code should use the v6 names.
 
---
 
## 1. Driver Lifecycle
 
`Driver` is **immutable, goroutine-safe, and expensive to create** — create exactly one instance per application and share it everywhere.
 
```go
import (
    "context"
    "github.com/neo4j/neo4j-go-driver/v6/neo4j"
)
 
func NewNeo4jDriver(uri, user, password string) (neo4j.Driver, error) {
    driver, err := neo4j.NewDriver(
        uri, // e.g. "neo4j+s://xxx.databases.neo4j.io" for Aura
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
 
### URI Schemes
 
| Scheme | When to use |
|--------|-------------|
| `neo4j://` | Unencrypted, cluster-routing |
| `neo4j+s://` | Encrypted (TLS), cluster-routing — **use for Aura** |
| `bolt://` | Unencrypted, single instance |
| `bolt+s://` | Encrypted, single instance |
 
### Auth Options
 
```go
neo4j.BasicAuth(user, password, "")           // username + password
neo4j.BearerAuth(token)                        // SSO / JWT
neo4j.KerberosAuth(base64EncodedTicket)        // Kerberos
neo4j.NoAuth()                                 // unauthenticated (dev only)
```
 
---
 
## 2. Choosing the Right API
 
The driver offers three levels of transaction control. Pick the lowest complexity that meets your needs:
 
| API | When to use | Auto-retry? | Lazy results? |
|-----|-------------|-------------|---------------|
| `ExecuteQuery()` | Most queries — simple, safe default | ✅ | ❌ (eager) |
| `session.ExecuteRead/Write()` | Need lazy streaming, or complex callback logic | ✅ | ✅ |
| `session.BeginTransaction()` | Spanning multiple functions, external API coordination | ❌ | ✅ |
 
---
 
## 3. ExecuteQuery (Recommended Default)
 
The simplest, highest-level API. Manages sessions, transactions, retries, and bookmarks automatically.
 
```go
result, err := neo4j.ExecuteQuery(ctx, driver,
    `MATCH (p:Person {name: $name})-[:KNOWS]->(friend)
     RETURN friend.name AS name`,
    map[string]any{"name": "Alice"},
    neo4j.EagerResultTransformer,
    neo4j.ExecuteQueryWithDatabase("neo4j"),        // ← always specify
    neo4j.ExecuteQueryWithReadersRouting(),          // ← for read queries
)
if err != nil {
    return fmt.Errorf("query people: %w", err)
}
 
for _, record := range result.Records {
    name, _ := record.Get("name")
    fmt.Println(name)
}
 
// Summary / counters
fmt.Println(result.Summary.Counters().NodesCreated())
```
 
**Key options** (variadic callbacks):
 
```go
neo4j.ExecuteQueryWithDatabase("mydb")         // required for performance
neo4j.ExecuteQueryWithReadersRouting()          // route reads to replicas
neo4j.ExecuteQueryWithAuthToken(token)          // per-query auth / impersonation
neo4j.ExecuteQueryWithImpersonatedUser("jane")  // impersonate without password
neo4j.ExecuteQueryWithoutBookmarkManager()       // opt out of causal consistency
```
 
**⚠ Never concatenate user input into query strings.** Always use `map[string]any` parameters.
 
---
 
## 4. Session-Based Transactions
 
Use when you need **lazy streaming** (large result sets) or more control within the callback.
 
```go
session := driver.NewSession(ctx, neo4j.SessionConfig{
    DatabaseName: "neo4j", // always specify
    AccessMode:   neo4j.AccessModeRead,
})
defer session.Close(ctx)
 
result, err := session.ExecuteRead(ctx,
    func(tx neo4j.ManagedTransaction) (any, error) {
        result, err := tx.Run(ctx,
            `MATCH (p:Person) RETURN p.name AS name LIMIT $limit`,
            map[string]any{"limit": 100},
        )
        if err != nil {
            return nil, err
        }
 
        var names []string
        for result.Next(ctx) { // lazy iteration — don't call Collect() on large sets
            name, _ := result.Record().Get("name")
            names = append(names, name.(string))
        }
        return names, result.Err()
    },
)
```
 
- The callback is **automatically retried** on transient failures (leader election, lock timeouts, etc.)
- **Do not perform side effects** in the callback that you don't want repeated on retry
- `ExecuteRead` routes to read replicas; `ExecuteWrite` routes to the cluster leader
---
 
## 5. Explicit Transactions
 
Use when transaction work spans multiple functions or requires coordination with external systems.
 
```go
session := driver.NewSession(ctx, neo4j.SessionConfig{DatabaseName: "neo4j"})
defer session.Close(ctx)
 
tx, err := session.BeginTransaction(ctx)
if err != nil {
    return err
}
 
// Pass tx to subordinate functions
if err := doPartA(ctx, tx); err != nil {
    tx.Rollback(ctx) // always rollback on error
    return err
}
if err := doPartB(ctx, tx); err != nil {
    tx.Rollback(ctx)
    return err
}
 
return tx.Commit(ctx)
```
 
**Explicit transactions are NOT automatically retried.** Your caller is responsible for retry logic. Prefer managed transactions unless you specifically need this control.
 
---
 
## 6. Error Handling
 
```go
import (
    "errors"
    "github.com/neo4j/neo4j-go-driver/v6/neo4j"
)
 
result, err := neo4j.ExecuteQuery(...)
if err != nil {
    var neo4jErr *neo4j.Neo4jError
    if errors.As(err, &neo4jErr) {
        // neo4jErr.Code is the GQLSTATUS/Neo4j error code
        // neo4jErr.Msg is the server message
        slog.Error("database error", "code", neo4jErr.Code, "msg", neo4jErr.Msg)
    }
 
    var connErr *neo4j.ConnectivityError
    if errors.As(err, &connErr) {
        slog.Error("connectivity error", "err", connErr)
    }
    return fmt.Errorf("execute query: %w", err)
}
```
 
**Error classification helpers** (useful for custom retry logic):
 
```go
neo4j.IsNeo4jError(err)            // server-side Cypher/database error
neo4j.IsTransactionExecutionLimit(err) // retries exhausted
// IsRetryable is internal; rely on managed transactions for automatic retry
```
 
**Within a managed transaction callback**, return the error to trigger retry:
 
```go
session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
    _, err := tx.Run(ctx, query, params)
    if err != nil {
        return nil, err // driver retries if transient
    }
    // ...
})
```
 
---
 
## 7. Data Types
 
Go ↔ Cypher type mapping:
 
| Cypher type | Go type |
|-------------|---------|
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
 
**Extracting typed values safely**:
 
```go
record.Get("name")          // returns (any, bool) — bool is whether key exists
record.AsMap()              // returns map[string]any for the whole record
 
// Type assert after extraction:
rawAge, ok := record.Get("age")
if !ok {
    return errors.New("missing 'age' field")
}
age, ok := rawAge.(int64) // Neo4j integers come back as int64
if !ok {
    return errors.New("'age' is not an integer")
}
 
// Node access:
rawNode, _ := record.Get("p")
node := rawNode.(neo4j.Node)
name := node.Props["name"].(string)
labels := node.Labels // []string
```
 
---
 
## 8. Best practices
 
### Always Specify the Database
 
```go
// With ExecuteQuery:
neo4j.ExecuteQueryWithDatabase("neo4j")
 
// With sessions:
neo4j.SessionConfig{DatabaseName: "neo4j"}
```
 
Omitting this costs a network round-trip on every call to resolve the home database.

### Context  

Always pass a `context.Context` for cancellation and timeout.  `context.WithTimeout`is recommended for production queries. `context.Background()` has no deadline — a slow query will block indefinitely.
 
### Lazy vs Eager Loading
 
```go
// Eager (default with ExecuteQuery) — fine for small/medium result sets
result, _ := neo4j.ExecuteQuery(ctx, driver, query, nil, neo4j.EagerResultTransformer, ...)
 
// Lazy — use with session.ExecuteRead/Write for large result sets
result, _ := tx.Run(ctx, query, params)
for result.Next(ctx) {       // stream records one at a time
    record := result.Record()
    // process...
}
if err := result.Err(); err != nil { ... }
```
 
### Batching Writes
 
```go
// Bad: one transaction per record
for _, item := range items {
    neo4j.ExecuteQuery(ctx, driver, writeQuery, item, ...)
}
 
// Good: all in one transaction using UNWIND
neo4j.ExecuteQuery(ctx, driver,
    `UNWIND $items AS item
     MERGE (n:Node {id: item.id})
     SET n += item`,
    map[string]any{"items": items},
    neo4j.EagerResultTransformer,
    neo4j.ExecuteQueryWithDatabase("neo4j"),
)
```
 
### CREATE vs MERGE
 
Use `CREATE` when you know the data is new — `MERGE` issues two queries internally (match then create).
 
### Connection Pool
 
```go
import "github.com/neo4j/neo4j-go-driver/v6/neo4j/config"
 
driver, _ := neo4j.NewDriver(uri, auth,
    func(conf *config.Config) {
        conf.MaxConnectionPoolSize = 50              // default: 100
        conf.ConnectionAcquisitionTimeout = 30 * time.Second
        conf.MaxConnectionLifetime = 1 * time.Hour
    },
)
```
 
---
 
## 9. Causal Consistency & Bookmarks
 
**Within a single session**, queries are automatically causally chained — no action required.
 
**Across sessions** (e.g. parallel workers), use `ExecuteQuery` (auto-managed) or share bookmarks explicitly:
 
```go
// sessionA and sessionB run concurrently; sessionC waits for both
sessionC := driver.NewSession(ctx, neo4j.SessionConfig{
    DatabaseName: "neo4j",
    Bookmarks:    neo4j.CombineBookmarks(
        sessionA.LastBookmarks(),
        sessionB.LastBookmarks(),
    ),
})
```
 
`ExecuteQuery` manages bookmarks automatically across calls to the same database — this is usually all you need.
 
---
 
## 10. Advanced Connection Config
 
```go
import (
    "github.com/neo4j/neo4j-go-driver/v6/neo4j/config"
    "github.com/neo4j/neo4j-go-driver/v6/neo4j/notifications"
)
 
driver, err := neo4j.NewDriver(uri, auth,
    func(conf *config.Config) {
        // Custom address resolver (e.g. for local dev against a cluster)
        conf.AddressResolver = func(addr config.ServerAddress) []config.ServerAddress {
            return []config.ServerAddress{
                neo4j.NewServerAddress("localhost", "7687"),
            }
        }
 
        // Reduce notification noise
        conf.NotificationsMinSeverity = notifications.WarningLevel
        conf.NotificationsDisabledClassifications = notifications.DisableClassifications(
            notifications.Hint, notifications.Generic,
        )
 
        // Bolt-level logging (debug)
        conf.Log = neo4j.ConsoleLogger(neo4j.DEBUG)
    },
)
```
 
---
 
## 11. Wrapping the Driver — Recommended Pattern
 
For testability and clean separation, wrap the driver behind a repository interface:
 
```go
type PersonRepo struct {
    driver neo4j.Driver
    db     string
}
 
func NewPersonRepo(driver neo4j.Driver, db string) *PersonRepo {
    return &PersonRepo{driver: driver, db: db}
}
 
func (r *PersonRepo) FindByName(ctx context.Context, name string) ([]Person, error) {
    result, err := neo4j.ExecuteQuery(ctx, r.driver,
        `MATCH (p:Person {name: $name}) RETURN p`,
        map[string]any{"name": name},
        neo4j.EagerResultTransformer,
        neo4j.ExecuteQueryWithDatabase(r.db),
        neo4j.ExecuteQueryWithReadersRouting(),
    )
    if err != nil {
        return nil, fmt.Errorf("find person %q: %w", name, err)
    }
 
    people := make([]Person, 0, len(result.Records))
    for _, rec := range result.Records {
        raw, _ := rec.Get("p")
        node := raw.(neo4j.Node)
        people = append(people, Person{
            Name: node.Props["name"].(string),
        })
    }
    return people, nil
}
```
 
---
 
## Quick Reference: Common Mistakes
 
| Mistake | Fix |
|---------|-----|
| String-interpolating Cypher params | Use `map[string]any` params always |
| Omitting `DatabaseName` | Always set in `SessionConfig` or `ExecuteQueryWithDatabase` |
| Creating a new driver per request | Create once, share across goroutines |
| Calling `Collect()` on huge result sets | Iterate with `result.Next(ctx)` instead |
| Side effects inside managed tx callbacks | Move side effects outside; callback may be retried |
| Using `MERGE` for guaranteed-new data | Use `CREATE` for new data; saves one round-trip |
| Not checking `result.Err()` after lazy iteration | Always check after the `for result.Next()` loop |
| Using explicit tx where managed tx suffices | Prefer `ExecuteRead/Write` for automatic retry |

