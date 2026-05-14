---
name: neo4j-driver-dotnet-skill
description: Neo4j .NET Driver v6 — IDriver lifecycle, DI registration (singleton), ExecutableQuery
  fluent API, ExecuteReadAsync/ExecuteWriteAsync managed transactions, IResultCursor (FetchAsync/
  ToListAsync), record value access (.Get<T>/As<T>), null safety, UNWIND batching, temporal types,
  await using, EagerResult, object mapping, CancellationToken, error handling, and common traps.
  Use when writing C# or .NET code connecting to Neo4j. Also triggers on Neo4j.Driver, IDriver,
  ExecutableQuery, ExecuteReadAsync, ExecuteWriteAsync, IResultCursor, IAsyncSession, or any Bolt/Aura
  work in .NET/C#. Does NOT handle Cypher authoring — use neo4j-cypher-skill.
  Does NOT cover driver version upgrades — use neo4j-migration-skill.
compatibility: .NET 8, 9, 10; Neo4j.Driver v6
allowed-tools: Bash WebFetch
version: 0.2.0
---

## When to Use
- Writing C# or .NET code connecting to Neo4j
- Setting up `IDriver`, DI registration, or session/transaction lifecycle
- Questions about `ExecutableQuery`, `IResultCursor`, async patterns, result mapping
- Debugging sessions, type mapping, null safety, or error handling in .NET

## When NOT to Use
- **Writing/optimizing Cypher queries** → `neo4j-cypher-skill`
- **Upgrading from older driver version** → `neo4j-migration-skill`

---

## Install

```bash
dotnet add package Neo4j.Driver
```

| Package | Use |
|---|---|
| `Neo4j.Driver` | Async API — **use this** |
| `Neo4j.Driver.Simple` | Synchronous wrapper |
| `Neo4j.Driver.Reactive` | System.Reactive streams |

---

## Driver Lifecycle

`IDriver` — thread-safe, connection-pooled, expensive to create. **Create one per application.**

```csharp
using Neo4j.Driver;

// URI schemes:
//   neo4j+s://xxx.databases.neo4j.io   — TLS + cluster routing (Aura)
//   neo4j://localhost                   — unencrypted + cluster routing
//   bolt+s://localhost:7687             — TLS + single instance
//   bolt://localhost:7687               — unencrypted + single instance

await using var driver = GraphDatabase.Driver(
    "neo4j+s://xxx.databases.neo4j.io",
    AuthTokens.Basic("neo4j", "password"));

await driver.VerifyConnectivityAsync();   // fail fast on startup
```

`IDriver` and `IAsyncSession` implement `IAsyncDisposable` — always `await using`, never plain `using`.

```csharp
// ❌ Wrong — synchronous Dispose() may block thread pool
using var driver = GraphDatabase.Driver(uri, auth);

// ✅ Correct
await using var driver = GraphDatabase.Driver(uri, auth);
```

Auth options: `AuthTokens.Basic(u, p)` / `AuthTokens.Bearer(token)` / `AuthTokens.Kerberos(ticket)` / `AuthTokens.None`

---

## Environment Variables

Load connection config from environment / `appsettings.json` — never hardcode credentials.

```json
// appsettings.json
{
  "Neo4j": {
    "Uri": "neo4j+s://xxx.databases.neo4j.io",
    "User": "neo4j",
    "Password": "secret",
    "Database": "neo4j"
  }
}
```

```csharp
// Access via IConfiguration (injected in Program.cs)
var uri      = builder.Configuration["Neo4j:Uri"];
var user     = builder.Configuration["Neo4j:User"];
var password = builder.Configuration["Neo4j:Password"];
var database = builder.Configuration["Neo4j:Database"] ?? "neo4j";
```

Override with environment variables (standard .NET behavior): `Neo4j__Uri=neo4j+s://...` (double underscore = colon separator). Never commit `appsettings.json` with real credentials — use `appsettings.Development.json` (gitignored) or env vars in CI/production.

---

## DI Registration (ASP.NET Core)

Register `IDriver` as **singleton** — never Scoped or Transient. Never register `IAsyncSession` in DI.

