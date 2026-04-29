---
name: neo4j-driver-java-skill
description: Neo4j Java Driver v6 — driver lifecycle, Maven/Gradle setup, executableQuery,
  executeRead/Write managed transactions, explicit transactions, async/reactive patterns,
  error handling, data type mapping, connection pool tuning, causal consistency/bookmarks.
  Use when writing Java or Kotlin code that connects to Neo4j via GraphDatabase.driver,
  executableQuery, SessionConfig, executeRead, executeWrite, or TransactionCallback.
  Does NOT handle Cypher authoring — use neo4j-cypher-skill.
  Does NOT cover driver version upgrades — use neo4j-migration-skill.
  Does NOT cover Spring Data Neo4j (@Node, Neo4jRepository) — use neo4j-spring-data-skill.
version: 1.0.0
allowed-tools: Bash WebFetch
---

## When to Use
- Java/Kotlin code connecting to Neo4j (Aura or self-managed)
- Setting up driver, sessions, transactions in Maven/Gradle projects
- Debugging result handling, error recovery, connection pool issues
- Async (`CompletableFuture`) or reactive (Project Reactor / RxJava) Neo4j access

## When NOT to Use
- **Cypher query authoring/optimization** → `neo4j-cypher-skill`
- **Driver version upgrades** → `neo4j-migration-skill`
- **Spring Data Neo4j** (`@Node`, `@Relationship`, `Neo4jRepository`) → `neo4j-spring-data-skill`

---

## Dependency

### Maven
```xml
<dependency>
    <groupId>org.neo4j.driver</groupId>
    <artifactId>neo4j-java-driver</artifactId>
    <version>6.0.5</version>
</dependency>
```

### Gradle
```groovy
implementation 'org.neo4j.driver:neo4j-java-driver:6.0.5'
```

Check latest: https://central.sonatype.com/artifact/org.neo4j.driver/neo4j-java-driver

---

## Environment Variables

Standard pattern for connection config — never hardcode credentials:

```java
String uri      = System.getenv().getOrDefault("NEO4J_URI",      "neo4j://localhost:7687");
String user     = System.getenv().getOrDefault("NEO4J_USERNAME",  "neo4j");
String password = System.getenv().getOrDefault("NEO4J_PASSWORD",  "");
String database = System.getenv().getOrDefault("NEO4J_DATABASE",  "neo4j");
```

Spring Boot: inject via `@Value("${spring.neo4j.uri}")` or `application.properties`:
```properties
spring.neo4j.uri=neo4j+s://xxx.databases.neo4j.io
spring.neo4j.authentication.username=neo4j
spring.neo4j.authentication.password=secret
```

---

## Driver Lifecycle

One `Driver` per application — thread-safe, expensive to create. Implement `AutoCloseable` or use try-with-resources.

```java
// Long-lived singleton
var driver = GraphDatabase.driver(
    "neo4j+s://xxx.databases.neo4j.io",          // Aura TLS+routing
    AuthTokens.basic(user, password));
driver.verifyConnectivity();                      // fail fast

// Short-lived (tests / CLI)
try (var driver = GraphDatabase.driver(uri, AuthTokens.basic(user, password))) {
    driver.verifyConnectivity();
    // ...
}
```

URI schemes:

| URI | Use |
|---|---|
| `neo4j://localhost` | Unencrypted, cluster routing |
| `neo4j+s://xxx.databases.neo4j.io` | TLS + cluster routing (Aura) |
| `bolt://localhost:7687` | Unencrypted, single instance |
| `bolt+s://localhost:7687` | TLS, single instance |

Auth options: `AuthTokens.basic(u,p)` · `AuthTokens.bearer(token)` · `AuthTokens.kerberos(b64)` · `AuthTokens.none()`

---

## Choosing the Right API

