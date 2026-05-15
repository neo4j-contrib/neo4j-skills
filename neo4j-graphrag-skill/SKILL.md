---
name: neo4j-graphrag-skill
description: Build GraphRAG retrieval pipelines on Neo4j using the neo4j-graphrag Python
  package (v1.16.0+). Covers retriever selection (VectorRetriever, HybridRetriever,
  VectorCypherRetriever, HybridCypherRetriever, Text2CypherRetriever, ToolsRetriever),
  external vector DB retrievers (Weaviate, Pinecone, Qdrant), retrieval_query Cypher
  fragments, query_params, filters, GraphRAG pipeline wiring (GraphRAG + LLM + prompt),
  all LLM providers (OpenAI, Anthropic, VertexAI, Bedrock, Cohere, Mistral, Ollama),
  embedder setup, index creation, token usage tracking, Cypher 25 SEARCH clause, and
  LangChain/LlamaIndex integration. Does NOT handle KG construction — use
  neo4j-document-import-skill. Does NOT handle plain vector search — use
  neo4j-vector-index-skill. Does NOT handle GDS analytics — use neo4j-gds-skill.
  Does NOT handle agent memory — use neo4j-agent-memory-skill.
version: 1.1.0
status: active
allowed-tools: Bash WebFetch
---

# Neo4j GraphRAG Skill

## When to Use

- Building GraphRAG retrieval pipelines with `neo4j-graphrag` Python package
- Choosing between VectorRetriever, HybridRetriever, VectorCypherRetriever, HybridCypherRetriever
- Writing `retrieval_query` Cypher fragments for graph-augmented context
- Wiring retriever + LLM into a `GraphRAG` pipeline
- Using LLM-routed multi-retriever with `ToolsRetriever`
- Debugging low retrieval quality
- Integrating Neo4j with LangChain, LlamaIndex, or Haystack

## When NOT to Use

- **KG construction from documents** → `neo4j-document-import-skill`
- **Plain vector/semantic search without graph traversal** → `neo4j-vector-index-skill`
- **Hybrid search that combines vector with fulltext or other ranked sources** → `neo4j-vector-index-skill`
- **GDS algorithms (PageRank, Louvain, node embeddings)** → `neo4j-gds-skill`
- **Agent long-term memory** → `neo4j-agent-memory-skill`
- **Writing raw Cypher queries** → `neo4j-cypher-skill`

---

## Retriever Selection

```
Has fulltext index?
  YES → Hybrid variants (HybridRetriever / HybridCypherRetriever)
  NO  → Vector variants (VectorRetriever / VectorCypherRetriever)

Need graph traversal after vector lookup?
  YES → Cypher variants (VectorCypherRetriever / HybridCypherRetriever)
  NO  → plain variants

Natural-language-to-Cypher?        → Text2CypherRetriever (no embedder needed)
LLM should route between retrievers? → ToolsRetriever
Vectors stored in external DB?      → WeaviateNeo4jRetriever / PineconeNeo4jRetriever / QdrantNeo4jRetriever
```

| Retriever | Vector | Fulltext | Graph | Best For |
|---|:---:|:---:|:---:|---|
| `VectorRetriever` | ✓ | — | — | Baseline semantic search |
| `HybridRetriever` | ✓ | ✓ | — | Better recall, no graph expansion |
| `VectorCypherRetriever` | ✓ | — | ✓ | GraphRAG without fulltext |
| `HybridCypherRetriever` | ✓ | ✓ | ✓ | **Production GraphRAG — default** |
| `Text2CypherRetriever` | — | — | ✓ | NL→Cypher, no embedder |
| `ToolsRetriever` | varies | varies | varies | LLM-routed multi-retriever |
| `WeaviateNeo4jRetriever` | ✓ | — | ✓ | Vectors in Weaviate |
| `PineconeNeo4jRetriever` | ✓ | — | ✓ | Vectors in Pinecone |
| `QdrantNeo4jRetriever` | ✓ | — | ✓ | Vectors in Qdrant |

---

## Install

