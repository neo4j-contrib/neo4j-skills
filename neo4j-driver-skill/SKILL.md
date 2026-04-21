---
name: neo4j-driver-skill
description: Use when writing or reviewing code that uses an official Neo4j driver (Python, JavaScript, Java, Go, .NET). Covers the modern execute_query API, parameters, routing, result access, and common pitfalls.
allowed-tools: WebFetch
---

# Neo4j Driver skill

Modern guidance for the five official Neo4j drivers. The APIs have converged on a single high-level entry point (`execute_query` / `executableQuery` / `ExecuteQuery`) that replaces most hand-written session+transaction code.

## When to use

Use this skill when code:
- imports `neo4j` (Python), `neo4j-driver` (JavaScript), `org.neo4j.driver` (Java), `github.com/neo4j/neo4j-go-driver` (Go), or `Neo4j.Driver` (.NET)
- uses `driver.session(...)`, `session.run(...)`, `session.execute_read/write`, or older transaction patterns
- is being written from scratch against Neo4j
- is being reviewed for driver correctness or performance

## Core rules (apply to all languages)

1. **`execute_query` is the default.** One call, one transaction, auto-retry on transient errors. Only drop to `session.execute_read/execute_write` when you need to interleave client-side logic between queries in one transaction.
2. **Self-managing transaction queries need `session.run` (auto-commit).** `CALL {...} IN TRANSACTIONS` and `USING PERIODIC COMMIT` manage their own transactions and fail inside a managed transaction — so neither `execute_query` nor `session.execute_read/write` work. Open a session and run them with `session.run(...)`.
3. **Configure the database name explicitly** (`database_="neo4j"`, `{database:'neo4j'}`, `.withDatabase(...)`, `ExecuteQueryWithDatabase(...)`) unless you specifically want home-database resolution. Otherwise the driver pays an extra round-trip per query to resolve the default.
4. **Always parameterize** with `$name` placeholders. Never string-concatenate values. Parameters enable query-plan caching and prevent Cypher injection.
5. **One driver per application**, shared across threads/requests. The driver owns a connection pool — do not create it per request. Close on shutdown (or use `with` / `try-with-resources` / `using`).
6. **Specify routing on read-only calls** in a cluster (`routing_=RoutingControl.READ`, `routing: neo4j.routing.READ`, `.withRouting(RoutingControl.READ)`, `ExecuteQueryWithReadersRouting()`). It sends reads to follower nodes.
7. **Bulk writes use `UNWIND $rows AS row`** with a list parameter — one round-trip for thousands of rows. Do not loop over `execute_query`.
8. **`execute_query` is eager** — it loads all records into memory. For huge result sets, use a session with `execute_read`/`execute_write` and iterate the `Result` without materializing it.
9. **Prefer `CREATE` over `MERGE`** when you know the data is new. `MERGE` does a match + create; `CREATE` is one step.
10. **Dynamic labels, relationship types, and property keys** — supported natively in Cypher 25 via the `$(expr)` syntax: `MATCH (n:$($label) {$($key): $value})` or `MERGE ()-[:$($type)]->()`. On Cypher 5 a plain parameter can only be a value; for dynamic labels/keys there, validate against an allow-list and interpolate, or call `apoc.merge.node` / `apoc.create.relationship`.

## Reading record fields

Read fields by name — `record["name"]`, `record.get("name")`, `record["name"].As<T>()`, etc. — and only pull what you need.

Each driver also exposes a whole-record map conversion (`record.data()` in Python, `record.toObject()` in JS, `record.asMap()` in Java, `record.AsMap()` in Go, `record.Values` / `record.AsObject()` in .NET). These are convenient for interactive sessions, logging, and quick prototyping, but they materialize every field even when you only need some.

If you actually need JSON, either `RETURN` the exact primitive fields you want (`RETURN n.name, n.age`) or apply a purpose-built transformer.

## Per-language references

Load the reference file for the language in the codebase:

- Python → [python.md](references/python.md)
- JavaScript / TypeScript → [javascript.md](references/javascript.md)
- Java → [java.md](references/java.md)
- Go → [go.md](references/go.md)
- .NET / C# → [dotnet.md](references/dotnet.md)

## Instructions

1. Detect the driver language from the dependency file (`requirements.txt`, `package.json`, `pom.xml`/`build.gradle`, `go.mod`, `*.csproj`).
2. Load the matching reference file above.
3. When writing new code, start from the "Canonical example" in the reference — do not hand-roll sessions unless rule 1 requires it.
4. When reviewing code, flag any of the ten core rules being broken.

## Resources

- [Python Driver Manual](https://neo4j.com/docs/python-manual/current/)
- [JavaScript Driver Manual](https://neo4j.com/docs/javascript-manual/current/)
- [Java Driver Manual](https://neo4j.com/docs/java-manual/current/)
- [Go Driver Manual](https://neo4j.com/docs/go-manual/current/)
- [.NET Driver Manual](https://neo4j.com/docs/dotnet-manual/current/)
- [Supported versions matrix](https://neo4j.com/developer/kb/neo4j-supported-versions/)
