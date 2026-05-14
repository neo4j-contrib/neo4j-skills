---
name: neo4j-spring-data-skill
description: Use when building Spring Boot applications with Neo4j using Spring Data Neo4j (SDN 7.x/8.x):
  @Node entity mapping, @Relationship, @RelationshipProperties, Neo4jRepository, ReactiveNeo4jRepository,
  @Query annotations, application.yml configuration, projections, Neo4jClient, Neo4jTemplate,
  transactions, auditing, or Spring AI Neo4jVectorStore vector search.
  Does NOT handle raw Java driver code without Spring — use neo4j-driver-java-skill.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT handle driver version upgrades — use neo4j-migration-skill.
version: 1.0.0
allowed-tools: Bash WebFetch
---

# Neo4j Spring Data Skill

## When to Use

- Configuring Spring Boot with Neo4j (`spring-boot-starter-data-neo4j`)
- Writing `@Node` entity classes and `@Relationship`/`@RelationshipProperties` mappings
- Defining `Neo4jRepository` or `ReactiveNeo4jRepository` interfaces
- Writing `@Query` annotations with Cypher on repository methods
- Using Spring projections (interface-based, DTO, dynamic) with Neo4j
- Configuring `application.yml` for Neo4j connection
- Custom queries via `Neo4jClient` or `Neo4jTemplate`
- Spring AI `Neo4jVectorStore` for vector search in Spring apps
- Transaction management, auditing, optimistic locking

## When NOT to Use

- **Raw Java driver without Spring** → `neo4j-driver-java-skill`
- **Cypher query authoring** → `neo4j-cypher-skill`
- **Driver version upgrades** → `neo4j-migration-skill`
- **GDS algorithms** → `neo4j-gds-skill`

---

## Version Matrix

| SDN    | Spring Boot | Spring Framework | Java | Neo4j |
|--------|-------------|-----------------|------|-------|
| 8.0.x  | 3.3.x / 3.4.x | 6.2.x          | 17+  | 5.15+ |
| 8.1.x  | 3.4.x+      | 7.0.x           | 17+  | 5.15+ |
| 7.5.x  | 3.2.x       | 6.1.x           | 17+  | 4.4+  |

Use `spring-boot-starter-data-neo4j` — it pulls SDN + driver. No explicit SDN version needed when using Spring Boot BOM.

---

## Setup

### Maven

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-neo4j</artifactId>
</dependency>
```

### Gradle

```gradle
implementation 'org.springframework.boot:spring-boot-starter-data-neo4j'
```

### Reactive stack (add alongside above)

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webflux</artifactId>
</dependency>
```

---

## Configuration

### application.yml — imperative (standard)

```yaml
spring:
  neo4j:
    uri: ${NEO4J_URI:bolt://localhost:7687}
    authentication:
      username: ${NEO4J_USERNAME:neo4j}
      password: ${NEO4J_PASSWORD}
  data:
    neo4j:
      database: ${NEO4J_DATABASE:neo4j}
```

### application.yml — Aura (TLS required)

```yaml
spring:
  neo4j:
    uri: ${NEO4J_URI}            # neo4j+s://xxxx.databases.neo4j.io
    authentication:
      username: ${NEO4J_USERNAME:neo4j}
      password: ${NEO4J_PASSWORD}
  data:
    neo4j:
      database: ${NEO4J_DATABASE:neo4j}
```

Credentials: store in `.env`; never hardcode. Verify `.env` is in `.gitignore`.

---

## Entity Mapping

```java
import org.springframework.data.neo4j.core.schema.*;

// Internal generated ID (default for most cases)
@Node("Person")
public class PersonEntity {
    @Id @GeneratedValue private Long id;         // element ID (Long)
    private String name;
    @Property("birth_year") private Integer birthYear;  // custom property name
    @Relationship(type = "KNOWS", direction = Relationship.Direction.OUTGOING)
    private List<PersonEntity> friends = new ArrayList<>();
}

// UUID business key
@Node("Product")
public class ProductEntity {
    @Id @GeneratedValue(generatorClass = GeneratedValue.UUIDStringGenerator.class)
    private String id;
    @Version private Long version;               // optimistic locking; required with business key
}

// User-assigned key (caller sets value; no @GeneratedValue)
@Node("Country")
public class CountryEntity {
    @Id private String isoCode;
    private String name;
}

// Multiple static labels
@Node(primaryLabel = "Vehicle", labels = {"Car", "Auditable"})
public class CarEntity { ... }

// Runtime labels
@Node("Content")
public class ContentEntity {
    @Id @GeneratedValue private Long id;
    @DynamicLabels private Set<String> tags = new HashSet<>();  // labels added at runtime
}
```

---

## Relationship Properties

Use `@RelationshipProperties` when the relationship itself carries data.

```java
@RelationshipProperties
public class RolesRelationship {

    @RelationshipId                     // internal relationship ID; required
    private Long id;

    private List<String> roles;

    @TargetNode                         // marks the other end of the relationship
    private PersonEntity person;
}
```

