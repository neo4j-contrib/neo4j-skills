# Neo4jClient Reference

Use `Neo4jClient` when repository methods are too rigid but you still want Spring-managed sessions, transactions, mapping, and parameter binding.

## Read Query

```java
Optional<String> title = neo4jClient
    .query("MATCH (m:Movie {id: $id}) RETURN m.title AS title")
    .bind(movieId).to("id")
    .fetchAs(String.class)
    .one();
```

## Write Query

```java
neo4jClient
    .query("MERGE (p:Person {id: $id}) SET p.name = $name")
    .bind(personId).to("id")
    .bind(name).to("name")
    .run();
```

## Custom Mapping

```java
List<MovieSummary> movies = neo4jClient
    .query("""
        MATCH (m:Movie)<-[:DIRECTED]-(p:Person)
        RETURN m.title AS title, collect(p.name) AS directors
        """)
    .fetchAs(MovieSummary.class)
    .mappedBy((typeSystem, record) -> new MovieSummary(
        record.get("title").asString(),
        record.get("directors").asList(Value::asString)
    ))
    .all();
```

## Guidance

- Always bind parameters instead of concatenating values into Cypher.
- Prefer repositories for simple aggregate persistence.
- Prefer `Neo4jClient` for hand-written Cypher, projections, and partial graph reads.
- Use Spring `@Transactional` boundaries rather than manually opening driver sessions.
