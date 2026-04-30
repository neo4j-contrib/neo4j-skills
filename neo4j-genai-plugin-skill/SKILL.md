---
name: neo4j-genai-plugin-skill
description: Use Neo4j GenAI Plugin ai.text.* functions and procedures for in-Cypher
  embedding generation, text completion, structured output, chat, tokenization, and
  batch ingestion. Covers ai.text.embed(), ai.text.embedBatch(), ai.text.completion(),
  ai.text.structuredCompletion(), ai.text.aggregateCompletion(), ai.text.chat(),
  ai.text.tokenCount(), ai.text.chunkByTokenLimit(), and provider configuration for
  OpenAI, Azure OpenAI, VertexAI, and Amazon Bedrock. Requires CYPHER 25. Replaces
  deprecated genai.vector.encode(). Use when writing pure-Cypher GraphRAG, embedding
  nodes in-graph, generating structured maps from prompts, or calling LLMs inside
  Cypher queries. Does NOT handle neo4j-graphrag Python library pipelines — use
  neo4j-graphrag-skill. Does NOT handle vector index creation/search — use
  neo4j-vector-index-skill.
version: 1.0.0
status: active
allowed-tools: Bash WebFetch
---

## When to Use
- Generating embeddings inside Cypher without external Python (`ai.text.embed()`)
- Batch-embedding nodes/chunks during ingestion (`ai.text.embedBatch()`)
- Calling LLMs directly in Cypher for completions or GraphRAG (`ai.text.completion()`)
- Extracting structured JSON maps from LLM inside Cypher (`ai.text.structuredCompletion()`)
- Aggregating LLM summaries over grouped rows (`ai.text.aggregateCompletion()`)
- Stateful chat sessions in Cypher (`ai.text.chat()`)
- Counting tokens or chunking text by token limit (`ai.text.tokenCount()`, `ai.text.chunkByTokenLimit()`)

## When NOT to Use
- **Python-based GraphRAG pipelines** (VectorCypherRetriever, HybridCypherRetriever) → `neo4j-graphrag-skill`
- **Vector index CREATE / kNN search / SEARCH clause** → `neo4j-vector-index-skill`
- **GDS embeddings** (FastRP, Node2Vec) → `neo4j-gds-skill`
- **Fulltext / keyword search** → `neo4j-cypher-skill`

---

## Prerequisites

**CYPHER 25 required** for all `ai.*` functions. Two ways to enable:

```cypher
// Per-query prefix (self-managed, no admin rights needed):
CYPHER 25 MATCH (n:Chunk) ...

// Per-database default (admin; applies to all sessions):
ALTER DATABASE neo4j SET DEFAULT LANGUAGE CYPHER 25
```

**Installation:**
- **Aura**: GenAI plugin enabled by default — no action needed
- **Self-managed JAR**: copy plugin JAR to `plugins/` directory
- **Docker**: `--env NEO4J_PLUGINS='["genai"]'`

---

## Provider Config Quick Reference

All `ai.text.*` functions accept a `configuration :: MAP` as last argument.

| Provider string | Required keys | Notes |
|---|---|---|
| `'openai'` | `token`, `model` | `token` = OpenAI API key |
| `'azure-openai'` | `token`, `resource`, `model` | `token` = OAuth2 bearer; `resource` = Azure resource name |
| `'vertexai'` | `model`, `project`, `region`, `token` or `apiKey` | `publisher` defaults to `'google'` |
| `'bedrock-titan'` | `model`, `region`, `accessKeyId`, `secretAccessKey` | Embedding only |
| `'bedrock-nova'` | `model`, `region`, `accessKeyId`, `secretAccessKey` | Completion only |

Optional for all: `vendorOptions :: MAP` passes provider-specific extras (e.g. `{ dimensions: 1024 }` for OpenAI).

❌ Never hardcode API key literals. ✅ Always use `$param` passed via driver parameters dict.

Full provider config table → [references/providers.md](references/providers.md)

---

## Embedding

### Single embed [2025.12]

```cypher
CYPHER 25
MATCH (c:Chunk)
WHERE c.embedding IS NULL
WITH c
CALL {
  WITH c
  SET c.embedding = ai.text.embed(c.text, 'openai', {
    token: $openaiKey,
    model: 'text-embedding-3-small'
  })
} IN TRANSACTIONS OF 500 ROWS
```