```java
@Node("Movie")
public class MovieEntity {

    @Id @GeneratedValue
    private Long id;

    private String title;

    @Relationship(type = "ACTED_IN", direction = Relationship.Direction.INCOMING)
    private List<RolesRelationship> actorsAndRoles = new ArrayList<>();
}
```

---

## Repository Interfaces

### Basic CRUD

```java
import org.springframework.data.neo4j.repository.Neo4jRepository;

public interface PersonRepository extends Neo4jRepository<PersonEntity, Long> {

    Optional<PersonEntity> findByName(String name);

    List<PersonEntity> findByBirthYearBetween(int from, int to);

    List<PersonEntity> findByNameContainingIgnoreCase(String fragment);

    long countByBirthYearGreaterThan(int year);

    void deleteByName(String name);
}
```

### @Query — custom Cypher

```java
// CORRECT: $param bound parameter
@Query("MATCH (p:Person {name: $name})-[:KNOWS]->(f:Person) RETURN f")
List<PersonEntity> findFriendsOf(String name);

// With pagination
@Query(value = "MATCH (p:Person) RETURN p ORDER BY p.name",
       countQuery = "MATCH (p:Person) RETURN count(p)")
Page<PersonEntity> findAllPaged(Pageable pageable);

// Return relationship-rich entity; map target via @Node return
@Query("MATCH (m:Movie)<-[r:ACTED_IN]-(p:Person {name: $name}) RETURN m, collect(r), collect(p)")
List<MovieEntity> findMoviesActedInBy(String name);
```

**Security rule**: NEVER string-concatenate user input into Cypher. Always use `$paramName`.

### Pagination and sorting

```java
Page<PersonEntity> findByBirthYearGreaterThan(int year, Pageable pageable);

List<PersonEntity> findTop10ByOrderByNameAsc();

List<PersonEntity> findByName(String name, Sort sort);
```

Usage:

```java
Pageable page = PageRequest.of(0, 20, Sort.by("name").ascending());
Page<PersonEntity> result = repo.findByBirthYearGreaterThan(1980, page);
```

---

## Projections

### Interface projection (closed — query-optimizable)

```java
public interface PersonSummary {
    String getName();
    Integer getBirthYear();
}

List<PersonSummary> findByBirthYearLessThan(int year);
```

### DTO projection (record — preferred in Java 17+)

```java
public record PersonDto(String name, Integer birthYear) {}

List<PersonDto> findByName(String name);
```

### Dynamic projection

```java
<T> List<T> findByName(String name, Class<T> type);

// Usage
repo.findByName("Alice", PersonSummary.class);
repo.findByName("Alice", PersonEntity.class);
```

### Open projection — SpEL (disables query optimization)

```java
public interface FullName {
    @Value("#{target.name + ' (' + target.birthYear + ')'}") String getDisplayName();
}
```

---

## Reactive Repository

```java
import org.springframework.data.neo4j.repository.ReactiveNeo4jRepository;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

public interface ReactivePersonRepository extends ReactiveNeo4jRepository<PersonEntity, Long> {

    Mono<PersonEntity> findByName(String name);

    @Query("MATCH (p:Person {name: $name})-[:KNOWS]->(f) RETURN f")
    Flux<PersonEntity> findFriendsOf(String name);
}
```

Do NOT mix imperative and reactive database access in the same application context.

---

## Custom Repository Implementation

Fragment pattern — use when `@Query` is not enough.

```java
// 1. Fragment interface
public interface PersonRepositoryCustom {
    List<PersonEntity> findByComplexCriteria(String criteria);
}

// 2. Impl — must end with "Impl"
public class PersonRepositoryCustomImpl implements PersonRepositoryCustom {
    private final Neo4jClient neo4jClient;
    PersonRepositoryCustomImpl(Neo4jClient c) { this.neo4jClient = c; }

    @Override
    public List<PersonEntity> findByComplexCriteria(String c) {
        return new ArrayList<>(neo4jClient
            .query("MATCH (p:Person) WHERE p.name CONTAINS $c RETURN p").bind(c).to("c")
            .fetchAs(PersonEntity.class)
            .mappedBy((t, r) -> { var e = new PersonEntity(); e.setName(r.get("p").asNode().get("name").asString()); return e; })
            .all());
    }
}

// 3. Compose
public interface PersonRepository extends Neo4jRepository<PersonEntity, Long>, PersonRepositoryCustom {}
```

---

## Neo4jClient — Low-Level Queries

Use when `@Query` is insufficient or you need full control over Cypher execution.

```java
// Bind params + fetch single scalar
neo4jClient.query("MATCH (p:Person {name: $name}) RETURN count(*) AS cnt")
    .bind("Alice").to("name")
    .fetchAs(Long.class)
    .mappedBy((t, r) -> r.get("cnt").asLong())
    .one();

// Bind + run write (no result)
neo4jClient.query("MERGE (p:Person {name: $name})")
    .bind(personName).to("name")
    .run();

// Custom object mapping
neo4jClient.query("MATCH (p:Person)-[:DIRECTED]->(m:Movie) WHERE p.name=$n RETURN p, collect(m) AS movies")
    .bind("Lilly Wachowski").to("n")
    .fetchAs(Director.class)
    .mappedBy((typeSystem, record) -> new Director(
        record.get("p").asNode().get("name").asString(),
        record.get("movies").asList(v -> new Movie(v.get("title").asString()))
    )).one();
```

