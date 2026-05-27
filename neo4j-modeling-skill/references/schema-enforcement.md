# Schema Enforcement

Run all DDL with `IF NOT EXISTS`. Apply before importing data.

## Constraint Types

```cypher
// 1. Uniqueness constraint — every node type used in MERGE
CREATE CONSTRAINT person_id_unique IF NOT EXISTS
  FOR (p:Person) REQUIRE p.id IS UNIQUE;

// 2. Existence constraint (Enterprise) — mandatory properties
CREATE CONSTRAINT person_name_exists IF NOT EXISTS
  FOR (p:Person) REQUIRE p.name IS NOT NULL;

// 3. Property type constraint (Enterprise) — enforce data type
CREATE CONSTRAINT person_born_integer IF NOT EXISTS
  FOR (p:Person) REQUIRE p.born IS :: INTEGER;

// 4. Key constraint (Enterprise) — unique + exists in one
CREATE CONSTRAINT movie_tmdbid_key IF NOT EXISTS
  FOR (m:Movie) REQUIRE m.tmdbId IS NODE KEY;
```

## Index Types

```cypher
// 5. Range index — equality and range filters on properties
CREATE INDEX person_name_idx IF NOT EXISTS
  FOR (p:Person) ON (p.name);

// 6. Fulltext index — CONTAINS, STARTS WITH, free text search
CREATE FULLTEXT INDEX person_fulltext IF NOT EXISTS
  FOR (n:Person) ON EACH [n.name, n.bio];

// 7. Vector index — embedding similarity search
CREATE VECTOR INDEX chunk_embedding_idx IF NOT EXISTS
  FOR (c:Chunk) ON (c.embedding)
  OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' } };

// 8. Relationship index — filter on rel properties
CREATE INDEX acted_in_year_idx IF NOT EXISTS
  FOR ()-[r:ACTED_IN]-() ON (r.year);
```

After creating indexes, poll until ONLINE:

```cypher
SHOW INDEXES YIELD name, state WHERE state <> 'ONLINE' RETURN name, state;
```

Do NOT use an index until state = `ONLINE`.

## Vector / Embedding Property Modeling

Store embeddings on dedicated `:Chunk` nodes, never on business nodes:

```
(:Document)-[:HAS_CHUNK]->(c:Chunk {text: "...", embedding: [...]})
```

Rules:
- Chunk node: `text` (source text), `embedding` (float array), `chunkIndex` (int)
- Parent document: metadata only (title, url, createdAt)
- Vector index on `c.embedding` only
- Chunk size 200–500 tokens with 20% overlap is production default [field]
- Do NOT put embedding on `:Document` — makes the node too large and pollutes traversal
