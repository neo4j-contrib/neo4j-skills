---
name: neo4j-driver-dotnet-skill
description: >
Comprehensive guide to using the official Neo4j .NET Driver (v6, current stable) — covering
installation, IDriver lifecycle and DI registration, all three query APIs (ExecutableQuery
fluent API, managed transactions via ExecuteReadAsync/ExecuteWriteAsync, auto-commit via
RunAsync), IResultCursor consumption patterns (FetchAsync loop vs ToListAsync), record value
access and null safety, WithParameters anonymous types and UNWIND batching, temporal type
mapping, await-using vs using, EagerResult unpacking, object mapping, performance, causal
consistency, and error handling. Use this skill whenever writing C# or .NET code that talks
to Neo4j, or when questions arise about sessions, transactions, result handling, data types,
bookmarks, or driver configuration. Also triggers on Neo4j.Driver, GraphDatabase.Driver,
ExecutableQuery, ExecuteReadAsync, ExecuteWriteAsync, IAsyncSession, IResultCursor, IRecord,
WithParameters, AsObject, or any Neo4j Bolt/Aura connection work in .NET or C#.  

Does NOT handle Cypher query authoring — use neo4j-cypher-skill. 
 
status: draft
version: 0.1.1
allowed-tools: Bash, WebFetch
--- 

# Neo4j .NET Driver

**Package**: `Neo4j.Driver`  
**Current stable**: v6  
**Supports**: .NET 8, 9, 10  
**Docs**: https://neo4j.com/docs/dotnet-manual/current/  
**API ref**: https://neo4j.com/docs/api/dotnet-driver/current/

---

## 1. Installation

```bash
dotnet add package Neo4j.Driver
```

Three packages are available:

| Package | Use |
|---------|-----|
| `Neo4j.Driver` | Async API — **use this** |
| `Neo4j.Driver.Simple` | Synchronous API (wraps async) |
| `Neo4j.Driver.Reactive` | Reactive streams (System.Reactive) |

---

## 2. Driver Lifecycle

`IDriver` is **thread-safe, connection-pooled, and expensive to create** — create one instance per application and share it. Use `await using` (not plain `using`) because `IDriver` implements `IAsyncDisposable`.

```csharp
using Neo4j.Driver;

// URI examples:
//   "neo4j://localhost"                 — unencrypted, cluster-routing
//   "neo4j+s://xxx.databases.neo4j.io"  — TLS, cluster-routing (Aura)
//   "bolt://localhost:7687"             — unencrypted, single instance
//   "bolt+s://localhost:7687"           — TLS, single instance
await using var driver = GraphDatabase.Driver(
    "neo4j+s://xxx.databases.neo4j.io",
    AuthTokens.Basic("neo4j", "password"));

await driver.VerifyConnectivityAsync();   // fail fast if unreachable
```

### `await using` vs `using` — Critical Difference

`IDriver` and `IAsyncSession` implement `IAsyncDisposable`. Using plain `using` calls the synchronous `Dispose()` which blocks and may not cleanly drain the connection pool:

```csharp
// ❌ Wrong — calls synchronous Dispose(), may block the thread pool
using var driver = GraphDatabase.Driver(uri, auth);

// ✅ Correct — calls DisposeAsync(), non-blocking async teardown
await using var driver = GraphDatabase.Driver(uri, auth);

// ✅ Also correct for long-lived singletons — explicit async close
var driver = GraphDatabase.Driver(uri, auth);
// ... on shutdown:
await driver.DisposeAsync();
```

This applies equally to `IAsyncSession` — always `await using var session = ...` or `finally { await session.DisposeAsync(); }`.

### Auth Options

```csharp
AuthTokens.Basic(user, password)           // username + password
AuthTokens.Bearer(token)                   // SSO / JWT
AuthTokens.Kerberos(base64Ticket)          // Kerberos
AuthTokens.None                            // unauthenticated (dev only)
```

### ASP.NET Core / Dependency Injection

Register `IDriver` as a **singleton** — not Scoped or Transient:

```csharp
// Program.cs
builder.Services.AddSingleton<IDriver>(_ =>
    GraphDatabase.Driver(
        builder.Configuration["Neo4j:Uri"],
        AuthTokens.Basic(
            builder.Configuration["Neo4j:User"],
            builder.Configuration["Neo4j:Password"])));

// Dispose on app shutdown
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

// Inject into controllers / services
public class PersonService(IDriver driver)
{
    public async Task<List<string>> GetNamesAsync()
    {
        var result = await driver.ExecutableQuery("MATCH (p:Person) RETURN p.name AS name")
            .WithConfig(new QueryConfig(database: "neo4j"))
            .ExecuteAsync();
        return result.Result.Select(r => r.Get<string>("name")).ToList();
    }
}
```

**⚠ Never register `IAsyncSession` in DI** — sessions are short-lived, not thread-safe, and must be opened per unit of work.

---