```csharp
// Program.cs
builder.Services.AddSingleton<IDriver>(_ =>
    GraphDatabase.Driver(
        builder.Configuration["Neo4j:Uri"],
        AuthTokens.Basic(
            builder.Configuration["Neo4j:User"],
            builder.Configuration["Neo4j:Password"])));

// Shutdown hook — dispose the singleton cleanly
builder.Services.AddHostedService<Neo4jShutdownService>();

// Neo4jShutdownService.cs
public class Neo4jShutdownService(IDriver driver, IHostApplicationLifetime lifetime)
    : IHostedService
{
    public Task StartAsync(CancellationToken _)
    {
        lifetime.ApplicationStopping.Register(() =>
            driver.DisposeAsync().AsTask().GetAwaiter().GetResult());
        return Task.CompletedTask;
    }
    public Task StopAsync(CancellationToken _) => Task.CompletedTask;
}

// Inject into services — sessions opened per unit of work
public class PersonService(IDriver driver)
{
    public async Task<List<string>> GetNamesAsync(CancellationToken ct = default)
    {
        var (records, _, _) = await driver
            .ExecutableQuery("MATCH (p:Person) RETURN p.name AS name")
            .WithConfig(new QueryConfig(database: "neo4j"))
            .ExecuteAsync(ct);
        return records.Select(r => r.Get<string>("name")).ToList();
    }
}
```

---

## Choose the Right API

| API | When | Auto-retry | Streaming |
|---|---|---|---|
| `driver.ExecutableQuery()` | Most queries — simple default | ✅ | ❌ eager |
| `session.ExecuteReadAsync/WriteAsync()` | Large results, multi-query tx | ✅ | ✅ |
| `session.RunAsync()` | `LOAD CSV`, `CALL {} IN TRANSACTIONS` | ❌ | ✅ |
| `session.BeginTransactionAsync()` | Multi-function, external coordination | ❌ | ✅ |

---

## ExecutableQuery — Recommended Default

Fluent builder; manages session, transaction, retries, and bookmarks automatically.

```csharp
// Read
var (records, summary, keys) = await driver
    .ExecutableQuery("MATCH (p:Person {name: $name})-[:KNOWS]->(f) RETURN f.name AS name")
    .WithParameters(new { name = "Alice" })
    .WithConfig(new QueryConfig(
        database: "neo4j",
        routing: RoutingControl.Readers))    // route reads to replicas
    .ExecuteAsync(cancellationToken);

foreach (var r in records)
    Console.WriteLine(r.Get<string>("name"));

// Use ResultConsumedAfter for wall-clock timing (ResultAvailableAfter = time-to-first-byte only)
Console.WriteLine($"{summary.ResultConsumedAfter.TotalMilliseconds} ms");

// Write
var (_, writeSummary, _) = await driver
    .ExecutableQuery("CREATE (p:Person {name: $name, age: $age})")
    .WithParameters(new { name = "Bob", age = 30 })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();
Console.WriteLine($"Created {writeSummary.Counters.NodesCreated} nodes");

// WithMap — project inline
var names = await driver
    .ExecutableQuery("MATCH (p:Person) RETURN p.name AS name")
    .WithConfig(new QueryConfig(database: "neo4j"))
    .WithMap(r => r["name"].As<string>())
    .ExecuteAsync();   // names.Result is IReadOnlyList<string>
```

Never `await` omitted: `ExecuteAsync()` returns `Task` — missing `await` compiles silently but query never runs.

Never string-interpolate Cypher. Always `WithParameters()` — prevents injection, enables plan caching.

---

## Managed Transactions

Use for large result sets (lazy streaming) or multiple queries per transaction. Callback auto-retried on transient failure — keep it idempotent, no side effects inside.

```csharp
await using var session = driver.AsyncSession(conf => conf.WithDatabase("neo4j"));

// Read — routes to replicas
var names = await session.ExecuteReadAsync(async tx =>
{
    var cursor = await tx.RunAsync(
        "MATCH (p:Person) WHERE p.name STARTS WITH $prefix RETURN p.name AS name",
        new { prefix = "Al" });
    return await cursor.ToListAsync(r => r.Get<string>("name"));
    // Consume cursor INSIDE callback — invalid after callback returns
});

// Write — void, no async needed
await session.ExecuteWriteAsync(tx =>
    tx.RunAsync("MERGE (p:Person {name: $name})", new { name = "Carol" }));

// Write — async when needing counters
var summary = await session.ExecuteWriteAsync(async tx =>
{
    var cursor = await tx.RunAsync(
        "CREATE (p:Person {name: $name})", new { name = "Alice" });
    return await cursor.ConsumeAsync();   // drains cursor, returns IResultSummary
});
Console.WriteLine($"Created {summary.Counters.NodesCreated} nodes");
```

Cursor rules:
- Consume with `ToListAsync()` or `FetchAsync()` loop **inside** the callback
- Returning a cursor from the callback → transaction closes → cursor invalid → exception

```csharp
// ❌ Returns cursor — tx closes immediately after lambda returns
var cursor = await session.ExecuteReadAsync(async tx =>
    await tx.RunAsync("MATCH (p:Person) RETURN p.name AS name"));
await cursor.FetchAsync();   // throws

// ✅ Consume inside
var names = await session.ExecuteReadAsync(async tx =>
{
    var cursor = await tx.RunAsync("MATCH (p:Person) RETURN p.name AS name");
    return await cursor.ToListAsync(r => r.Get<string>("name"));
});
```

