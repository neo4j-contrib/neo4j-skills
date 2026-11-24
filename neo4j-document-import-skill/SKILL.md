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
  Does NOT handle vector index creation — use neo4j-vector-index-skill.
version: 1.0.8
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
- **Vector index creation** → `neo4j-vector-index-skill`
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
pip install neo4j-graphrag                   # includes SimpleKGPipeline
pip install neo4j-graphrag[openai]           # + OpenAI LLM/embedder
pip install neo4j-graphrag[anthropic]        # + Anthropic Claude
pip install neo4j-graphrag[google]           # + Vertex AI / Gemini
pip install neo4j-graphrag[bedrock]          # + Amazon Bedrock (boto3) — added v1.15.0
pip install neo4j-graphrag[ollama]           # + Ollama (local)
pip install neo4j-graphrag[mistralai]        # + MistralAI
pip install neo4j-graphrag[fuzzy-matching]   # + FuzzyMatchResolver (rapidfuzz)
# spaCy entity resolver (Python <= 3.13 only — unsupported on 3.14+):
pip install neo4j-graphrag[nlp]
```

Requires: driver `neo4j>=6.3.1,<7` (installed automatically with neo4j-graphrag), Python `>=3.10,<3.15`, Neo4j>=5.18.1 (Aura>=5.18.0).

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

# Option B — Rich GraphSchema (production; best extraction quality)
from neo4j_graphrag.components.schema import (
    GraphSchema, NodeType, RelationshipType, PropertyType, ConstraintType, GraphConstraintType
)
schema = GraphSchema(
    node_types=[
        NodeType(
            label="Person",
            description="A human individual",
            properties=[
                PropertyType(name="name", type="STRING"),
                PropertyType(name="role", type="STRING"),
            ],
        ),
        NodeType(
            label="Organization",
            description="A company or institution",
            properties=[
                PropertyType(name="name", type="STRING"),
                PropertyType(name="industry", type="STRING"),
            ],
        ),
    ],
    relationship_types=[
        RelationshipType(label="WORKS_AT", description="Employment relationship"),
    ],
    patterns=[("Person", "WORKS_AT", "Organization")],
    # Optional: constraints emitted to ParquetWriter metadata (v1.15.0+)
    constraints=[
        ConstraintType(type=GraphConstraintType.UNIQUENESS, node_type="Person", property_name="name"),
        ConstraintType(type=GraphConstraintType.KEY, node_type="Organization", property_name="name"),
    ],
)

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
    model_name="gpt-4.1",
    model_params={"temperature": 0},
    # Note: SimpleKGPipeline auto-enables structured output for OpenAI/VertexAI LLMs (v1.14.0+)
    # Do NOT set response_format manually — it is managed by the pipeline
)
embedder = OpenAIEmbeddings()   # OPENAI_API_KEY from env

pipeline = SimpleKGPipeline(
    llm=llm,
    driver=driver,
    embedder=embedder,
    schema=schema,              # GraphSchema, dict, "FREE", or "EXTRACTED"
    from_file=True,             # False → pass text= instead of file_path=
    on_error="IGNORE",          # RAISE to surface extraction failures
    perform_entity_resolution=True,
    neo4j_database="neo4j",     # omit to use default
)
```

**LLM alternatives** (same interface):
- `AnthropicLLM(model_name="claude-3-5-sonnet-20241022")`
- `VertexAILLM(model_name="gemini-2.0-flash")`
- `OllamaLLM(model_name="llama3")` — local; no API key needed
- `BedrockLLM(model_name="anthropic.claude-3-5-sonnet-20241022-v2:0")` — Amazon Bedrock (v1.15.0+); keyword is `model_name`, not `model_id`

---

## Step 3 — Run the Pipeline

