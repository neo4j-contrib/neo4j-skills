---
name: neo4j-vector-search-skill
description: >
  Use when setting up vector indexes in Neo4j, running vector similarity search,
  embedding data into the graph (storing embeddings on nodes), using the SEARCH
  clause (Neo4j 2026.02.1+) or db.index.vector.queryNodes() procedure, or choosing
  embedding providers and dimension configuration. Does NOT handle GraphRAG pipelines
  with graph traversal after vector lookup — use neo4j-graphrag-skill. Does NOT
  handle fulltext (keyword) search — use neo4j-cypher-skill.
status: draft
version: 0.1.0
allowed-tools: Bash, WebFetch
---

# Neo4j Vector Search Skill

> **Status: Draft / WIP** — Content is a placeholder. Reference files to be added.

## When to Use

- Creating a vector index on a node property (embeddings)
- Running vector similarity search (semantic/nearest-neighbor lookup)
- Storing embeddings on graph nodes as part of an ingestion pipeline
- Using the new `SEARCH` clause (Neo4j 2026.02.1+) or the legacy `db.index.vector.queryNodes()` procedure
- Choosing similarity function (cosine vs euclidean) and embedding dimensions
- Post-filtering vector results with graph traversal (but retrieval_query patterns → graphrag-skill)

## When NOT to Use

- **GraphRAG pipelines (retrieval_query, HybridCypherRetriever)** → use `neo4j-graphrag-skill`
- **Fulltext / keyword search (FULLTEXT INDEX, `db.index.fulltext.queryNodes`)** → use `neo4j-cypher-skill`
- **GDS node embeddings (FastRP, Node2Vec)** → use `neo4j-gds-skill`

---

## Version Detection

```cypher
-- Run this first to determine which syntax to use:
CALL dbms.components() YIELD versions RETURN versions[0] AS neo4j_version
```

| Result | Syntax to use |
|---|---|
| `2026.02.1` or higher | `SEARCH` clause (in-index filtering supported) |
| `2025.x` | `db.index.vector.queryNodes()` procedure |

---

## Post-Creation Verification

After creating a vector index, always verify the config before ingesting data:
```cypher
SHOW INDEXES YIELD name, state, indexConfig
WHERE name = 'chunk_embedding'
RETURN name, state, indexConfig;
-- state must be 'ONLINE'; check `vector.dimensions` matches your embedding model
```

Also validate at ingestion time:
```python
expected_dim = 1536  # must match OPTIONS `vector.dimensions`
assert len(embedding) == expected_dim, \
    f"Embedding dimension mismatch: got {len(embedding)}, expected {expected_dim}"
```

---

## Core Patterns

### Create vector index

```cypher
CYPHER 25
CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,            -- match your embedding model output
    `vector.similarity_function`: 'cosine' -- or 'euclidean'
  }
}
```

### Vector search — new SEARCH clause (2026.02.1+)

```cypher
CYPHER 25
MATCH (c)
  SEARCH c IN (
    VECTOR INDEX chunk_embedding
    FOR $embedding
    WHERE c.source = $source        -- in-index metadata filter
    LIMIT 10
  ) SCORE AS score
RETURN c.text, score
ORDER BY score DESC
```

### Vector search — legacy procedure (2025.x)

```cypher
CYPHER 25
CALL db.index.vector.queryNodes('chunk_embedding', 10, $embedding)
YIELD node AS c, score
WHERE c.source = $source           -- post-filter (not in-index)
RETURN c.text, score
ORDER BY score DESC
```

### Store embedding on ingest (Python)

```python
from neo4j import GraphDatabase
from openai import OpenAI

openai = OpenAI()
driver = GraphDatabase.driver(uri, auth=(user, password))

def embed(text: str) -> list[float]:
    return openai.embeddings.create(
        model="text-embedding-3-small", input=text
    ).data[0].embedding

# Store chunk with embedding
driver.execute_query(
    "MERGE (c:Chunk {id: $id}) SET c.text = $text, c.embedding = $embedding",
    id="chunk-1", text="Alice works at Acme.", embedding=embed("Alice works at Acme.")
)
```

---

## Embedding Dimension Reference

| Provider / Model | Dimensions |
|---|---|
| OpenAI text-embedding-3-small | 1536 (default) or 256–1536 |
| OpenAI text-embedding-3-large | 3072 (default) or 256–3072 |
| OpenAI text-embedding-ada-002 | 1536 |
| Voyage voyage-3-large | 1024 |
| Cohere embed-v3 | 1024 |
| Google text-embedding-004 | 768 |
| Ollama nomic-embed-text | 768 |

---

## Checklist

- [ ] `vector.dimensions` matches the embedding model output dimension
- [ ] Vector index created before ingesting embeddings
- [ ] Similarity function chosen explicitly (`cosine` for normalized models; `euclidean` for unnormalized)
- [ ] `SEARCH` clause used only on Neo4j 2026.02.1+; procedure fallback for 2025.x
- [ ] Dimension mismatch will cause silent wrong results — verify index config after creation
- [ ] All existing embeddings re-generated if model or dimension changes (index must be dropped and recreated)

---

## References

- [Vector Search Docs](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/)
- [SEARCH clause (2026.x)](https://neo4j.com/docs/cypher-manual/current/clauses/search/)
- [Developer: Vector Search](https://neo4j.com/developer/genai-ecosystem/vector-search/)
- [GraphAcademy: Vector Indexes and Unstructured Data](https://graphacademy.neo4j.com/courses/llm-vectors-unstructured/)
