---
name: neo4j-vector-index-skill
description: Create and manage Neo4j vector indexes, run vector similarity search (ANN/kNN),
  store embeddings on nodes or relationships, use SEARCH clause (Neo4j 2026.01+) or
  db.index.vector.queryNodes() procedure (pre-2026.01 fallback), configure HNSW and quantization
  options, pick similarity function and embedding provider dimensions, and batch-update
  embeddings. Use when tasks involve CREATE VECTOR INDEX, vector.dimensions, cosine/euclidean
  search, embedding ingestion pipelines, or semantic nearest-neighbor lookup in Neo4j.
  Does NOT handle GraphRAG retrieval_query graph traversal — use neo4j-graphrag-skill.
  Does NOT handle fulltext/keyword indexes (FULLTEXT INDEX, db.index.fulltext) — use neo4j-cypher-skill.
  Does NOT handle GDS graph embeddings (FastRP, Node2Vec) — use neo4j-gds-skill.
version: 1.0.0
compatibility: Neo4j >= 5.13 for GA vector indexes; prefer latest Neo4j/Cypher 25;
  SEARCH clause requires 2026.01+
allowed-tools: Bash WebFetch
---

## When to Use
- Creating a vector index (`CREATE VECTOR INDEX`) on nodes or relationships
- Running vector similarity / nearest-neighbor search
- Storing embeddings on graph nodes during ingestion
- Choosing similarity function, dimensions, HNSW params, or quantization
- Using `SEARCH` clause (2026.01+) or `db.index.vector.queryNodes()` for older deployments
- Batch-updating embeddings after model change
- Combining vector results with immediate graph neighborhood (full retrieval_query pipelines → `neo4j-graphrag-skill`)

## When NOT to Use
- **GraphRAG pipelines** (VectorCypherRetriever, HybridCypherRetriever, retrieval_query) → `neo4j-graphrag-skill`
- **Non-vector search and index admin** (`FULLTEXT INDEX`, `db.index.fulltext.*`, range/text/lookup indexes) → `neo4j-cypher-skill`
- **GDS graph embeddings** (FastRP, Node2Vec, GraphSAGE) → `neo4j-gds-skill`
- **Embedding provider configuration, auth, and full `ai.text.*` reference** → `neo4j-genai-plugin-skill`
- **Production memory sizing** (heap, page cache, OS filesystem cache for vector indexes) → Operations Manual: Vector index memory configuration

---

## Pre-flight — Determine Version and Store Format

Use the latest Neo4j version and Cypher 25 for new work. If supporting older deployments, version drives syntax choice:
```cypher
CALL dbms.components() YIELD versions RETURN versions[0] AS neo4j_version
```

| Version | Use |
|---|---|
| `2026.01` or higher | `SEARCH` clause (in-index filtering, preferred) |
| Earlier versions with vector index support | `db.index.vector.queryNodes()` procedure fallback |

For native `VECTOR` property storage, use Aura or self-managed Enterprise Edition with `block` store format. Check self-managed databases:
```cypher
SHOW DATABASES YIELD name, store
RETURN name, store
```
Use `VECTOR` only when `store` contains `block`; use `LIST<FLOAT>` on Community Edition or `aligned` stores.

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

Index with properties for filtered vector search (2026.01+ only):
```cypher
CYPHER 25
CREATE VECTOR INDEX chunk_embedding_filtered IF NOT EXISTS
FOR (c:Chunk) ON c.embedding
WITH [c.source, c.lang]
OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' } }
```

**Index config reference:**

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `vector.dimensions` | INTEGER 1–4096 | none | Optional but recommended; when set, must match embedding model exactly |
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

## Step 3 — Generate and Store Embeddings

Assumes source/chunk nodes already exist. Batch UNWIND pattern (use for > 100 nodes — never one-node-per-transaction):
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
            "UNWIND $rows AS row MATCH (c:Chunk {id: row.id}) CALL db.create.setNodeVectorProperty(c, 'embedding', row.embedding)",
            rows=rows[i:i+batch_size]
        )
