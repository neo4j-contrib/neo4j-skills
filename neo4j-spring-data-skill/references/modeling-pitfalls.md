# SDN Modeling Pitfalls and Projection Guide

## findAll() — Greedy Graph Traversal

`findAll()` fetches the entire reachable graph from the entity root. For datasets > ~100 nodes this causes timeouts or OOM. Use a custom `@Query` with `LIMIT`:

```java
@Query("MATCH (m:Movie)<-[r:ACTED_IN]-(p:Person) RETURN m, collect(r), collect(p) LIMIT 20")
List<MovieEntity> findMoviesSubset();
```

Never use `findAll()` in production without a `LIMIT`.

## Bidirectional Relationships — Avoid Unless Needed

Defining `Movie → actors` AND `Person → movies` in the same entity graph causes chain-loading: fetching a movie loads actors, which loads their other movies, which loads those casts, etc. This can fetch the entire graph.

- Define only the direction needed for your use case.
- If both directions are genuinely needed, use `@Query` with explicit depth control.
- Avoid `@Relationship` on both ends of the same relationship type unless the domain truly requires it.

## Interface vs DTO Projection — When to Use Each

### Interface projection (closed)

Use when you need a subset of existing entity properties for display or serialization. SDN can optimize the Cypher query to only fetch those fields.

```java
public interface MovieSummary {
    String getTitle();
    Integer getYear();
    String getPoster();
}

List<MovieSummary> findByYearGreaterThan(int year);
```

### DTO projection (record/class)

Use when you need **computed or aggregated fields** not present on the entity. The `@Query` computes extra columns that map to DTO fields.

```java
public record MovieWithCastSize(String title, String poster, Long castSize) {}

@Query("MATCH (m:Movie)<-[:ACTED_IN]-(p:Person) RETURN m.title AS title, m.poster AS poster, count(p) AS castSize")
List<MovieWithCastSize> findMoviesWithCastSize();
```

**Caution**: DTO projection does NOT reduce database load. SDN fetches the full entity in case SpEL or other features access unlisted fields. Use interface projections when reducing payload size matters; use DTO projections for computed columns.

### Multi-level (nested) projection

SDN supports projections that contain other projections. Useful for partial relationship traversal:

```java
public interface MovieWithDirector {
    String getTitle();
    PersonSummary getDirector();  // nested projection

    interface PersonSummary {
        String getName();
    }
}
```

## Type Mapping: Java ↔ Neo4j

| Java Type | Neo4j Cypher Type | Notes |
|---|---|---|
| `String` | `String` | Direct |
| `Long` | `Integer` | Neo4j Integer = Java Long (64-bit) |
| `Double` | `Float` | Neo4j Float maps to Java Double |
| `Boolean` | `Boolean` | Direct |
| `java.time.LocalDate` | `Date` | |
| `java.time.ZonedDateTime` | `DateTime` | |
| `java.time.LocalDateTime` | `LocalDateTime` | |
| `java.time.OffsetTime` | `Time` | |
| `java.time.LocalTime` | `LocalTime` | |
| `java.time.temporal.TemporalAmount` | `Duration` | `java.time.Duration` or `Period` both map here; original type lost on return |
| `org.neo4j.driver.types.Point` | `Point` | Use for 2D/3D spatial properties |

Integer values outside `Long` range are returned as `String`.

## Not Building the Entire Graph Into the Application

Resist mapping every label, relationship, and property. Build entities for the specific use case. Mapping `Actor`, `Director`, `User`, `Genre` as separate entities alongside `Movie` creates sprawl and often loads unwanted data.

- Start with the minimum model for your primary use case.
- Add entities incrementally as use cases require.
- Use `@Query` projections to cross type boundaries without introducing new entity classes.
