# Async & Reactive API — Neo4j Java Driver

## Async API (`driver.asyncSession()`)

Non-blocking via `CompletableFuture` / `CompletionStage`. Every method returns `CompletionStage` instead of blocking.

### Session lifecycle — close in both paths

Most common mistake: leaking sessions on error.

```java
import org.neo4j.driver.async.AsyncSession;
import org.neo4j.driver.async.ResultCursor;

CompletableFuture<List<String>> getNames(Driver driver) {
    AsyncSession session = driver.asyncSession(
        SessionConfig.builder().withDatabase("neo4j").build());

    return session
        .executeReadAsync(tx ->
            tx.runAsync("MATCH (p:Person) RETURN p.name AS name")
              .thenCompose(ResultCursor::listAsync)
              .thenApply(records -> records.stream()
                  .map(r -> r.get("name").asString())
                  .toList())
        )
        // close on success
        .thenCompose(names -> session.closeAsync().thenApply(v -> names))
        // close on failure — use exceptionallyCompose (Java 12+) for async close
        .exceptionallyCompose(e ->
            session.closeAsync().thenApply(v -> { throw new RuntimeException(e); })
        )
        .toCompletableFuture();
}
```

`exceptionallyCompose` (Java 12+): use when recovery step is itself async. `exceptionally` does not wait for `closeAsync()` to complete.

### Reading records

```java
// listAsync — collect everything into List<Record>
cursor.listAsync(r -> new Person(r.get("name").asString(), r.get("age").asInt()))

// forEachAsync — process one at a time without building List
cursor.forEachAsync(r -> System.out.println(r.get("name").asString()))
```

### Async write

```java
CompletionStage<Void> createPerson(Driver driver, String name) {
    AsyncSession session = driver.asyncSession(
        SessionConfig.builder().withDatabase("neo4j").build());

    return session
        .executeWriteAsync(tx ->
            tx.runAsync("CREATE (p:Person {name: $name})", Map.of("name", name))
              .thenCompose(ResultCursor::consumeAsync)
        )
        .thenCompose(summary -> session.closeAsync())
        .exceptionallyCompose(e ->
            session.closeAsync().thenApply(v -> { throw new RuntimeException(e); })
        );
}
```

### Never block inside async callback

```java
// ❌ Deadlock risk
session.executeReadAsync(tx ->
    tx.runAsync(query)
      .thenApply(cursor -> cursor.listAsync().toCompletableFuture().join()) // blocks!
);

// ✅ Chain with thenCompose
session.executeReadAsync(tx ->
    tx.runAsync(query).thenCompose(ResultCursor::listAsync)
);
```

---

## Reactive API (`driver.rxSession()`)

Project Reactor / RxJava backpressure-aware streaming. Use only when downstream consumer is itself reactive.

```java
import org.neo4j.driver.reactive.RxSession;
import reactor.core.publisher.Flux;

Flux<String> getNames(Driver driver) {
    return Flux.usingWhen(
        // acquire
        Mono.fromSupplier(() -> driver.rxSession(
            SessionConfig.builder().withDatabase("neo4j").build())),
        // use
        session -> Flux.from(session.executeRead(tx ->
            Flux.from(tx.run("MATCH (p:Person) RETURN p.name AS name"))
                .flatMap(result -> Flux.from(result.records()))
                .map(r -> r.get("name").asString())
        )),
        // close on success
        RxSession::close,
        // close on error
        (session, err) -> session.close(),
        // close on cancel
        RxSession::close
    );
}
```

Key rules:
- `Flux.usingWhen` ensures session closes in all paths (success / error / cancel).
- Never subscribe inside a reactive chain — let the framework subscribe.
- Reactive is only worth the complexity when the consumer is reactive (e.g. Spring WebFlux). For Spring MVC or synchronous code, use the sync or async API.
