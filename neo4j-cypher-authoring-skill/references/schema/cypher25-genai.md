> Source: manual — neo4j-cypher-authoring-skill v2026.02.0  generated: 2026-03-23
> See: https://neo4j.com/docs/cypher-manual/25/genai-integrations/

> **Availability**: The Neo4j GenAI plugin is **always-on in Aura**. For self-managed Neo4j 5+ and
> 2025.x+, it must be installed separately (`neo4j-genai-plugin.jar`). Only use `ai.*` functions
> when the schema context `capabilities` list includes `"genai"`. Aura instances may omit
> `genai` from capabilities — still safe to use `ai.*` on Aura.

# Neo4j GenAI Plugin — `ai.*` Functions

The GenAI plugin adds vector similarity scalar functions and (on Aura) inline embedding generation.
It does **not** replace vector index search — they serve different purposes.

---

## Scalar vs Top-K: Key Distinction

| Use case | Tool | Returns |
|---|---|---|
| Score similarity between **two known vectors** | `ai.similarity.*()` scalar function | A single FLOAT score |
| Find the **top-K most similar nodes** to a query vector | `db.index.vector.queryNodes()` or SEARCH clause | A ranked list of nodes + scores |

**Do NOT use `ai.similarity.*` to rank large result sets** — this requires materializing all vectors
and computing pairwise scores in the query layer. Use vector index search for top-K retrieval.

**Use `ai.similarity.*` when**: comparing two specific stored vectors; re-scoring a pre-filtered
candidate set (e.g., result of a property filter + OPTIONAL MATCH); computing distances between
embeddings you just created inline with `ai.embedding.*`.

---

## 1. Similarity Functions (`ai.similarity.*`)

### Cosine Similarity (range: −1 to 1; higher = more similar)

```cypher
CYPHER 25
MATCH (a:Product {id: $id1}), (b:Product {id: $id2})
RETURN ai.similarity.cosine(a.embedding, b.embedding) AS cosineSim
```

### Euclidean Similarity (range: 0 to 1; higher = closer)

```cypher
CYPHER 25
MATCH (a:Product {id: $id1}), (b:Product {id: $id2})
RETURN ai.similarity.euclidean(a.embedding, b.embedding) AS euclideanSim
```

### Re-scoring a candidate set (correct pattern)

```cypher
// Good: filter candidates with index first, then re-score against a second vector
CYPHER 25
CALL db.index.vector.queryNodes('productEmbeddings', 50, $queryVec)
YIELD node AS candidate, score AS baseScore
MATCH (candidate)-[:BELONGS_TO]->(cat:Category {name: $category})
RETURN candidate.name, ai.similarity.cosine(candidate.embedding, $refinementVec) AS refinedScore
ORDER BY refinedScore DESC LIMIT 10
```

---

## 2. Embedding Generation (`ai.embedding.*`) — Aura only

> `ai.embedding.*` is **Aura-only**. Requires a GenAI provider configured in the Aura workspace
> (OpenAI, Azure OpenAI, Vertex AI, or Amazon Bedrock). Not available on self-managed Neo4j
> even with the GenAI plugin installed.

```cypher
// Generate an embedding inline and use it for a vector index search
CYPHER 25
WITH ai.embedding.openai($textInput, {token: $apiKey}) AS queryVec
CALL db.index.vector.queryNodes('articleEmbeddings', 10, queryVec)
YIELD node AS article, score
RETURN article.title, score
ORDER BY score DESC
```

### Supported provider functions

| Function | Provider |
|---|---|
| `ai.embedding.openai(text, {token})` | OpenAI text-embedding-ada-002 (or configured model) |
| `ai.embedding.azureOpenai(text, {token, resource, deployment})` | Azure OpenAI |
| `ai.embedding.vertexAi(text, {token, project, location})` | Google Vertex AI |
| `ai.embedding.bedrock(text, {region, model})` | AWS Bedrock |

**Arguments**: first arg is the text string; second arg is a config map with auth details.
Dimensions depend on the configured model — must match the vector index dimensions.

---

## 3. Availability Check

```cypher
// Check if GenAI plugin is installed
CYPHER 25
SHOW FUNCTIONS WHERE name STARTS WITH 'ai.'
YIELD name RETURN count(name) AS genAiFunctions;
// 0 → GenAI plugin not installed; > 0 → available

// Check if embedding functions are available (Aura only)
CYPHER 25
SHOW FUNCTIONS WHERE name = 'ai.embedding.openai'
YIELD name RETURN count(name) > 0 AS embeddingAvailable;
```

---

## Key Rules

- **Capability gate**: use `ai.*` only when `"genai"` is in the schema context `capabilities` list,
  or when the target is confirmed to be Aura (which always has the plugin).
- **`ai.similarity.*` is scalar, not a search procedure**: it takes two LIST<FLOAT> arguments and
  returns a single FLOAT. It does NOT query an index.
- **Top-K retrieval** → always use `db.index.vector.queryNodes()` or the SEARCH clause, not
  `ai.similarity.*` in a scan.
- **`ai.embedding.*` is Aura-only**: never emit these on self-managed Neo4j, even with genai in
  capabilities — the function is not registered in the non-Aura plugin build.
- **Dimension mismatch**: embedding vectors from `ai.embedding.*` must match the target vector
  index's configured `vector.dimensions`. State this assumption in an inline comment if dimensions
  are not provided in the schema context.