## 3. Choosing the Right API

| API | When to use | Auto-retry? | Streaming? |
|-----|-------------|-------------|------------|
| `driver.ExecutableQuery()` | Most queries — simple, safe default | ✅ | ❌ (eager) |
| `session.ExecuteReadAsync/WriteAsync()` | Large results, multiple queries per tx | ✅ | ✅ |
| `session.RunAsync()` | `LOAD CSV`, `CALL {} IN TRANSACTIONS` | ❌ | ✅ |
| `session.BeginTransactionAsync()` | Multi-function work, external coordination | ❌ | ✅ |

---

## 4. `ExecutableQuery` — Recommended Default

The highest-level API. Fluent builder; manages sessions, transactions, retries, and bookmarks automatically.

```csharp
using Neo4j.Driver;

// Read query
var result = await driver.ExecutableQuery(@"
        MATCH (p:Person {name: $name})-[:KNOWS]->(friend)
        RETURN friend.name AS name")
    .WithParameters(new { name = "Alice" })
    .WithConfig(new QueryConfig(
        database: "neo4j",                      // always specify — avoids a round-trip
        routing: RoutingControl.Readers))        // route reads to replicas
    .ExecuteAsync();

foreach (var record in result.Result)
{
    Console.WriteLine(record.Get<string>("name"));
}

Console.WriteLine($"Returned {result.Result.Count} records " +
                  $"in {result.Summary.ResultConsumedAfter.TotalMilliseconds} ms");
```

### `ResultAvailableAfter` vs `ResultConsumedAfter`

The summary exposes two timing properties. They measure different things and are easy to confuse:

```csharp
var summary = result.Summary;

// Time until the SERVER sent the first record (network latency + query planning + first row)
// — useful for measuring server-side query execution time
var timeToFirstRecord = summary.ResultAvailableAfter.TotalMilliseconds;

// Time until ALL records were received and consumed by the driver
// — this is the true wall-clock duration of the full operation
// — use this for application-level performance monitoring and logging
var totalTime = summary.ResultConsumedAfter.TotalMilliseconds;

// For most profiling and observability purposes, ResultConsumedAfter is what you want.
// ResultAvailableAfter < ResultConsumedAfter — the gap is network transfer time for all rows.
```