```python
# From PDF file:
result = asyncio.run(pipeline.run_async(
    file_path="report.pdf",        # auto-dispatches to PdfLoader
    document_metadata={"source": "Q4 report", "year": "2025"},   # values must be strings
))

# From Markdown file (v1.15.0+):
result = asyncio.run(pipeline.run_async(
    file_path="notes.md",          # auto-dispatches to MarkdownLoader
    document_metadata={"source": "meeting notes"},
))

# Note: old `from_pdf=True` parameter is DEPRECATED since v1.15.0; use `from_file=True` instead
# pipeline = SimpleKGPipeline(..., from_file=True)   ← correct
# pipeline = SimpleKGPipeline(..., from_pdf=True)    ← deprecated

# From raw text — needs a separate pipeline built with from_file=False
# (text= on a from_file=True pipeline raises PipelineDefinitionError):
text_pipeline = SimpleKGPipeline(llm=llm, driver=driver, embedder=embedder,
                                 schema=schema, from_file=False)
result = asyncio.run(text_pipeline.run_async(
    text=document_text,
))

# Batch — process multiple files:
async def ingest_all(paths):
    for p in paths:
        await pipeline.run_async(file_path=str(p))

asyncio.run(ingest_all(list(pdf_dir.glob("*.pdf"))))
```

`document_metadata` dict (`Dict[str, str]` — string values only) is stored as properties on the `:Document` node.

---

## Step 4 — Chunking Configuration

Default splitter: `FixedSizeSplitter()` = `chunk_size=4000, chunk_overlap=200, approximate=True`. Sizes are **characters**, not tokens.

```python
from neo4j_graphrag.components.text_splitters.fixed_size_splitter import FixedSizeSplitter

splitter = FixedSizeSplitter(
    chunk_size=2000,      # characters (not tokens)
    chunk_overlap=200,    # ~10% of chunk_size; preserves boundary context
    approximate=True,     # default; avoids cutting words
)

pipeline = SimpleKGPipeline(
    ...,
    text_splitter=splitter,
)
```

Chunking guidance:
| Document type | chunk_size (chars) | chunk_overlap (chars) |
|---|---|---|
| Dense technical text | 1000–2000 | 200–300 |
| Narrative / news articles | 2000–4000 | 300–500 |
| Legal / financial docs | 1000–1500 | 150–250 |

Rule: chunk must fit within LLM context for extraction + within embedding model limits (`text-embedding-3-small`: 8191 tokens ≈ 4 chars/token for English). `chunk_size` counts characters.

---

## Step 5 — Entity Resolution

Merge duplicate extracted entities after pipeline run.

```python
from neo4j_graphrag.components.resolver import (
    SinglePropertyExactMatchResolver,   # identical name → merge
    FuzzyMatchResolver,                  # Levenshtein similarity; needs rapidfuzz
    SpaCySemanticMatchResolver,          # cosine similarity; needs neo4j-graphrag[nlp]
)

# Exact match (fastest; good baseline)
resolver = SinglePropertyExactMatchResolver(driver)
asyncio.run(resolver.run())

# Fuzzy match (handles typos / alternate spellings)
from neo4j_graphrag.components.resolver import FuzzyMatchResolver
resolver = FuzzyMatchResolver(driver, similarity_threshold=0.9)
asyncio.run(resolver.run())

# Scope resolution to specific labels only:
resolver = SinglePropertyExactMatchResolver(
    driver,
    filter_query="WHERE entity:Organization OR entity:Person",   # node variable is `entity`
)
asyncio.run(resolver.run())
```

Run resolvers after ingestion, not inline — bulk merges are faster.

---

## Resulting Graph Structure

SimpleKGPipeline produces this lexical graph layer (default `LexicalGraphConfig`):

```
(:Chunk {index, text, embedding})
    -[:FROM_DOCUMENT]->
(:Document {path, createdAt, document_type, ...metadata})

(:Chunk)-[:NEXT_CHUNK]->(:Chunk)          ← linked list for ordered traversal
```

Entity extraction adds (entities also get labels `__Entity__` and `__KGBuilder__`):
```
(:Person:__Entity__ {name, ...})-[:FROM_CHUNK]->(:Chunk)
(:Organization:__Entity__ {name, ...})-[:FROM_CHUNK]->(:Chunk)
(:Person)-[:WORKS_AT]->(:Organization)
```