Async void trap:
```csharp
// ❌ CS1998 warning — async with no await; RunAsync Task discarded
await session.ExecuteWriteAsync(async tx =>
    tx.RunAsync("MERGE (p:Person {name: $name})", new { name = "Alice" }));

// ✅ No async, return Task directly
await session.ExecuteWriteAsync(tx =>
    tx.RunAsync("MERGE (p:Person {name: $name})", new { name = "Alice" }));
```

---

## FetchAsync Loop

```csharp
var cursor = await tx.RunAsync("MATCH (p:Person) RETURN p.name AS name");

while (await cursor.FetchAsync())          // true while records remain
{
    Process(cursor.Current.Get<string>("name"));
}
// Do NOT use cursor.Current after the loop — it holds the last record, not null
// Do NOT call FetchAsync() again after it returned false — throws InvalidOperationException
```

Cursor consumption methods:

| Method | Records | Summary | Use |
|---|---|---|---|
| `ToListAsync()` | ✅ all | ❌ | Need records |
| `ToListAsync(mapper)` | ✅ mapped | ❌ | Need mapped records |
| `FetchAsync()` loop | ✅ one/time | ❌ until ConsumeAsync | Large/lazy |
| `ConsumeAsync()` | ❌ discards | ✅ | Need counters |
| `SingleAsync()` | ✅ exactly 1 | ❌ | Expect one row |

---

## Record Value Access

```csharp
// Two equivalent patterns — prefer .Get<T>()
string name = record.Get<string>("name");
int    age  = record.Get<int>("age");

string name2 = record["name"].As<string>();   // indexer + As<T>
string name3 = record[0].As<string>();        // by column index

// Null safety — .As<T>() on null graph value throws InvalidCastException
string? city = record["city"].As<string?>();  // ✅ nullable
int?    age2 = record["age"].As<int?>();      // ✅ nullable

// Absent key — throws KeyNotFoundException (typo or not in RETURN)
if (record.Keys.Contains("city"))
    var city3 = record.Get<string?>("city");
```

---

## Type Mapping

| Cypher | .NET default | Notes |
|---|---|---|
| `Integer` | `long` | safe: `int`, `long?`, `int?` |
| `Float` | `double` | safe: `float`, `double?` |
| `String` | `string` | use `string?` if nullable |
| `Boolean` | `bool` | |
| `List` | `IReadOnlyList<object>` | |
| `Map` | `IReadOnlyDictionary<string,object>` | |
| `Node` | `INode` | `.Labels`, `.Properties`, `.ElementId` |
| `Relationship` | `IRelationship` | `.Type`, `.StartNodeElementId` |
| `Date` | `LocalDate` | `.ToDateOnly()` (.NET 6+) |
| `DateTime` | `ZonedDateTime` | `.ToDateTimeOffset()` (ms precision) |
| `LocalDateTime` | `LocalDateTime` | |
| `Duration` | `Duration` | `.ToTimeSpan()` throws if has months/days |
| `null` | `null` | use nullable types |

`ElementId` stable within one transaction only — do not use to MATCH across separate transactions.

```csharp
// Pass CLR types as params — driver converts automatically
await driver.ExecutableQuery("CREATE (e:Event {at: $ts})")
    .WithParameters(new { ts = DateTimeOffset.UtcNow })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();
```

---

## UNWIND Batching

```csharp
// ❌ One transaction per record — high overhead
foreach (var item in items)
    await driver.ExecutableQuery("MERGE (n:Node {id: $id})")
        .WithParameters(new { id = item.Id })
        .WithConfig(new QueryConfig(database: "neo4j"))
        .ExecuteAsync();

// ✅ Single transaction via UNWIND — anonymous types only (custom classes don't serialize)
var rows = items.Select(i => new { id = i.Id, name = i.Name }).ToArray();
await driver.ExecutableQuery(@"
    UNWIND $rows AS row
    MERGE (n:Node {id: row.id})
    SET n.name = row.name")
    .WithParameters(new { rows })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();
```

Custom class instances passed to `WithParameters` for UNWIND do not serialize — use `new object[] { new { ... } }` or `Dictionary<string, object>`.

---

## Object Mapping (Preview API)

```csharp
using Neo4j.Driver.Preview.Mapping;   // REQUIRED — without this, AsObject<T>() is CS1061

public record Person(string Name, int Age);   // C# records work well here

var result = await driver
    .ExecutableQuery("MATCH (p:Person) RETURN p.name AS name, p.age AS age")
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();

var person = result.Result[0].AsObject<Person>();   // RETURN keys map to record properties

// Bulk mapping
var (people, _, _) = await driver
    .ExecutableQuery("MATCH (p:Person) RETURN p.name AS name, p.age AS age")
    .WithConfig(new QueryConfig(database: "neo4j"))
    .AsObjectsAsync<Person>();
```

