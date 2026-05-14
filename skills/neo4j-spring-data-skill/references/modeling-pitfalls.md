# SDN Modeling Pitfalls and Projection Guide

## findAll() — Greedy Graph Traversal

`findAll()` fetches the entire reachable graph. For datasets > ~100 nodes this causes timeouts or OOM. Use a custom `@Query` with `LIMIT`:

```java
@Query("MATCH (m:Movie)<-[r:ACTED_IN]-(p:Person) RETURN m, collect(r), collect(p) LIMIT 20")
List<MovieEntity> findMoviesSubset();
```

Never call `findAll()` in production without a `LIMIT`.

## Bidirectional Relationships — Avoid Unless Needed

Defining `Movie → actors` AND `Person → movies` causes chain-loading: fetching a movie loads actors, which loads their other movies, which loads those casts, etc. — can fetch the entire graph.

- Define only the direction needed for the use case.
- If both directions are required, use `@Query` with explicit depth control.
- Avoid `@Relationship` on both ends of the same type unless the domain requires it.

## Interface vs DTO Projection — When to Use Each

### Interface projection (closed)

Use for a subset of existing entity properties. SDN can optimize the Cypher query to fetch only those fields.

```java
public interface MovieSummary {
    String getTitle();
    Integer getYear();
    String getPoster();
}

List<MovieSummary> findByYearGreaterThan(int year);
```

### DTO projection (record/class)

Use for **computed or aggregated fields** not on the entity. The `@Query` computes extra columns mapped to DTO fields.

```java
public record MovieWithCastSize(String title, String poster, Long castSize) {}

@Query("MATCH (m:Movie)<-[:ACTED_IN]-(p:Person) RETURN m.title AS title, m.poster AS poster, count(p) AS castSize")
List<MovieWithCastSize> findMoviesWithCastSize();
```

**Caution**: DTO projection does NOT reduce database load — SDN fetches the full entity in case SpEL or other features access unlisted fields. Use interface projections to reduce payload; use DTO projections for computed columns.

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

Map only what the use case needs. Mapping every label (`Actor`, `Director`, `User`, `Genre`) alongside `Movie` creates sprawl and loads unwanted data.

- Start with the minimum model.
- Add entities incrementally as use cases require.
- Use `@Query` projections to cross type boundaries without new entity classes.