```bash
pip install neo4j-graphrag[openai]        # OpenAI LLM + embeddings
pip install neo4j-graphrag[anthropic]     # Anthropic Claude
pip install neo4j-graphrag[google]        # Vertex AI / Gemini
pip install neo4j-graphrag[bedrock]       # Amazon Bedrock (boto3)
pip install neo4j-graphrag[cohere]        # Cohere
pip install neo4j-graphrag[mistralai]     # MistralAI
pip install neo4j-graphrag[ollama]        # Ollama (local)
pip install neo4j-graphrag[weaviate]      # Weaviate external retriever
pip install neo4j-graphrag[pinecone]      # Pinecone external retriever
pip install neo4j-graphrag[qdrant]        # Qdrant external retriever
```

Requires: Python >= 3.10, `neo4j >= 5.17.0` (driver 6.x supported).

---

## Step 2 — Choose Retriever

```
Has fulltext index? YES → Hybrid variants (better recall)
                   NO  → Vector variants (baseline)

Needs graph context after vector lookup? YES → Cypher variants
                                         NO  → plain variants

For natural-language-to-Cypher? → Text2CypherRetriever (no embedder needed)
For multi-tool LLM routing?     → ToolsRetriever
Using external vector DB?       → WeaviateNeo4jRetriever / PineconeNeo4jRetriever / QdrantNeo4jRetriever
```

| Retriever | Vector | Fulltext | Graph | When to use |
|---|:---:|:---:|:---:|---|
| `VectorRetriever` | ✓ | — | — | Baseline; quick start |
| `HybridRetriever` | ✓ | ✓ | — | Better recall; no graph context |
| `VectorCypherRetriever` | ✓ | — | ✓ | GraphRAG without fulltext |
| `HybridCypherRetriever` | ✓ | ✓ | ✓ | **Production GraphRAG — default choice** |
| `Text2CypherRetriever` | — | — | ✓ | LLM generates Cypher; no embedder |
| `ToolsRetriever` | varies | varies | varies | Multi-retriever LLM routing |

For custom Cypher hybrid search outside the `neo4j-graphrag` retriever APIs, use `neo4j-vector-index-skill`.

**Vector backend selection [v1.16+, auto]**: on Neo4j 2026.01+ all four vector/hybrid retrievers auto-route through the Cypher 25 `SEARCH ... WHERE` clause when filters are SEARCH-compatible (simple AND comparisons) and all filter props are declared in the index `WITH [n.prop]` list. `$or`, `$in`, `$like`, or undeclared props → automatic fallback to `db.index.vector.queryNodes()` procedure path (with warning log). Declare filterable properties via `filterable_properties=[...]` on `create_vector_index()`.

---

## Step 3 — Create Indexes (run once)

```cypher
// Vector index (all retrievers need this)
CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
} };

// Fulltext index (Hybrid retrievers only)
CREATE FULLTEXT INDEX chunk_fulltext IF NOT EXISTS
FOR (c:Chunk) ON EACH [c.text];

// Confirm ONLINE before ingesting:
SHOW INDEXES YIELD name, state
WHERE name IN ['chunk_embedding', 'chunk_fulltext']
RETURN name, state;
// Both must show state = 'ONLINE'
```

If index not ONLINE: wait, poll every 5s. Do NOT start ingestion until ONLINE.

---

## Step 4 — Core Pattern (HybridCypherRetriever)

```python
from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import HybridCypherRetriever

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
embedder = OpenAIEmbeddings(model="text-embedding-3-large")  # OPENAI_API_KEY from env

# retrieval_query: Cypher fragment executed after the vector/fulltext lookup.
# Auto-injected variables:  node  (matched node)   score  (similarity float)
# MUST include a RETURN clause.  score must appear in RETURN.
retrieval_query = """
MATCH (node)<-[:HAS_CHUNK]-(article:Article)
OPTIONAL MATCH (article)-[:MENTIONS]->(org:Organization)
RETURN node.text AS chunk_text,
       article.title AS article_title,
       collect(DISTINCT org.name) AS mentioned_organizations,
       score
"""

retriever = HybridCypherRetriever(
    driver=driver,
    vector_index_name="chunk_embedding",
    fulltext_index_name="chunk_fulltext",
    retrieval_query=retrieval_query,
    embedder=embedder,
)

llm = OpenAILLM(model_name="gpt-4.1", model_params={"temperature": 0})

rag = GraphRAG(
    retriever=retriever,
    llm=llm,
)

response = rag.search(
    query_text="Who does Alice work for?",
    retriever_config={"top_k": 5},
)
print(response.answer)
driver.close()
```