| API | When | Auto-retry | Streaming |
|---|---|:---:|:---:|
| `driver.executableQuery()` | Default for most queries | ✅ | ❌ eager |
| `session.executeRead/Write()` | Large results, callback control | ✅ | ✅ |
| `session.beginTransaction()` | Multi-method, external coordination | ❌ | ✅ |
| `session.run()` | Self-managing queries (`CALL IN TRANSACTIONS`) | ❌ | ✅ |
| `driver.asyncSession()` | Non-blocking `CompletableFuture` | ✅ | ✅ |
| `driver.rxSession()` | Reactor/RxJava backpressure | ✅ | ✅ |

`CALL { … } IN TRANSACTIONS` and `USING PERIODIC COMMIT` self-manage their transaction — use `session.run()` only. `executableQuery` and `executeRead/Write` will fail for these queries.

---

## `executableQuery` — Default

```java
// Read — route to replicas
var result = driver.executableQuery("""
        MATCH (p:Person {name: $name})-[:KNOWS]->(friend)
        RETURN friend.name AS name
        """)
    .withParameters(Map.of("name", "Alice"))
    .withConfig(QueryConfig.builder()
        .withDatabase("neo4j")            // always specify — avoids home-db round-trip
        .withRouting(RoutingControl.READ)
        .build())
    .execute();

result.records().forEach(r -> System.out.println(r.get("name").asString()));
long ms = result.summary().resultAvailableAfter(TimeUnit.MILLISECONDS);

// Write
driver.executableQuery("CREATE (p:Person {name: $name, age: $age})")
    .withParameters(Map.of("name", "Bob", "age", 30))
    .withConfig(QueryConfig.builder().withDatabase("neo4j").build())
    .execute();
```

Never string-interpolate Cypher. Always `.withParameters(Map.of(...))`.

---

## Managed Transactions (`executeRead` / `executeWrite`)

Sessions are NOT thread-safe — one per request/thread, always close.

```java
try (var session = driver.session(SessionConfig.builder()
        .withDatabase("neo4j").build())) {

    // Read → replica routing
    var names = session.executeRead(tx -> {
        var result = tx.run(
            "MATCH (p:Person) WHERE p.name STARTS WITH $prefix RETURN p.name AS name",
            Map.of("prefix", "Al"));
        return result.stream().map(r -> r.get("name").asString()).toList(); // collect INSIDE
    });

    // Write → leader routing
    session.executeWriteWithoutResult(tx ->
        tx.run("CREATE (p:Person {name: $name})", Map.of("name", "Carol"))
    );
}
```

### Result must be consumed INSIDE the callback

`Result` is a lazy cursor tied to the open transaction. Transaction closes when callback returns — any read after that throws `ResultConsumedException`.

```java
// ❌ Returns Result — already closed by the time caller uses it
var result = session.executeRead(tx ->
    tx.run("MATCH (p:Person) RETURN p.name AS name"));
result.stream().forEach(...); // throws ResultConsumedException

// ✅ Collect to List inside callback
var names = session.executeRead(tx ->
    tx.run("MATCH (p:Person) RETURN p.name AS name")
      .stream().map(r -> r.get("name").asString()).toList());
```

### Callback rules

- Consume each `Result` before next `tx.run()` — multiple open cursors = undefined behaviour.
- No side effects (HTTP, email, metric increments) — callback may be retried on transient errors.
- Use `MERGE` (idempotent), not `CREATE`, for retry-safe writes.
- `executeRead` → replica; `executeWrite` → leader.

### TransactionConfig — timeouts & metadata

```java
var config = TransactionConfig.builder()
    .withTimeout(Duration.ofSeconds(5))
    .withMetadata(Map.of("app", "myService", "user", userId))  // visible in SHOW TRANSACTIONS
    .build();
session.executeRead(tx -> { /* ... */ }, config);
```

---

## Explicit Transactions

Use when work spans multiple methods or requires external coordination. Not auto-retried.

```java
try (var session = driver.session(SessionConfig.builder().withDatabase("neo4j").build())) {
    var tx = session.beginTransaction();
    try {
        doPartA(tx);
        doPartB(tx);
        tx.commit();
    } catch (Exception e) {
        try { tx.rollback(); } catch (Exception rb) { e.addSuppressed(rb); }
        throw e;
    }
}
```

`tx.rollback()` is a network call — wrap in its own try/catch and use `addSuppressed` so the original exception is not lost.

