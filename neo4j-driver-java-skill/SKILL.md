---
name: neo4j-driver-java-skill
description: >
  Use when writing Java code that connects to Neo4j using the raw Java driver
  (org.neo4j.driver:neo4j-java-driver): GraphDatabase.driver(), executableQuery(),
  session and transaction management, reactive streams, or result handling.
  Does NOT handle Spring Data Neo4j (@Node, @Relationship, Neo4jRepository) —
  use neo4j-spring-data-skill. Does NOT handle Cypher query authoring — use
  neo4j-cypher-skill. Does NOT handle driver version upgrades — use neo4j-migration-skill.
status: draft
version: 0.1.0
allowed-tools: Bash, WebFetch
---

# Neo4j Java Driver Skill

> **Status: Draft / WIP** — Content is a placeholder. Reference files to be added.

## When to Use

- Setting up the raw Neo4j Java driver in Maven or Gradle
- Writing `GraphDatabase.driver()` singleton and `executableQuery()` patterns
- Session and transaction management (explicit, managed)
- Reactive driver usage (Project Reactor / RxJava)
- Error handling (`ServiceUnavailable`, `AuthenticationException`, `ConstraintException`)

## When NOT to Use

- **Spring Data Neo4j (@Node, @Relationship, Neo4jRepository)** → use `neo4j-spring-data-skill`
- **Cypher query authoring** → use `neo4j-cypher-skill`
- **Driver version upgrades** → use `neo4j-migration-skill`

---

## Setup

**Maven:**
```xml
<dependency>
    <groupId>org.neo4j.driver</groupId>
    <artifactId>neo4j-java-driver</artifactId>
    <version>5.x.x</version>  <!-- check Maven Central for latest -->
</dependency>
```

**Gradle:**
```groovy
implementation 'org.neo4j.driver:neo4j-java-driver:5.x.x'
```

---

## Core Patterns

### Driver singleton

```java
import org.neo4j.driver.*;
import static org.neo4j.driver.Values.parameters;

// singleton -- create once at application startup
Driver driver = GraphDatabase.driver(
    System.getenv("NEO4J_URI"),
    AuthTokens.basic(
        System.getenv("NEO4J_USERNAME"),
        System.getenv("NEO4J_PASSWORD")
    )
);
driver.verifyConnectivity();

// close on shutdown:
driver.close();
```

### executableQuery (recommended for simple queries)

```java
var result = driver.executableQuery(
        "MATCH (p:Person {name: $name})-[:KNOWS]->(f) RETURN f.name AS friend")
    .withParameters(Map.of("name", "Alice"))
    .withConfig(QueryConfig.builder().withDatabase("neo4j").build())
    .execute();

result.records().forEach(r -> System.out.println(r.get("friend").asString()));
```

### Session + write transaction

```java
try (var session = driver.session(SessionConfig.forDatabase("neo4j"))) {
    session.executeWrite(tx -> {
        tx.run("MERGE (p:Person {id: $id}) SET p.name = $name",
               Map.of("id", "1", "name", "Alice"));
        return null;
    });
}
```

### Error handling and result access

```java
import org.neo4j.driver.exceptions.*;

try {
    var result = driver.executableQuery("MATCH (p:Person {id: $id}) RETURN p")
                       .withParameters(Map.of("id", "1")).execute();

    // Always check before accessing — empty result throws on .get()
    if (!result.records().isEmpty()) {
        var record = result.records().get(0);
        System.out.println(record.get("p").asNode().get("name").asString());
    }
} catch (AuthenticationException e) {
    // wrong credentials
} catch (ServiceUnavailableException e) {
    // database unreachable
} catch (ConstraintException e) {
    // unique constraint violated
}
```

---

## Checklist

- [ ] One driver instance per application (singleton), closed on shutdown
- [ ] Credentials loaded from env vars, never hardcoded
- [ ] `try-with-resources` used for sessions
- [ ] `executeWrite` / `executeRead` used (not `session.run` directly)
- [ ] `executableQuery` used for simple single-query operations
- [ ] Database name specified explicitly (avoids default DB ambiguity)

---

## Fetching Current Docs

```
https://neo4j.com/docs/llms.txt     ← full documentation index
https://neo4j.com/llms-full.txt     ← rich reference with code examples
```

## References

- [Java Driver Manual](https://neo4j.com/docs/java-manual/)
- [GraphAcademy: Using Neo4j with Java](https://graphacademy.neo4j.com/courses/drivers-java/)
- [GraphAcademy: Building Neo4j Applications with Java](https://graphacademy.neo4j.com/courses/app-java/)
