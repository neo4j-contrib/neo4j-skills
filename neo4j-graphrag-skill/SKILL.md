---
name: neo4j-graphrag-skill
description: >
  Use when building GraphRAG pipelines on Neo4j with the neo4j-graphrag Python
  package: VectorRetriever, VectorCypherRetriever, HybridRetriever,
  HybridCypherRetriever, retrieval_query graph traversal patterns, GraphRAG pipeline
  (retriever + LLM), SimpleKGPipeline for knowledge graph construction from documents,
  or LangChain/LlamaIndex Neo4j integrations. Does NOT handle plain vector search
  without graph traversal — use neo4j-vector-search-skill. Does NOT handle GDS
  analytics — use neo4j-gds-skill. Does NOT handle agent memory — use
  neo4j-agent-memory-skill.
status: draft
version: 0.1.0
allowed-tools: Bash, WebFetch
---

# Neo4j GraphRAG Skill

> **Status: Draft / WIP** — Content is a placeholder. Reference files for retrieval patterns to be added.

## When to Use

- Building GraphRAG retrieval pipelines with `neo4j-graphrag` Python package
- Choosing between VectorRetriever, VectorCypherRetriever, HybridCypherRetriever
- Writing `retrieval_query` Cypher fragments that traverse the graph after vector lookup
- Constructing a knowledge graph from documents with `SimpleKGPipeline`
- Integrating Neo4j with LangChain (`langchain-neo4j`), LlamaIndex, or Haystack
- Debugging low retrieval quality (when to use graph traversal vs plain vector)

## When NOT to Use

- **Plain vector/semantic search without graph traversal** → use `neo4j-vector-search-skill`
- **GDS algorithms (PageRank, Louvain, embeddings)** → use `neo4j-gds-skill`
- **Agent long-term memory** → use `neo4j-agent-memory-skill`
- **Document chunking + loading only** → use `neo4j-document-import-skill`

---

## Retriever Selection

```
Question involves multi-hop, co-occurrence, or relational reasoning?
  → YES: HybridCypherRetriever (best) or VectorCypherRetriever
  → NO: HybridRetriever (keyword + semantic) or VectorRetriever (baseline)

Have fulltext index? YES → include Hybrid variants (better recall)
Need graph context after retrieval? YES → include Cypher variants
```

| Retriever | Vector | Fulltext | Graph traversal | When to use |
|---|:---:|:---:|:---:|---|
| `VectorRetriever` | yes | no | no | Baseline — quick start |
| `HybridRetriever` | yes | yes | no | Better recall, no graph |
| `VectorCypherRetriever` | yes | no | yes | GraphRAG without fulltext |
| `HybridCypherRetriever` | yes | yes | yes | **Production GraphRAG** |

---

## Package Name

```bash
pip install neo4j-graphrag openai  # or any supported LLM/embedder
# IMPORTANT: old package was `neo4j-genai` — uninstall it if present
# pip uninstall neo4j-genai && pip install neo4j-graphrag
# Import paths changed: neo4j_graphrag.retrievers (not neo4j_genai.retrievers)
```

---

## Prerequisites (run once before ingesting)

```cypher
-- Fulltext index (required for Hybrid retrievers)
CREATE FULLTEXT INDEX chunk_fulltext IF NOT EXISTS
FOR (c:Chunk) ON EACH [c.text];

-- Vector index (required for all retrievers)
CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' } };

-- Confirm indexes are ONLINE before ingesting:
SHOW INDEXES YIELD name, state WHERE name IN ['chunk_fulltext','chunk_embedding']
RETURN name, state;  -- must be 'ONLINE'
```

---

## Core Pattern

```python
from neo4j import GraphDatabase
from neo4j_graphrag.retrievers import HybridCypherRetriever
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.llm import OpenAILLM

driver = GraphDatabase.driver("neo4j+s://<host>", auth=("neo4j", "<password>"))
embedder = OpenAIEmbeddings()

# retrieval_query: Cypher fragment executed after vector lookup.
# `node` and `score` are AUTO-INJECTED by the retriever — do NOT declare them.
# Additional parameters can be passed via query_params={} in retriever.search().
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

rag = GraphRAG(retriever=retriever, llm=OpenAILLM(model_name="gpt-4o"))
print(rag.search("Who does Alice work for?").answer)
```

### Knowledge graph construction

```python
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
import asyncio

pipeline = SimpleKGPipeline(
    llm=OpenAILLM(model_name="gpt-4o"),
    driver=driver,
    embedder=embedder,
    entities=["Person", "Organization", "Location"],
    relations=["WORKS_AT", "LOCATED_IN", "KNOWS"],
    on_error="IGNORE",
)
asyncio.run(pipeline.run_async(text=document_text))
```

---

## Embedding Dimension Note

Embedding dimensions must match the vector index. If you switch embedding models, drop and recreate the vector index and re-embed all chunks. Changing `vector.dimensions` on an existing index is not supported.

---

## Checklist

- [ ] Vector index and fulltext index created before ingesting data
- [ ] `retrieval_query` uses `node` and `score` variables (provided by retriever)
- [ ] `retrieval_query` returns at least `score` column
- [ ] Embedding dimensions match `vector.dimensions` in index config
- [ ] `query_params` passed to `retriever.search()` when `retrieval_query` uses named params
- [ ] `neo4j-genai` (old name) replaced with `neo4j-graphrag` in requirements

---

## Fetching Current Docs

```
https://neo4j.com/docs/llms.txt     ← full documentation index
https://neo4j.com/llms-full.txt     ← rich reference with code examples
```

## References

- [GraphRAG Python Docs](https://neo4j.com/docs/neo4j-graphrag-python/)
- [neo4j-graphrag GitHub](https://github.com/neo4j/neo4j-graphrag-python)
- [GraphRAG.com](https://graphrag.com/)
- [GraphAcademy: Constructing Knowledge Graphs with Neo4j GraphRAG](https://graphacademy.neo4j.com/courses/genai-graphrag-python/)
- [LangChain Neo4j Integration](https://neo4j.com/labs/genai-ecosystem/langchain/)
