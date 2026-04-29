---
name: neo4j-document-import-skill
description: Ingests unstructured and semi-structured documents into Neo4j as a knowledge graph.
  Use when chunking PDFs, HTML, plain text, or Markdown; extracting entities and relationships
  from text with an LLM (SimpleKGPipeline, neo4j-graphrag); loading JSON via apoc.load.json;
  building Document→Chunk→Entity graph structures; or connecting LangChain/LlamaIndex document
  loaders to Neo4j. Covers neo4j-graphrag SimpleKGPipeline, LLM Graph Builder web UI, entity
  resolution, chunking strategies, and graph schema design for RAG pipelines.
  Does NOT handle structured CSV/relational import — use neo4j-import-skill.
  Does NOT handle GraphRAG retrieval after ingestion — use neo4j-graphrag-skill.
  Does NOT handle vector index creation — use neo4j-vector-search-skill.
version: 1.0.0
status: stable
allowed-tools: Bash WebFetch
---

# Neo4j Document Import Skill

## When to Use

- Ingesting PDFs, HTML, plain text, Markdown into Neo4j as a knowledge graph
- Chunking documents and storing `:Chunk` nodes with embeddings
- Extracting entities and relationships from text with an LLM
- Using `SimpleKGPipeline` (neo4j-graphrag) programmatically
- Using Neo4j LLM Graph Builder (no-code web UI)
- Loading semi-structured JSON via `apoc.load.json`
- Connecting LangChain or LlamaIndex document loaders to Neo4j

## When NOT to Use

- **Structured CSV / relational data** → `neo4j-import-skill`
- **GraphRAG retrieval after ingestion** → `neo4j-graphrag-skill`
- **Vector index creation** → `neo4j-vector-search-skill`
- **Cypher query writing** → `neo4j-cypher-skill`

---

## Approach Decision Table

| Situation | Approach |
|---|---|
| No code; drag-and-drop UX wanted | LLM Graph Builder web UI |
| Programmatic pipeline; PDFs/text | `SimpleKGPipeline` (neo4j-graphrag) |
| JSON / REST API responses | `apoc.load.json` or Python + UNWIND |
| LangChain already in stack | `Neo4jGraph` + document loader |
| LlamaIndex already in stack | `Neo4jQueryEngine` / `Neo4jVectorStore` |
| Chunk-only (no entity extraction) | Manual chunking + MERGE pattern |

---

## Install

```bash
pip install neo4j-graphrag              # includes SimpleKGPipeline
pip install neo4j-graphrag[openai]      # + OpenAI LLM/embedder
pip install neo4j-graphrag[anthropic]   # + Anthropic Claude
pip install neo4j-graphrag[google]      # + Vertex AI / Gemini
# spaCy entity resolver (Python <= 3.13 only — unsupported on 3.14+):
pip install neo4j-graphrag[nlp]
```

Requires: `neo4j>=6.0.0`, Python>=3.10, Neo4j>=5.18.1 (Aura>=5.18.0).

---

## Step 1 — Define Graph Schema

Schema controls what the LLM extracts. Define before pipeline construction.

```python
# Option A — Simple string lists (LLM infers descriptions)
entities = ["Person", "Organization", "Location", "Product", "Event"]
relations = ["WORKS_AT", "LOCATED_IN", "KNOWS", "MENTIONS", "PART_OF"]
patterns = [
    ("Person", "WORKS_AT", "Organization"),
    ("Organization", "LOCATED_IN", "Location"),
    ("Person", "KNOWS", "Person"),
    ("Article", "MENTIONS", "Organization"),
]

# Option B — Rich schema (better extraction quality)
from neo4j_graphrag.experimental.components.schema import (
    SchemaBuilder, SchemaEntity, SchemaRelation
)
schema = SchemaBuilder().create_schema_from_dict({
    "entities": {
        "Person": {"description": "A human individual", "properties": {"name": "str", "role": "str"}},
        "Organization": {"description": "A company or institution", "properties": {"name": "str", "industry": "str"}},
    },
    "relations": {
        "WORKS_AT": {"description": "Employment relationship"},
    },
    "patterns": [("Person", "WORKS_AT", "Organization")],
})

# Option C — Auto-extract schema from text (no constraints)
schema = "EXTRACTED"   # LLM infers types; noisier output
schema = "FREE"        # No schema guidance; most noise
```

