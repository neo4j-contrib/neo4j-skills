# neo4j-driver-dotnet-skill

Official Neo4j .NET Driver v6 — usage guide for C# / .NET applications connecting to Neo4j.

## Topics covered

- **Install** — `Neo4j.Driver` NuGet package, package variants
- **Driver lifecycle** — `IDriver` singleton, `await using`, `VerifyConnectivityAsync`
- **DI registration** — `AddSingleton<IDriver>`, shutdown hook, session-per-unit-of-work
- **API selection** — `ExecutableQuery` vs managed vs explicit transactions decision table
- **ExecutableQuery** — fluent builder, `WithParameters`, `WithConfig`, `WithMap`, `EagerResult` deconstruct
- **Managed transactions** — `ExecuteReadAsync`/`ExecuteWriteAsync`, retry safety, async void trap
- **IResultCursor** — `ToListAsync`, `FetchAsync` loop, `ConsumeAsync`, `SingleAsync`
- **Record access** — `.Get<T>()`, `.As<T>()`, null safety, absent key handling
- **Type mapping** — Cypher → .NET table, temporal types, `ElementId` lifetime
- **UNWIND batching** — anonymous type arrays, `Dictionary<string,object>`
- **Object mapping** — `AsObject<T>`, `AsObjectsAsync<T>`, C# record types (Preview API)
- **Error handling** — exception hierarchy, `ClientException` ordering, rollback safety
- **Common mistakes** — 20+ mistake/fix table

## Version / compatibility

Driver v6, .NET 8/9/10. Docs: https://neo4j.com/docs/dotnet-manual/current/

## Not covered

- Cypher query authoring → `neo4j-cypher-skill`
- Driver version upgrades → `neo4j-migration-skill`

## Install

```bash
dotnet add package Neo4j.Driver
```
