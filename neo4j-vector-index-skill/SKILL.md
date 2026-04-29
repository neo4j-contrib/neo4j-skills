---
name: neo4j-vector-index-skill
description: Create and manage Neo4j vector indexes, run vector similarity search (ANN/kNN),
  store embeddings on nodes or relationships, use SEARCH clause (Neo4j 2026.01+) or
  db.index.vector.queryNodes() procedure (2025.x fallback), configure HNSW and quantization
  options, pick similarity function and embedding provider dimensions, and batch-update
  embeddings. Use when tasks involve CREATE VECTOR INDEX, vector.dimensions, cosine/euclidean
  search, embedding ingestion pipelines, or semantic nearest-neighbor lookup in Neo4j.
  Does NOT handle GraphRAG retrieval_query graph traversal — use neo4j-graphrag-skill.
  Does NOT handle fulltext/keyword indexes (FULLTEXT INDEX, db.index.fulltext) — use neo4j-cypher-skill.
  Does NOT handle GDS graph embeddings (FastRP, Node2Vec) — use neo4j-gds-skill.
version: 1.0.0
compatibility: Neo4j >= 2025.01; SEARCH clause requires 2026.01+
allowed-tools: Bash WebFetch
---

## When to Use
- Creating a vector index (`CREATE VECTOR INDEX`) on nodes or relationships
- Running vector similarity / nearest-neighbor search
- Storing embeddings on graph nodes during ingestion
- Choosing similarity function, dimensions, HNSW params, or quantization
- Using `SEARCH` clause (2026.01+) or `db.index.vector.queryNodes()` (2025.x)
- Batch-updating embeddings after model change
- Combining vector results with immediate graph neighborhood (full retrieval_query pipelines → `neo4j-graphrag-skill`)

## When NOT to Use
- **GraphRAG pipelines** (VectorCypherRetriever, HybridCypherRetriever, retrieval_query) → `neo4j-graphrag-skill`
- **Fulltext / keyword search** (FULLTEXT INDEX, `db.index.fulltext.queryNodes`) → `neo4j-cypher-skill`
- **GDS graph embeddings** (FastRP, Node2Vec, GraphSAGE) → `neo4j-gds-skill`
- **Index admin** (list all indexes, drop range/text/lookup indexes) → `neo4j-cypher-skill`

---

## Pre-flight — Determine Version

Drives syntax choice:
```cypher
CALL dbms.components() YIELD versions RETURN versions[0] AS neo4j_version
```

| Version | Use |
|---|---|
| `2026.01` or higher | `SEARCH` clause (in-index filtering, preferred) |
| `2025.x` | `db.index.vector.queryNodes()` procedure |

---

## Step 1 — Create Vector Index

Node index (single label):
```cypher
CYPHER 25
CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine',
    `vector.quantization.enabled`: true,
    `vector.hnsw.m`: 16,
    `vector.hnsw.ef_construction`: 100
  }
}
```

Relationship index:
```cypher
CYPHER 25
CREATE VECTOR INDEX rel_embedding IF NOT EXISTS
FOR ()-[r:HAS_CHUNK]-() ON (r.embedding)
OPTIONS { indexConfig: { `vector.dimensions`: 768, `vector.similarity_function`: 'cosine' } }
```

Multi-label index (2026.01+ only, vector-3.0 provider):
```cypher
CYPHER 25
CREATE VECTOR INDEX multi_chunk IF NOT EXISTS
FOR (n:Chunk|Document) ON n.embedding
OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' } }
```

**Index config reference:**

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `vector.dimensions` | INTEGER 1–4096 | none | Required; must match embedding model exactly |
| `vector.similarity_function` | STRING | `'cosine'` | `'cosine'` or `'euclidean'` |
| `vector.quantization.enabled` | BOOLEAN | `true` | Reduces storage; slight accuracy tradeoff; needs vector-2.0+ (5.18+) |
| `vector.hnsw.m` | INTEGER 1–512 | `16` | HNSW graph connections; higher = better recall, more memory |
| `vector.hnsw.ef_construction` | INTEGER 1–3200 | `100` | Build-time candidates; higher = better recall, slower build |

**Similarity function choice:**

| Use case | Function |
|---|---|
| Normalized embeddings (OpenAI, Cohere, Voyage, Google) | `'cosine'` |
| Unnormalized / raw distance matters | `'euclidean'` |

---

## Step 2 — Wait for Index ONLINE