Use Option B for production; Option A for prototyping; `"EXTRACTED"` only for exploration.

---

## Step 2 — SimpleKGPipeline Setup

```python
import asyncio
from neo4j import GraphDatabase
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.embeddings import OpenAIEmbeddings

driver = GraphDatabase.driver(
    "neo4j+s://xxxx.databases.neo4j.io",
    auth=("neo4j", "password")
)

llm = OpenAILLM(
    model_name="gpt-4o",
    model_params={"temperature": 0, "response_format": {"type": "json_object"}},
)
embedder = OpenAIEmbeddings()   # OPENAI_API_KEY from env

pipeline = SimpleKGPipeline(
    llm=llm,
    driver=driver,
    embedder=embedder,
    entities=entities,          # from Step 1
    relations=relations,
    patterns=patterns,
    from_file=True,             # False → pass text= instead of file_path=
    on_error="IGNORE",          # RAISE to surface extraction failures
    perform_entity_resolution=True,
    neo4j_database="neo4j",     # omit to use default
)
```

**LLM alternatives** (same interface):
- `AnthropicLLM(model_name="claude-3-5-sonnet-20241022")`
- `VertexAILLM(model_name="gemini-1.5-pro-002")`
- `OllamaLLM(model_name="llama3")` — local; no API key needed

---

## Step 3 — Run the Pipeline

```python
# From PDF or Markdown file:
result = asyncio.run(pipeline.run_async(
    file_path="report.pdf",
    document_metadata={"source": "Q4 report", "year": 2025},
))

# From raw text:
result = asyncio.run(pipeline.run_async(
    text=document_text,
))

# Batch — process multiple files:
async def ingest_all(paths):
    for p in paths:
        await pipeline.run_async(file_path=str(p))

asyncio.run(ingest_all(list(pdf_dir.glob("*.pdf"))))
```

`document_metadata` dict is stored as properties on the `:Document` node.

---

## Step 4 — Chunking Configuration

Default splitter: `FixedSizeSplitter(chunk_size=300, chunk_overlap=50)`.

```python
from neo4j_graphrag.experimental.components.text_splitters.fixed_size_splitter import FixedSizeSplitter

splitter = FixedSizeSplitter(
    chunk_size=512,       # tokens; 300–512 typical for GPT-4o
    chunk_overlap=50,     # ~10% of chunk_size; preserves boundary context
    approximate=True,     # respect sentence/word boundaries when possible
)

pipeline = SimpleKGPipeline(
    ...,
    text_splitter=splitter,
)
```

Chunking guidance:
| Document type | chunk_size | chunk_overlap |
|---|---|---|
| Dense technical text | 256–512 | 50–80 |
| Narrative / news articles | 512–1024 | 80–128 |
| Legal / financial docs | 256–384 | 40–64 |

Rule: chunk must fit within LLM context for extraction + within embedding model limits. GPT-4o: 128k context; `text-embedding-3-small`: 8191 tokens. Never set chunk_size > 2048.

---

## Step 5 — Entity Resolution

Merge duplicate extracted entities after pipeline run.

```python
from neo4j_graphrag.experimental.components.resolver import (
    SinglePropertyExactMatchResolver,   # identical name → merge
    FuzzyMatchResolver,                  # Levenshtein similarity; needs rapidfuzz
    SpaCySemanticMatchResolver,          # cosine similarity; needs neo4j-graphrag[nlp]
)

# Exact match (fastest; good baseline)
resolver = SinglePropertyExactMatchResolver(driver)
asyncio.run(resolver.run())

# Fuzzy match (handles typos / alternate spellings)
from neo4j_graphrag.experimental.components.resolver import FuzzyMatchResolver
resolver = FuzzyMatchResolver(driver, threshold=0.9)
asyncio.run(resolver.run())

# Scope resolution to specific labels only:
resolver = SinglePropertyExactMatchResolver(
    driver,
    filter_query="WHERE n:Organization OR n:Person",
)
asyncio.run(resolver.run())
```

