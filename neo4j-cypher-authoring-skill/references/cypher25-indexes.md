> Source: git@github.com:neo4j/docs-cypher.git@238ab12a / git@github.com:neo4j/docs-cheat-sheet.git@e11fe2f2
> Generated: 2026-03-20T00:00:00Z
> Files: indexes/syntax.adoc, indexes/search-performance-indexes/create-indexes.adoc, indexes/search-performance-indexes/index-hints.adoc, indexes/search-performance-indexes/using-indexes.adoc, indexes/semantic-indexes/full-text-indexes.adoc, indexes/semantic-indexes/vector-indexes.adoc, clauses/search.adoc

## Index Type Selection Table

| Index Type | Use When | Predicate Types Solved |
| --- | --- | --- |
| `RANGE` | Ordered, comparable values (default) | `=`, `<`, `>`, `<=`, `>=`, `IS NOT NULL`, `STARTS WITH`, `IN` |
| `TEXT` | `STRING` property predicates only | `=`, `STARTS WITH`, `ENDS WITH`, `CONTAINS`, regex |
| `POINT` | Spatial `POINT` properties | `point.distance()`, `point.withinBBox()` |
| `FULLTEXT` | Multi-label/type, multi-property text search (Lucene BM25) | `db.index.fulltext.queryNodes()` / `queryRelationships()` |
| `VECTOR` | Approximate nearest neighbor (embedding similarity) | `SEARCH ... IN (VECTOR INDEX ...)`, `db.index.vector.queryNodes()` |
| `LOOKUP` | Token lookup (created by default) | Node label scan, relationship type scan |

> **Rule**: Use RANGE for most equality/range predicates. Use TEXT when `ENDS WITH` or `CONTAINS` is critical. Use POINT for geo. Use FULLTEXT for ranked keyword search across multiple labels. Use VECTOR for embedding similarity search.

## Search-Performance Indexes — CREATE / DROP

```cypher
// Range index on node property (default — RANGE keyword optional)
CREATE INDEX person_name IF NOT EXISTS
FOR (p:Person) ON (p.name)

// Range index on relationship property
CREATE RANGE INDEX knows_since
FOR ()-[k:KNOWS]-() ON (k.since)

// Composite range index
CREATE INDEX person_name_age
FOR (p:Person) ON (p.name, p.age)

// Text index (STRING only — enables ENDS WITH / CONTAINS)
CREATE TEXT INDEX person_name_text
FOR (p:Person) ON (p.name)

// Point index
CREATE POINT INDEX person_location
FOR (p:Person) ON (p.location)
OPTIONS {
  indexConfig: {
    `spatial.wgs-84.min`: [-180.0, -90.0],
    `spatial.wgs-84.max`: [180.0, 90.0]
  }
}

// Drop index
DROP INDEX index_name IF EXISTS

// List all indexes
SHOW INDEXES YIELD name, type, state, labelsOrTypes, properties
SHOW RANGE INDEXES         // filter by type: RANGE, TEXT, POINT, FULLTEXT, VECTOR
```

## Fulltext Indexes — CREATE / QUERY

```cypher
// Create (multi-label, multi-property)
CREATE FULLTEXT INDEX namesAndTeams
FOR (n:Employee|Manager) ON EACH [n.name, n.team]
OPTIONS { indexConfig: { `fulltext.analyzer`: 'english' } }

// Create on relationship
CREATE FULLTEXT INDEX rel_fulltext
FOR ()-[r:REVIEWED|EMAILED]-() ON EACH [r.message]

// Query node fulltext index (returns node, score)
CALL db.index.fulltext.queryNodes('namesAndTeams', 'Alice')
YIELD node, score

// Query relationship fulltext index
CALL db.index.fulltext.queryRelationships('rel_fulltext', 'feedback')
YIELD relationship AS r, score

// Lucene query syntax examples: 'Alice', 'name:Alice', 'Alice AND manager', 'Ali*'
```