**Commit uncertainty**: if `tx.commit()` throws `ServiceUnavailableException`, the commit may or may not have succeeded. Design writes as idempotent (`MERGE` + unique constraints) so retrying is safe.

Choose explicit vs managed:
- Auto-retry needed → `executeRead` / `executeWrite`
- Work spans multiple methods → explicit (pass `tx` as parameter)
- Coordinating with external I/O → explicit (commit only after I/O succeeds)

---

## Error Handling

```java
try {
    driver.executableQuery("...").execute();
} catch (ServiceUnavailableException e) {
    // No servers — check connection
} catch (SessionExpiredException e) {
    // Server closed session — open new one
} catch (TransientException e) {
    // Managed txns retry automatically; explicit txns need manual retry
} catch (Neo4jException e) {
    // Cypher/constraint error — e.code() gives GQL status code
}
```

Managed transactions auto-retry `TransientException` — no catch needed.

---

## Data Types & Value Extraction

| Cypher type | Java accessor |
|---|---|
| `Integer` | `value.asLong()` / `value.asInt()` |
| `Float` | `value.asDouble()` |
| `String` | `value.asString()` |
| `Boolean` | `value.asBoolean()` |
| `List` | `value.asList()` |
| `Map` | `value.asMap()` |
| `Node` | `value.asNode()` |
| `Relationship` | `value.asRelationship()` |
| `Date` | `value.asLocalDate()` |
| `DateTime` | `value.asZonedDateTime()` |

```java
var record = result.records().get(0);
String name = record.get("name").asString();
long age    = record.get("age").asLong();

var node = record.get("p").asNode();
String label = node.labels().iterator().next();
Map<String,Object> props = node.asMap();
```

### Null safety — two distinct cases

| Situation | `record.get(key)` | `.asString()` |
|---|---|---|
| Key present, value non-null | the value | returns string |
| Key present, value is graph null | `Value` where `.isNull()` = true | **throws** `Uncoercible` |
| Key absent (typo / not projected) | `Value.NULL` sentinel | **throws** `NoSuchElementException` |

```java
// Graph null — use default overload (safe only if key is always projected):
String city = record.get("city").asString("Unknown");

// Absent key — check containsKey first:
if (record.containsKey("city") && !record.get("city").isNull()) {
    String city = record.get("city").asString();
}
```

---

## Object Mapping

Map query results to Java records/classes directly — eliminates manual accessor calls.

```java
// Domain record — field names match RETURN aliases (case-sensitive)
public record Person(String name, long age) {}

// Map single record
var person = driver.executableQuery("MATCH (p:Person {name: $name}) RETURN p.name AS name, p.age AS age")
    .withParameters(Map.of("name", "Alice"))
    .withConfig(QueryConfig.builder().withDatabase("neo4j").build())
    .execute()
    .records()
    .stream()
    .map(r -> r.get("name").asString())   // or: r.as(Person.class) — see note
    .findFirst()
    .orElseThrow();

// Using .as(Person.class) — maps RETURN keys to record fields by name
var person2 = driver.executableQuery("""
        MATCH (p:Person {name: $name})
        RETURN p.name AS name, p.age AS age
        """)
    .withParameters(Map.of("name", "Tom Hanks"))
    .withConfig(QueryConfig.builder().withDatabase("neo4j").build())
    .execute()
    .records()
    .stream()
    .map(record -> record.get("p").as(Person.class))
    .findFirst()
    .orElseThrow(() -> new RuntimeException("Person not found"));
```

Nested mapping — return a map projection and include `COLLECT {}` for lists:

```java
public record Movie(String title, List<Person> actors) {}

var movieCypher = """
    MATCH (movie:Movie)
    LIMIT 1
    RETURN movie {
        .title,
        actors: COLLECT {
            MATCH (actor:Person)-[:ACTED_IN]->(movie)
            RETURN actor
        }
    }
    """;

var movie = driver.executableQuery(movieCypher)
    .withConfig(QueryConfig.builder().withDatabase("neo4j").build())
    .execute()
    .records()
    .stream()
    .map(r -> r.get("movie").as(Movie.class))
    .findFirst()
    .orElseThrow();
```