Index builds asynchronously — do NOT query until ONLINE:
```cypher
SHOW VECTOR INDEXES YIELD name, state, populationPercent
WHERE name = 'chunk_embedding'
RETURN name, state, populationPercent
```

Poll every 5s until `state = 'ONLINE'` and `populationPercent = 100.0`. If `state = 'FAILED'` → stop, check logs.

Shell poll (cypher-shell):
```bash
until cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "SHOW VECTOR INDEXES YIELD name, state WHERE name='chunk_embedding' RETURN state" \
  | grep -q ONLINE; do
  sleep 5
done
```

---

## Step 3 — Ingest Embeddings

Batch UNWIND pattern (use for > 100 nodes — never one-node-per-transaction):
```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(uri, auth=(user, password))

def embed_batch(texts: list[str]) -> list[list[float]]:
    response = openai_client.embeddings.create(
        model="text-embedding-3-small", input=texts
    )
    return [r.embedding for r in response.data]

def store_embeddings(records: list[dict], batch_size: int = 500):
    expected_dim = 1536  # must match vector.dimensions
    texts = [r["text"] for r in records]
    embeddings = embed_batch(texts)
    for emb in embeddings:
        assert len(emb) == expected_dim, f"Dim mismatch: {len(emb)} != {expected_dim}"
    rows = [{"id": r["id"], "embedding": emb}
            for r, emb in zip(records, embeddings)]
    for i in range(0, len(rows), batch_size):
        driver.execute_query(
            "UNWIND $rows AS row MATCH (c:Chunk {id: row.id}) SET c.embedding = row.embedding",
            rows=rows[i:i+batch_size]
        )
```

❌ Never create index after embeddings are already stored — always create index first.
✅ Create index → poll ONLINE → ingest embeddings.

---

## Step 4 — Run Vector Search

### SEARCH clause (2026.01+, preferred)

```cypher
CYPHER 25
MATCH (c:Chunk)
  SEARCH c IN (
    VECTOR INDEX chunk_embedding
    FOR $queryEmbedding
    LIMIT 10
  ) SCORE AS score
RETURN c.text, score
ORDER BY score DESC
```

With in-index filter (AND only — no OR/NOT):
```cypher
CYPHER 25
MATCH (c:Chunk)
  SEARCH c IN (
    VECTOR INDEX chunk_embedding
    FOR $queryEmbedding
    WHERE c.source = $source AND c.lang = 'en'
    LIMIT 10
  ) SCORE AS score
RETURN c.text, c.source, score
ORDER BY score DESC
```

### Procedure fallback (2025.x)

```cypher
CYPHER 25
CALL db.index.vector.queryNodes('chunk_embedding', 10, $queryEmbedding)
YIELD node AS c, score
WHERE c.source = $source
RETURN c.text, score
ORDER BY score DESC
```

Relationship index procedure:
```cypher
CYPHER 25
CALL db.index.vector.queryRelationships('rel_embedding', 5, $queryEmbedding)
YIELD relationship AS r, score
RETURN r.text, score
```

**SEARCH clause hard limits:**
- `WHERE` inside SEARCH: AND predicates only; no OR, NOT, list ops, string ops, VECTOR/LIST/POINT types
- Index name cannot be a parameter (`$indexName` not allowed — use literal string)
- Binding variable must come from the enclosing MATCH pattern
- Query vector cannot reference the binding variable

---

## Step 5 — Combine with Graph Traversal (simple cases)

Vector search as entry point, then graph hop:
```cypher
CYPHER 25
MATCH (c:Chunk)
  SEARCH c IN (
    VECTOR INDEX chunk_embedding
    FOR $queryEmbedding
    LIMIT 10
  ) SCORE AS score
MATCH (c)<-[:HAS_CHUNK]-(a:Article)
OPTIONAL MATCH (a)-[:MENTIONS]->(org:Organization)
RETURN c.text, a.title, score, collect(DISTINCT org.name) AS organizations
ORDER BY score DESC
```

For full retrieval_query pipelines, HybridCypherRetriever, or `neo4j-graphrag` library → delegate to `neo4j-graphrag-skill`.

---

## Embedding Provider Quick-Reference

| Provider / Model | Dimensions | Similarity | Notes |
|---|---|---|---|
| OpenAI text-embedding-3-small | 1536 | cosine | Default; reducible to 256–1536 via `dimensions=` param |
| OpenAI text-embedding-3-large | 3072 | cosine | Reducible to 256–3072 |
| OpenAI text-embedding-ada-002 | 1536 | cosine | Legacy; prefer 3-small |
| Cohere embed-v3 (English) | 1024 | cosine | Use `input_type='search_document'` at ingest, `'search_query'` at query |
| Voyage voyage-3-large | 1024 | cosine | High quality; needs `voyage-ai` package |
| Google text-embedding-004 | 768 | cosine | Via Vertex AI |
| Ollama nomic-embed-text | 768 | cosine | Local dev/testing |
| Ollama mxbai-embed-large | 1024 | cosine | Local; production-quality |

