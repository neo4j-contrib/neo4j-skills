# Repository Pattern — Wrapping the Driver

Wrap the driver behind a repository interface for testability and clean separation:

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

## Causal Consistency — Cross-Session Bookmarks

Within a single session, queries are automatically causally chained. Across concurrent sessions, share bookmarks explicitly:

```go
// sessionA and sessionB run concurrently; sessionC waits for both
sessionC := driver.NewSession(ctx, neo4j.SessionConfig{
    DatabaseName: "neo4j",
    Bookmarks: neo4j.CombineBookmarks(
        sessionA.LastBookmarks(),
        sessionB.LastBookmarks(),
    ),
})
```

`ExecuteQuery` manages bookmarks automatically across calls to the same database — usually all you need.
