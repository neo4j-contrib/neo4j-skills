> **Status: Draft / WIP**

# neo4j-driver-dotnet-skill

Comprehensive guide to using the official Neo4j .NET Driver (v6, current stable) — covering
installation, IDriver lifecycle and DI registration, all three query APIs (ExecutableQuery
fluent API, managed transactions via ExecuteReadAsync/ExecuteWriteAsync, auto-commit via
RunAsync), IResultCursor consumption patterns (FetchAsync loop vs ToListAsync), record value
access and null safety, WithParameters anonymous types and UNWIND batching, temporal type
mapping, await-using vs using, EagerResult unpacking, object mapping, performance, causal
consistency, and error handling.

**Install:**
```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-driver-dotnet-skill
```

Or paste this link into your coding assistant:
https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-driver-dotnet-skill