```

Creating the index before storing embeddings avoids a later population step, but creating it after embeddings are stored is valid.
Always poll until the index is `ONLINE` before querying.

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

With in-index filter (requires filtered properties in the index `WITH` list):
```cypher
CYPHER 25
MATCH (c:Chunk)
  SEARCH c IN (
    VECTOR INDEX chunk_embedding_filtered
    FOR $queryEmbedding
    WHERE c.source = $source AND c.lang = 'en'
    LIMIT 10
  ) SCORE AS score
RETURN c.text, c.source, score
ORDER BY score DESC
```

### Procedure fallback (pre-2026.01; deprecated in 2026.04+)
```cypher
CALL db.index.vector.queryNodes('chunk_embedding', 10, $queryEmbedding)
YIELD node AS c, score
WHERE c.source = $source
RETURN c.text, score
ORDER BY score DESC
```

Relationship index procedure:
```cypher
CALL db.index.vector.queryRelationships('rel_embedding', 5, $queryEmbedding)
YIELD relationship AS r, score
RETURN r.text, score
```

**SEARCH clause hard limits:**
- `WHERE` inside `SEARCH` accepts property predicates on the `SEARCH` binding variable, joined with `AND`; filtered properties must be in the index `WITH` list.
- Unsupported: `OR`, `<>`, list operators, string operators, type predicates, `POINT`/`VECTOR`/`LIST` expressions, and comparisons to another property of the binding variable. `NOT` is only allowed for boolean properties.
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
RETURN vector.similarity.cosine(a.embedding, b.embedding) AS cosine_sim,
       vector.similarity.euclidean(a.embedding, b.embedding) AS euclidean_sim
```

For `VECTOR`-only functions such as `vector_distance()`, `vector_dimension_count()`, and `vector_norm()`, load the vector functions docs.

Convert LIST to typed VECTOR:
```cypher
// vector(value, dimension, coordinateType)
// coordinateType: FLOAT64, FLOAT32, INTEGER8/16/32/64
WITH vector([1.0, 2.0, 3.0], 3, FLOAT32) AS v
RETURN vector_dimension_count(v)
```

---

## Index Management

```cypher
// Show all vector indexes with config
SHOW VECTOR INDEXES YIELD name, state, populationPercent,
  labelsOrTypes, properties, indexConfig
RETURN name, state, populationPercent, labelsOrTypes, properties, indexConfig;

// Drop (node data unchanged — only index structure removed)
DROP INDEX chunk_embedding IF EXISTS;

// No ALTER VECTOR INDEX — to change index schema or options:
// 1. DROP INDEX old_index IF EXISTS
// 2. CREATE VECTOR INDEX new_index ... with new schema/OPTIONS
// 3. Poll until ONLINE
// Re-generate embeddings only if the embedding model or stored vectors change
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `IllegalArgumentException: Index dimension mismatch` | Query or stored embedding dim does not match configured `vector.dimensions` | Fix embed generation; drop + recreate index with correct dim |
| Search returns incomplete results | Index still `POPULATING` | Poll until `state = 'ONLINE'` |
| `Unknown procedure db.index.vector.queryNodes` | Neo4j version lacks vector index procedure | Use Neo4j 5.13+ for GA vector indexes; upgrade |
| `SEARCH clause not available` | Neo4j < 2026.01 | Use `queryNodes()` procedure, or upgrade for `SEARCH` |
| `OR/NOT not allowed in SEARCH WHERE` | SEARCH in-index filter restriction | Move unsupported predicates to outer WHERE after SEARCH |
| Zero results from correct query | Wrong similarity function or all-zeros embedding | Verify with `vector.similarity.cosine()`; check embed call succeeded |
| Score always 1.0 | Identical or duplicated vectors | Check embedding generation; add dimension assertion before ingest |
| `vector.quantization.enabled` option rejected | provider vector-1.0 (Neo4j < 5.18) | Omit quantization option or upgrade to 5.18+ |

---

## Checklist
- [ ] Configured `vector.dimensions`, if set, matches embedding model output exactly
- [ ] Vector index exists and is `ONLINE` before querying
- [ ] Similarity function chosen explicitly (`cosine` for normalized, `euclidean` for distance-based)
- [ ] Dimension validated on every embedding before ingest
- [ ] `SEARCH` clause only on Neo4j >= 2026.01; procedure fallback only for older deployments
- [ ] SEARCH `WHERE` uses AND-only predicates on supported properties included with index `WITH`
- [ ] Batch UNWIND pattern used for > 100 nodes
- [ ] If the embedding model/output dimension changes: re-generate embeddings and recreate the index

---

## In-Cypher Embedding Generation — ai.text.embed() [2025.11]

Generate embeddings at query time without external Python code. Use `ai.text.embed()` — the current API since [2025.11]:

```cypher
// Syntax (requires CYPHER 25)
CYPHER 25
// ai.text.embed(resource :: STRING, provider :: STRING, configuration :: MAP) :: VECTOR
```

Use lowercase provider strings (`'openai'`, `'vertexai'`, `'bedrock-titan'`, `'azure-openai'`) for consistency; identifiers are case-insensitive. Full provider config → `neo4j-genai-plugin-skill`.

SEARCH pattern (2026.01+) — embed at query time, search immediately:
```cypher
CYPHER 25
WITH ai.text.embed("my query", "openai", { token: $openaiKey, model: 'text-embedding-3-small' }) AS userEmbedding
MATCH (c:Chunk)
  SEARCH c IN (VECTOR INDEX chunk_embedding FOR userEmbedding LIMIT 6) SCORE AS score
