---
name: neo4j-driver-go-skill
description: >
  Use when writing Go code that connects to Neo4j: installing neo4j-go-driver/v5,
  configuring neo4j.NewDriverWithContext(), neo4j.ExecuteQuery(), session and
  transaction management, context propagation, or result serialization with
  rec.AsMap(). Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT handle driver version upgrades — use neo4j-migration-skill.
status: draft
version: 0.1.0
allowed-tools: Bash, WebFetch
---

# Neo4j Go Driver Skill

> **Status: Draft / WIP** — Content is a placeholder. Reference files to be added.

## When to Use

- Setting up the Neo4j Go driver (`go get github.com/neo4j/neo4j-go-driver/v5`)
- Writing `neo4j.NewDriverWithContext()` and `neo4j.ExecuteQuery()` patterns
- Context propagation, session management, and write transactions in Go
- Serializing results with `rec.AsMap()` for JSON encoding
- Error handling and driver lifecycle in Go services

## When NOT to Use

- **Cypher query authoring** → use `neo4j-cypher-skill`
- **Driver version upgrades** → use `neo4j-migration-skill`

---

## Setup

```bash
go get github.com/neo4j/neo4j-go-driver/v5   # Go >= 1.21 required
```

---

## Core Patterns

### Driver singleton

> **Context timeout**: always use `context.WithTimeout` for production queries. `context.Background()` has no deadline — a slow query will block indefinitely.

```go
package main

import (
    "context"
    "os"
    "time"
    "github.com/neo4j/neo4j-go-driver/v5/neo4j"
)

func main() {
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    driver, err := neo4j.NewDriverWithContext(
        os.Getenv("NEO4J_URI"),
        neo4j.BasicAuth(
            os.Getenv("NEO4J_USERNAME"),
            os.Getenv("NEO4J_PASSWORD"),
            "",
        ),
    )
    if err != nil { panic(err) }
    defer driver.Close(ctx)

    if err := driver.VerifyConnectivity(ctx); err != nil { panic(err) }
}
```

### ExecuteQuery (recommended)

```go
result, err := neo4j.ExecuteQuery(ctx, driver,
    "MATCH (p:Person {name: $name})-[:KNOWS]->(f) RETURN f.name AS friend",
    map[string]any{"name": "Alice"},
    neo4j.EagerResultTransformer,
    neo4j.ExecuteQueryWithDatabase("neo4j"),
)
if err != nil { panic(err) }

for _, rec := range result.Records {
    fmt.Println(rec.AsMap()["friend"])
}
```

### Session + write transaction

```go
session := driver.NewSession(ctx, neo4j.SessionConfig{DatabaseName: "neo4j"})
defer session.Close(ctx)

_, err = session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
    _, err := tx.Run(ctx,
        "MERGE (p:Person {id: $id}) SET p.name = $name",
        map[string]any{"id": "1", "name": "Alice"},
    )
    return nil, err
})
```

---

## Key Notes

- Neo4j integers map to `int64` in Go — no integer footgun like JavaScript
- Use `rec.AsMap()` to convert records to `map[string]any` for JSON encoding
- `neo4j.EagerResultTransformer` loads all results into memory; use streaming transformers for large result sets
- Always pass a `context.Context` — use it for cancellation and timeouts

---

## Checklist

- [ ] Driver created once at startup, closed with `defer driver.Close(ctx)`
- [ ] Credentials from env vars, not hardcoded
- [ ] `neo4j.ExecuteQuery` used for simple queries (auto-retries transient errors)
- [ ] `session.ExecuteWrite` used for write transactions
- [ ] `rec.AsMap()` called when JSON serialization is needed
- [ ] Context passed through for cancellation/timeout control

---

## Fetching Current Docs

```
https://neo4j.com/docs/llms.txt     ← full documentation index
https://neo4j.com/llms-full.txt     ← rich reference with code examples
```

## References

- [Go Driver Manual](https://neo4j.com/docs/go-manual/)
- [GraphAcademy: Using Neo4j with Go](https://graphacademy.neo4j.com/courses/drivers-go/)