// Write query
var writeResult = await driver.ExecutableQuery(@"
        CREATE (p:Person {name: $name, age: $age})")
    .WithParameters(new { name = "Bob", age = 30 })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();

Console.WriteLine($"Created {writeResult.Summary.Counters.NodesCreated} nodes");
```

### `EagerResult<T>` — Understanding the Return Type

`ExecuteAsync()` returns `EagerResult<IReadOnlyList<IRecord>>`. It has three members:

```csharp
var result = await driver.ExecutableQuery("MATCH (p:Person) RETURN p.name AS name")
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();

var records = result.Result;      // IReadOnlyList<IRecord> — the rows
var summary = result.Summary;     // IResultSummary — counters, timing, query text
var keys    = result.Keys;        // IReadOnlyList<string> — projected column names

// Deconstruct into tuple:
var (records2, summary2, keys2) = await driver
    .ExecutableQuery("MATCH (p:Person) RETURN p.name AS name")
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();
```

**⚠ Never forget `await`** — `ExecuteAsync()` returns a `Task`. Omitting `await` compiles silently but nothing executes:

```csharp
// ❌ Compiles and does nothing — query never runs
driver.ExecutableQuery("CREATE (p:Person {name: $name})")
    .WithParameters(new { name = "Alice" })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();   // Task not awaited — fire and forget with no result

// ✅ Correct
await driver.ExecutableQuery("CREATE (p:Person {name: $name})")
    .WithParameters(new { name = "Alice" })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();
```

**⚠ Never string-interpolate or concatenate Cypher.** Always use `WithParameters()` — prevents injection and enables server-side query plan caching.

---

## 5. Managed Transactions (`ExecuteReadAsync` / `ExecuteWriteAsync`)

Use for large result sets (lazy streaming via cursor) or multiple queries in one transaction.

```csharp
await using var session = driver.AsyncSession(conf =>
    conf.WithDatabase("neo4j"));

// Read — routes to replicas; callback auto-retried on transient failure
var names = await session.ExecuteReadAsync(async tx =>
{
    var cursor = await tx.RunAsync(
        "MATCH (p:Person) WHERE p.name STARTS WITH $prefix RETURN p.name AS name",
        new { prefix = "Al" });

    // Consume the cursor INSIDE the callback — it is invalid after the tx closes
    return await cursor.ToListAsync(r => r.Get<string>("name"));
});

// Write — routes to leader
await session.ExecuteWriteAsync(async tx =>
{
    await tx.RunAsync(
        "CREATE (p:Person {name: $name})",
        new { name = "Carol" });
});
```

### IResultCursor — Two Consumption Patterns

The cursor returned by `tx.RunAsync()` / `session.RunAsync()` is a **forward-only async stream**. There are two ways to consume it:

**Pattern 1: `ToListAsync()` — collect all records eagerly**

```csharp
var cursor = await tx.RunAsync("MATCH (p:Person) RETURN p.name AS name");

// Collect all records at once — simplest for moderate result sets
var records = await cursor.ToListAsync();
// or with projection:
var names = await cursor.ToListAsync(r => r.Get<string>("name"));
```

**Pattern 2: `FetchAsync()` loop — lazy streaming one record at a time**

```csharp
var cursor = await tx.RunAsync("MATCH (p:Person) RETURN p.name AS name");

var names = new List<string>();
while (await cursor.FetchAsync())          // returns true while records remain
{
    names.Add(cursor.Current.Get<string>("name"));   // cursor.Current holds the current row
}
// After the loop, cursor.Current is the LAST record read — do not use it
```

**Critical rules for the `FetchAsync` loop:**

```csharp
// ❌ Wrong — cursor.Current after loop ends is undefined (last record, not null)
while (await cursor.FetchAsync()) { }
var lastRecord = cursor.Current;   // the last row, not an end-of-stream sentinel

// ❌ Wrong — calling FetchAsync() again after it returned false
bool hasMore = await cursor.FetchAsync();   // false
await cursor.FetchAsync();                  // throws InvalidOperationException

// ✅ Correct — only use cursor.Current inside the loop body
while (await cursor.FetchAsync())
{
    var name = cursor.Current.Get<string>("name");   // safe
    Process(name);
}
// cursor.Current is not touched after the loop
```

**Never iterate a cursor outside the transaction callback.** The cursor is tied to the open transaction; after the callback returns the transaction closes:

```csharp
// ❌ WRONG — returns cursor; transaction closes immediately after callback returns
var cursor = await session.ExecuteReadAsync(async tx =>
{
    return await tx.RunAsync("MATCH (p:Person) RETURN p.name AS name");
    // tx disposed here; cursor is now invalid
});
await cursor.FetchAsync();   // throws TransactionTerminatedException or similar

// ✅ CORRECT — consume fully inside the callback
var names = await session.ExecuteReadAsync(async tx =>
{
    var cursor = await tx.RunAsync("MATCH (p:Person) RETURN p.name AS name");
    return await cursor.ToListAsync(r => r.Get<string>("name"));
});
```

### `ConsumeAsync()` — Getting the Summary from a Cursor

`ConsumeAsync()` discards any remaining records and returns the `IResultSummary` for the query — including write counters. It is the only way to access counters (`NodesCreated`, `RelationshipsCreated`, etc.) when using session-based transactions rather than `ExecutableQuery`.

```csharp
// Getting counters from a write inside ExecuteWriteAsync:
var summary = await session.ExecuteWriteAsync(async tx =>
{
    var cursor = await tx.RunAsync(
        "CREATE (p:Person {name: $name})",
        new { name = "Alice" });
    return await cursor.ConsumeAsync();   // ← drains cursor, returns IResultSummary
});

Console.WriteLine($"Created {summary.Counters.NodesCreated} nodes");

// ConsumeAsync() after a FetchAsync loop to get the summary:
var cursor = await tx.RunAsync("MATCH (p:Person) RETURN p.name AS name");
while (await cursor.FetchAsync())
{
    Process(cursor.Current.Get<string>("name"));
}
var summary2 = await cursor.ConsumeAsync();   // get summary after manual iteration

// ⚠ Once ConsumeAsync() is called, the cursor is exhausted.
// Any further call to FetchAsync() throws InvalidOperationException.
// ConsumeAsync() on a partially consumed cursor discards remaining records — 
// this is safe but those records are gone.
```

**Comparison of cursor consumption methods:**

| Method | Records returned | Summary returned | Use when |
|--------|-----------------|-----------------|----------|
| `ToListAsync()` | ✅ all | ❌ no | Need records, not summary |
| `ToListAsync(mapper)` | ✅ mapped | ❌ no | Need mapped records |
| `FetchAsync()` loop | ✅ one at a time | ❌ no (until ConsumeAsync) | Large results, lazy streaming |
| `ConsumeAsync()` | ❌ discards rest | ✅ yes | Need counters/summary |
| `SingleAsync()` | ✅ exactly one | ❌ no | Expect exactly one row |

### Retry Safety

The callback **may execute more than once** on transient failures. Keep callbacks idempotent.

There is also a critical async pattern distinction for write callbacks that return no value:

```csharp
// ❌ Wrong — 'async' with no 'await' inside discards the RunAsync Task.
// The compiler emits CS1998 warning. The driver sees the callback complete immediately
// and may commit before the query's network round-trip has finished.
await session.ExecuteWriteAsync(async tx =>
    tx.RunAsync("MERGE (p:Person {name: $name})", new { name = "Alice" }));

// ✅ Correct — no 'async' keyword; return the Task directly so the driver awaits it
await session.ExecuteWriteAsync(tx =>
    tx.RunAsync("MERGE (p:Person {name: $name})", new { name = "Alice" }));

// ✅ Also correct — 'async' with explicit 'await' inside
await session.ExecuteWriteAsync(async tx =>
{
    await tx.RunAsync("MERGE (p:Person {name: $name})", new { name = "Alice" });
});

// ✅ When the callback returns a value, always use async + await:
var names = await session.ExecuteReadAsync(async tx =>
{
    var cursor = await tx.RunAsync("MATCH (p:Person) RETURN p.name AS name");
    return await cursor.ToListAsync(r => r.Get<string>("name"));   // must await
});
```

**Rule**: for `void` callbacks (no return value), prefer `tx => tx.RunAsync(...)` without `async`. For callbacks that return data, use `async tx => { var cursor = await tx.RunAsync(...); return await cursor.ToListAsync(...); }`.

```csharp
// ❌ Side effect fires on every retry — and the RunAsync is also unawaited
await session.ExecuteWriteAsync(async tx =>
{
    await httpClient.PostAsync("https://api.example.com/notify", null);  // retried!
    await tx.RunAsync("MERGE (p:Person {name: $name})", new { name = "Alice" });
});

// ✅ Database work only; side effects moved outside
await session.ExecuteWriteAsync(tx =>
    tx.RunAsync("MERGE (p:Person {name: $name})", new { name = "Alice" }));
await httpClient.PostAsync("https://api.example.com/notify", null);
```
```

### TransactionConfig — Timeouts and Metadata

```csharp
await session.ExecuteReadAsync(
    async tx =>
    {
        var cursor = await tx.RunAsync("MATCH (p:Person) RETURN p.name AS name");
        return await cursor.ToListAsync(r => r.Get<string>("name"));
    },
    conf => conf
        .WithTimeout(TimeSpan.FromSeconds(5))
        .WithMetadata(new Dictionary<string, object> { { "app", "myService" } })
);
```

---

## 6. Explicit Transactions

Use when a transaction must span multiple methods or coordinate with external systems. **Not automatically retried.**

```csharp
await using var session = driver.AsyncSession(conf => conf.WithDatabase("neo4j"));
await using var tx = await session.BeginTransactionAsync();
try
{
    await DoPartA(tx);
    await DoPartB(tx);
    await tx.CommitAsync();
}
catch
{
    await tx.RollbackAsync();   // can itself throw — see below
    throw;
}

static async Task DoPartA(IAsyncTransaction tx)
{
    await tx.RunAsync("CREATE (p:Person {name: $name})", new { name = "Alice" });
}
```

### Rollback Can Throw

`RollbackAsync()` is a network call. If the server is unreachable, it throws. Use `try/catch` around it to avoid hiding the original exception:

```csharp
catch (Exception original)
{
    try { await tx.RollbackAsync(); }
    catch (Exception rollbackEx)
    {
        // Log rollback failure but let original exception propagate
        logger.LogError(rollbackEx, "Rollback failed");
    }
    throw;
}
```

### Commit Uncertainty

If `CommitAsync()` throws a network-level exception, the commit may or may not have succeeded. Design writes to be idempotent using `MERGE` and unique constraints.

---

## 7. Session Configuration

```csharp
await using var session = driver.AsyncSession(conf => conf
    .WithDatabase("neo4j")                         // always specify
    .WithDefaultAccessMode(AccessMode.Read)        // manual routing hint
    .WithAuthToken(AuthTokens.Basic("user", "pw")) // per-session auth (multi-tenant)
    .WithImpersonatedUser("jane")                  // impersonate without password
    .WithFetchSize(500));                          // batch size for streaming (default 1000)
```

### CancellationToken — Propagate It Everywhere

Every async driver method accepts an optional `CancellationToken`. In web applications, always pass the token from the request context so that abandoned requests (client disconnected, timeout) cancel in-flight database queries and release connections back to the pool promptly.

```csharp
// ASP.NET Core controller — HttpContext.RequestAborted is cancelled when client disconnects
[HttpGet("people")]
public async Task<IActionResult> GetPeople(CancellationToken cancellationToken)
{
    // ExecutableQuery: pass token as last argument to ExecuteAsync
    var result = await driver
        .ExecutableQuery("MATCH (p:Person) RETURN p.name AS name")
        .WithConfig(new QueryConfig(database: "neo4j"))
        .ExecuteAsync(cancellationToken);   // ← propagate here

    return Ok(result.Result.Select(r => r.Get<string>("name")));
}

// Session-based: pass token to RunAsync, FetchAsync, CommitAsync, etc.
public async Task<List<string>> GetNamesAsync(CancellationToken cancellationToken)
{
    await using var session = driver.AsyncSession(conf => conf.WithDatabase("neo4j"));

    return await session.ExecuteReadAsync(async tx =>
    {
        var cursor = await tx.RunAsync(
            "MATCH (p:Person) RETURN p.name AS name",
            cancellationToken: cancellationToken);      // ← RunAsync accepts the token
        return await cursor.ToListAsync(
            r => r.Get<string>("name"), cancellationToken);
    }, cancellationToken: cancellationToken);           // ← ExecuteReadAsync accepts it too
}

// Explicit transaction: propagate to every async call
await using var tx = await session.BeginTransactionAsync(cancellationToken);
await tx.RunAsync("CREATE (p:Person {name: $name})", new { name }, cancellationToken);
await tx.CommitAsync(cancellationToken);
```

**What happens without `CancellationToken`**: the query keeps running on the server side even after the HTTP response has been sent or the client has disconnected. Under load, this leads to connection pool exhaustion and cascading failures. Always propagate the token end-to-end.

---

## 8. Record Value Access

### Two Equivalent Access Patterns

```csharp
// Pattern 1: indexer + .As<T>() extension
string name = record["name"].As<string>();
int    age  = record["age"].As<int>();

// Pattern 2: .Get<T>() typed extension method (cleaner, preferred)
string name = record.Get<string>("name");
int    age  = record.Get<int>("age");

// By index (0-based):
string name = record[0].As<string>();
```

Both patterns throw `KeyNotFoundException` if the key was never projected. Use `.Keys` to inspect what was returned.

### `.As<T>()` Throws on Null — Use Nullable Types

When a property is `null` in the graph (e.g. from `OPTIONAL MATCH` or an absent node property), calling `.As<int>()` or `.As<string>()` on a null value **throws `InvalidCastException`**. Use nullable types for any value that may be absent:

```csharp
// Query: OPTIONAL MATCH (p)-[:LIVES_IN]->(c:City) RETURN p.name AS name, c.name AS city

// ❌ Throws InvalidCastException when city is null
string city = record["city"].As<string>();

// ✅ Nullable reference type — returns null safely
string? city = record["city"].As<string?>();

// ✅ Nullable value types too
int? age = record["age"].As<int?>();

// ✅ Manual null check via object
var raw = record["city"];
string city = raw == null ? "Unknown" : raw.As<string>();

// ✅ Idiomatic: TryGetValue for properties that may not exist on a node
if (node.Properties.TryGetValue("born", out var born))
{
    int birthYear = born.As<int>();
}
```

**Rule**: any field that can be `null` in the graph must use a nullable type (`string?`, `int?`) in the `.As<T>()` call.

### Absent Key vs Graph Null

```csharp
// Absent key (typo or not in RETURN clause) — throws KeyNotFoundException
record["typo"];         // ❌ throws
record.Get<string>("typo");  // ❌ throws

// Check before accessing:
if (record.Keys.Contains("city"))
{
    var city = record.Get<string?>("city");   // may still be null from graph
}
```

---

## 9. Data Types and Mapping

### Cypher → .NET Type Mapping

| Cypher type | .NET type (default) | Safe `.As<T>()` targets |
|-------------|--------------------|-----------------------|
| `Integer` | `long` | `long`, `int`, `long?`, `int?` |
| `Float` | `double` | `double`, `float`, `double?` |
| `String` | `string` | `string`, `string?` |
| `Boolean` | `bool` | `bool`, `bool?` |
| `List` | `IReadOnlyList<object>` | `IReadOnlyList<T>` |
| `Map` | `IReadOnlyDictionary<string,object>` | `IReadOnlyDictionary<string,object>` |
| `Node` | `INode` | `INode` |
| `Relationship` | `IRelationship` | `IRelationship` |
| `Path` | `IPath` | `IPath` |
| `Date` | `LocalDate` | `LocalDate`, `DateOnly` |
| `DateTime` | `ZonedDateTime` | `ZonedDateTime`, `DateTimeOffset` |
| `LocalDateTime` | `LocalDateTime` | `LocalDateTime`, `DateTime` |
| `Time` | `OffsetTime` | `OffsetTime` |
| `LocalTime` | `LocalTime` | `LocalTime`, `TimeOnly` |
| `Duration` | `Duration` | `Duration`, `TimeSpan` |
| `null` | `null` | use nullable types |

### Graph Types

```csharp
// Node
var node = record.Get<INode>("p");
var labels     = node.Labels;                        // IReadOnlyList<string>: ["Person"]
var name       = node["name"].As<string>();           // property access
var name2      = node.Properties["name"].As<string>();// same via Properties dict
var elementId  = node.ElementId;                     // stable id within this transaction

// Relationship
var rel = record.Get<IRelationship>("r");
var type       = rel.Type;                            // "KNOWS"
var since      = rel["since"].As<LocalDate>();
var startId    = rel.StartNodeElementId;
var endId      = rel.EndNodeElementId;

// ⚠ ElementId is only stable within one transaction.
// Do not use it to MATCH entities across separate transactions.
```

### Temporal Types

```csharp
// ZonedDateTime → DateTimeOffset (lossy — drops nanoseconds)
var dt  = record.Get<ZonedDateTime>("created_at");
var dto = dt.ToDateTimeOffset();   // precision truncated to milliseconds

// Or cast directly with .As<DateTimeOffset>():
var dto2 = record["created_at"].As<DateTimeOffset>();

// LocalDate → DateOnly (.NET 6+)
var ld    = record.Get<LocalDate>("date_field");
var dateOnly = ld.ToDateOnly();   // or .As<DateOnly>()

// Duration → TimeSpan (only exact if duration has no months/days)
var dur  = record.Get<Duration>("dur_field");
var span = dur.ToTimeSpan();      // throws if duration contains month/day components

// Passing CLR types as parameters — driver converts automatically:
await driver.ExecutableQuery("CREATE (e:Event {at: $ts})")
    .WithParameters(new { ts = DateTimeOffset.UtcNow })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();
```

---

## 10. WithParameters — Anonymous Types and UNWIND

### Anonymous Types

`WithParameters()` accepts an anonymous type, a `Dictionary<string, object>`, or any object with public properties. Anonymous types are concise but have limitations:

```csharp
// ✅ Anonymous type — property names must match $param names exactly
await driver.ExecutableQuery("CREATE (p:Person {name: $name, age: $age})")
    .WithParameters(new { name = "Alice", age = 30 })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();

// ✅ Dictionary — more explicit, less refactoring risk
await driver.ExecutableQuery("CREATE (p:Person {name: $name, age: $age})")
    .WithParameters(new Dictionary<string, object> { { "name", "Alice" }, { "age", 30 } })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();
```

**⚠ Refactoring risk with anonymous types**: if you rename a C# parameter using IDE tooling, the anonymous type property name changes but the Cypher `$param` name doesn't. This compiles fine but throws `ClientException: Expected parameter(s): name` at runtime:

```csharp
// After renaming 'name' → 'personName' with refactoring:
// ❌ Broken — Cypher still uses $name but parameter is now personName
await driver.ExecutableQuery("CREATE (p:Person {name: $name})")
    .WithParameters(new { personName = "Alice" })   // was 'name' before rename
    .ExecuteAsync();
```

### UNWIND Batching — Correct Parameter Shape

For `UNWIND`, pass an array or list of objects. Each element becomes one row. **Custom classes do not serialize automatically** — use anonymous types or `Dictionary<string, object>` for each row:

```csharp
// ❌ Wrong — custom class instances don't serialize through the parameter layer
record Person(string Name, int Age);
var people = new[] { new Person("Alice", 30), new Person("Bob", 25) };
await driver.ExecutableQuery("UNWIND $people AS p MERGE (:Person {name: p.Name})")
    .WithParameters(new { people })   // throws at runtime — can't serialise Person records
    .ExecuteAsync();

// ✅ Correct — array of anonymous types
var people = new object[]
{
    new { name = "Alice", age = 30, city = "London" },
    new { name = "Bob",   age = 25, city = "Paris" },
};

await driver.ExecutableQuery(@"
        UNWIND $people AS person
        MERGE (p:Person {name: person.name})
        SET p.age = person.age
        MERGE (c:City {name: person.city})
        MERGE (p)-[:LIVES_IN]->(c)")
    .WithParameters(new { people })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();

// ✅ Also correct — array of Dictionary<string, object>
var rows = people.Select(p => new Dictionary<string, object>
{
    { "name", p.Name },
    { "age",  p.Age },
    { "city", p.City }
}).ToArray();
```

---

## 11. Object Mapping

The driver supports mapping records directly to C# classes without manual property extraction.

### Automatic Mapping with `AsObject<T>()`

Object mapping requires the preview mapping namespace. Without it the extension methods are not in scope and the code will not compile:

```csharp
// ⚠ This using directive is REQUIRED — without it AsObject<T>() and AsObjectsAsync<T>()
// are not visible, causing CS1061 compile errors.
using Neo4j.Driver.Preview.Mapping;

class Person
{
    public string Name { get; set; }
    public int Age { get; set; }
}

var result = await driver.ExecutableQuery(@"
        MERGE (p:Person {name: $name, age: $age})
        RETURN p.name AS name, p.age AS age")
    .WithParameters(new { name = "Alice", age = 21 })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();

var person = result.Result[0].AsObject<Person>();
// Cypher return key names must match class property names (case-insensitive by default)
// — 'name' maps to Name, 'age' maps to Age
```

### Blueprint Mapping (anonymous types)

```csharp
var person = result.Result[0].AsObjectFromBlueprint(new { name = "", age = 0 });
Console.WriteLine(person.name);  // "Alice"
Console.WriteLine(person.age);   // 21
```

### Lambda Mapping

```csharp
var person = result.Result[0].AsObject(
    (string name, int age) => new { Name = name, Age = age, BirthYear = 2025 - age });
```

### Bulk Mapping with `AsObjectsAsync<T>()`

```csharp
var (results, summary, _) = await driver
    .ExecutableQuery("MATCH (p:Person) RETURN p.name AS name, p.age AS age")
    .WithConfig(new QueryConfig(database: "neo4j"))
    .AsObjectsAsync<Person>();   // maps all records directly
```

---

## 12. Performance

### Always Specify the Database

Omitting the database causes an extra network round-trip on every call:

```csharp
// ExecutableQuery:
.WithConfig(new QueryConfig(database: "neo4j"))

// Session:
driver.AsyncSession(conf => conf.WithDatabase("neo4j"))
```

### Route Reads to Replicas

```csharp
// ExecutableQuery:
.WithConfig(new QueryConfig(database: "neo4j", routing: RoutingControl.Readers))

// Managed transaction — ExecuteReadAsync routes automatically:
await session.ExecuteReadAsync(async tx => { ... });
```

### Batch Writes with UNWIND

```csharp
// ❌ One transaction per record — high overhead
foreach (var item in items)
{
    await driver.ExecutableQuery("CREATE (n:Node {id: $id})")
        .WithParameters(new { id = item.Id })
        .WithConfig(new QueryConfig(database: "neo4j"))
        .ExecuteAsync();
}

// ✅ Single transaction via UNWIND
var rows = items.Select(i => new { id = i.Id, name = i.Name }).ToArray();
await driver.ExecutableQuery(@"
        UNWIND $rows AS row
        MERGE (n:Node {id: row.id})
        SET n.name = row.name")
    .WithParameters(new { rows })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();
```

### Lazy Streaming with FetchAsync

```csharp
// ExecutableQuery is always eager — fine for moderate results
var result = await driver.ExecutableQuery("MATCH (p:Person) RETURN p")
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();

// For large result sets, stream lazily inside ExecuteReadAsync
await using var session = driver.AsyncSession(conf => conf.WithDatabase("neo4j"));
await session.ExecuteReadAsync(async tx =>
{
    var cursor = await tx.RunAsync("MATCH (p:Person) RETURN p.name AS name");
    while (await cursor.FetchAsync())
    {
        ProcessRecord(cursor.Current.Get<string>("name"));
    }
});
```

### Connection Pool Tuning

```csharp
await using var driver = GraphDatabase.Driver(uri, auth, conf => conf
    .WithMaxConnectionPoolSize(50)                          // default: 100
    .WithConnectionAcquisitionTimeout(TimeSpan.FromSeconds(30))
    .WithMaxConnectionLifetime(TimeSpan.FromHours(1))
    .WithConnectionIdleTimeout(TimeSpan.FromMinutes(10)));
```

---

## 13. Causal Consistency & Bookmarks

**Within a single session**, transactions are automatically causally chained.

**Across sessions**, use `ExecutableQuery` (auto-managed) or pass bookmarks explicitly:

```csharp
Bookmarks bookmarksA, bookmarksB;

await using (var sessionA = driver.AsyncSession(conf => conf.WithDatabase("neo4j")))
{
    await sessionA.ExecuteWriteAsync(tx =>
        tx.RunAsync("MERGE (p:Person {name: 'Alice'})"));
    bookmarksA = sessionA.LastBookmarks;
}

await using (var sessionB = driver.AsyncSession(conf => conf.WithDatabase("neo4j")))
{
    await sessionB.ExecuteWriteAsync(tx =>
        tx.RunAsync("MERGE (p:Person {name: 'Bob'})"));
    bookmarksB = sessionB.LastBookmarks;
}

// sessionC waits until both Alice and Bob exist
await using var sessionC = driver.AsyncSession(conf => conf
    .WithDatabase("neo4j")
    .WithBookmarks(bookmarksA, bookmarksB));   // causal dependency

await sessionC.ExecuteWriteAsync(tx =>
    tx.RunAsync(
        "MATCH (a:Person {name:'Alice'}), (b:Person {name:'Bob'}) MERGE (a)-[:KNOWS]->(b)"));
```

---

## 14. Error Handling

```csharp
using Neo4j.Driver;

try
{
    await driver.ExecutableQuery("...")
        .WithConfig(new QueryConfig(database: "neo4j"))
        .ExecuteAsync();
}
catch (AuthenticationException ex)
{
    Console.Error.WriteLine($"Bad credentials: {ex.Message}");
}
catch (ServiceUnavailableException ex)
{
    Console.Error.WriteLine($"Database unreachable: {ex.Message}");
}
catch (ClientException ex) when (ex.Code == "Neo.ClientError.Schema.ConstraintValidationFailed")
{
    // Unique or existence constraint violation — most common app-level error
    // Must be caught specifically; it is a subclass of Neo4jException
    Console.Error.WriteLine($"Constraint violated: {ex.Message}");
}
catch (Neo4jException ex)
{
    // All other server-side errors
    Console.Error.WriteLine($"Neo4j error [{ex.Code}]: {ex.Message}");
}
```

`ClientException` for constraint violations is a subclass of `Neo4jException` — always catch it **before** the generic `Neo4jException` handler or it will be swallowed silently.

GQL status codes (on `ex.GqlStatus`) are stable across server versions and preferable to string-matching `ex.Code` for programmatic branching.

---

## 15. Repository Pattern — Recommended Structure

```csharp
public interface IPersonRepository
{
    Task<IReadOnlyList<Person>> FindByNamePrefixAsync(string prefix);
    Task CreateAsync(Person person);
    Task BulkCreateAsync(IEnumerable<Person> people);
}

public class PersonRepository(IDriver driver, string database = "neo4j")
    : IPersonRepository
{
    public async Task<IReadOnlyList<Person>> FindByNamePrefixAsync(string prefix)
    {
        var result = await driver
            .ExecutableQuery(@"
                MATCH (p:Person)
                WHERE p.name STARTS WITH $prefix
                RETURN p.name AS name, p.age AS age")
            .WithParameters(new { prefix })
            .WithConfig(new QueryConfig(database, RoutingControl.Readers))
            .ExecuteAsync();

        return result.Result
            .Select(r => new Person(r.Get<string>("name"), r.Get<int>("age")))
            .ToList();
    }

    public async Task CreateAsync(Person person)
    {
        await driver
            .ExecutableQuery("CREATE (p:Person {name: $name, age: $age})")
            .WithParameters(new { name = person.Name, age = person.Age })
            .WithConfig(new QueryConfig(database))
            .ExecuteAsync();
    }

    public async Task BulkCreateAsync(IEnumerable<Person> people)
    {
        var rows = people
            .Select(p => new { name = p.Name, age = p.Age })
            .ToArray();

        await driver
            .ExecutableQuery(@"
                UNWIND $rows AS row
                MERGE (p:Person {name: row.name})
                SET p.age = row.age")
            .WithParameters(new { rows })
            .WithConfig(new QueryConfig(database))
            .ExecuteAsync();
    }
}

public record Person(string Name, int Age);
```

---

## 16. Quick Reference: Common Mistakes

| Mistake | Fix |
|---------|-----|
| String-interpolating Cypher | Use `.WithParameters()` always |
| `using var driver = ...` | Use `await using var driver = ...` — `IDriver` is `IAsyncDisposable` |
| `using var session = ...` | Use `await using var session = ...` |
| Registering `IDriver` as Scoped or Transient in DI | Register as Singleton — one driver per application |
| Registering `IAsyncSession` in DI | Never — sessions are per-unit-of-work, not injectable |
| Forgetting `await` on `ExecuteAsync()` | Task silently never runs — always `await` |
| `async tx => tx.RunAsync(...)` without inner `await` | Use `tx => tx.RunAsync(...)` (no `async`) or `async tx => { await tx.RunAsync(...); }` |
| Omitting `database` in `QueryConfig` / `AsyncSession` | Always specify — saves a round-trip every call |
| Not passing `CancellationToken` in web apps | Propagate `HttpContext.RequestAborted` to all async driver calls |
| `.As<string>()` on a null graph value | Use `.As<string?>()` — non-nullable `.As<T>()` throws on null |
| `record["key"]` when key is absent | Throws `KeyNotFoundException` — check `record.Keys.Contains()` first |
| Using `cursor.Current` after `FetchAsync()` loop | Last record, not null — don't use it after the loop |
| Calling `FetchAsync()` after it returned `false` | Throws — only call while it returns `true` |
| Returning cursor from managed tx callback | Consume with `ToListAsync()` or `ConsumeAsync()` inside the callback |
| Need counters from session-based write | Call `await cursor.ConsumeAsync()` to get `IResultSummary` |
| `AsObject<T>()` causes CS1061 compile error | Add `using Neo4j.Driver.Preview.Mapping;` — the extension methods live there |
| Using `ResultAvailableAfter` for total query timing | Use `ResultConsumedAfter` — `ResultAvailableAfter` is time-to-first-byte only |
| Passing custom class instances to `WithParameters` for UNWIND | Use `new object[] { new { name = ..., age = ... } }` — anonymous types |
| Renaming C# params but not Cypher `$params` | Anonymous type properties and Cypher names must match |
| `record["age"].As<int>()` when age might be `null` | Use `record["age"].As<int?>()` |
| `ExecuteWriteAsync` for a read query | Use `ExecuteReadAsync` — routes to replicas |
| Side effects inside managed tx callbacks | Move outside — callback may be retried |
| `MERGE` for guaranteed-new data | Use `CREATE` — `MERGE` costs an extra match round-trip |
| Catching `Neo4jException` before `ClientException` | Catch `ClientException` for constraints first — it's a subclass |
| `Duration.ToTimeSpan()` when duration has months/days | Throws — only safe for pure second/nanosecond durations |