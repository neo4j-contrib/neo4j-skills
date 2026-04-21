# .NET driver (`Neo4j.Driver`)

Install: `dotnet add package Neo4j.Driver`.

## Canonical example

```csharp
using Neo4j.Driver;

await using var driver = GraphDatabase.Driver(
    "neo4j://localhost:7687",
    AuthTokens.Basic("neo4j", "password"));

await driver.VerifyConnectivityAsync();

var result = await driver
    .ExecutableQuery("MATCH (p:Person {name: $name}) RETURN p.name AS name, p.age AS age")
    .WithParameters(new { name = "Alice" })
    .WithConfig(new QueryConfig(
        database: "neo4j",
        routing: RoutingControl.Readers))
    .ExecuteAsync();

foreach (var record in result.Result)
{
    var map = record.Values;           // IReadOnlyDictionary<string, object>
    var name = record["name"].As<string>();
}
```

`ExecuteAsync()` returns an `EagerResult<IReadOnlyList<IRecord>>` exposing `Result`, `Summary`, `Keys`.

## Accessing fields

- `record["name"].As<string>()` — typed extraction
- `record.Get<int>("age")` — typed extraction by name
- `record.Values` — whole record as `IReadOnlyDictionary<string, object>`
- `record.Keys` — column names

## Mapped results

```csharp
var names = await driver
    .ExecutableQuery("MATCH (p:Person) RETURN p.name AS name")
    .WithConfig(new QueryConfig(database: "neo4j"))
    .WithMap(r => r["name"].As<string>())
    .ExecuteAsync();
// names.Result is IReadOnlyList<string>
```

## Bulk writes

```csharp
var rows = new[] {
    new { id = 1, name = "Alice" },
    new { id = 2, name = "Bob" }
};

await driver
    .ExecutableQuery("UNWIND $rows AS row MERGE (p:Person {id: row.id}) SET p += row")
    .WithParameters(new { rows })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();
```

## When to drop to a session

```csharp
await using var session = driver.AsyncSession(o => o.WithDatabase("neo4j"));

await session.ExecuteWriteAsync(async tx =>
{
    var r = await tx.RunAsync(
        "MATCH (a:Account {id:$id}) RETURN a.balance AS b",
        new { id = fromId });
    var rec = await r.SingleAsync();
    var balance = rec["b"].As<long>();
    if (balance < amount) throw new InvalidOperationException("insufficient funds");

    await tx.RunAsync("MATCH (a:Account {id:$id}) SET a.balance = a.balance - $amt",
                      new { id = fromId, amt = amount });
    await tx.RunAsync("MATCH (a:Account {id:$id}) SET a.balance = a.balance + $amt",
                      new { id = toId,   amt = amount });
});
```

Transaction callbacks must be idempotent — the driver retries on transient failures.