## Vector Indexes — CREATE / QUERY

```cypher
// Create vector index on node property
CREATE VECTOR INDEX moviePlots IF NOT EXISTS
FOR (m:Movie) ON m.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'  -- or 'euclidean'
  }
}

// Create vector index on relationship property
CREATE VECTOR INDEX review_embeddings
FOR ()-[r:REVIEWED]-() ON (r.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 256,
    `vector.similarity_function`: 'cosine'
  }
}
```

### SEARCH Clause (Cypher 25, Neo4j 2026.01+, Preview)

Preferred way to query vector indexes in Cypher 25.

```cypher
// Syntax
[OPTIONAL] MATCH pattern
  SEARCH binding_variable IN (
    VECTOR INDEX index_name
    FOR query_vector
    [WHERE filter_predicate]
    LIMIT top_k
  ) [SCORE AS score_alias]
```

```cypher
// Find 5 movies most similar to a given embedding
MATCH (m:Movie {title: 'Godfather, The'})
MATCH (movie:Movie)
  SEARCH movie IN (
    VECTOR INDEX moviePlots
    FOR m.embedding
    LIMIT 5
  ) SCORE AS score
RETURN movie.title, score

// With pre-filter inside SEARCH (reduces candidate set via index)
MATCH (movie:Movie)
  SEARCH movie IN (
    VECTOR INDEX moviePlots
    FOR $queryEmbedding
    WHERE movie.rating >= 8.0
    LIMIT 10
  ) SCORE AS score
RETURN movie.title, score

// Exclude the query vector itself
MATCH (movie:Movie)
  SEARCH movie IN (VECTOR INDEX moviePlots FOR $vec LIMIT 6) SCORE AS score
WHERE score < 1
RETURN movie.title, score
```

### Legacy Procedure (works pre-2026.01)

```cypher
// Query node vector index via procedure
MATCH (m:Movie {title: 'Godfather, The'})
CALL db.index.vector.queryNodes('moviePlots', 5, m.embedding)
YIELD node AS movie, score
RETURN movie.title, score

// Query relationship vector index
CALL db.index.vector.queryRelationships('review_embeddings', 10, $queryVector)
YIELD relationship AS r, score
```

## Index Hints (Query Planner Overrides)

Use `USING` after the `MATCH` clause to force a specific index. Advanced use only — incorrect hints can worsen performance.

```cypher
// Force range index on node
MATCH (n:Person)
USING INDEX n:Person(name)
WHERE n.name = $value
RETURN n

// Force text index on node
MATCH (c:Country)
USING TEXT INDEX c:Country(name)
WHERE c.name STARTS WITH 'Ger'
RETURN c

// Force range index seek (avoids scan)
MATCH (s:Scientist)
USING INDEX SEEK s:Scientist(born)
WHERE s.born > 1850
RETURN s

// Force index on relationship
MATCH ()-[r:INVENTED_BY]-()
USING INDEX r:INVENTED_BY(year)
WHERE r.year = 560
RETURN r

// Multiple hints — requires join in plan (may be expensive)
MATCH (s:Scientist {born: 1850}), (p:Pioneer {born: 525})
USING INDEX s:Scientist(born)
USING INDEX p:Pioneer(born)
RETURN s, p
```

**Hint forms**: `USING INDEX`, `USING TEXT INDEX`, `USING POINT INDEX`, `USING RANGE INDEX`, `USING INDEX SEEK`, `USING SCAN` (forces label scan, no index)

## SHOW INDEXES Reference

```cypher
SHOW INDEXES YIELD *
// Key columns: name, type, state, labelsOrTypes, properties, indexProvider, owningConstraint

SHOW INDEXES
YIELD name, type, options, createStatement
RETURN name, type, options.indexConfig AS config, createStatement
```

Index `state` values: `ONLINE` (usable), `POPULATING` (building — check `populationPercent`), `FAILED`.
