---
name: neo4j-driver-java-skill
description: >
  Comprehensive guide to using the official Neo4j Java Driver (v6, current stable) — covering
  installation (Maven/Gradle), driver lifecycle, all three transaction APIs (executableQuery,
  managed transactions via executeRead/Write, explicit transactions), async/reactive patterns,
  error handling, data type mapping, performance tuning, causal consistency/bookmarks, and
  connection configuration. Use this skill whenever writing Java code that talks to Neo4j,
  whenever reviewing or debugging Neo4j driver usage in Java, or whenever questions arise about
  sessions, transactions, bookmarks, result handling, driver configuration, or Spring integration.
  Also triggers on neo4j-java-driver, GraphDatabase.driver, executableQuery, SessionConfig,
  executeRead, executeWrite, TransactionCallback, or any Neo4j Bolt/Aura connection work in Java.
  
  Does NOT handle Cypher query authoring — use
  neo4j-cypher-skill. Does NOT handle driver version upgrades — use neo4j-migration-skill.
status: draft
version: 0.1.1
allowed-tools: Bash, WebFetch
---

# Neo4j Java Driver

**Maven group**: `org.neo4j.driver:neo4j-java-driver`  
**Current stable**: v6  
**Docs**: https://neo4j.com/docs/java-manual/current/  
**API ref**: https://neo4j.com/docs/api/java-driver/current/

---

## 1. Installation

### Maven (`pom.xml`)

```xml
<dependency>
    <groupId>org.neo4j.driver</groupId>
    <artifactId>neo4j-java-driver</artifactId>
    <version>6.0.5</version>
</dependency>
```

### Gradle (`build.gradle`)

```groovy
implementation 'org.neo4j.driver:neo4j-java-driver:6.0.5'
```