Run resolvers after ingestion, not inline — bulk merges are faster.

---

## Resulting Graph Structure

Pipeline always produces this lexical graph layer:

```
(:Document {id, fileName, status, ...metadata})
    -[:HAS_CHUNK]->
(:Chunk {id, text, index, embedding, ...})
    -[:NEXT_CHUNK]->          ← linked list for ordered traversal
(:Chunk {...})

(:Chunk)-[:FROM_DOCUMENT]->(:Document)   ← back-pointer
```

Entity extraction adds:
```
(:Chunk)-[:MENTIONS]->(:Person {name, ...})
(:Chunk)-[:MENTIONS]->(:Organization {name, ...})
(:Person)-[:WORKS_AT]->(:Organization)
```

Verify after ingestion:
```cypher
CYPHER 25
MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
RETURN d.fileName, count(c) AS chunks LIMIT 10;

MATCH (c:Chunk)-[:MENTIONS]->(e)
RETURN labels(e)[0] AS type, count(*) AS cnt ORDER BY cnt DESC LIMIT 20;
```

---

## LLM Graph Builder (No-Code UI)

Use when: non-developers need to ingest docs; rapid prototyping; no Python environment.

**Hosted**: https://llm-graph-builder.neo4jlabs.com/

**Local** (Docker):
```bash
git clone https://github.com/neo4j-labs/llm-graph-builder
cd llm-graph-builder
# Set OPENAI_API_KEY (or other provider keys) in .env
docker-compose up
# Opens at http://localhost:8080
```

Supported sources: PDF, plain text, Markdown, images, web pages, YouTube transcripts, S3/GCS bucket uploads.

LLM providers: OpenAI, Gemini, Claude, Llama3, Diffbot, Qwen.

Limitations: best with long-form English text; poor on tabular data (use `neo4j-import-skill` for CSV/Excel); visual diagrams not extracted.

---

## APOC JSON Ingestion (Semi-Structured)

Use when source is JSON from REST APIs, S3, or file exports.

```cypher
CYPHER 25
CALL apoc.load.json("https://example.com/articles.json") YIELD value
UNWIND value.articles AS article
CALL (article) {
  MERGE (d:Document {id: article.id})
  SET d.title = article.title, d.url = article.url, d.publishedAt = article.publishedAt
  FOREACH (tag IN article.tags |
    MERGE (t:Tag {name: tag})
    MERGE (d)-[:HAS_TAG]->(t)
  )
} IN TRANSACTIONS OF 1000 ROWS
```

Local file: `apoc.load.json("file:///import/data.json")`. File must be in `$NEO4J_HOME/import/` or APOC `allowlist` configured.

Check APOC available: `RETURN apoc.version()`. APOC is included on all Aura tiers.

---

## LangChain Integration Pattern

```python
from langchain_community.graphs import Neo4jGraph
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from neo4j import GraphDatabase

graph = Neo4jGraph(
    url="neo4j+s://xxxx.databases.neo4j.io",
    username="neo4j",
    password="password",
)

loader = PyPDFLoader("report.pdf")
docs = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)
chunks = splitter.split_documents(docs)

embedder = OpenAIEmbeddings()
driver = GraphDatabase.driver(url, auth=("neo4j", "password"))

for i, chunk in enumerate(chunks):
    emb = embedder.embed_query(chunk.page_content)
    driver.execute_query(
        """
        MERGE (doc:Document {id: $doc_id})
        SET doc.source = $source
        CREATE (c:Chunk {id: $chunk_id, text: $text, embedding: $emb, index: $idx})
        CREATE (doc)-[:HAS_CHUNK]->(c)
        """,
        doc_id=chunk.metadata.get("source", "unknown"),
        source=chunk.metadata.get("source"),
        chunk_id=f"chunk-{i}",
        text=chunk.page_content,
        emb=emb,
        idx=i,
    )
```

For entity extraction with LangChain: use `LLMGraphTransformer` (from `langchain_experimental.graph_transformers`). Produces same `:Document`/`:Chunk`/entity pattern.

---

## Constraints and Indexes (Run Before Ingestion)