---

## Error Handling

```csharp
try
{
    await driver.ExecutableQuery("...")
        .WithConfig(new QueryConfig(database: "neo4j"))
        .ExecuteAsync();
}
catch (AuthenticationException ex)      { /* bad credentials */ }
catch (ServiceUnavailableException ex)  { /* database unreachable */ }
catch (ClientException ex)
    when (ex.Code == "Neo.ClientError.Schema.ConstraintValidationFailed")
{
    // Unique/existence constraint violation — catch BEFORE Neo4jException
}
catch (Neo4jException ex)               { /* all other server errors */ }
```

Catch `ClientException` before `Neo4jException` — it's a subclass; generic handler swallows it.

`ex.GqlStatus` — stable GQL status codes; prefer over string-matching `ex.Code`.

Explicit transaction rollback can itself throw — isolate it:
```csharp
catch (Exception original)
{
    try { await tx.RollbackAsync(); }
    catch (Exception ex) { logger.LogError(ex, "Rollback failed"); }
    throw;
}
```

If `CommitAsync()` throws a network error, commit may or may not have succeeded — design writes idempotent with `MERGE` + unique constraints.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| `using var driver` | `await using var driver` — `IDriver` is `IAsyncDisposable` |
| `using var session` | `await using var session` |
| `IDriver` as Scoped/Transient in DI | Register as Singleton |
| `IAsyncSession` in DI | Never — open per unit of work |
| Missing `await` on `ExecuteAsync()` | Task silently never runs |
| `async tx => tx.RunAsync(...)` no inner await | Remove `async`, return Task directly |
| Omit `database` in `QueryConfig`/`AsyncSession` | Always specify — saves a round-trip |
| No `CancellationToken` in web apps | Propagate `HttpContext.RequestAborted` |
| `.As<string>()` on null graph value | `.As<string?>()` — non-nullable throws |
| `record["key"]` absent key | Check `record.Keys.Contains()` first |
| `cursor.Current` after FetchAsync loop | Last record, not null — don't use after loop |
| `FetchAsync()` after `false` return | Throws — stop loop, don't call again |
| Return cursor from managed tx callback | Consume with `ToListAsync()` inside callback |
| Need counters from session write | `await cursor.ConsumeAsync()` |
| `AsObject<T>()` CS1061 compile error | Add `using Neo4j.Driver.Preview.Mapping;` |
| `ResultAvailableAfter` for total timing | Use `ResultConsumedAfter` (full wall-clock) |
| Custom class in `WithParameters` for UNWIND | Use anonymous types or `Dictionary<string,object>` |
| Rename C# param but not Cypher `$param` | Anonymous property names must match `$param` names |
| `ExecuteWriteAsync` for reads | Use `ExecuteReadAsync` — routes to replicas |
| Side effects inside managed tx callback | Move outside — callback retried on failure |
| `Duration.ToTimeSpan()` with months/days | Only safe for pure second/nanosecond durations |
| Catch `Neo4jException` before `ClientException` | `ClientException` is subclass — catch it first |

---

## References

Load on demand:
- [references/transactions.md](references/transactions.md) — explicit transactions, `BeginTransactionAsync`, rollback, commit uncertainty, `TransactionConfig` (timeout, metadata), causal consistency and bookmarks
- [references/performance.md](references/performance.md) — spatial types (Point/WGS-84/Cartesian), connection pool tuning, `WithFetchSize`, session config options, `CancellationToken` patterns, large result streaming
- [references/object-mapping.md](references/object-mapping.md) — `AsObject<T>`, blueprint mapping, lambda mapping, `AsObjectsAsync<T>`, repository pattern example

---

## Checklist
- [ ] `IDriver` registered as singleton in DI (or `await using` for short-lived apps)
- [ ] `await using` on driver and sessions (not plain `using`)
- [ ] `database` specified in `QueryConfig` / `AsyncSession` config
- [ ] `ExecutableQuery` used for simple queries; `ExecuteReadAsync`/`ExecuteWriteAsync` for streaming/multi-query
- [ ] Cursor consumed inside managed tx callback (not returned)
- [ ] Nullable types (`string?`, `int?`) on any graph value that can be null
- [ ] `WithParameters()` used (no string interpolation)
- [ ] UNWIND batching with anonymous types (not custom class instances)
- [ ] `CancellationToken` propagated in web app handlers
- [ ] `ClientException` caught before `Neo4jException`
- [ ] Writes idempotent (`MERGE` + constraints) for retry safety
- [ ] No side effects inside `ExecuteReadAsync`/`ExecuteWriteAsync` callbacks