---

## VectorCypherRetriever

```python
from neo4j_graphrag.retrievers import VectorCypherRetriever

retriever = VectorCypherRetriever(
    driver=driver,
    index_name="chunk_embedding",
    retrieval_query=retrieval_query,
    embedder=embedder,
)

response = rag.search(
    query_text="What happened at Apple?",
    retriever_config={"top_k": 10},
)
```

---

## Text2CypherRetriever

Translates natural language to Cypher using an LLM. **No embedder required.**

> **Security (v1.16.0+):** Every LLM-generated Cypher is run through `EXPLAIN` first.
> Any statement classified as write/destructive raises `Text2CypherRetrievalError` instead
> of executing — prevents prompt-injection attacks.

```python
from neo4j_graphrag.retrievers import Text2CypherRetriever

retriever = Text2CypherRetriever(
    driver=driver,
    llm=OpenAILLM(model_name="gpt-4.1"),
    neo4j_schema=None,       # None = auto-fetch schema from DB; pass string to trim
    examples=[
        "Q: Who works at Neo4j? A: MATCH (p:Person)-[:WORKS_AT]->(c:Company {name:'Neo4j'}) RETURN p.name"
    ],
)
results = retriever.search(query_text="Which people work at Neo4j?")
```

---

## ToolsRetriever (LLM-routed multi-retriever)

```python
from neo4j_graphrag.retrievers import ToolsRetriever

tools_retriever = ToolsRetriever(
    llm=llm,
    retrievers=[vector_retriever, text2cypher_retriever],
)
# LLM decides which retriever(s) to invoke per query

# Convert any retriever to a standalone Tool:
tool = vector_retriever.convert_to_tool()
```

---

## Filters (pre-filter before vector search)

```python
results = retriever.search(
    query_text="quarterly earnings",
    top_k=5,
    filters={
        "date": {"$gte": "2024-01-01"},
        "source": {"$eq": "10-K"},
    },
)
# Operators: $eq  $ne  $lt  $lte  $gt  $gte  $between  $in  $like  $ilike
```

---

## query_params (parameterized retrieval_query)

```python
retrieval_query = """
MATCH (node)<-[:HAS_CHUNK]-(a:Article)-[:MENTIONS]->(org:Organization {name: $entity_name})
RETURN node.text, a.title, score
"""

# Pass via retriever.search directly:
results = retriever.search(
    query_text="What happened at Apple?",
    top_k=10,
    query_params={"entity_name": "Apple"},
)

# Or via GraphRAG.search:
response = rag.search(
    query_text="What happened at Apple?",
    retriever_config={"top_k": 10, "query_params": {"entity_name": "Apple"}},
)
```

---

## Cypher 25 SEARCH Clause (v1.16.0, Neo4j 2026.x+)

```python
# Enable SEARCH clause syntax in vector/hybrid retrievers (requires Neo4j 2026+)
retriever = VectorRetriever(
    driver=driver,
    index_name="chunk_embedding",
    embedder=embedder,
    use_search_clause=True,
)
```

---

## ORDER BY on Cypher Retrievers (v1.16.0)

```python
results = retriever.search(
    query_text="...",
    top_k=10,
    order_by="score DESC",
)
```

If `neo4j_schema=None`: retriever fetches schema automatically. For large schemas, pass a trimmed string to reduce LLM prompt size.

**Destructive-query guard [v1.16+]**: `Text2CypherRetriever` runs `EXPLAIN` on the generated Cypher before execution and rejects queries that produce writes (`CREATE`, `MERGE`, `DELETE`, `SET`, `REMOVE`, etc.). LLM-generated writes are never executed against the graph.


---

## Custom Prompt Template

