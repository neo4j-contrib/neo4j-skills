> Source: git@github.com:neo4j/docs-cypher.git + git@github.com:neo4j/docs-cheat-sheet.git@238ab12a / e11fe2f2
> Generated: 2026-03-20T00:11:34Z
> Files: vector-index.adoc (cheat), full-text-index.adoc (cheat), search-performance-index.adoc (cheat), indexes/syntax.adoc (cypher), indexes/semantic-indexes/vector-indexes.adoc (cypher), indexes/semantic-indexes/full-text-indexes.adoc (cypher)

# Vector indexes

```cypher
CREATE VECTOR INDEX `abstract-embeddings`
FOR (a:Abstract) ON (a.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }
}
```

Create a vector index on nodes with label `Abstract`, property `embedding`, and a vector dimension of `1536` using the `cosine` similarity function and the name `abstract-embeddings`.
Note that the `OPTIONS` map is mandatory since a vector index cannot be created without setting the vector dimensions and similarity function.

```cypher
CREATE VECTOR INDEX `review-embeddings`
FOR ()-[r:REVIEWED]-() ON (r.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 256,
    `vector.similarity_function`: 'cosine'
  }
}
```

Create a vector index on relationships with relationship type `REVIEWED`, property `embedding`, and a vector dimension of `256` using the `cosine` similarity function and the name `review-embeddings`.
Note that the `OPTIONS` map is mandatory since a vector index cannot be created without setting the vector dimensions and similarity function.

```cypher
CALL db.index.vector.queryNodes('abstract-embeddings', 10, abstract.embedding)
```

Query the node vector index `abstract-embeddings` for a neighborhood of `10` similar abstracts.

```cypher
CALL db.index.vector.queryRelationships('review-embeddings', 10, $query)
```

Query the relationship vector index `review-embeddings` for a neighborhood of `10` similar reviews to the vector given by the `query` parameter.

```cypher
MATCH (n:Node {id: $id})
CALL db.create.setNodeVectorProperty(n, 'propertyKey', $vector)
```

Set the vector properties of a node using `db.create.setNodeVectorProperty`.

```cypher
MATCH ()-[r:Relationship {id: $id}]->()
CALL db.create.setRelationshipVectorProperty(r, 'propertyKey', $vector)
```

Set the vector properties of a relationship using `db.create.setRelationshipVectorProperty`.

```cypher
SHOW VECTOR INDEXES
```

List all vector indexes.

```cypher
DROP INDEX `abstract-embeddings`
```

Drop a vector index.

---

# Full-text indexes

```cypher
CREATE FULLTEXT INDEX node_fulltext_index
FOR (n:Friend) ON EACH [n.name]
OPTIONS {
  indexConfig: {
    `fulltext.analyzer`: 'swedish'
  }
}
```

Create a fulltext index on nodes with the name `index_name` and analyzer `swedish`.
The other index settings will have their default values.

```cypher
CREATE FULLTEXT INDEX relationship_fulltext_index
FOR ()-[r:KNOWS]-() ON EACH [r.info, r.note]
OPTIONS {
  indexConfig: {
    `fulltext.analyzer`: 'english'
  }
}
```

Create a fulltext index on relationships with the name `index_name` and analyzer `english`.
The other index settings will have their default values.

```cypher
CALL db.index.fulltext.queryNodes("node_fulltext_index", "Alice") YIELD node, score
```

Query a full-text index on nodes.

```cypher
CALL db.index.fulltext.queryRelationships("relationship_fulltext_index", "Alice") YIELD relationship, score
```

Query a full-text index on relationships.

```cypher
SHOW FULLTEXT INDEXES
```

List all full-text indexes.

```cypher
DROP INDEX node_fulltext_index
```

Drop a full-text index.

---

# Search-performance indexes

Cypher includes four search-performance indexes: range (default), text, point, and token lookup.

```cypher
CREATE INDEX index_name
FOR (p:Person) ON (p.name)
```

--
Create a range index with the name `index_name` on nodes with label `Person` and property `name`.

It is possible to omit the `index_name`, if not specified the index name will be decided by the DBMS. Best practice is to always specify a sensible name when creating an index. 

The create syntax is `CREATE [RANGE|TEXT|POINT|LOOKUP|FULLTEXT|VECTOR] INDEX ...`. Defaults to range if not explicitly stated.
--

```cypher
CREATE RANGE INDEX index_name
FOR ()-[k:KNOWS]-() ON (k.since)
```

Create a range index on relationships with type `KNOWS` and property `since` with the name `index_name`.

```cypher
CREATE INDEX $nameParam
FOR (p:Person) ON (p.name, p.age)
```

Create a composite range index with the name given by the parameter `nameParam` on nodes with label `Person` and the properties `name` and `age`, throws an error if the index already exist.

```cypher
CREATE INDEX index_name IF NOT EXISTS
FOR (p:Person) ON (p.name, p.age)
```

Create a composite range index with the name `index_name` on nodes with label `Person` and the properties `name` and `age` if it does not already exist, does nothing if it did exist.