Only mapped properties defined in the record are populated — extra properties returned by Cypher are ignored.

---

## Performance Patterns

**Always specify database** — omitting triggers home-db round-trip on every call.

**Route reads to replicas** — `RoutingControl.READ` in `QueryConfig` or use `executeRead`.

**Batch writes with `UNWIND`** — pass `List<Map<String,Object>>` (plain maps only; custom objects fail):

```java
List<Map<String, Object>> rows = people.stream()
    .map(p -> Map.<String, Object>of("name", p.name(), "age", p.age()))
    .toList();

driver.executableQuery("UNWIND $items AS item MERGE (p:Person {name: item.name}) SET p.age = item.age")
    .withParameters(Map.of("items", rows))
    .withConfig(QueryConfig.builder().withDatabase("neo4j").build())
    .execute();
```

Allowed leaf types in parameter maps: `String`, `Long`/`Integer`/`Short`/`Byte`, `Double`/`Float`, `Boolean`, `List<?>`, `Map<String,?>`, `null`. Custom objects and `LocalDate` must be converted first.

**Group writes in one transaction** — one `executeWrite` with a loop, not one `executeWrite` per iteration.

**Connection pool** — default 100 connections. Tune if exhausted:
```java
Config.builder()
    .withMaxConnectionPoolSize(50)
    .withConnectionAcquisitionTimeout(30, TimeUnit.SECONDS)
    .build()
```

---

## Common Errors

| Mistake | Fix |
|---|---|
| String-interpolate Cypher params | `.withParameters(Map.of(...))` always |
| Omit database name | Set in `QueryConfig` / `SessionConfig` every time |
| New `Driver` per request | Create once at startup; share everywhere |
| Share `Session` across threads | One session per request/thread |
| Return `Result` from tx callback | Collect to `List`/`Map` inside callback |
| Leave `Result` open before next `tx.run()` | Consume before next call |
| Side effects in managed tx callback | Move outside — callback may retry |
| Pass custom objects to UNWIND params | Convert to `List<Map<String,Object>>` |
| `asString()` on graph null | `.asString("default")` or check `.isNull()` |
| `asString()` on absent key | `containsKey()` before optional access |
| Naked `tx.rollback()` in catch | Wrap in try/catch; use `addSuppressed` |
| Assume `commit()` failure = no commit | Commit uncertainty — design writes idempotent |
| Block inside async callback (`.join()`) | Chain with `thenCompose` |
| Skip session close in async error path | `exceptionallyCompose` to close then re-throw |
| One transaction per write in loop | Batch with `UNWIND` or group in one callback |
| `executeWrite` for a read | Use `executeRead` — routes to replica |

---

## References

Load on demand:
- [references/async-reactive.md](references/async-reactive.md) — full async `CompletableFuture` patterns, reactive `RxSession` with `Flux.usingWhen`, deadlock avoidance
- [references/advanced-config.md](references/advanced-config.md) — full `Config.builder()` options, TLS, notification filtering, session-level auth, user impersonation, cross-session bookmarks, spatial types (Values.point/WGS-84/Cartesian)

Docs:
- Java Driver manual: https://neo4j.com/docs/java-manual/current/
- API reference: https://neo4j.com/docs/api/java-driver/current/

---

## Checklist
- [ ] One `Driver` instance created at startup; closed on shutdown
- [ ] `verifyConnectivity()` called after driver creation
- [ ] Database name specified in every `QueryConfig` / `SessionConfig`
- [ ] Parameters used (never string-interpolated Cypher)
- [ ] `Result` consumed inside managed transaction callback
- [ ] No side effects inside `executeRead/Write` callbacks
- [ ] Sessions closed via try-with-resources
- [ ] Async sessions closed in both success and error paths (`exceptionallyCompose`)
- [ ] `ServiceUnavailableException` on commit handled as commit-uncertain
- [ ] `UNWIND` params are `List<Map<String,Object>>` (no custom objects)
- [ ] `containsKey()` checked before accessing optional result columns