RETURN c.text, score
ORDER BY score DESC
```

Procedure fallback pattern:
```cypher
CYPHER 25
WITH ai.text.embed(
    "What are good open source projects",
    "openai",
    { token: $openaiKey, model: 'text-embedding-3-small' }) AS userEmbedding
CALL db.index.vector.queryNodes('chunk_embedding', 6, userEmbedding)
YIELD node AS c, score
RETURN c.text, score
ORDER BY score DESC
```

❌ Never pass API key as literal string in production — use `$param` or `apoc.static.get()`.
✅ Use `$openaiKey` parameter; inject via driver params dict.

**Rule**: Use same model at ingest time and query time — embeddings from different models are not comparable.

**Deprecated** (still works but do not use in new code):
- `genai.vector.encode()` [deprecated] → use `ai.text.embed()` [2025.11]
- `genai.vector.encodeBatch()` [deprecated] → use `CALL ai.text.embedBatch()` [2025.11]
- `genai.vector.listEncodingProviders()` [deprecated] → use `CALL ai.text.embed.providers()` [2025.11]

For full `ai.text.*` reference (completion, structured output, chat, tokenization) → `neo4j-genai-plugin-skill`.

---

## Cypher-Based Embedding Ingestion — db.create.setNodeVectorProperty

Set vector property via Cypher (e.g. during LOAD CSV or MERGE pipeline):
```cypher
LOAD CSV WITH HEADERS FROM 'https://example.com/data.csv' AS row
MERGE (q:Question {text: row.question})
WITH q, row
CALL db.create.setNodeVectorProperty(q, 'embedding', apoc.convert.fromJsonList(row.question_embedding))
```

Use when embedding is already in CSV/JSON form as a string — `apoc.convert.fromJsonList()` converts `"[0.1,0.2,...]"` to `LIST<FLOAT>`.
For Python-generated embeddings, use the Python UNWIND batch pattern (Step 3) instead.

---

## Chunking Strategy Before Ingestion

Embedding models have token limits. Chunk before embedding.

**Strategy decision table:**

| Data type | Recommended strategy |
|---|---|
| API docs, structured pages | Split by method / endpoint / section |
| Prose documents, PDFs | Paragraph split (`\n\n`) with size cap |
| Arbitrary/mixed text | Character split with overlap |
| Audio/image | Equal-length segments |

**Python chunking pattern (LangChain `CharacterTextSplitter`):**
```python
from langchain_text_splitters import CharacterTextSplitter

splitter = CharacterTextSplitter(
    separator="\n\n",       # split on paragraph boundaries
    chunk_size=1500,        # max chars per chunk
    chunk_overlap=200,      # overlap to preserve cross-paragraph context
)
chunks = splitter.split_documents(documents)
```

**How splitter combines:**
1. Splits on `separator` (`\n\n`) → paragraph list
2. Combines paragraphs up to `chunk_size` chars
3. If single paragraph > `chunk_size` → kept as oversized chunk (not split further)
4. Last paragraph of chunk appended to start of next if ≤ `chunk_overlap` chars

**Batch embed + store pattern (large corpora):**
```python
BATCH_SIZE = 500  # tune: 100–1000 depending on model rate limits