`ai.text.embed()` returns `VECTOR` — directly storable and queryable in a vector index.

### Batch embed procedure [2025.12]

```cypher
CYPHER 25
MATCH (c:Chunk) WHERE c.embedding IS NULL
WITH collect(c) AS chunks
UNWIND chunks AS c
WITH c.text AS text, c AS node
CALL ai.text.embedBatch(text, 'openai', { token: $openaiKey, model: 'text-embedding-3-small' })
YIELD index, resource, vector
MATCH (c:Chunk {text: resource})
SET c.embedding = vector
```

Procedure signature: `CALL ai.text.embedBatch(resource, provider, config) YIELD index, resource, vector`

### List configured embed providers

```cypher
CYPHER 25
CALL ai.text.embed.providers()
YIELD name, requiredConfigType, optionalConfigType, defaultConfig
RETURN name, requiredConfigType
```

---

## Text Completion [2025.12]

```cypher
CYPHER 25
RETURN ai.text.completion(
  'Summarize: ' + $text,
  'openai',
  { token: $openaiKey, model: 'gpt-4o-mini' }
) AS summary
```

Returns `STRING`.

### Aggregate completion — summarize across rows

```cypher
CYPHER 25
MATCH (c:Chunk)-[:PART_OF]->(a:Article {id: $articleId})
RETURN ai.text.aggregateCompletion(
  c.text,
  'Summarize the following article chunks in 3 sentences',
  'openai',
  { token: $openaiKey, model: 'gpt-4o-mini' }
) AS summary
```

`value` parameter = each row's STRING fed to the LLM. Uses `toString()` for non-string values.

---

## Pure-Cypher GraphRAG Pattern [2025.12]

Embed question → vector search → graph traverse → LLM completion — all in one Cypher query:

```cypher
CYPHER 25
WITH ai.text.embed($question, 'openai', { token: $openaiKey, model: 'text-embedding-3-small' }) AS qEmbedding
CALL db.index.vector.queryNodes('chunk_embedding', 10, qEmbedding) YIELD node AS chunk, score
MATCH (chunk)<-[:HAS_CHUNK]-(article:Article)
OPTIONAL MATCH path = shortestPath((article)-[*..3]-(other:Article))
WITH chunk, article, collect(DISTINCT other.title) AS related, score
ORDER BY score DESC LIMIT 5
WITH collect(chunk.text + '\n[Source: ' + article.title + ']') AS context, $question AS question
RETURN ai.text.completion(
  'Answer based on context:\n' + reduce(s='', c IN context | s + c + '\n') + '\nQuestion: ' + question,
  'openai',
  { token: $openaiKey, model: 'gpt-4o-mini' }
) AS answer
```

Key insight (Bergman): shortest path between seed nodes surfaces relationships not visible from direct neighbors alone.

---

## Structured Output [2025.12]

Returns `MAP` — directly storable as node properties or used downstream in Cypher.

```cypher
CYPHER 25
MATCH (p:Product {id: $productId})
WITH p,
  ai.text.structuredCompletion(
    'Extract key attributes from: ' + p.description,
    {
      type: 'object',
      properties: {
        category: { type: 'string' },
        tags: { type: 'array', items: { type: 'string' } },
        priceRange: { type: 'string', enum: ['budget', 'mid', 'premium'] }
      },
      required: ['category', 'tags', 'priceRange'],
      additionalProperties: false
    },
    'openai',
    { token: $openaiKey, model: 'gpt-4o-mini' }
  ) AS extracted
SET p.category = extracted.category,
    p.priceRange = extracted.priceRange
WITH p, extracted.tags AS tags
UNWIND tags AS tag
MERGE (t:Tag {name: tag})
MERGE (p)-[:TAGGED]->(t)
```

### Aggregate structured completion — extract across multiple rows

```cypher
CYPHER 25
MATCH (:User {id: $userId})-[:ORDERED]->(o:Order)-[:CONTAINS]->(p:Product)
RETURN ai.text.aggregateStructuredCompletion(
  p.name + ': ' + p.category,
  'Build a shopping profile for this user',
  {
    type: 'object',
    properties: {
      preferredCategories: { type: 'array', items: { type: 'string' } },
      spendingTier: { type: 'string', enum: ['economy', 'standard', 'premium'] }
    },
    required: ['preferredCategories', 'spendingTier']
  },
  'openai',
  { token: $openaiKey, model: 'gpt-4o-mini' }
) AS profile
```