```python
from neo4j_graphrag.generation.prompts import RagTemplate

template = RagTemplate(
    template="""Answer using ONLY the context below.
Context: {context}
Question: {query_text}
Answer:""",
    expected_inputs=["context", "query_text"],
)

rag = GraphRAG(retriever=retriever, llm=llm, prompt_template=template)
```

---

## return_context and response_fallback

```python
response = rag.search(
    query_text="...",
    retriever_config={"top_k": 5},
    return_context=True,                        # include raw retrieved chunks
    response_fallback="No relevant context.",   # skip LLM call if retriever returns nothing
)
print(response.answer)
print(response.retriever_result)    # RawSearchResult when return_context=True
```

---

## Message History (multi-turn)

```python
from neo4j_graphrag.message_history import InMemoryMessageHistory

history = InMemoryMessageHistory()
r1 = rag.search(query_text="Who is Alice?", message_history=history)
r2 = rag.search(query_text="Where does she work?", message_history=history)
```

---

## External Retrievers

```python
# --- Weaviate ---
from neo4j_graphrag.retrievers import WeaviateNeo4jRetriever
import weaviate

weaviate_client = weaviate.connect_to_local()
retriever = WeaviateNeo4jRetriever(
    driver=driver,
    client=weaviate_client,
    collection="Chunk",
    id_property_external="neo4j_id",
    id_property_neo4j="id",
    retrieval_query=retrieval_query,
    node_label_neo4j="Chunk",       # optional: speeds up Neo4j lookup
)

# --- Pinecone ---
from neo4j_graphrag.retrievers import PineconeNeo4jRetriever
from pinecone import Pinecone

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
retriever = PineconeNeo4jRetriever(
    driver=driver,
    client=pc,
    index_name="my-index",
    id_property_neo4j="id",
    retrieval_query=retrieval_query,
)

# --- Qdrant ---
from neo4j_graphrag.retrievers import QdrantNeo4jRetriever
from qdrant_client import QdrantClient

retriever = QdrantNeo4jRetriever(
    driver=driver,
    client=QdrantClient(url="http://localhost:6333"),
    collection_name="Chunk",
    id_property_external="neo4j_id",
    id_property_neo4j="id",
    id_property_getter=lambda hit: hit.payload["neo4j_id"],  # custom ID extraction
    retrieval_query=retrieval_query,
)
```

---

## LLM Providers

All implement `LLMBase`. All support sync + async, tool calling, and automatic rate limiting.

| Class | Extra | Notes |
|---|---|---|
| `OpenAILLM` | `openai` | Structured output; tool calling |
| `AzureOpenAILLM` | `openai` | Azure-hosted OpenAI |
| `AnthropicLLM` | `anthropic` | Tool calling |
| `VertexAILLM` | `google` | Structured output; tool calling |
| `MistralAILLM` | `mistralai` | Tool calling |
| `CohereLLM` | `cohere` | |
| `OllamaLLM` | `ollama` | Local; tool calling |
| `BedrockLLM` | `bedrock` | Boto3 Converse API; added v1.15.0 |

```python
from neo4j_graphrag.llm import (
    OpenAILLM, AzureOpenAILLM, AnthropicLLM, VertexAILLM,
    MistralAILLM, CohereLLM, OllamaLLM, BedrockLLM,
)

llm = OpenAILLM(model_name="gpt-4.1", model_params={"temperature": 0})
llm = AnthropicLLM(model_name="claude-3-5-sonnet-20241022")
llm = VertexAILLM(model_name="gemini-2.0-flash")
llm = OllamaLLM(model_name="llama3")           # no API key needed
llm = BedrockLLM(model_id="anthropic.claude-3-5-sonnet-20241022-v2:0")

# Token usage tracking (v1.15.0+)
response = llm.invoke("Hello")
# response.usage → LLMUsage(request_tokens=N, response_tokens=M, total_tokens=T)

# Graceful resource cleanup (v1.16.0+)
llm.close()         # sync
await llm.aclose()  # async
```

---

## Embedder Providers

All include automatic rate limiting with tenacity exponential backoff.

