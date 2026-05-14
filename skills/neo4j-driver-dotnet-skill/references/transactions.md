# Explicit Transactions, TransactionConfig, and Causal Consistency

## Explicit Transactions (`BeginTransactionAsync`)

Use when a transaction must span multiple methods or coordinate with external systems. Not automatically retried.

```csharp
await using var session = driver.AsyncSession(conf => conf.WithDatabase("neo4j"));
await using var tx = await session.BeginTransactionAsync();
try
{
    await DoPartA(tx);
    await DoPartB(tx);
    await tx.CommitAsync();
}
catch (Exception original)
{
    try { await tx.RollbackAsync(); }
    catch (Exception rollbackEx)
    {
        logger.LogError(rollbackEx, "Rollback failed");
    }
    throw;
}

static async Task DoPartA(IAsyncTransaction tx)
{
    await tx.RunAsync("CREATE (p:Person {name: $name})", new { name = "Alice" });
}
```

`RollbackAsync()` is a network call — it can throw. Isolate it with its own `try/catch` to avoid hiding the original exception.

If `CommitAsync()` throws a network-level exception, the commit may or may not have succeeded — design writes as idempotent using `MERGE` + unique constraints.

---

## TransactionConfig — Timeouts and Metadata

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

Metadata appears in `SHOW TRANSACTIONS` — useful for tracing slow queries.

---

## Session Configuration Options

```csharp
await using var session = driver.AsyncSession(conf => conf
    .WithDatabase("neo4j")
    .WithDefaultAccessMode(AccessMode.Read)        // manual routing hint
    .WithAuthToken(AuthTokens.Basic("user", "pw")) // per-session auth (multi-tenant)
    .WithImpersonatedUser("jane")                  // impersonate without password
    .WithFetchSize(500));                          // batch size for streaming (default 1000)
```

---

## Causal Consistency — Cross-Session Bookmarks

Within a single session, transactions are automatically causally chained. Across sessions, use `ExecutableQuery` (auto-managed bookmarks) or pass bookmarks explicitly:

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

// sessionC waits until both Alice and Bob are visible
await using var sessionC = driver.AsyncSession(conf => conf
    .WithDatabase("neo4j")
    .WithBookmarks(bookmarksA, bookmarksB));

await sessionC.ExecuteWriteAsync(tx =>
    tx.RunAsync(
        "MATCH (a:Person {name:'Alice'}), (b:Person {name:'Bob'}) MERGE (a)-[:KNOWS]->(b)"));
```