Full API: [references/neo4j-client.md](references/neo4j-client.md)

---

## Transaction Management

```java
@Service
@Transactional                      // class-level: all methods transactional
public class PersonService {
    @Transactional(readOnly = true) // read-only hint
    public Optional<PersonEntity> findByName(String name) { ... }

    @Transactional                  // explicit write
    public PersonEntity save(PersonEntity p) { return repository.save(p); }
}
```

`Neo4jTransactionManager` auto-configured. Do NOT mix with JPA `PlatformTransactionManager` without explicit qualifier. Use `@Transactional` on concrete class, not interface.

---

## Spring AI — Neo4jVectorStore

### Dependency

```xml
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-starter-vector-store-neo4j</artifactId>
</dependency>
```

### application.yml

```yaml
spring:
  ai:
    vectorstore:
      neo4j:
        initialize-schema: true         # creates vector index on first run
        index-name: my-index
        embedding-dimension: 1536       # must match your embedding model
        distance-type: cosine           # cosine (default) or euclidean
        label: Document                 # node label for stored chunks
        embedding-property: embedding   # property for the vector
```

Requires Neo4j 5.15+. Reuses `spring.neo4j.*` connection config.

### Usage

```java
@Autowired VectorStore vectorStore;

// Store
vectorStore.add(List.of(new Document("text", Map.of("author", "alice"))));

// Similarity search
List<Document> results = vectorStore.similaritySearch(
    SearchRequest.builder().query("spring neo4j").topK(5).similarityThreshold(0.75).build()
);

// With metadata filter
vectorStore.similaritySearch(
    SearchRequest.builder().query("spring neo4j").topK(5)
        .filterExpression("author == 'alice'").build()
);
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `MappingException: Could not find entity` | Entity not scanned | Check `@EnableNeo4jRepositories` base package |
| Relationships null after load | Default depth may skip deep rels | Use `@Query` with `RETURN m, collect(r), collect(p)` |
| N+1 queries | Per-entity relationship fetch | Rewrite with single `@Query`; use projections |
| `OptimisticLockingFailureException` | Stale `@Version` on concurrent write | Retry in service layer |
| `IllegalStateException: Cannot mix reactive/imperative` | Both repo types in same context | Pick one stack |
| Projection null fields | Getter name mismatch | Match getter to property name; check `@Property` alias |
| `@Query` empty with rels | Missing `collect(r), collect(p)` | Return root node + rels + related nodes together |
| `Cannot delete node, node has relationships` | `deleteById` without detach | Use `@Query` with `DETACH DELETE` |
| Transaction not rolling back | `@Transactional` on interface | Apply on concrete service class |

---

## Relationship Loading — Key Rule

SDN loads related entities eagerly up to a configured depth (default: 1 hop). For deeper graphs:

```java
// Explicit @Query to control what gets loaded
@Query("""
    MATCH (m:Movie)<-[r:ACTED_IN]-(p:Person)
    WHERE m.title = $title
    RETURN m, collect(r), collect(p)
    """)
Optional<MovieEntity> findByTitleWithCast(String title);
```

`collect(r), collect(p)` in RETURN is required for SDN to map `@RelationshipProperties` correctly.

---

## References

- [Spring Data Neo4j Reference (8.x)](https://docs.spring.io/spring-data/neo4j/reference/)
- [Spring AI Neo4jVectorStore](https://docs.spring.io/spring-ai/reference/api/vectordbs/neo4j.html)
- [GraphAcademy: Building Neo4j Apps with Spring Data](https://graphacademy.neo4j.com/courses/app-spring-data/)
- [Neo4j Getting Started — SDN](https://neo4j.com/docs/getting-started/languages-guides/java/spring-data-neo4j/)
- [SDN Advanced projections](https://docs.spring.io/spring-data/neo4j/reference/repositories/projections.html)
- [SDN Auditing](https://docs.spring.io/spring-data/neo4j/reference/object-mapping/auditing.html)
- [Modeling pitfalls, projection guide, type mapping](references/modeling-pitfalls.md)

---

## Checklist

- [ ] `@Node` uses explicit label string, not default class name
- [ ] `@Id @GeneratedValue` (or `@Id` + `@Version` for business key with optimistic lock)
- [ ] `@RelationshipProperties` class has `@RelationshipId` and `@TargetNode`
- [ ] `@Relationship` direction is explicit (OUTGOING / INCOMING)
- [ ] `@Query` Cypher uses `$paramName` — no string concatenation
- [ ] Relationship-rich `@Query` returns `collect(r), collect(p)` alongside root node
- [ ] Database name set in `application.yml` (avoids default DB ambiguity)
- [ ] Unique constraint exists in DB for any business key used in repository lookups
- [ ] `@Transactional` on concrete service class (not interface)
- [ ] No imperative + reactive mix in same application context
- [ ] Credentials in env vars; `.env` in `.gitignore`
- [ ] `spring.ai.vectorstore.neo4j.initialize-schema: true` for first run (Spring AI)