No `HAS_CHUNK` / `MENTIONS` — that shape needs a custom writer or `LexicalGraphConfig` overrides.

Verify after ingestion:
```cypher
CYPHER 25
MATCH (c:Chunk)-[:FROM_DOCUMENT]->(d:Document)
RETURN d.path, count(c) AS chunks LIMIT 10;

MATCH (e:__Entity__)-[:FROM_CHUNK]->(c:Chunk)
RETURN [l IN labels(e) WHERE NOT l STARTS WITH '__'][0] AS type, count(*) AS cnt ORDER BY cnt DESC LIMIT 20;
```

---

## LLM Graph Builder (No-Code UI)

Read [references/other-ingestion.md](references/other-ingestion.md#llm-graph-builder-no-code-ui) when you need this.

## APOC JSON Ingestion (Semi-Structured)

Read [references/other-ingestion.md](references/other-ingestion.md#apoc-json-ingestion-semi-structured) when you need this.

## LangChain Integration Pattern

Read [references/other-ingestion.md](references/other-ingestion.md#langchain-integration-pattern) when you need this.

## Constraints and Indexes (Run Before Ingestion)

```cypher
CYPHER 25
// Prevent duplicate documents
CREATE CONSTRAINT doc_id_unique IF NOT EXISTS
  FOR (d:Document) REQUIRE d.id IS UNIQUE;

// Prevent duplicate chunks
CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
  FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

// Entity names: index only — NO uniqueness constraint before ingestion.
// The extractor writes same-name entities as separate nodes; a UNIQUE constraint makes
// the writer fail (ConstraintError) and, with on_error="IGNORE", leaves the graph empty.
// Add uniqueness after the resolver has merged duplicates.
CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name);
CREATE INDEX org_name IF NOT EXISTS FOR (o:Organization) ON (o.name);

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
| `Import from files not enabled, please set apoc.import.file.enabled=true in your apoc.conf` | Local file access off (default) | Add `apoc.import.file.enabled=true` to `conf/apoc.conf`; restart. HTTP URLs don't need it |
| Chunking cuts words mid-way | `approximate=False` cuts at exact character count (default is `True`) | Keep `approximate=True` in `FixedSizeSplitter` |
| `chunk_size` too large → LLM timeouts | Extraction prompt + chunk exceeds context | Reduce `chunk_size` (characters; default 4000) |
| `SpaCySemanticMatchResolver` fails on Python 3.14 | spaCy not supported on 3.14+ | Use `FuzzyMatchResolver` or downgrade to Python 3.13 |
| `neo4j-driver` package not found | Deprecated package name since 6.0 | Use `neo4j` package: `pip install "neo4j>=6.3.1,<7"` (neo4j-graphrag pins it) |
| `ValidationError` on `NodeType` with no properties | `NodeType` requires ≥1 property since v1.13.0 | Add at least `PropertyType(name="name", type="STRING")`; string-list labels get it automatically |
| `from_pdf` deprecation warning | `from_pdf=True` removed in v1.15.0 | Use `from_file=True` instead |
| `response_format` in `model_params` ignored | `SimpleKGPipeline` auto-enables structured output for OpenAI/VertexAI (v1.14.0+) | Remove `response_format` from `model_params`; the pipeline manages it |

---

## Verification Checklist

- [ ] Constraints created and ONLINE before ingestion starts
- [ ] Vector index created before storing embeddings
- [ ] `chunk_size` (characters) within embedding model limit
- [ ] `chunk_overlap` set to 10–15% of chunk_size
- [ ] `(Chunk)-[:FROM_DOCUMENT]->(Document)` + `NEXT_CHUNK` present (enables graph traversal in retrieval)
- [ ] `document_metadata` populated with source identifier
- [ ] Entity resolver run after bulk ingestion
- [ ] `apoc.version()` confirmed if using `apoc.load.json`
- [ ] `.env` has API keys; `.env` in `.gitignore`
- [ ] Verify structure: `MATCH (c:Chunk)-[:FROM_DOCUMENT]->(d:Document) RETURN count(c)`
- [ ] Verify entities: `MATCH (e:__Entity__)-[:FROM_CHUNK]->(c:Chunk) RETURN labels(e), count(*)`

---

## GraphSchema — Current API (≥1.8.0)

`entities`/`relations`/`potential_schema` are deprecated. Use `schema=GraphSchema(...)`.

```python
from neo4j_graphrag.components.schema import (
    GraphSchema, NodeType, RelationshipType, PropertyType,
    ConstraintType, GraphConstraintType,
)

schema = GraphSchema(
    node_types=[
        NodeType(label="Person", properties=[PropertyType(name="name", type="STRING")]),
        NodeType(label="Organization", properties=[PropertyType(name="name", type="STRING")]),
    ],
    relationship_types=[RelationshipType(label="WORKS_AT")],
    patterns=[("Person", "WORKS_AT", "Organization")],
    # Constraints (v1.15.0+) — emitted to ParquetWriter metadata and enforce schema; one NodeType per label (duplicates rejected v1.23.0)
    constraints=[
        # UNIQUENESS — property must be unique across nodes of that label
        ConstraintType(type=GraphConstraintType.UNIQUENESS, node_type="Person", property_name="name"),
        # KEY — uniqueness + existence (null not allowed)
        ConstraintType(type=GraphConstraintType.KEY, node_type="Organization", property_name="name"),
        # EXISTENCE — property must be non-null (replaces deprecated PropertyType.required)
        ConstraintType(type=GraphConstraintType.EXISTENCE, node_type="Event", property_name="date"),
        # Composite KEY (v1.15.0+)
        ConstraintType(
            type=GraphConstraintType.KEY,
            node_type="Person",
            property_names=("first_name", "last_name"),
        ),
    ],
)
pipeline = SimpleKGPipeline(llm=llm, driver=driver, embedder=embedder, schema=schema)
```

`schema="FREE"` (no guidance) or `schema="EXTRACTED"` (LLM infers types) — exploration only, noisier output.

### Auto-Extract Schema from Text (v1.15.0+)

When no `schema` is passed to `SimpleKGPipeline`, `SchemaFromTextExtractor` runs automatically.
To run it explicitly:

```python
from neo4j_graphrag.components.schema import (
    SchemaFromTextExtractor,
    SchemaFromExistingGraphExtractor,
)

# Infer schema from sample text
extractor = SchemaFromTextExtractor(llm=llm, use_structured_output=True)
schema = asyncio.run(extractor.run(text=sample_text))

# Derive schema from an existing Neo4j graph
extractor = SchemaFromExistingGraphExtractor(driver=driver)
schema = asyncio.run(extractor.run())
```

### Parquet Export (experimental, v1.14.0+)

```python
from neo4j_graphrag.components.kg_writer import ParquetWriter
from neo4j_graphrag.components.filename_collision_handler import FilenameCollisionHandler

# Use ParquetWriter instead of KGWriter inside a Pipeline to export to Parquet files
# nodes_dest / relationships_dest: your ParquetOutputDestination implementations (local, S3, GCS…)
writer = ParquetWriter(
    nodes_dest=nodes_dest,
    relationships_dest=relationships_dest,
    collision_handler=FilenameCollisionHandler(),
)
# Produces one Parquet file per node label and per relationship type
# Metadata includes UNIQUENESS, EXISTENCE, KEY constraints (v1.15.0/1.16.0); pin >=1.23.0 — earlier fails on mixed-type LIST props, emits extra KEY(__id__) → Data Importer re-import error 22N41
```

---

## LexicalGraphConfig — Customize Labels

Read [references/other-ingestion.md](references/other-ingestion.md#lexicalgraphconfig--customize-labels) when you need this.

## Custom Document Loaders

Read [references/other-ingestion.md](references/other-ingestion.md#custom-document-loaders) when you need this.

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
- [Extended KG Construction Reference](references/kg-construction.md)