---

## Chat [2025.12]

Supported providers: **openai** and **azure-openai** only.

```cypher
// Start new conversation (chatId = null → new session)
CYPHER 25
WITH ai.text.chat(
  'Hello, who are you?',
  null,
  'openai',
  { token: $openaiKey, model: 'gpt-4o-mini' }
) AS result
RETURN result.message AS reply, result.chatId AS sessionId

// Continue conversation (pass returned chatId)
CYPHER 25
WITH ai.text.chat(
  'What did I just ask you?',
  $chatId,
  'openai',
  { token: $openaiKey, model: 'gpt-4o-mini' }
) AS result
RETURN result.message AS reply, result.chatId AS sessionId
```

Returns `MAP { message: STRING, chatId: STRING }`. Store `chatId` to continue session.

---

## Tokenization & Chunking [2025.12]

```cypher
// Count tokens before sending to LLM
CYPHER 25
RETURN ai.text.tokenCount($text, 'openai', { token: $openaiKey, model: 'gpt-4o-mini' }) AS tokenCount

// Chunk text by token limit (no external dependencies)
CYPHER 25
UNWIND ai.text.chunkByTokenLimit($longText, 512, 'gpt-4', 50) AS chunk
MERGE (c:Chunk { text: chunk })
```

`ai.text.chunkByTokenLimit(input, limit, model='gpt-4', overlap=0)` — `model` controls tokenizer; `overlap` = tokens of overlap between chunks.

---

## Write Gate

`SET node.embedding = ai.text.embed(...)` and `SET node.* = ai.text.structuredCompletion(...)` write to the graph.

Before bulk writes:
1. Count nodes first: `MATCH (c:Chunk) WHERE c.embedding IS NULL RETURN count(c)`
2. Verify config with one test node before batch
3. Use `CALL { ... } IN TRANSACTIONS OF 500 ROWS` for batches > 1000 nodes
4. Require explicit confirmation before executing

---

## Deprecated — Do NOT Use

| Old function | Replacement |
|---|---|
| `genai.vector.encode()` [deprecated] | `ai.text.embed()` |
| `genai.vector.encodeBatch()` [deprecated] | `CALL ai.text.embedBatch()` |
| `genai.vector.listEncodingProviders()` [deprecated] | `CALL ai.text.embed.providers()` |

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Unknown function 'ai.text.embed'` | Missing CYPHER 25 prefix OR plugin not installed | Add `CYPHER 25` prefix; verify plugin installed |
| `Cypher version not supported` | Using `CYPHER 25` on Neo4j < 5.20 or missing plugin | Upgrade Neo4j; ensure GenAI plugin loaded |
| `Configuration key 'token' missing` | Provider config map incomplete | Check required keys for provider (see table above) |
| `null` returned from embed | Wrong model name or provider auth failed | Test with `RETURN ai.text.embed('test', 'openai', {token:$k, model:'text-embedding-3-small'})` standalone |
| `Unsupported provider` | Provider string typo (case-sensitive, lowercase) | Use `'openai'` not `'OpenAI'`; run `CALL ai.text.embed.providers()` |
| `ai.text.chat` fails on VertexAI | Chat only supported on openai/azure-openai | Switch to openai/azure-openai for chat |

---

## Checklist
- [ ] `CYPHER 25` prefix present on every ai.text.* query
- [ ] GenAI plugin installed (Aura: automatic; self-managed: JAR in plugins/)
- [ ] API key passed as `$param`, never as literal string
- [ ] `model` key explicit in config (no silent defaults)
- [ ] Provider string lowercase (`'openai'`, `'vertexai'`, `'bedrock-titan'`)
- [ ] Bulk writes use `IN TRANSACTIONS OF 500 ROWS`; count target nodes first
- [ ] `genai.vector.encode()` replaced with `ai.text.embed()` [2025.12]
- [ ] Chat sessions: store returned `chatId` for continuation; only openai/azure-openai supported
- [ ] Structured output schema uses `additionalProperties: false` to prevent hallucination keys

---

## References
- [Full provider config](references/providers.md) — all required/optional keys per provider
- [Official docs](https://neo4j.com/docs/genai/plugin/current/)
- [API reference](https://neo4j.com/docs/genai/plugin/current/reference/functions-procedures/)