| Class | Extra | Dims |
|---|---|---|
| `OpenAIEmbeddings` | `openai` | 3072 / 1536 |
| `AzureOpenAIEmbeddings` | `openai` | varies |
| `VertexAIEmbeddings` | `google` | 768 |
| `MistralAIEmbeddings` | `mistralai` | 1024 |
| `CohereEmbeddings` | `cohere` | 1024 |
| `OllamaEmbeddings` | `ollama` | varies |
| `SentenceTransformerEmbeddings` | `sentence-transformers` | 384+ |
| `BedrockEmbeddings` | `bedrock` | varies; added v1.15.0 |

```python
from neo4j_graphrag.embeddings import (
    OpenAIEmbeddings, VertexAIEmbeddings, CohereEmbeddings,
    OllamaEmbeddings, SentenceTransformerEmbeddings, BedrockEmbeddings,
)

embedder = OpenAIEmbeddings(model="text-embedding-3-large")   # 3072 dims
embedder = OpenAIEmbeddings(model="text-embedding-3-small")   # 1536 dims
embedder = SentenceTransformerEmbeddings(model="all-MiniLM-L6-v2")  # 384 dims, local
embedder = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0")
```

---

## Index Setup

```python
from neo4j_graphrag.indexes import create_vector_index

# Vector index — adjust dimensions to match your embedding model
create_vector_index(
    driver,
    name="chunk_embedding",
    label="Chunk",
    embedding_property="embedding",
    dimensions=1536,
    similarity_fn="cosine",       # or "euclidean"
)

# Fulltext index (run as Cypher)
# CREATE FULLTEXT INDEX chunk_fulltext IF NOT EXISTS
#   FOR (c:Chunk) ON EACH [c.text]
```

---

## Schema Inspection

```python
from neo4j_graphrag.schema import get_schema, get_structured_schema

schema_str = get_schema(driver, sample=1000)           # human-readable string
schema_dict = get_structured_schema(driver, sample=1000)  # dict with labels/rels/props
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: neo4j_genai` | Old package name | `pip uninstall neo4j-genai && pip install neo4j-graphrag` |
| `retrieval_query` returns 0 rows | Missing `MATCH` or wrong rel direction | `EXPLAIN` the fragment; check `CALL db.schema.visualization()` |
| `KeyError: 'score'` in results | `retrieval_query` RETURN missing `score` | Add `score` to every `retrieval_query` RETURN clause |
| `score` variable not found | `score` re-declared in `retrieval_query` | Do **not** re-declare `score` — it is auto-injected |
| `Text2CypherRetrievalError` | LLM generated a write statement | Expected security behavior (v1.16.0+); refine prompt or schema |
| `TypeError: coroutine` | Missing `await` / `asyncio.run()` | Wrap async calls: `asyncio.run(pipeline.run_async(...))` |
| Empty results from HybridRetriever | Fulltext index not ONLINE | `SHOW INDEXES YIELD name, state WHERE state <> 'ONLINE'` |
| Embedding dimension mismatch | Index dims ≠ model dims | Recreate index with correct `dimensions=` value |

---

## Verification Checklist

- [ ] `neo4j-graphrag` (not `neo4j-genai`) installed; `neo4j >= 5.17.0` driver
- [ ] Vector index ONLINE before ingesting embeddings or running retriever
- [ ] Fulltext index ONLINE if using Hybrid variants
- [ ] Embedding dims in `create_vector_index` match the embedder output
- [ ] `retrieval_query` returns `node` and `score` in RETURN (not re-declared)
- [ ] `query_params` passed via `retriever_config` on `rag.search()` (not on retriever constructor)
- [ ] API keys in env vars; never hardcoded
- [ ] `llm.close()` called when done to release resources

---

## References

Load on demand:
- [neo4j-graphrag package docs](https://neo4j.com/docs/neo4j-graphrag-python/current/)
- [RAG & GraphRAG user guide](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html)
- [KG Builder user guide](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html)
- [GitHub — neo4j-graphrag-python](https://github.com/neo4j/neo4j-graphrag-python)
- [Examples folder](https://github.com/neo4j/neo4j-graphrag-python/tree/main/examples)
