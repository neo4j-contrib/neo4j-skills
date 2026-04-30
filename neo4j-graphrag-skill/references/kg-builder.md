# SimpleKGPipeline Reference

## Full Constructor

```python
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline

pipeline = SimpleKGPipeline(
    llm,                          # LLMInterface — used for entity/rel extraction
    driver,                       # Neo4j driver
    embedder,                     # Embedder — for chunk embeddings
    from_file: bool = True,       # True: pass file_path; False: pass text=
    entities: list = None,        # simple: ["Person", "Org"] or detailed dicts
    relations: list = None,       # simple: ["WORKS_AT"] or detailed dicts
    schema: dict = None,          # explicit schema (overrides entities/relations)
    perform_entity_resolution: bool = True,
    neo4j_database: str = None,
    on_error: str = "IGNORE",     # "RAISE" or "IGNORE"
    prompt_template: str = None,  # custom extraction prompt
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
)
```

## Schema Modes

**Simple string lists** (auto-generates extraction prompt):
```python
entities=["Person", "Organization", "Location"]
relations=["WORKS_AT", "LOCATED_IN", "KNOWS"]
```

**Detailed dicts** (adds LLM guidance per type):
```python
entities=[
    {"label": "Person", "description": "A human individual", "properties": [{"name": "name", "type": "str"}]},
    {"label": "Organization", "description": "A company or institution"},
]
relations=[
    {"label": "WORKS_AT", "description": "Person employed by Organization",
     "properties": [{"name": "since", "type": "str"}]},
]
```

**Schema patterns** (restrict which entity pairs a relation connects):
```python
schema={
    "node_types": [...],
    "relationship_types": [...],
    "patterns": [
        {"start": "Person", "end": "Organization", "relation": "WORKS_AT"},
    ]
}
```

**Schema modes** (set via `schema` param):
- `EXTRACTED` (default) — LLM infers schema from text
- `FREE` — unguided extraction; no schema constraint
- Custom — pass explicit `schema` dict

## Chunking Options

```python
from neo4j_graphrag.experimental.components.text_splitters.fixed_size_splitter import FixedSizeSplitter

pipeline = SimpleKGPipeline(
    ...,
    chunk_size=800,      # tokens per chunk
    chunk_overlap=150,   # overlap between consecutive chunks
)
# For LangChain splitters:
from langchain.text_splitter import RecursiveCharacterTextSplitter
# Pass custom splitter via pipeline component wiring (advanced — see pipeline docs)
```

## Graph Structure Created

```
(Document {source, metadata})
  -[:FROM_DOCUMENT]->
(Chunk {text, embedding, index, ...})
  -[:HAS_ENTITY]->
(Entity {name, label, description, ...})
  -[:<RELATION_TYPE>]->
(Entity)
```

## entity_resolution

When `perform_entity_resolution=True` (default): similar entity nodes are merged using LLM judgment. Increases accuracy, slower. Set `False` for initial development, `True` for production ingestion.

## Structured Output

Use with OpenAI or VertexAI to enforce JSON schema at API level (reduces parsing errors):
```python
llm = OpenAILLM(model_name="gpt-4o", model_params={"use_structured_output": True})
```
Not available for Anthropic, Ollama, Mistral (as of v1.x).

## Batch Processing Multiple Documents

```python
import asyncio

async def ingest_all(docs):
    for doc in docs:
        await pipeline.run_async(
            text=doc["text"],
            document_metadata={"title": doc["title"], "date": doc["date"]},
        )

asyncio.run(ingest_all(documents))
```

Sequential by default. For parallel: use `asyncio.gather()` — monitor Neo4j connection pool.

## Debug: Inspect LLM Extraction

```python
# Force errors to surface:
pipeline = SimpleKGPipeline(..., on_error="RAISE")

# Check what was extracted:
result = asyncio.run(pipeline.run_async(text="Alice works at Neo4j in London."))
# Inspect result for extracted entities and relations
```