```cypher
CREATE TEXT INDEX index_name
FOR (p:Person) ON (p.name)
```

--
Create a text index on nodes with label `Person` and property `name`.
Text indexes only solve predicates involving `STRING` property values.
--

```cypher
CREATE TEXT INDEX index_name
FOR ()-[r:KNOWS]-() ON (r.city)
```

Create a text index on relationships with type `KNOWS` and property `city`. 
Text indexes only solve predicates involving `STRING` property values.

```cypher
CREATE POINT INDEX index_name
FOR (p:Person) ON (p.location)
OPTIONS {
  indexConfig: {
    `spatial.cartesian.min`: [-100.0, -100.0],
    `spatial.cartesian.max`: [100.0, 100.0]
  }
}
```

Create a point index on nodes with label `Person` and property `location` with the name `index_name` and the given `spatial.cartesian` settings. The other index settings will have their default values.
Point indexes only solve predicates involving `POINT` property values.

```cypher
CREATE POINT INDEX $nameParam
FOR ()-[h:STREET]-() ON (h.intersection)
```

Create a point index with the name given by the parameter `nameParam` on relationships with the type `STREET` and property `intersection`.
Point indexes only solve predicates involving `POINT` property values.

```cypher
CREATE LOOKUP INDEX index_name
FOR (n) ON EACH labels(n)
```

Create a token lookup index on nodes with any label.

```cypher
CREATE LOOKUP INDEX index_name
FOR ()-[r]-() ON EACH type(r)
```

Create a token lookup index on relationships with any relationship type.

```cypher
SHOW INDEXES
```

List all indexes, returns only the default outputs (`id`, `name`, `state`, `populationPercent`, `type`, `entityType`, `labelsOrTypes`, `properties`, `indexProvider`, `owningConstraint`, `lastRead`, and `readCount`).

```cypher
SHOW INDEXES YIELD *
```

List all indexes and return all columns.

```cypher
SHOW INDEX YIELD name, type, entityType, labelsOrTypes, properties
```

List all indexes and return only specific columns.

```cypher
SHOW INDEXES
YIELD name, type, options, createStatement
RETURN name, type, options.indexConfig AS config, createStatement
```

List all indexes and return only specific columns using the `RETURN` clause.
Note that `YIELD` is mandatory if `RETURN` is used.

```cypher
SHOW RANGE INDEXES
```

List range indexes, can also be filtered on `ALL`, `FULLTEXT`, `LOOKUP`, `POINT`, `TEXT`, and `VECTOR`.

```cypher
DROP INDEX index_name
```

Drop the index named `index_name`, throws an error if the index does not exist.

```cypher
DROP INDEX index_name IF EXISTS
```

Drop the index named `index_name` if it exists, does nothing if it does not exist.

```cypher
DROP INDEX $nameParam
```

Drop an index using a parameter.

```cypher
MATCH (n:Person)
USING INDEX n:Person(name)
WHERE n.name = $value
```

Index usage can be enforced when Cypher uses a suboptimal index, or when more than one index should be used.

---

# SEARCH clause (vector index query)

> **Available: Neo4j 2026.02.1+** — GA for node vector indexes only. Not available on older versions.
> For pre-2026.02 databases, use `db.index.vector.queryNodes()` instead.
> Fulltext indexes do NOT support SEARCH clause — always use `db.index.fulltext.queryNodes()`.
> Relationship vector indexes do NOT support SEARCH clause — always use `db.index.vector.queryRelationships()`.

## SEARCH clause syntax (2026.02.1+)

```cypher
CYPHER 25
MATCH (c:Chunk)
SEARCH c IN (VECTOR INDEX news FOR $embedding LIMIT 10)
SCORE AS score
WHERE score > 0.8
RETURN c.text, score
ORDER BY score DESC
```

**Key syntax rules:**
- Variable name only — NOT `SEARCH (n)`, must be `SEARCH n`
- `IN (VECTOR INDEX index_name FOR $embedding LIMIT N)` — LIMIT is required inside parens
- `SCORE AS varname` — bind the similarity score **after** the closing paren, before WHERE/RETURN
- `WHERE` and `ORDER BY` come after `SCORE AS`

## Procedure fallback (all versions)

Node vector index (pre-2026.02 or relationship indexes):

```cypher
CYPHER 25
CALL db.index.vector.queryNodes('moviePlotsEmbedding', 10, $embedding)
YIELD node, score
RETURN node.title, score
ORDER BY score DESC
```

Relationship vector index (always use procedure — no SEARCH support):

```cypher
CYPHER 25
CALL db.index.vector.queryRelationships('review-embeddings', 10, $embedding)
YIELD relationship, score
RETURN relationship.text, score
ORDER BY score DESC
```

Fulltext query procedure (all versions — SEARCH clause never covers fulltext):

```cypher
CYPHER 25
CALL db.index.fulltext.queryNodes('entityIndex', $searchTerm)
YIELD node, score
RETURN node.name, score
ORDER BY score DESC
LIMIT 10
```

---

# Syntax
## CREATE INDEX

The general structure of the `CREATE INDEX` command is:

> **Note**: Content truncated to token budget.
