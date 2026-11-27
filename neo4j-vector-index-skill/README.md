# neo4j-vector-index-skill

Skill for creating and querying vector indexes in Neo4j for semantic or structural similarity search.

**Covers:**
- Creating vector indexes: `CREATE VECTOR INDEX` with dimensions and similarity function
- Waiting for index `ONLINE` status; `SHOW VECTOR INDEXES`
- Embedding ingestion: Python batch loop with `UNWIND`, `db.create.setNodeVectorProperty`
- In-Cypher embedding with `ai.text.embed()` [2025.12] — replaces deprecated `genai.vector.encode()`
- Batch embedding procedure `ai.text.embedBatch()` for large datasets
- Vector search: `SEARCH` clause [2026.01+] and `db.index.vector.queryNodes()` procedure fallback
- Combining vector search with graph traversal (hybrid retrieval)
- Hybrid search, including semantic + lexical + structural sources
- Vector indexes over embeddings already written by GDS algorithms
- Chunking strategy before ingestion (fixed-size, sentence, semantic)
- Similarity function guidance: cosine vs euclidean — match your model's training loss
- Common errors: wrong dimensions, index not ONLINE, provider null returns

**Version / compatibility:**
- `SEARCH` clause requires Neo4j 2026.01+; `db.index.vector.queryNodes` available 5.x+
- `ai.text.embed()` requires Neo4j 2025.12+ and CYPHER 25; `genai.vector.encode()` is deprecated
- Vector type is native in CYPHER 25; stored as `LIST<FLOAT>` in older versions

**Not covered:**
- Full `ai.text.*` plugin reference (completion, chat, structured output) → `neo4j-genai-plugin-skill`
- GraphRAG pipelines with `neo4j-graphrag` → `neo4j-graphrag-skill`
- Fulltext-only / keyword-only search → `neo4j-cypher-skill`
- Computing GDS node embedding algorithms (FastRP, GraphSAGE) → `neo4j-gds-skill`

**Install:**
```bash
npx skills add https://github.com/neo4j/agent-skills --skill neo4j-vector-index-skill
```

Or paste this link into your coding assistant:
https://github.com/neo4j/agent-skills/tree/main/neo4j-vector-index-skill
