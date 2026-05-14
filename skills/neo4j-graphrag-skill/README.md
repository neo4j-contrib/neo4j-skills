# neo4j-graphrag-skill

Skill for building GraphRAG retrieval pipelines on Neo4j using the `neo4j-graphrag` Python package (formerly `neo4j-genai`).

**Covers:**
- Retriever selection: `VectorRetriever`, `HybridRetriever`, `VectorCypherRetriever`, `HybridCypherRetriever`, `Text2CypherRetriever`
- `retrieval_query` — Cypher fragments for post-vector graph traversal; `node` and `score` auto-injection
- `query_params` — parameterized retrieval queries
- Pipeline wiring: `GraphRAG(retriever=..., llm=...)` with `.search()`
- Embedder setup: `OpenAIEmbeddings`, `VertexAIEmbeddings`, etc.
- Index prerequisites: vector index + fulltext index for Hybrid retrievers
- Custom prompt templates via `prompt_template`
- LangChain (`langchain-neo4j`), LlamaIndex, and Haystack integrations
- Pre-filter vector search with `filters=`
- Text2CypherRetriever for exact structured queries (counts, lookups)

**Version / compatibility:**
- `neo4j-graphrag` v1.7+ (renamed from `neo4j-genai`; uninstall old package if present)
- Python ≥ 3.10

**Not covered:**
- KG construction from documents (`SimpleKGPipeline`) → `neo4j-document-import-skill`
- Pure-Cypher GraphRAG with `ai.text.*` → `neo4j-genai-plugin-skill`
- Vector index creation → `neo4j-vector-index-skill`

**Install:**
```bash
pip install neo4j-graphrag
```

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-graphrag-skill
```

Or paste this link into your coding assistant:
https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-graphrag-skill
