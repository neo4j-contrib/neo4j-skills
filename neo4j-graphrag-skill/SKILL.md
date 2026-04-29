---
name: neo4j-graphrag-skill
description: Build GraphRAG retrieval pipelines and knowledge graphs on Neo4j using the
  neo4j-graphrag Python package (formerly neo4j-genai). Covers retriever selection
  (VectorRetriever, HybridRetriever, VectorCypherRetriever, HybridCypherRetriever,
  Text2CypherRetriever), retrieval_query Cypher fragments, query_params, pipeline
  wiring (GraphRAG + LLM), SimpleKGPipeline for doc-to-graph extraction, embedder
  setup, index creation, and LangChain/LlamaIndex integration. Does NOT handle plain
  vector search without graph traversal — use neo4j-vector-search-skill. Does NOT
  handle GDS analytics — use neo4j-gds-skill. Does NOT handle agent memory — use
  neo4j-agent-memory-skill. Does NOT handle Cypher authoring — use neo4j-cypher-skill.
version: 1.0.0
status: active
allowed-tools: Bash WebFetch
---

# Neo4j GraphRAG Skill

## When to Use

- Building GraphRAG retrieval pipelines with `neo4j-graphrag` Python package
- Choosing between VectorRetriever, HybridRetriever, VectorCypherRetriever, HybridCypherRetriever
- Writing `retrieval_query` Cypher fragments that traverse the graph after vector lookup
- Wiring retriever + LLM into a `GraphRAG` pipeline
- Constructing a knowledge graph from documents with `SimpleKGPipeline`
- Debugging low retrieval quality (when to use graph traversal vs plain vector)
- Integrating Neo4j with LangChain (`langchain-neo4j`), LlamaIndex, or Haystack

## When NOT to Use

- **Plain vector/semantic search without graph traversal** → `neo4j-vector-search-skill`
- **GDS algorithms (PageRank, Louvain, node embeddings)** → `neo4j-gds-skill`
- **Agent long-term memory** → `neo4j-agent-memory-skill`
- **Writing raw Cypher queries** → `neo4j-cypher-skill`
- **Document chunking / loading only** → `neo4j-document-import-skill`

---

## Step 1 — Install

```bash
pip install neo4j-graphrag
# LLM/embedder extras (choose one or more):
pip install neo4j-graphrag[openai]        # OpenAI + AzureOpenAI
pip install neo4j-graphrag[google]        # VertexAI
pip install neo4j-graphrag[anthropic]     # Anthropic
pip install neo4j-graphrag[ollama]        # Ollama (local)
pip install neo4j-graphrag[cohere]        # Cohere
pip install neo4j-graphrag[sentence-transformers]  # local embeddings

# BREAKING: old package `neo4j-genai` is deprecated — imports also changed:
pip uninstall neo4j-genai
# neo4j_genai.retrievers → neo4j_graphrag.retrievers
# neo4j_genai.generation → neo4j_graphrag.generation
```

Requires: Python ≥ 3.10, Neo4j ≥ 5.18.1 or Aura ≥ 5.18.0.

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

---

## Step 3 — Create Indexes (run once)

```cypher
-- Vector index (all retrievers need this)
CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
} };

-- Fulltext index (Hybrid retrievers only)
CREATE FULLTEXT INDEX chunk_fulltext IF NOT EXISTS
FOR (c:Chunk) ON EACH [c.text];

-- Confirm ONLINE before ingesting:
SHOW INDEXES YIELD name, state
WHERE name IN ['chunk_embedding', 'chunk_fulltext']
RETURN name, state;
-- Both must show state = 'ONLINE'
```

If index not ONLINE: wait, poll every 5s. Do NOT start ingestion until ONLINE.

---

## Step 4 — Core Pattern (HybridCypherRetriever)

```python
from neo4j import GraphDatabase
from neo4j_graphrag.retrievers import HybridCypherRetriever
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.llm import OpenAILLM

driver = GraphDatabase.driver("neo4j+s://<host>:7687", auth=("neo4j", "<password>"))
embedder = OpenAIEmbeddings(model="text-embedding-3-small")  # 1536 dims — match index

# retrieval_query: Cypher fragment executed after vector lookup.
# `node` = matched node from vector index   (AUTO-INJECTED — do NOT declare)
# `score` = similarity float                (AUTO-INJECTED — do NOT declare)
# MUST include RETURN clause. MUST return `score` column.
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

llm = OpenAILLM(model_name="gpt-4o", model_params={"temperature": 0})
rag = GraphRAG(retriever=retriever, llm=llm)

response = rag.search(query_text="Who does Alice work for?", retriever_config={"top_k": 5})
print(response.answer)
```

---

## Step 5 — query_params (Parameterized retrieval_query)