`vector.dimensions` must exactly match model output — no auto-truncation.

---

## Vector Functions

Ad-hoc similarity (not for kNN search — use index for that):
```cypher
MATCH (a:Chunk {id: $id1}), (b:Chunk {id: $id2})
RETURN vector.similarity.cosine(a.embedding, b.embedding) AS sim
// vector.similarity.euclidean(a, b) — same signature, 0–1 range

// vector_distance (2025.10+) — metrics: EUCLIDEAN, EUCLIDEAN_SQUARED, MANHATTAN, COSINE, DOT, HAMMING
// Returns distance (lower = more similar, inverse of similarity)
RETURN vector_distance(a.embedding, b.embedding, 'COSINE') AS dist

// vector_dimension_count (2025.10+)
RETURN vector_dimension_count(n.embedding) AS dims

// vector_norm (2025.20+) — metrics: EUCLIDEAN, MANHATTAN
RETURN vector_norm(n.embedding, 'EUCLIDEAN') AS norm
```

Convert LIST to typed VECTOR:
```cypher
// vector(value, dimension, coordinateType)
// coordinateType: FLOAT64, FLOAT32, INTEGER8/16/32/64
WITH vector([1.0, 2.0, 3.0], 3, 'FLOAT32') AS v
RETURN vector_dimension_count(v)
```

---

## Index Management

```cypher
-- Show all vector indexes with config
SHOW VECTOR INDEXES YIELD name, state, populationPercent,
  labelsOrTypes, properties, indexConfig
RETURN name, state, populationPercent, labelsOrTypes, properties, indexConfig;

-- Drop (node data unchanged — only index structure removed)
DROP INDEX chunk_embedding IF EXISTS;

-- No ALTER VECTOR INDEX — to change dimensions or similarity function:
-- 1. DROP INDEX old_index IF EXISTS
-- 2. CREATE VECTOR INDEX new_index ... with new OPTIONS
-- 3. Re-generate all embeddings with new model
-- 4. Poll until ONLINE
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `IllegalArgumentException: Index dimension mismatch` | Stored embedding dim ≠ `vector.dimensions` | Fix embed generation; drop + recreate index with correct dim |
| Search returns incomplete results | Index still `POPULATING` | Poll until `state = 'ONLINE'` |
| `Unknown procedure db.index.vector.queryNodes` | Neo4j < 5.11 | No vector index support below 5.11; upgrade |
| `SEARCH clause not available` | Neo4j < 2026.01 | Use `queryNodes()` procedure |
| `OR/NOT not allowed in SEARCH WHERE` | SEARCH in-index filter restriction | Move complex predicates to outer WHERE after SEARCH |
| Zero results from correct query | Wrong similarity function or all-zeros embedding | Verify with `vector.similarity.cosine()`; check embed call succeeded |
| Score always 1.0 | All-zeros or identical vectors | Embedding generation failed; add dimension assertion before ingest |
| `vector.quantization.enabled` option rejected | provider vector-1.0 (Neo4j < 5.18) | Omit quantization option or upgrade to 5.18+ |

---

## Checklist
- [ ] `vector.dimensions` matches embedding model output exactly
- [ ] Vector index created before ingesting embeddings
- [ ] Similarity function chosen explicitly (`cosine` for normalized, `euclidean` for distance-based)
- [ ] Index polled to `state = 'ONLINE'` before first query
- [ ] Dimension validated on every embedding before ingest
- [ ] `SEARCH` clause only on Neo4j >= 2026.01; procedure fallback on 2025.x
- [ ] SEARCH `WHERE` uses AND-only predicates with scalar types
- [ ] Batch UNWIND pattern used for > 100 nodes
- [ ] If model changes: drop index → recreate with new dimensions → re-generate all embeddings

---

## References
Load on demand:
- [Vector index docs](https://neo4j.com/docs/cypher-manual/25/indexes/semantic-indexes/vector-indexes/)
- [SEARCH clause docs](https://neo4j.com/docs/cypher-manual/25/clauses/search/)
- [Vector functions docs](https://neo4j.com/docs/cypher-manual/25/functions/vector/)
