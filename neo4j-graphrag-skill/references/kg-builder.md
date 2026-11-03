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
    prompt_template=ERExtractionTemplate(),  # or str — a str REPLACES the whole prompt
    text_splitter=None,           # TextSplitter; default FixedSizeSplitter(4000, 200) chars
    file_loader=None,             # DataLoader (pdf_loader= is deprecated)
    lexical_graph_config=None,
)
# No chunk_size / chunk_overlap params (TypeError) — pass a splitter via text_splitter=
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
        ("Person", "WORKS_AT", "Organization"),   # (source, relationship, target)
    ]
}
```

**Schema modes** (set via `schema` param):
- `EXTRACTED` (default) — LLM infers schema from text
- `FREE` — unguided extraction; no schema constraint
- Custom — pass explicit `schema` dict

**Schema constraints** (validated during extraction; `GraphSchema` model):

| Kind | Scope | Notes |
|---|---|---|
| `EXISTENCE` | node label OR relationship type | property must be present on every entity of that type |
| `UNIQUENESS` | node label OR relationship type [v1.16.1+] | property values must be unique per type; before v1.16.1 silently dropped on relationships |
| `KEY` | node label OR relationship type | composite identity; cannot coexist with `UNIQUENESS` on same property set |

Set exactly one of `node_label` or `relationship_type` per constraint. `UNIQUENESS` + `KEY` on the same relationship type and property set is rejected by schema validation.

v1.23.0: `GraphSchema` rejects duplicate node labels — define each label once with all its properties. LLM-extracted schemas merge same-label node types (union of properties) and drop `EXISTENCE` / `UNIQUENESS` already covered by a `KEY` instead of raising `SchemaValidationError`. `Neo4jWriter` honours `neo4j_database` in setup/cleanup (earlier versions hit home database).

## Chunking Options

```python
from neo4j_graphrag.components.text_splitters.fixed_size_splitter import FixedSizeSplitter

pipeline = SimpleKGPipeline(
    ...,
    text_splitter=FixedSizeSplitter(chunk_size=800, chunk_overlap=150),  # characters
)
# For LangChain splitters: `from langchain_text_splitters import ...` (not langchain.text_splitter),
# wrap in LangChainTextSplitterAdapter, pass as text_splitter=
# → see knowledge-graph-construction.md#langchain-adapter
```

## Graph Structure Created

```
(Chunk {text, embedding, index, ...})
  -[:FROM_DOCUMENT]->
(Document {path, createdAt, <document_metadata keys>})

(Chunk)-[:NEXT_CHUNK]->(Chunk)

(:Person:__Entity__ {name, ...})     // entity type is a label, plus __Entity__
  -[:FROM_CHUNK]->
(Chunk)

(:Person:__Entity__)-[:<RELATION_TYPE>]->(:Organization:__Entity__)
// all pipeline nodes also carry __KGBuilder__
```

## entity_resolution

When `perform_entity_resolution=True` (default): `SinglePropertyExactMatchResolver` merges nodes with same label and identical `name`. No LLM; near-duplicates stay separate — run `FuzzyMatchResolver` / `SpaCySemanticMatchResolver` after ingestion (knowledge-graph-construction.md). Set `False` for initial development, `True` for production ingestion.

## Structured Output

Automatic: `SimpleKGPipeline` enables structured output when `llm.supports_structured_output` is True (`OpenAILLM`, `VertexAILLM`, `AnthropicLLM`). No flag. Never put `use_structured_output` in `model_params` — passed to the provider API → `TypeError`.

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
