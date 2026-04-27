---
name: neo4j-spring-data-skill
description: >
  Use when building Spring Boot applications with Neo4j using Spring Data Neo4j (SDN):
  @Node entity mapping, @Relationship, Neo4jRepository, ReactiveNeo4jRepository,
  @Query annotations, application.yml configuration, projections, or Neo4j-OGM.
  Also covers Spring AI Neo4jVectorStore integration.
  Does NOT handle raw Java driver code (no Spring) — use neo4j-driver-java-skill.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT handle driver version upgrades — use neo4j-migration-skill.
status: draft
version: 0.1.0
allowed-tools: Bash, WebFetch
---

# Neo4j Spring Data Skill

> **Status: Draft / WIP** — Content is a placeholder. Reference files to be added.

## When to Use

- Configuring Spring Boot with Neo4j (`spring-boot-starter-data-neo4j`)
- Writing `@Node` entity classes and `@Relationship` mappings
- Defining `Neo4jRepository` / `ReactiveNeo4jRepository` interfaces
- Writing `@Query` annotations with Cypher on repository methods
- Using Spring projections (interface-based or DTO-based) with Neo4j
- Configuring `application.yml` for Neo4j connection
- Spring AI `Neo4jVectorStore` for vector search in Spring apps

## When NOT to Use

- **Raw Java driver without Spring** → use `neo4j-driver-java-skill`
- **Cypher query authoring** → use `neo4j-cypher-skill`
- **Driver version upgrades** → use `neo4j-migration-skill`

---

## Setup

**pom.xml:**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-neo4j</artifactId>
</dependency>
```

**application.yml:**
```yaml
spring:
  neo4j:
    uri: ${NEO4J_URI:neo4j+s://host.databases.neo4j.io}
    authentication:
      username: ${NEO4J_USERNAME:neo4j}
      password: ${NEO4J_PASSWORD}
  data:
    neo4j:
      database: ${NEO4J_DATABASE:neo4j}
```

---

## Core Patterns

### Entity mapping

```java
import org.springframework.data.neo4j.core.schema.*;

@Node("Person")
public class Person {
    @Id @GeneratedValue private Long id;
    private String name;
    private String email;

    @Relationship(type = "KNOWS", direction = Relationship.Direction.OUTGOING)
    private List<Person> friends = new ArrayList<>();
}
```

### Repository

> **Security**: `@Query` annotations MUST use `$parameter` placeholders — never string-concatenate user input into Cypher. Spring Data does not sanitize string interpolation; concatenation is a Cypher injection hole.

```java
import org.springframework.data.neo4j.repository.Neo4jRepository;

public interface PersonRepository extends Neo4jRepository<Person, Long> {
    Optional<Person> findByName(String name);

    // CORRECT: $name is a bound parameter
    @Query("MATCH (p:Person {name: $name})-[:KNOWS]->(f) RETURN f")
    List<Person> findFriendsOf(String name);

    // WRONG: never do this
    // @Query("MATCH (p:Person {name: '" + name + "'}) RETURN p")  // injection risk
}
```

### Reactive repository

```java
import org.springframework.data.neo4j.repository.ReactiveNeo4jRepository;
import reactor.core.publisher.Flux;

public interface PersonRepository extends ReactiveNeo4jRepository<Person, Long> {
    @Query("MATCH (p:Person {name: $name})-[:KNOWS]->(f) RETURN f")
    Flux<Person> findFriendsOf(String name);
}
```

---

## Checklist

- [ ] `@Node` uses a specific label string (not just `@Node` with default class name)
- [ ] `@Id @GeneratedValue` on internal ID field (or `@Id` on a business key with constraint)
- [ ] `@Relationship` direction is explicit (OUTGOING / INCOMING)
- [ ] `@Query` Cypher uses `$paramName` parameters (not concatenation)
- [ ] Database name configured in `application.yml` (avoids default DB ambiguity)
- [ ] Unique constraint in DB for any business key used in repository lookups

---

## References

- [Spring Data Neo4j Reference](https://docs.spring.io/spring-data/neo4j/reference/)
- [GraphAcademy: Building Neo4j Applications with Spring Data](https://graphacademy.neo4j.com/courses/app-spring-data/)
- [Spring AI Neo4jVectorStore](https://docs.spring.io/spring-ai/reference/api/vectordbs/neo4j.html)