Pass runtime parameters into `retrieval_query` via `retriever_config`:

```python
retrieval_query = """
MATCH (node)<-[:HAS_CHUNK]-(article:Article)-[:MENTIONS]->(org:Organization)
WHERE org.name = $entity_name
RETURN node.text AS chunk_text, article.title AS title, score
"""

retriever = VectorCypherRetriever(
    driver=driver,
    index_name="chunk_embedding",
    retrieval_query=retrieval_query,
    embedder=embedder,
)

# Pass query_params inside retriever_config on each search:
response = rag.search(
    query_text="What happened at Apple?",
    retriever_config={"top_k": 10, "query_params": {"entity_name": "Apple"}},
)

# Direct retriever call (without GraphRAG wrapper):
results = retriever.search(
    query_text="What happened at Apple?",
    top_k=10,
    query_params={"entity_name": "Apple"},
)
```

---

## Step 6 — Filters (Pre-filter before vector search)

```python
# Filter reduces candidate pool BEFORE vector similarity ranking
results = retriever.search(
    query_text="quarterly results",
    top_k=5,
    filters={"date": {"$gte": "2024-01-01"}},
)
# Supported operators: $eq $ne $lt $lte $gt $gte $between $in $like $ilike
```

---

## Step 7 — VectorRetriever (return_properties)

```python
from neo4j_graphrag.retrievers import VectorRetriever

retriever = VectorRetriever(
    driver=driver,
    index_name="chunk_embedding",
    embedder=embedder,
    return_properties=["text", "source", "page_number"],  # subset of node props
)
# No retrieval_query needed — returns node properties directly
```

---

## Step 8 — Text2CypherRetriever (no embedder)

```python
from neo4j_graphrag.retrievers import Text2CypherRetriever

# LLM generates Cypher from natural language; no vector index needed
retriever = Text2CypherRetriever(
    driver=driver,
    llm=OpenAILLM(model_name="gpt-4o"),
    neo4j_schema=None,   # auto-fetched from db; or pass string
    examples=["Q: Who works at Neo4j? A: MATCH (p:Person)-[:WORKS_AT]->(c:Company {name:'Neo4j'}) RETURN p.name"],
)
results = retriever.search(query_text="Which people work at Neo4j?")
```

If `neo4j_schema=None`: retriever fetches schema automatically. For large schemas, pass a trimmed string to reduce LLM prompt size.

---

## Step 9 — SimpleKGPipeline (Document → Knowledge Graph)

```python
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
import asyncio

pipeline = SimpleKGPipeline(
    llm=OpenAILLM(model_name="gpt-4o"),
    driver=driver,
    embedder=embedder,
    # Schema: list of entity types and relation types to extract
    entities=["Person", "Organization", "Location"],
    relations=["WORKS_AT", "LOCATED_IN", "KNOWS"],
    # Optional: detailed schema with descriptions and properties
    # schema={"node_types": [...], "relationship_types": [...], "patterns": [...]},
    on_error="IGNORE",               # "RAISE" or "IGNORE"
    perform_entity_resolution=True,  # merge similar entities (default True)
    from_file=False,                 # True = pass file_path; False = pass text=
)

# Run from text:
asyncio.run(pipeline.run_async(text=document_text))

# Run from file:
asyncio.run(pipeline.run_async(file_path="path/to/doc.pdf"))

# Attach metadata to Document node:
asyncio.run(pipeline.run_async(
    text=document_text,
    document_metadata={"source": "annual_report_2024", "author": "CFO"},
))
```

Structured output (OpenAI/VertexAI only — improves reliability):

```python
pipeline = SimpleKGPipeline(
    llm=OpenAILLM(model_name="gpt-4o", model_params={"use_structured_output": True}),
    ...
)
```

---

## Step 10 — Custom Prompt Template

