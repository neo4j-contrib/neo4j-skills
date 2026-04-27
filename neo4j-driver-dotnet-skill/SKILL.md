---
name: neo4j-driver-dotnet-skill
description: >
  Use when writing C# or .NET code that connects to Neo4j: installing Neo4j.Driver,
  configuring GraphDatabase.Driver(), ExecutableQuery(), async patterns, session and
  transaction management, or result handling. Does NOT handle Cypher query authoring
  — use neo4j-cypher-skill. Does NOT handle driver version upgrades — use
  neo4j-migration-skill.
status: draft
version: 0.1.0
allowed-tools: Bash, WebFetch
---

# Neo4j .NET Driver Skill

> **Status: Draft / WIP** — Content is a placeholder. Reference files to be added.

## When to Use

- Setting up the Neo4j .NET driver (`dotnet add package Neo4j.Driver`)
- Writing `GraphDatabase.Driver()` singleton and `ExecutableQuery()` patterns
- Async patterns (`ExecuteQueryAsync`, `IAsyncSession`)
- Session and transaction management in C# applications
- Dependency injection setup (ASP.NET Core)

## When NOT to Use

- **Cypher query authoring** → use `neo4j-cypher-skill`
- **Driver version upgrades** → use `neo4j-migration-skill`

---

## Setup

```bash
dotnet add package Neo4j.Driver
```

---

## Core Patterns

### Driver singleton

```csharp
using Neo4j.Driver;

await using var driver = GraphDatabase.Driver(
    Environment.GetEnvironmentVariable("NEO4J_URI"),
    AuthTokens.Basic(
        Environment.GetEnvironmentVariable("NEO4J_USERNAME"),
        Environment.GetEnvironmentVariable("NEO4J_PASSWORD")
    )
);
await driver.VerifyConnectivityAsync();
```

### ExecutableQuery (recommended)

```csharp
var result = await driver.ExecutableQuery(
    "MATCH (p:Person {name: $name})-[:KNOWS]->(f) RETURN f.name AS friend")
    .WithParameters(new { name = "Alice" })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();

foreach (var record in result.Result)
    Console.WriteLine(record["friend"].As<string>());
```

### Session + write transaction

```csharp
await using var session = driver.AsyncSession(o => o.WithDatabase("neo4j"));
await session.ExecuteWriteAsync(async tx =>
{
    await tx.RunAsync(
        "MERGE (p:Person {id: $id}) SET p.name = $name",
        new { id = "1", name = "Alice" }
    );
});
```

### Dependency injection (ASP.NET Core)

```csharp
// Program.cs
builder.Services.AddSingleton<IDriver>(sp =>
    GraphDatabase.Driver(
        builder.Configuration["NEO4J_URI"],
        AuthTokens.Basic(
            builder.Configuration["NEO4J_USERNAME"],
            builder.Configuration["NEO4J_PASSWORD"]
        )
    )
);
```

---

## Checklist

- [ ] Driver registered as singleton in DI container
- [ ] `await using` (or explicit `DisposeAsync`) for driver and sessions
- [ ] Credentials from environment / configuration, not hardcoded
- [ ] `ExecuteWriteAsync` used for write operations (not `RunAsync` directly on session)
- [ ] Database specified explicitly in `QueryConfig` or `AsyncSessionConfig`

---

## Fetching Current Docs

```
https://neo4j.com/docs/llms.txt     ← full documentation index
https://neo4j.com/llms-full.txt     ← rich reference with code examples
```

## References

- [.NET Driver Manual](https://neo4j.com/docs/dotnet-manual/)
- [GraphAcademy: Building Neo4j Applications with .NET](https://graphacademy.neo4j.com/courses/app-dotnet/)