Check [Maven Central](https://central.sonatype.com/artifact/org.neo4j.driver/neo4j-java-driver) for the latest version.

---

## 2. Driver Lifecycle

`Driver` is **thread-safe, immutable, and expensive to create** — create exactly one instance per application, share it everywhere, and close it on shutdown.

```java
import org.neo4j.driver.AuthTokens;
import org.neo4j.driver.Driver;
import org.neo4j.driver.GraphDatabase;

public class Neo4jConfig {

    public static Driver createDriver(String uri, String user, String password) {
        // URI examples:
        //   "neo4j://localhost"           — unencrypted, cluster routing
        //   "neo4j+s://xxx.databases.neo4j.io"  — TLS, cluster routing (Aura)
        //   "bolt://localhost:7687"        — unencrypted, single instance
        //   "bolt+s://localhost:7687"      — TLS, single instance
        var driver = GraphDatabase.driver(uri, AuthTokens.basic(user, password));
        driver.verifyConnectivity();   // fail fast if unreachable
        return driver;
    }
}

// In try-with-resources (preferred for short-lived use):
try (var driver = GraphDatabase.driver(uri, AuthTokens.basic(user, password))) {
    driver.verifyConnectivity();
    // ... do work ...
}

// Or close explicitly (long-lived singleton):
driver.close();
```

### Auth Options

```java
AuthTokens.basic(user, password)         // username + password
AuthTokens.bearer(token)                 // SSO / JWT
AuthTokens.kerberos(base64Ticket)        // Kerberos
AuthTokens.none()                        // unauthenticated (dev only)
```

---

## 3. Choosing the Right API

| API | When to use | Auto-retry? | Streaming? |
|-----|-------------|-------------|------------|
| `driver.executableQuery()` | Most queries — simple, safe default | ✅ | ❌ (eager) |
| `session.executeRead/Write()` | Large results, complex callback logic | ✅ | ✅ |
| `session.beginTransaction()` | Multi-function work, external coordination | ❌ | ✅ |
| `driver.asyncSession()` | Non-blocking I/O with `CompletableFuture` | ✅ | ✅ |
| Reactive (`RxSession`) | Project Reactor / RxJava backpressure | ✅ | ✅ |

---

## 4. `executableQuery` — Recommended Default

The highest-level API. Manages sessions, transactions, retries, and bookmarks automatically.

```java
import java.util.Map;
import java.util.concurrent.TimeUnit;
import org.neo4j.driver.QueryConfig;
import org.neo4j.driver.RoutingControl;

// Read query — route to replicas
var result = driver.executableQuery("""
        MATCH (p:Person {name: $name})-[:KNOWS]->(friend)
        RETURN friend.name AS name
        """)
    .withParameters(Map.of("name", "Alice"))
    .withConfig(QueryConfig.builder()
        .withDatabase("neo4j")           // always specify — avoids a round-trip
        .withRouting(RoutingControl.READ) // route reads to replicas
        .build())
    .execute();

// Access records
result.records().forEach(r -> System.out.println(r.get("name").asString()));

// Query summary / counters
var summary = result.summary();
System.out.printf("Returned %d records in %d ms%n",
    result.records().size(),
    summary.resultAvailableAfter(TimeUnit.MILLISECONDS));

// Write query
var writeResult = driver.executableQuery("""
        CREATE (p:Person {name: $name, age: $age})
        RETURN p
        """)
    .withParameters(Map.of("name", "Bob", "age", 30))
    .withConfig(QueryConfig.builder().withDatabase("neo4j").build())
    .execute();

System.out.printf("Created %d nodes%n",
    writeResult.summary().counters().nodesCreated());
```

**⚠ Never string-interpolate Cypher.** Always use `.withParameters()` with a `Map` — prevents injection and enables query plan caching.

---

## 5. Managed Transactions (`executeRead` / `executeWrite`)

Use when you need lazy result streaming (large data sets) or more control within the transaction callback.

```java
import org.neo4j.driver.Session;
import org.neo4j.driver.SessionConfig;

// Sessions are NOT thread-safe — create one per request/thread and close promptly
try (var session = driver.session(SessionConfig.builder()
        .withDatabase("neo4j")   // always specify
        .build())) {

    // Read — routes to replicas automatically
    var names = session.executeRead(tx -> {
        var result = tx.run("""
                MATCH (p:Person)
                WHERE p.name STARTS WITH $prefix
                RETURN p.name AS name
                """,
            Map.of("prefix", "Al"));

        // ✅ Collect INSIDE the callback — Result is invalid after the tx closes
        return result.stream()
            .map(r -> r.get("name").asString())
            .toList();
    });

    // Write — routes to leader
    session.executeWriteWithoutResult(tx ->
        tx.run("CREATE (p:Person {name: $name})", Map.of("name", "Carol"))
    );
}
```

### Critical: Result Lifecycle in Callbacks

`Result` is a **lazy cursor tied to the open transaction**. The transaction closes the moment the callback returns. Any attempt to read a `Result` after that throws `ResultConsumedException`.

```java
// ❌ WRONG — returns a Result, which is already closed by the time the caller uses it
var result = session.executeRead(tx ->
    tx.run("MATCH (p:Person) RETURN p.name AS name")
    // Result returned here; transaction immediately closes
);
result.stream().forEach(...); // throws ResultConsumedException at runtime

// ✅ CORRECT — collect to a List inside the callback
var names = session.executeRead(tx -> {
    var result = tx.run("MATCH (p:Person) RETURN p.name AS name");
    return result.stream()
        .map(r -> r.get("name").asString())
        .toList();                              // fully consumed before callback exits
});
```

### Multiple `tx.run()` Calls in One Callback

When running several queries in sequence, each `Result` must also be consumed before the next `tx.run()` or before the callback returns:

```java
var summary = session.executeWrite(tx -> {
    // First run — consume it before the second run
    var people = tx.run("MATCH (p:Person) RETURN p.name AS name")
        .stream()
        .map(r -> r.get("name").asString())
        .toList();  // consumed ✅

    // Second run using first result
    for (var name : people) {
        tx.run("MERGE (p:Person {name: $name})-[:VISITED]->(c:City {name: $city})",
            Map.of("name", name, "city", "London"));
        // No return value needed — tx.run() result auto-consumed when ignored
    }

    return people.size();
});
```

When you call `tx.run()` and don't assign the result, the cursor is discarded and the statement is still sent — this is fine for fire-and-forget writes. But if you need to inspect the result, always assign and consume it.

### Retry Safety

The callback **may execute more than once** if the server returns a transient error. Design callbacks to be idempotent:

```java
// ❌ Dangerous — counter incremented on every retry attempt
int[] count = {0};
session.executeWriteWithoutResult(tx -> {
    count[0]++;  // could be 1, 2, 3... depending on retries
    tx.run("CREATE (p:Person {name: $name})", Map.of("name", "Alice"));
});

// ✅ Safe — MERGE is idempotent; no external state touched
session.executeWriteWithoutResult(tx ->
    tx.run("MERGE (p:Person {name: $name})", Map.of("name", "Alice"))
);
```

**Key rules for transaction callbacks:**
- **Never return a `Result` object** — collect to `List`, `Map`, or a domain object before the callback exits.
- **Consume each `Result` before calling `tx.run()` again** — multiple open cursors on a single transaction is undefined behaviour in most server configurations.
- **No side effects** (HTTP calls, emails, metric increments) inside the callback — it may be retried.
- `executeRead` → replica routing; `executeWrite` → leader routing.

### TransactionConfig — Timeouts & Metadata

```java
import org.neo4j.driver.TransactionConfig;
import java.time.Duration;

var config = TransactionConfig.builder()
    .withTimeout(Duration.ofSeconds(5))
    .withMetadata(Map.of("app", "myService", "user", userId))
    .build();

session.executeRead(tx -> { /* ... */ }, config);
session.executeWrite(tx -> { /* ... */ }, config);
```

Metadata appears in `SHOW TRANSACTIONS` and server query logs — great for observability.

---

## 6. Explicit Transactions

Use when transaction work spans multiple methods or requires coordination with external systems. **Not automatically retried.**

```java
try (var session = driver.session(SessionConfig.builder().withDatabase("neo4j").build())) {
    var tx = session.beginTransaction();
    try {
        doPartA(tx);
        doPartB(tx);
        tx.commit();
    } catch (Exception e) {
        // Rollback — but rollback itself can throw (e.g. network failure).
        // Suppress the rollback exception so the original exception propagates cleanly.
        try {
            tx.rollback();
        } catch (Exception rollbackEx) {
            e.addSuppressed(rollbackEx);   // visible in the stack trace but doesn't hide e
        }
        throw e;
    }
}

private static void doPartA(Transaction tx) {
    tx.run("CREATE (p:Person {name: $name})", Map.of("name", "Alice"));
}
```

### Rollback Can Throw

`tx.rollback()` is a network call. If the connection is broken or the server is unavailable, it throws. **Never** let a rollback exception silently swallow the original error:

```java
// ❌ Swallows the real exception if rollback also throws
} catch (Exception e) {
    tx.rollback();   // throws → e is lost
    throw e;
}

// ✅ Use addSuppressed so both exceptions are visible
} catch (Exception e) {
    try { tx.rollback(); } catch (Exception rb) { e.addSuppressed(rb); }
    throw e;
}
```

### Commit Uncertainty

If `tx.commit()` throws a network-level exception (e.g. `ServiceUnavailableException`), the commit may or may not have succeeded on the server — the driver cannot know. This is the "commit uncertainty" problem:

```java
try {
    tx.commit();
} catch (ServiceUnavailableException e) {
    // The transaction may have committed or not.
    // Do NOT retry blindly — you could create duplicate data.
    // Options:
    //   1. Make the operation idempotent (MERGE, not CREATE) so a retry is safe.
    //   2. Query afterward to check whether the data now exists.
    //   3. Accept the uncertainty and surface an appropriate error to the caller.
    throw new DataAccessException("Commit uncertain — check database state", e);
}
```

**The safest mitigation**: design writes to be idempotent using `MERGE` and unique constraints, so that retrying an uncertain commit is always safe.

### When to Use Explicit vs Managed Transactions

```
Need automatic retry?          → Use executeRead / executeWrite
Work spans multiple methods?   → Explicit transaction (pass tx as parameter)
Coordinating with external I/O → Explicit transaction (commit only after I/O succeeds)
```

Prefer `executeRead/Write` unless you specifically need explicit boundary control.

---

## 7. Session Configuration

```java
import org.neo4j.driver.AccessMode;

// Read-only session (manual routing hint)
var session = driver.session(SessionConfig.builder()
    .withDatabase("neo4j")
    .withDefaultAccessMode(AccessMode.READ)
    .build());

// Per-session auth (cheaper than a new Driver for multi-tenant apps)
var session = driver.session(SessionConfig.builder()
    .withDatabase("neo4j")
    .withAuthToken(AuthTokens.basic("tenant-user", "pass"))
    .build());

// User impersonation (no password needed; executing user must have privilege)
var session = driver.session(SessionConfig.builder()
    .withDatabase("neo4j")
    .withImpersonatedUser("jane")
    .build());
```

**Sessions are short-lived and NOT thread-safe** — open inside a try-with-resources or close explicitly. Never share a session between threads.

---

## 8. Async API

For non-blocking execution using `CompletableFuture` / `CompletionStage`. The async API mirrors the sync API (`executeReadAsync`, `executeWriteAsync`, `beginTransactionAsync`) but every method returns a `CompletionStage` rather than blocking.

### Correct Session Lifecycle — Close in Both Paths

The most common async mistake is leaking sessions when an error occurs. Always chain `closeAsync()` in both the success and error paths:

```java
import org.neo4j.driver.async.AsyncSession;
import org.neo4j.driver.async.ResultCursor;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;

CompletableFuture<List<String>> getNames(Driver driver) {
    AsyncSession session = driver.asyncSession(
        SessionConfig.builder().withDatabase("neo4j").build());

    return session
        .executeReadAsync(tx ->
            tx.runAsync("MATCH (p:Person) RETURN p.name AS name")
              .thenCompose(ResultCursor::listAsync)           // collect all records
              .thenApply(records -> records.stream()
                  .map(r -> r.get("name").asString())
                  .toList())
        )
        // ✅ Close session after success — thenCompose chains the close
        .thenCompose(names -> session.closeAsync().thenApply(v -> names))
        // ✅ Close session after failure — handle re-throws after closing
        .exceptionallyCompose(e ->
            session.closeAsync().thenApply(v -> { throw new RuntimeException(e); })
        )
        .toCompletableFuture();
}
```

**`exceptionally` vs `exceptionallyCompose`**: Use `exceptionallyCompose` (Java 12+) when the recovery step is itself async (like `closeAsync()`). If you use `exceptionally`, the session close may not complete before the exception propagates.

### Reading Results — `listAsync` vs `forEachAsync`

```java
session.executeReadAsync(tx ->
    tx.runAsync("MATCH (p:Person) RETURN p.name AS name, p.age AS age")
      .thenCompose(cursor ->
          // listAsync — collect everything into a List<Record>
          cursor.listAsync(r -> new Person(
              r.get("name").asString(),
              r.get("age").asInt()
          ))
      )
)
```

```java
// forEachAsync — process records one at a time without building a List
session.executeReadAsync(tx ->
    tx.runAsync("MATCH (p:Person) RETURN p.name AS name")
      .thenCompose(cursor -> cursor.forEachAsync(
          r -> System.out.println(r.get("name").asString())
      ))
)
```

### Async Write

```java
CompletionStage<Void> createPerson(Driver driver, String name) {
    AsyncSession session = driver.asyncSession(
        SessionConfig.builder().withDatabase("neo4j").build());

    return session
        .executeWriteAsync(tx ->
            tx.runAsync("CREATE (p:Person {name: $name})", Map.of("name", name))
              .thenCompose(ResultCursor::consumeAsync)   // discard results, get summary
        )
        .thenCompose(summary -> session.closeAsync())
        .exceptionallyCompose(e ->
            session.closeAsync().thenApply(v -> { throw new RuntimeException(e); })
        );
}
```

### ⚠ Do Not Mix Blocking and Async Code

Never call `.toCompletableFuture().get()` or `join()` on an async chain from within another async callback — this blocks a thread that the driver's async machinery may need, causing deadlock under load.

```java
// ❌ Deadlock risk — blocking inside an async callback
session.executeReadAsync(tx ->
    tx.runAsync(query)
      .thenApply(cursor -> cursor.listAsync().toCompletableFuture().join()) // blocks!
);

// ✅ Chain with thenCompose instead
session.executeReadAsync(tx ->
    tx.runAsync(query).thenCompose(ResultCursor::listAsync)
);
```

---

## 9. Error Handling

```java
import org.neo4j.driver.exceptions.Neo4jException;
import org.neo4j.driver.exceptions.ServiceUnavailableException;
import org.neo4j.driver.exceptions.SessionExpiredException;
import org.neo4j.driver.exceptions.TransientException;

try {
    driver.executableQuery("...").execute();
} catch (ServiceUnavailableException e) {
    // No servers available — check connection
    log.error("Database unavailable", e);
} catch (SessionExpiredException e) {
    // Session was closed by server; open a new one
    log.error("Session expired", e);
} catch (TransientException e) {
    // Transient failure — managed transactions retry automatically,
    // but you must retry explicit transactions yourself
    log.warn("Transient error: {}", e.code(), e);
} catch (Neo4jException e) {
    // Server-side Cypher or constraint error; e.code() gives GQL status
    log.error("Neo4j error [{}]: {}", e.code(), e.getMessage());
}
```

**Managed transactions** (`executeRead/Write`) automatically retry on transient errors — no catch needed. Explicit transactions require your own retry logic.

---

## 10. Data Types & Value Extraction

Cypher values come back as `Value` objects. Use typed accessors to extract them safely.

| Cypher type | Java type / accessor |
|-------------|---------------------|
| `Integer` | `value.asLong()` / `value.asInt()` |
| `Float` | `value.asDouble()` |
| `String` | `value.asString()` |
| `Boolean` | `value.asBoolean()` |
| `List` | `value.asList()` |
| `Map` | `value.asMap()` |
| `Node` | `value.asNode()` |
| `Relationship` | `value.asRelationship()` |
| `Path` | `value.asPath()` |
| `Date` | `value.asLocalDate()` |
| `DateTime` | `value.asZonedDateTime()` |
| `null` | `value.isNull()` → `true` |

```java
// From a record
var record = result.records().get(0);
String name   = record.get("name").asString();
long age      = record.get("age").asLong();
boolean alive = record.get("alive").asBoolean();

// Node access
var node = record.get("p").asNode();
String personName = node.get("name").asString();
Iterable<String> labels = node.labels();    // e.g. ["Person"]
Map<String,Object> props = node.asMap();

// Relationship
var rel = record.get("r").asRelationship();
String type = rel.type();
```

### Null Safety — Absent Key vs Graph Null

These are **two distinct situations** that the driver handles differently. Confusing them is a common source of runtime errors.

**Absent key** — the column was never projected by the `RETURN` clause (or a typo in the key name):

```java
// Query: RETURN p.name AS name
var record = result.records().get(0);

// ❌ record.get("nme")  — typo; key is absent
Value v = record.get("nme");   // returns Value.NULL — does NOT throw
v.asString();                  // ← throws NoSuchElementException (absent key)

// ✅ Check key existence first
if (record.containsKey("nme")) { ... }  // false for absent key

// ✅ Or use the index-based accessor which throws clearly:
record.get("nme");  // always check containsKey for optional columns
```

**Graph null** — the key is projected but the property or optional match returned `null` from the database:

```java
// Query: MATCH (p:Person) OPTIONAL MATCH (p)-[:LIVES_IN]->(c:City)
//        RETURN p.name AS name, c.name AS city
var record = result.records().get(0);

Value cityValue = record.get("city");   // key EXISTS; value may be null
cityValue.isNull();                     // true when no City was matched

// ❌ This throws even though the key exists:
String city = cityValue.asString();     // throws Uncoercible if value is null

// ✅ Null-safe with a default:
String city = cityValue.asString("Unknown");  // returns "Unknown" when null

// ✅ Or check first:
String city = cityValue.isNull() ? null : cityValue.asString();
```

**Summary table:**

| Situation | `record.get(key)` returns | `.asString()` behaviour |
|-----------|--------------------------|------------------------|
| Key present, value non-null | the value | returns the string |
| Key present, value is graph null | `Value` where `.isNull()` is `true` | **throws** `Uncoercible` |
| Key absent (typo / not projected) | `Value.NULL` sentinel | **throws** `NoSuchElementException` |

The safe pattern for optional data:

```java
// Check key presence AND null in one shot:
String city = record.containsKey("city") && !record.get("city").isNull()
    ? record.get("city").asString()
    : "Unknown";

// Or rely on the default overload (handles graph null but NOT absent key):
String city = record.get("city").asString("Unknown");  // only safe if key is always projected
```

---

## 11. Performance

### Always Specify the Database

Omitting the database name causes a round-trip to resolve the home database on every call.

```java
// executableQuery:
.withConfig(QueryConfig.builder().withDatabase("neo4j").build())

// Session:
SessionConfig.builder().withDatabase("neo4j").build()
```

### Route Reads to Replicas

```java
// executableQuery:
.withConfig(QueryConfig.builder()
    .withDatabase("neo4j")
    .withRouting(RoutingControl.READ)
    .build())

// Managed transaction:
session.executeRead(tx -> { /* automatically routes to replica */ });
```

### Batch Writes with `UNWIND`

`UNWIND` expects a `List<Map<String, Object>>` as the parameter — each map becomes one row in the Cypher loop. This is the shape the driver serialises correctly over Bolt.

```java
// Build the parameter list — each element is a Map matching your Cypher variable
record PersonData(String name, int age, String city) {}

List<PersonData> people = List.of(
    new PersonData("Alice", 30, "London"),
    new PersonData("Bob",   25, "Paris")
);

// Convert to List<Map<String, Object>> — the required shape for UNWIND
List<Map<String, Object>> rows = people.stream()
    .map(p -> Map.<String, Object>of(
        "name", p.name(),
        "age",  p.age(),
        "city", p.city()
    ))
    .toList();

// ❌ Wrong — passing a List<PersonData> directly; Bolt can't serialise custom objects
driver.executableQuery("UNWIND $items AS item MERGE (p:Person {name: item.name})")
    .withParameters(Map.of("items", people))   // ← fails at runtime
    .execute();

// ✅ Correct — List of plain Maps
driver.executableQuery("""
        UNWIND $items AS item
        MERGE (p:Person {name: item.name})
        SET p.age = item.age
        MERGE (c:City {name: item.city})
        MERGE (p)-[:LIVES_IN]->(c)
        """)
    .withParameters(Map.of("items", rows))     // ← List<Map<String,Object>>
    .withConfig(QueryConfig.builder().withDatabase("neo4j").build())
    .execute();
```

**Allowed parameter value types** (the leaves of the Map structure):

| Java type | Cypher type |
|-----------|-------------|
| `String` | String |
| `Long` / `Integer` / `Short` / `Byte` | Integer |
| `Double` / `Float` | Float |
| `Boolean` | Boolean |
| `List<?>` (of the above) | List |
| `Map<String, ?>` (of the above) | Map |
| `null` | null |

Custom objects, enums, and dates must be converted to one of the above before being put in the parameter map. Passing anything else (e.g. a `LocalDate` directly) throws `ClientException: Unable to convert` at runtime.

### Group Multiple Queries in One Transaction

```java
// Bad: one transaction per query (high overhead)
for (int i = 0; i < 1000; i++) {
    session.executeWrite(tx -> tx.run("<QUERY>", params));
}

// Good: all in one transaction callback
session.executeWriteWithoutResult(tx -> {
    for (int i = 0; i < 1000; i++) {
        tx.run("<QUERY>", params);
    }
});
```

### `CREATE` vs `MERGE`

Use `CREATE` when the data is guaranteed new — `MERGE` issues an internal match before creating, adding overhead.

### Connection Pool vs Session Limits — Two Distinct Failure Modes

The driver has **two separate resource pools**. They fail differently and are tuned separately.

**Connection pool** — physical TCP connections to Neo4j. Controlled by `Config`:

```java
var driver = GraphDatabase.driver(uri, auth,
    Config.builder()
        .withMaxConnectionPoolSize(50)                          // default: 100
        .withConnectionAcquisitionTimeout(30, TimeUnit.SECONDS) // wait for a free connection
        .withMaxConnectionLifetime(1, TimeUnit.HOURS)
        .withConnectionLivenessCheckTimeout(30, TimeUnit.MINUTES)
        .build());
```

When the pool is exhausted and a new connection is needed, the driver waits up to `connectionAcquisitionTimeout` then throws `ClientException: Unable to acquire connection from the pool within configured maximum time`. This means your application is creating more concurrent sessions than connections available — either increase the pool size or reduce concurrency.

**Session limit** — sessions are logical (not a separate pool), but each open session holds a connection for the duration of a transaction. The practical limit on concurrent sessions is therefore `maxConnectionPoolSize`.

```java
// This pattern silently starves the pool under concurrency:
// ❌ Opening many sessions and not closing them promptly
List<Session> sessions = new ArrayList<>();
for (int i = 0; i < 200; i++) {
    sessions.add(driver.session(...));  // borrows a connection each time
    // ... never closed → pool exhausted after 100 (default)
}

// ✅ Always use try-with-resources so connections return to the pool immediately
try (var session = driver.session(...)) {
    // connection held only for the duration of this block
}
```

**Diagnosing which pool is exhausted:**

| Error message | Cause | Fix |
|---|---|---|
| `Unable to acquire connection from the pool within configured maximum time` | Connection pool full | Increase `maxConnectionPoolSize` or reduce concurrency |
| `Connection to the database terminated` / `ServiceUnavailableException` | Network/server issue, not pool | Check server health, firewall, TLS |
| Session appears to hang with no error | Session leak — connection never returned | Audit for sessions not closed in all code paths |

The session-level liveness check (`withConnectionLivenessCheckTimeout`) validates idle connections before handing them back to your code — useful for long-lived applications where connections may have been silently dropped by a firewall or load balancer.

---

## 12. Causal Consistency & Bookmarks

**Within a single session**, transactions are automatically causally chained — nothing to do.

**Across sessions** (parallel workers), use `executableQuery` (auto-managed) or pass bookmarks explicitly:

```java
import org.neo4j.driver.Bookmark;

List<Bookmark> bookmarks = new ArrayList<>();

try (var sessionA = driver.session(SessionConfig.builder().withDatabase("neo4j").build())) {
    sessionA.executeWriteWithoutResult(tx -> createPerson(tx, "Alice"));
    bookmarks.addAll(sessionA.lastBookmarks());
}

try (var sessionB = driver.session(SessionConfig.builder().withDatabase("neo4j").build())) {
    sessionB.executeWriteWithoutResult(tx -> createPerson(tx, "Bob"));
    bookmarks.addAll(sessionB.lastBookmarks());
}

// sessionC waits until Alice and Bob both exist
try (var sessionC = driver.session(SessionConfig.builder()
        .withDatabase("neo4j")
        .withBookmarks(bookmarks)  // ← causal dependency
        .build())) {
    sessionC.executeWriteWithoutResult(tx -> connectPeople(tx, "Alice", "Bob"));
}
```

`executableQuery` shares a `BookmarkManager` automatically — use it for most cases and only drop to explicit bookmarks for complex coordination.

---

## 13. Advanced Connection Configuration

```java
import org.neo4j.driver.Config;
import org.neo4j.driver.Logging;
import org.neo4j.driver.net.ServerAddress;
import org.neo4j.driver.NotificationConfig;
import org.neo4j.driver.NotificationSeverity;

var driver = GraphDatabase.driver(uri, auth,
    Config.builder()
        // Custom resolver for local dev against cluster
        .withResolver(address -> Set.of(ServerAddress.of("localhost", 7687)))

        // TLS configuration
        .withEncryption()
        .withTrustStrategy(Config.TrustStrategy.trustAllCertificates()) // dev only!

        // Reduce notification noise
        .withNotificationConfig(NotificationConfig.defaultConfig()
            .enableMinimumSeverity(NotificationSeverity.WARNING))

        // Bolt-level debug logging
        .withLogging(Logging.slf4j())  // or Logging.console(Level.DEBUG)

        // Fetch size (controls record batching from server)
        .withFetchSize(1000)           // default: 1000

        .build());
```

---

## 14. Repository Pattern — Recommended Structure

Wrap the driver behind an interface for testability and clean separation:

```java
public interface PersonRepository {
    List<Person> findByNamePrefix(String prefix);
    void createPerson(String name, int age);
}

public class Neo4jPersonRepository implements PersonRepository {

    private final Driver driver;
    private final String database;

    public Neo4jPersonRepository(Driver driver, String database) {
        this.driver = driver;
        this.database = database;
    }

    @Override
    public List<Person> findByNamePrefix(String prefix) {
        var result = driver.executableQuery("""
                MATCH (p:Person)
                WHERE p.name STARTS WITH $prefix
                RETURN p.name AS name, p.age AS age
                """)
            .withParameters(Map.of("prefix", prefix))
            .withConfig(QueryConfig.builder()
                .withDatabase(database)
                .withRouting(RoutingControl.READ)
                .build())
            .execute();

        return result.records().stream()
            .map(r -> new Person(r.get("name").asString(), r.get("age").asInt()))
            .toList();
    }

    @Override
    public void createPerson(String name, int age) {
        driver.executableQuery("CREATE (p:Person {name: $name, age: $age})")
            .withParameters(Map.of("name", name, "age", age))
            .withConfig(QueryConfig.builder().withDatabase(database).build())
            .execute();
    }
}
```

---

## 16. Quick Reference: Common Mistakes

| Mistake | Fix |
|---------|-----|
| String-interpolating Cypher params | Always use `.withParameters(Map.of(...))` |
| Omitting database name | Set in `QueryConfig` or `SessionConfig` — every time |
| Creating a new `Driver` per request | Create once at startup, close on shutdown |
| Sharing a `Session` across threads | Sessions are single-threaded; use one per request |
| Returning `Result` from a tx callback | Collect to `List`/`Map` before the callback exits |
| Leaving a `Result` open before next `tx.run()` | Consume each result before the next run call |
| Side effects inside managed tx callbacks | Move them outside — the callback may be retried |
| Passing custom objects to UNWIND params | Convert to `List<Map<String,Object>>` first |
| Calling `record.get("key").asString()` on graph null | Use `.asString("default")` or check `.isNull()` first |
| Calling `.asString()` on an absent key | Check `record.containsKey()` before accessing optional columns |
| Naked `tx.rollback()` in a catch block | Wrap in its own try/catch and use `addSuppressed` |
| Assuming `commit()` failure = no commit | Commit uncertainty is real — design writes as idempotent |
| Blocking inside an async callback (`.join()`, `.get()`) | Chain with `thenCompose` instead |
| Not closing async session in error path | Use `exceptionallyCompose` to close before re-throwing |
| One transaction per write in a loop | Batch with `UNWIND` or group in one tx callback |
| Using `MERGE` for guaranteed-new data | Use `CREATE` — `MERGE` costs an extra match round-trip |
| Not closing sessions | Use try-with-resources; leaked sessions exhaust the connection pool |
| Using `executeWrite` for a read | Use `executeRead` — routes to replicas, not the leader |
| Ignoring pool exhaustion errors | Tune `maxConnectionPoolSize` or audit for session leaks |