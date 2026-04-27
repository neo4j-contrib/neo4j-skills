---
name: neo4j-document-import-skill
description: >
  Use when importing unstructured or semi-structured content into Neo4j as a knowledge
  graph: PDF, HTML, plain text, or JSON documents; chunking strategies; entity and
  relationship extraction with LLMs (SimpleKGPipeline, LLM Graph Builder);
  apoc.load.json for JSON ingestion; or LangChain/LlamaIndex document loaders
  targeting Neo4j. Does NOT handle structured CSV/relational imports — use
  neo4j-import-skill. Does NOT handle GraphRAG retrieval pipelines — use
  neo4j-graphrag-skill. Does NOT handle vector index setup — use
  neo4j-vector-search-skill.
status: draft
version: 0.1.0
allowed-tools: Bash, WebFetch
---

# Neo4j Document Import Skill

> **Status: Draft / WIP** — Content is a placeholder. Reference files for chunking strategies and pipeline patterns to be added.

## When to Use

- Ingesting PDFs, HTML pages, or plain text into a Neo4j knowledge graph
- Chunking documents and storing chunks as `:Chunk` nodes with embeddings
- Extracting entities and relationships from text with an LLM (SimpleKGPipeline)
- Using Neo4j LLM Graph Builder (no-code drag-and-drop pipeline)
- Loading semi-structured JSON into the graph with `apoc.load.json`
- Connecting LangChain or LlamaIndex document loaders to Neo4j

## When NOT to Use

- **Structured CSV / relational data import** → use `neo4j-import-skill`
- **GraphRAG retrieval after documents are loaded** → use `neo4j-graphrag-skill`
- **Vector index creation** → use `neo4j-vector-search-skill`

---

## Pipeline Decision Tree

```
Have pre-structured CSV/relational data?
  → YES: use neo4j-import-skill

Have unstructured/semi-structured documents?
  ├── Want no-code UI pipeline?        → LLM Graph Builder (no-code)
  ├── Need LLM entity extraction?      → SimpleKGPipeline (neo4j-graphrag)
  ├── Source is JSON/API?              → apoc.load.json or Python + UNWIND
  └── Want LangChain/LlamaIndex?       → Neo4jGraph + document loader
```

---

## Core Patterns

### LLM entity extraction (SimpleKGPipeline)

```python
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.embeddings import OpenAIEmbeddings
import asyncio

pipeline = SimpleKGPipeline(
    llm=OpenAILLM(model_name="gpt-4o"),
    driver=driver,
    embedder=OpenAIEmbeddings(),
    entities=["Person", "Organization", "Location", "Product"],
    relations=["WORKS_AT", "LOCATED_IN", "KNOWS", "MENTIONS"],
    on_error="IGNORE",
)
asyncio.run(pipeline.run_async(text=document_text))
```

### Chunking + embedding (manual pipeline)

```python
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)
chunks = splitter.split_text(document_text)
embedder = OpenAIEmbeddings()

for i, chunk in enumerate(chunks):
    embedding = embedder.embed_query(chunk)
    driver.execute_query(
        """
        MERGE (doc:Document {id: $doc_id})
        CREATE (c:Chunk {id: $chunk_id, text: $text, embedding: $embedding})
        CREATE (doc)-[:HAS_CHUNK]->(c)
        """,
        doc_id="doc-1", chunk_id=f"doc-1-chunk-{i}",
        text=chunk, embedding=embedding
    )
```

### apoc.load.json (semi-structured JSON)

```cypher
CYPHER 25
CALL apoc.load.json("https://example.com/data.json") YIELD value
UNWIND value.items AS item
CALL (item) {
  MERGE (n:Item {id: item.id})
  SET n += item.properties
} IN TRANSACTIONS OF 1000 ROWS
```

---

## Checklist

- [ ] Chunk size chosen for embedding model context limit (512–1024 tokens typical)
- [ ] Chunk overlap set to preserve context at boundaries (10–15% of chunk size)
- [ ] Vector index created before storing embeddings
- [ ] `:Document`→`[:HAS_CHUNK]`→`:Chunk` pattern used (enables graph traversal in retrieval)
- [ ] Unique constraint on `Document.id` to prevent duplicate ingestion
- [ ] APOC available on target Neo4j (included on all Aura tiers including Free)

---

## References

- [LLM Graph Builder](https://neo4j.com/labs/genai-ecosystem/llm-graph-builder/)
- [neo4j-graphrag SimpleKGPipeline](https://neo4j.com/docs/neo4j-graphrag-python/)
- [APOC load procedures](https://neo4j.com/docs/apoc/current/import/)
- [GraphAcademy: Building Knowledge Graphs with LLMs](https://graphacademy.neo4j.com/courses/llm-knowledge-graph-construction/)
- [LangChain Neo4j Integration](https://neo4j.com/labs/genai-ecosystem/langchain/)
