# neo4j-vector-index-skill

Skill for creating and querying vector indexes in Neo4j for semantic similarity search.

**Covers:**
- Creating vector indexes: `CREATE VECTOR INDEX` with dimensions and similarity function
- Waiting for index `ONLINE` status; `SHOW VECTOR INDEXES`
- Embedding ingestion: Python batch loop with `UNWIND`, `db.create.setNodeVectorProperty`
- In-Cypher embedding with `ai.text.embed()` [2025.11] — replaces deprecated `genai.vector.encode()`
- Batch embedding procedure `ai.text.embedBatch()` for large datasets
- Vector search: `SEARCH` clause [2026.01+] and `db.index.vector.queryNodes()` compatibility fallback
- Combining vector search with graph traversal (hybrid retrieval)
- Chunking strategy before ingestion (fixed-size, sentence, semantic)
- Similarity function guidance: cosine vs euclidean — match your model's training loss
- Common errors: wrong dimensions, index not ONLINE, provider/configuration failures

**Version / compatibility:**
- Vector indexes are generally available from Neo4j 5.13; use the latest Neo4j and Cypher 25 for new work
- `SEARCH` clause requires Neo4j 2026.01+; `db.index.vector.queryNodes` is available in older vector-index deployments and deprecated in Neo4j 2026.04+
- `ai.text.embed()` requires Neo4j 2025.11+ and CYPHER 25; `genai.vector.encode()` is deprecated
- Native `VECTOR` storage is supported on Aura and on self-managed Enterprise Edition databases using `block` format.
  New EE databases default to `block` from Neo4j 5.22, but existing stores may differ; check self-managed databases with `SHOW DATABASES YIELD name, store RETURN name, store`.
  Community Edition or `aligned` databases should use `LIST<FLOAT>` compatibility workflows.

**Not covered:**
- Embedding provider configuration, auth, and full `ai.text.*` plugin reference → `neo4j-genai-plugin-skill`
- GraphRAG pipelines with `neo4j-graphrag` → `neo4j-graphrag-skill`
- Fulltext / keyword search, including `FULLTEXT INDEX` and `db.index.fulltext.*` → `neo4j-cypher-skill`
- GDS node embedding algorithms (FastRP, GraphSAGE) → `neo4j-gds-skill`
- General index administration beyond vector indexes, such as range, text, lookup, and fulltext indexes → `neo4j-cypher-skill`
- Production memory sizing and vector index memory configuration → Operations Manual: Vector index memory configuration

**Install:**
```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-vector-index-skill
```

Or paste this link into your coding assistant:
https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-vector-index-skill