```python
from neo4j_graphrag.generation.prompts import RagTemplate

custom_template = RagTemplate(
    template="""Answer the question using ONLY the context below.
Context: {context}
Question: {query_text}
Answer:""",
    expected_inputs=["context", "query_text"],
)

rag = GraphRAG(retriever=retriever, llm=llm, prompt_template=custom_template)
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: neo4j_genai` | Old package installed | `pip uninstall neo4j-genai && pip install neo4j-graphrag` |
| `retrieval_query` returns 0 rows | Missing `MATCH` or wrong rel direction | Add `EXPLAIN` prefix; verify node/rel names with `CALL db.schema.visualization()` |
| `KeyError: 'score'` in results | `retrieval_query` missing `score` in RETURN | Add `score` to every `retrieval_query` RETURN clause |
| `score` variable not found | Declared `score` as Cypher variable | Remove it — `score` is auto-injected; never re-declare |
| `node` variable not found | Wrong variable name in retrieval_query | Use exactly `node` (lowercase); auto-injected by retriever |
| Embedding dimension mismatch | Index created with different dims | Drop index, recreate with correct `vector.dimensions`, re-embed all chunks |
| `IndexNotFoundError` | Index name typo or index not ONLINE | `SHOW INDEXES YIELD name, state` — verify name and state=ONLINE |
| Low recall on hybrid search | Fulltext index not on right property | Fulltext index must cover same property as `node.text` in retrieval_query |
| `perform_entity_resolution` slow | Large corpus with many entities | Set `perform_entity_resolution=False` for initial testing; enable in production |
| `TypeError: coroutine` | Calling `pipeline.run_async()` without `await`/`asyncio.run()` | Wrap in `asyncio.run(pipeline.run_async(...))` |
| Empty KG after pipeline run | `on_error="IGNORE"` masks extraction failures | Temporarily set `on_error="RAISE"` to see LLM extraction errors |

---

## Embedder Quick Reference

```python
from neo4j_graphrag.embeddings import (
    OpenAIEmbeddings,           # OpenAI text-embedding-3-*
    AzureOpenAIEmbeddings,      # Azure-hosted OpenAI
    VertexAIEmbeddings,         # Google Vertex AI
    MistralAIEmbeddings,        # Mistral
    CohereEmbeddings,           # Cohere embed-v3
    OllamaEmbeddings,           # Local via Ollama
    SentenceTransformerEmbeddings,  # Local HuggingFace
)

# Dimension mapping (must match vector index):
# text-embedding-3-small → 1536
# text-embedding-3-large → 3072
# text-embedding-ada-002 → 1536
# all-MiniLM-L6-v2       → 384
```

All embedders include automatic rate limiting with exponential backoff.

---

## LLM Quick Reference

```python
from neo4j_graphrag.llm import (
    OpenAILLM,
    AzureOpenAILLM,
    AnthropicLLM,
    VertexAILLM,
    MistralAILLM,
    CohereLLM,
    OllamaLLM,
)
# Any LangChain chat model also accepted by GraphRAG/SimpleKGPipeline
```

---

## GraphRAG.search() Full Signature

```python
response = rag.search(
    query_text="...",
    retriever_config={
        "top_k": 5,              # candidates per search (default 5)
        "query_params": {...},   # passed to retrieval_query Cypher
        "filters": {...},        # pre-filter before vector search
    },
    return_context=False,        # True: include retrieved chunks in response
    response_fallback="No context found.",  # returned when retriever yields nothing
)
# response.answer → str
# response.retriever_result → RawSearchResult (if return_context=True)
```

---

## Failure Recovery

- 0 results from retrieval: run `retriever.search()` directly (skip LLM); check `top_k`, index name, embedding dims
- LLM hallucinating: reduce `top_k`, improve `retrieval_query` to return more specific context
- Slow queries: add `LIMIT` inside `retrieval_query` on expensive expansions; use `filters` to pre-reduce candidates
- KG builder produces empty graph: set `on_error="RAISE"`, check LLM extraction output, verify entity/relation names match schema
- Embedding dimension mismatch: `SHOW INDEXES YIELD name, options` — check `vector.dimensions`

---

## References

- [references/retrievers.md](references/retrievers.md) — full retriever API, all constructor params, result_formatter, ToolsRetriever, external DB retrievers
- [references/kg-builder.md](references/kg-builder.md) — SimpleKGPipeline advanced config, chunking options, schema modes, entity resolution
- [GraphRAG Python Docs](https://neo4j.com/docs/neo4j-graphrag-python/current/)
- [neo4j-graphrag GitHub](https://github.com/neo4j/neo4j-graphrag-python)
- [GraphAcademy: Constructing Knowledge Graphs](https://graphacademy.neo4j.com/courses/genai-graphrag-python/)

---

## Checklist

- [ ] `neo4j-genai` uninstalled; `neo4j-graphrag` installed; import paths updated
- [ ] Vector index ONLINE before ingesting or querying
- [ ] Fulltext index ONLINE if using Hybrid retriever
- [ ] Embedding dims match `vector.dimensions` in index config
- [ ] `retrieval_query` includes `node` and `score` in RETURN clause (both required)
- [ ] `node` and `score` NOT re-declared in `retrieval_query` — auto-injected
- [ ] `query_params` passed via `retriever_config` or direct `retriever.search()` arg
- [ ] `retriever_config={"top_k": N}` set on `rag.search()` (default 5)
- [ ] `SimpleKGPipeline.run_async()` called with `asyncio.run()`
- [ ] `on_error="RAISE"` used during development; switch to `"IGNORE"` in production
- [ ] Credentials in env vars; never hardcoded
