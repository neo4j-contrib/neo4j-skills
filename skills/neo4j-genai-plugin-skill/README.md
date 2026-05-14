# neo4j-genai-plugin-skill

Skill for calling LLM providers directly from Cypher using the Neo4j GenAI Plugin `ai.text.*` functions [2025.12].

**Covers:**
- `ai.text.embed()` / `ai.text.embedBatch()` — generate vector embeddings in Cypher; replaces deprecated `genai.vector.encode()`
- `ai.text.completion()` / `ai.text.aggregateCompletion()` — LLM text generation over query results
- `ai.text.structuredCompletion()` / `ai.text.aggregateStructuredCompletion()` — JSON Schema-validated structured output
- `ai.text.chat()` — stateful chat with `chatId` (OpenAI / Azure only)
- `ai.text.tokenCount()` / `ai.text.chunkByTokenLimit()` — tokenization and chunking helpers
- Provider discovery: `ai.text.embed.providers()`, `ai.text.completion.providers()`
- Provider configuration — OpenAI, Azure OpenAI, VertexAI, Amazon Bedrock
- Pure-Cypher GraphRAG: embed → vector search → graph traversal → completion in one query
- CYPHER 25 requirement: per-query prefix and `ALTER DATABASE` default
- Migration from deprecated `genai.vector.*` → `ai.text.*`

**Version / compatibility:**
- `ai.text.*` requires Neo4j 2025.12+ (self-managed) or Aura with GenAI Plugin enabled
- All functions require `CYPHER 25` prefix or `ALTER DATABASE neo4j SET DEFAULT LANGUAGE CYPHER 25`
- Provider strings are lowercase: `'openai'`, `'azure-openai'`, `'vertexai'`, `'bedrock-titan'`

**Not covered:**
- Vector index creation and management → `neo4j-vector-index-skill`
- GraphRAG pipelines via Python (`neo4j-graphrag` package) → `neo4j-graphrag-skill`
- KG construction from documents → `neo4j-document-import-skill`

**Install:**
```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-genai-plugin-skill
```

Or paste this link into your coding assistant:
https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-genai-plugin-skill