for i in range(0, len(chunks), BATCH_SIZE):
    batch = chunks[i : i + BATCH_SIZE]
    texts = [c.page_content for c in batch]
    embeddings = embed_batch(texts)          # single API call for whole batch
    rows = [{"id": c.metadata["id"], "text": t, "embedding": emb}
            for c, t, emb in zip(batch, texts, embeddings)]
    driver.execute_query(
        """
        UNWIND $rows AS row
        MERGE (c:Chunk {id: row.id})
        SET c.text = row.text
        WITH c, row
        CALL db.create.setNodeVectorProperty(c, 'embedding', row.embedding)
        """,
        rows=rows
    )
```

**Overlapping chunks**: End of chunk N = start of chunk N+1. Improves recall for queries that span paragraph boundaries.

---

## Similarity Function — Extended Guidance

Existing table (Step 1) gives the basic rule. Additional guidance from course patterns:

**Choose based on training loss function:**
- Check embedding model docs — models trained with cosine loss → use `'cosine'`
- Models trained with L2/Euclidean loss → use `'euclidean'`
- When docs are silent: default to `'cosine'` (all major hosted APIs use it)

**Common pitfall — wrong similarity function:**
```
❌ Created index with 'euclidean' but model outputs L2-normalized vectors
   → scores are mathematically correct but rankings differ from expected cosine order
   → no error thrown; wrong results silently returned
✅ Verify: run vector.similarity.cosine(a.embedding, b.embedding) manually on known
   similar pairs — score should be > 0.9 for near-duplicate text
```

**Sanity check query after index creation:**
```cypher
MATCH (c:Chunk) WITH c LIMIT 2
WITH collect(c) AS nodes
RETURN vector.similarity.cosine(nodes[0].embedding, nodes[1].embedding) AS cosine_check,
       vector.similarity.euclidean(nodes[0].embedding, nodes[1].embedding) AS euclidean_check
```
If both return `null` → embeddings not set. If cosine returns `1.0` for unrelated chunks → check for duplicated or failed embedding generation.

---

## Gotchas — Extended

| Gotcha | Detail | Fix |
|---|---|---|
| Querying before the index is ONLINE | Inserting nodes before index exists is valid — index auto-populates. But querying during `POPULATING` returns partial results | Always poll `state = 'ONLINE'` before first query |
| Wrong dimensions — query-time failure | Stored vector dim ≠ `vector.dimensions` → `IllegalArgumentException` at query time, not at ingest time | Assert `len(emb) == expected_dim` before storing embeddings |
| Different models at ingest vs query | No error; cosine scores ~0.3–0.5 for clearly similar text | Use same model string/version for both; store model name as node metadata |
| Missing model or provider config | `ai.text.embed()` fails before returning a usable embedding | Test the embed call standalone; check `CYPHER 25 RETURN ai.text.embed(...)` before embedding into a pipeline |
| Large single-transaction ingest | One transaction for 10k nodes → OOM or timeout | Use `UNWIND $rows ... CALL IN TRANSACTIONS OF 500 ROWS` or Python batch loop |
| Chunk overlap not set | Adjacent chunks with no overlap → context at boundaries lost → poor recall for cross-paragraph queries | Set `chunk_overlap` ≥ 10% of `chunk_size` |

---

## References
Load on demand:
- [Vector index docs](https://neo4j.com/docs/cypher-manual/25/indexes/semantic-indexes/vector-indexes/)
- [SEARCH clause docs](https://neo4j.com/docs/cypher-manual/25/clauses/search/)
- [Vector functions docs](https://neo4j.com/docs/cypher-manual/25/functions/vector/)
- [ai.text.embed() / GenAI plugin docs](https://neo4j.com/docs/genai/plugin/current/) [2025.11] — replaces deprecated `genai.vector.encode()`
- [db.create.setNodeVectorProperty docs](https://neo4j.com/docs/operations-manual/current/reference/procedures/)
