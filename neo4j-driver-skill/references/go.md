# Go driver (`github.com/neo4j/neo4j-go-driver/v6`)

Install: `go get github.com/neo4j/neo4j-go-driver/v6/neo4j`.

## Canonical example

```go
package main

import (
    "context"
    "fmt"
    "github.com/neo4j/neo4j-go-driver/v6/neo4j"
)

func main() {
    ctx := context.Background()

    driver, err := neo4j.NewDriverWithContext(
        "neo4j://localhost:7687",
        neo4j.BasicAuth("neo4j", "password", ""))
    if err != nil { panic(err) }
    defer driver.Close(ctx)

    if err := driver.VerifyConnectivity(ctx); err != nil { panic(err) }

    result, err := neo4j.ExecuteQuery(ctx, driver,
        "MATCH (p:Person {name: $name}) RETURN p.name AS name, p.age AS age",
        map[string]any{"name": "Alice"},
        neo4j.EagerResultTransformer,
        neo4j.ExecuteQueryWithDatabase("neo4j"),
        neo4j.ExecuteQueryWithReadersRouting(),
    )
    if err != nil { panic(err) }

    for _, r := range result.Records {
        fmt.Println(r.AsMap())   // map[string]any
    }
}
```

## Accessing fields

- `record.Get("name")` → `(any, bool)`
- `record.AsMap()` → `map[string]any` for the whole record
- `record.Keys` — column names
- `neo4j.GetRecordValue[T](record, "name")` for typed extraction (v6)

## Bulk writes

```go
rows := []map[string]any{
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"},
}
neo4j.ExecuteQuery(ctx, driver,
    "UNWIND $rows AS row MERGE (p:Person {id: row.id}) SET p += row",
    map[string]any{"rows": rows},
    neo4j.EagerResultTransformer,
    neo4j.ExecuteQueryWithDatabase("neo4j"))
```

## Configuration options

- `ExecuteQueryWithDatabase("neo4j")` — set it explicitly to avoid the home-database round-trip
- `ExecuteQueryWithReadersRouting()` / `ExecuteQueryWithWritersRouting()`
- `ExecuteQueryWithImpersonatedUser("alice")`
- `ExecuteQueryWithBookmarkManager(bm)`

## When to drop to a session

```go
session := driver.NewSession(ctx, neo4j.SessionConfig{DatabaseName: "neo4j"})
defer session.Close(ctx)

_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
    r, err := tx.Run(ctx,
        "MATCH (a:Account {id:$id}) RETURN a.balance AS b",
        map[string]any{"id": fromId})
    if err != nil { return nil, err }
    rec, err := r.Single(ctx)
    if err != nil { return nil, err }
    balance, _ := rec.Get("b")
    if balance.(int64) < amount { return nil, fmt.Errorf("insufficient funds") }
    // ... two more tx.Run calls ...
    return nil, nil
})
```

Transaction callbacks must be idempotent — the driver retries on transient failures.