```cypher
CYPHER 25
// Prevent duplicate documents
CREATE CONSTRAINT doc_id_unique IF NOT EXISTS
  FOR (d:Document) REQUIRE d.id IS UNIQUE;

// Prevent duplicate chunks
CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
  FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

// Entity deduplication
CREATE CONSTRAINT person_name_unique IF NOT EXISTS
  FOR (p:Person) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT org_name_unique IF NOT EXISTS
  FOR (o:Organization) REQUIRE o.name IS UNIQUE;

// Vector index for chunk embeddings (adjust dims for your model)
CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
  FOR (c:Chunk) ON c.embedding
  OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

// Poll until index ONLINE:
// SHOW INDEXES YIELD name, state WHERE state <> 'ONLINE'
```

Do not start ingestion until all indexes are ONLINE:
```cypher
SHOW INDEXES YIELD name, state WHERE state <> 'ONLINE';
```
If rows returned: wait, then re-run. ONLINE = safe to ingest.

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| LLM extracts node types not in schema | Schema too loose or `"EXTRACTED"` mode | Define explicit `entities` + `patterns`; use Option B schema |
| `MissingEmbedderError` | `embedder=` omitted | Always pass `embedder=` even if not doing vector search — pipeline stores embeddings on Chunk nodes |
| Zero entities extracted | LLM context overflow | Reduce `chunk_size`; switch to model with larger context |
| Duplicate entity nodes after ingestion | Entity resolution not run | Run `SinglePropertyExactMatchResolver` after bulk ingest |
| `apoc.load.json` permission denied | APOC allowlist not configured | Add URL to `apoc.import.file.enabled=true` and `dbms.security.allow_csv_import_from_file_urls=true` |
| Chunking loses sentence mid-way | `approximate=False` (default) cuts at exact token count | Set `approximate=True` in `FixedSizeSplitter` |
| `chunk_size` too large → LLM timeouts | Extraction prompt + chunk exceeds context | Keep chunk_size ≤ 512 for GPT-4o extraction; ≤ 2048 absolute max |
| `SpaCySemanticMatchResolver` fails on Python 3.14 | spaCy not supported on 3.14+ | Use `FuzzyMatchResolver` or downgrade to Python 3.13 |
| `neo4j-driver` package not found | Deprecated package name since 6.0 | Use `neo4j` package: `pip install neo4j>=6.0.0` |

---

## Verification Checklist

- [ ] Constraints created and ONLINE before ingestion starts
- [ ] Vector index created before storing embeddings
- [ ] `chunk_size` within embedding model limit (≤2048; ≤512 for extraction)
- [ ] `chunk_overlap` set to 10–15% of chunk_size
- [ ] `Document`→`HAS_CHUNK`→`Chunk` pattern used (enables graph traversal in retrieval)
- [ ] `document_metadata` populated with source identifier
- [ ] Entity resolver run after bulk ingestion
- [ ] `apoc.version()` confirmed if using `apoc.load.json`
- [ ] `.env` has API keys; `.env` in `.gitignore`
- [ ] Verify structure: `MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk) RETURN count(c)`
- [ ] Verify entities: `MATCH (c:Chunk)-[:MENTIONS]->(e) RETURN labels(e)[0], count(*)`

---

## References

Load on demand:
- [neo4j-graphrag KG Builder guide](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html)
- [neo4j-graphrag library overview](https://neo4j.com/docs/neo4j-graphrag-python/current/)
- [LLM Graph Builder (hosted)](https://llm-graph-builder.neo4jlabs.com/)
- [LLM Graph Builder GitHub](https://github.com/neo4j-labs/llm-graph-builder)
- [APOC load procedures](https://neo4j.com/docs/apoc/current/import/)
- [GraphAcademy: Building Knowledge Graphs with LLMs](https://graphacademy.neo4j.com/courses/llm-knowledge-graph-construction/)
- [LangChain Neo4j Integration](https://python.langchain.com/docs/integrations/graphs/neo4j_cypher/)
- [LlamaIndex Neo4jQueryEngine](https://docs.llamaindex.ai/en/stable/examples/index_structs/knowledge_graph/Neo4jKGIndexDemo/)
