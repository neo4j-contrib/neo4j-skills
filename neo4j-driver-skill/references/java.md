# Java driver (`org.neo4j.driver:neo4j-java-driver`)

Maven: `org.neo4j.driver:neo4j-java-driver`. JDK 17+ for driver 6.x.

## Canonical example

```java
import org.neo4j.driver.AuthTokens;
import org.neo4j.driver.Driver;
import org.neo4j.driver.EagerResult;
import org.neo4j.driver.GraphDatabase;
import org.neo4j.driver.QueryConfig;
import org.neo4j.driver.RoutingControl;
import org.neo4j.driver.SessionConfig;
import java.util.Map;

try (Driver driver = GraphDatabase.driver(
        "neo4j://localhost:7687",
        AuthTokens.basic("neo4j", "password"))) {

    driver.verifyConnectivity();

    EagerResult result = driver.executableQuery(
            "MATCH (p:Person {name: $name}) RETURN p.name AS name, p.age AS age")
        .withParameters(Map.of("name", "Alice"))
        .withConfig(QueryConfig.builder()
            .withDatabase("neo4j")
            .withRouting(RoutingControl.READ)
            .build())
        .execute();

    result.records().forEach(r -> {
        Map<String, Object> row = r.asMap();   // plain Map
    });
}
```

`EagerResult` exposes `records()`, `summary()`, `keys()`.

## Accessing fields

- `record.get("name").asString()` / `.asInt()` / `.asLong()` / `.asDouble()` / `.asBoolean()` / `.asList()` / `.asMap()`
- `record.asMap()` — whole record as `Map<String,Object>` (values unwrapped to Java types)
- `record.keys()` — list of column names

## Bulk writes

```java
var rows = List.of(
    Map.of("id", 1, "name", "Alice"),
    Map.of("id", 2, "name", "Bob"));

driver.executableQuery(
        "UNWIND $rows AS row MERGE (p:Person {id: row.id}) SET p += row")
    .withParameters(Map.of("rows", rows))
    .withConfig(QueryConfig.builder().withDatabase("neo4j").build())
    .execute();
```

## When to drop to a session

```java
try (var session = driver.session(SessionConfig.forDatabase("neo4j"))) {
    session.executeWrite(tx -> {
        var balance = tx.run(
            "MATCH (a:Account {id:$id}) RETURN a.balance AS b",
            Map.of("id", fromId)
        ).single().get("b").asLong();
        if (balance < amount) throw new RuntimeException("insufficient funds");
        tx.run("MATCH (a:Account {id:$id}) SET a.balance = a.balance - $amt",
               Map.of("id", fromId, "amt", amount));
        tx.run("MATCH (a:Account {id:$id}) SET a.balance = a.balance + $amt",
               Map.of("id", toId,   "amt", amount));
        return null;
    });
}
```

Transaction lambdas must be idempotent — the driver retries on transient failures.

## Reactive / async

- Async: `driver.executableQuery(...).executeAsync()` returns `CompletionStage<EagerResult>`.
- Reactive: `driver.session(ReactiveSession.class)` for back-pressured streaming.
