# KG Construction — Extended Reference

Overflow from `SKILL.md` — load when detailed chunking strategy or entity resolution config needed.

---

## Chunking Strategy Comparison

| Strategy | How it splits | Best for | neo4j-graphrag class |
|---|---|---|---|
| Fixed-size | Token count with optional boundary respect | Dense technical docs; most use-cases | `FixedSizeSplitter(chunk_size, chunk_overlap)` |
| Sentence/paragraph | Natural language boundaries (`\n\n`, `.`) | Narrative text, news articles, course content | LangChain `CharacterTextSplitter(separator="\n\n")` |
| Semantic | Embedding similarity between adjacent sentences | Long-form documents with topic shifts | LangChain `SemanticChunker` (requires embedder) |
| N-gram | Overlapping windows of n words | Short snippets, keyword-dense text | Custom — not built into neo4j-graphrag |
| Structural | By section/heading/method (doc-specific) | API docs, legal contracts, structured PDFs | Custom — parse structure then chunk |

**Rule**: Start with `FixedSizeSplitter(chunk_size=512, chunk_overlap=50)`. Switch to paragraph-based when sentences must not break (courses, articles). Switch to semantic chunking only when topic coherence within chunks is critical and embedder calls during ingestion are affordable.

**Combination pattern** (course content model from GraphAcademy course):
```
Course → Module → Lesson → Paragraph
```
Split doc into structural units (Module/Lesson), then chunk each Lesson into Paragraphs (`\n\n`). Store both levels; query at Paragraph for vector search, traverse to Lesson for context. Pattern:
```python
from langchain_text_splitters import CharacterTextSplitter
splitter = CharacterTextSplitter(separator="\n\n", chunk_size=1500, chunk_overlap=200)
paragraphs = splitter.split_documents(lesson_docs)
```

LangChain `CharacterTextSplitter` behavior:
1. Split by `separator` (paragraph breaks)
2. Combine paragraphs up to `chunk_size` chars
3. If single paragraph > `chunk_size`: keep as-is (no mid-paragraph cut)
4. Add last paragraph of chunk N to start of chunk N+1 only if it's ≤ `chunk_overlap` chars

---

## Entity Resolver — Full Config

Resolvers merge duplicate entities after bulk ingest. All use APOC `refactor.mergeNodes` internally.

### Class Hierarchy

```
EntityResolver (base)
  ├── SinglePropertyExactMatchResolver  — exact name match
  ├── BasePropertySimilarityResolver (abstract)
  │     ├── FuzzyMatchResolver          — Levenshtein; pip install rapidfuzz
  │     └── SpaCySemanticMatchResolver  — cosine; pip install neo4j-graphrag[nlp]
  └── (custom subclass)
```

### SinglePropertyExactMatchResolver

```python
from neo4j_graphrag.experimental.components.resolver import SinglePropertyExactMatchResolver

resolver = SinglePropertyExactMatchResolver(
    driver=driver,
    filter_query="WHERE n:Organization OR n:Person",   # optional: narrow scope
    resolve_property="name",   # default: "name"
    neo4j_database="neo4j",    # optional
)
stats = asyncio.run(resolver.run())
# stats.number_of_nodes_to_resolve, stats.number_of_created_nodes
```

### FuzzyMatchResolver

```python
from neo4j_graphrag.experimental.components.resolver import FuzzyMatchResolver

resolver = FuzzyMatchResolver(
    driver=driver,
    resolve_properties=["name"],   # list of properties to concatenate + compare
    threshold=0.9,    # Levenshtein similarity 0–1; lower = more aggressive merging
    filter_query="WHERE n:Organization",
)
asyncio.run(resolver.run())
```

### SpaCySemanticMatchResolver

Requires `pip install neo4j-graphrag[nlp]`. Python ≤3.13 only (spaCy not on 3.14+).

```python
from neo4j_graphrag.experimental.components.resolver import SpaCySemanticMatchResolver

resolver = SpaCySemanticMatchResolver(
    driver=driver,
    resolve_properties=["name"],
    threshold=0.85,   # cosine similarity 0–1; higher = stricter
    filter_query="WHERE n:Person",
)
asyncio.run(resolver.run())
```

**Resolver selection:**
| Scenario | Resolver | threshold |
|---|---|---|
| Exact duplicates (OCR, same source) | `SinglePropertyExactMatchResolver` | — |
| Typos / alternate spellings | `FuzzyMatchResolver` | 0.85–0.92 |
| Semantic synonyms ("CEO" / "Chief Executive") | `SpaCySemanticMatchResolver` | 0.80–0.88 |
| Python 3.14+ | `FuzzyMatchResolver` | 0.90 |

Run resolvers after all ingest batches complete — running inline per-batch is slower.

---

## LexicalGraphConfig — All Fields

All fields have defaults — only override as needed:

| Field | Default | Controls |
|---|---|---|
| `document_node_label` | `"Document"` | Label of the document node |
| `chunk_node_label` | `"Chunk"` | Label of the chunk node |
| `chunk_to_document_relationship_type` | `"FROM_DOCUMENT"` | Chunk→Document relationship |
| `next_chunk_relationship_type` | `"NEXT_CHUNK"` | Chunk→next Chunk (linked list) |
| `node_to_chunk_relationship_type` | `"MENTIONS"` | Entity→Chunk relationship |
| `chunk_id_property` | `"id"` | Property storing chunk UUID |
| `chunk_index_property` | `"index"` | Property storing chunk position |
| `chunk_text_property` | `"text"` | Property storing chunk text |
| `chunk_embedding_property` | `"embedding"` | Property storing chunk vector |

---

## GraphSchema — Rich NodeType / RelationshipType

Descriptions and typed properties improve LLM extraction quality:

```python
from neo4j_graphrag.experimental.components.schema import (
    GraphSchema, NodeType, RelationshipType, PropertyType
)

schema = GraphSchema(
    node_types=[
        NodeType(
            label="Person",
            description="A human individual mentioned in the text",
            properties=[
                PropertyType(name="name", type="STRING"),
                PropertyType(name="role", type="STRING"),
            ],
            additional_properties=False,   # strict: reject other LLM-invented props
        ),
        NodeType(
            label="Organization",
            description="A company, institution, or group",
            properties=[PropertyType(name="name", type="STRING")],
            additional_properties=True,    # allow LLM to add extra props
        ),
    ],
    relationship_types=[
        RelationshipType(label="WORKS_AT", description="Employment or affiliation"),
        RelationshipType(label="LOCATED_IN", description="Geographic location"),
    ],
    patterns=[
        ("Person", "WORKS_AT", "Organization"),
        ("Organization", "LOCATED_IN", "Location"),
    ],
    additional_node_types=False,         # strict: reject node types not in list
    additional_relationship_types=False, # strict: reject relationship types not in list
)
```

`additional_node_types=True`: LLM may invent new node types. `False` = production (precision); `True` = exploration (recall).

Labels starting or ending with `__` are reserved for internal neo4j-graphrag use.

---

## Custom DataLoader — Full Pattern

```python
from neo4j_graphrag.experimental.components.data_loader import DataLoader, PdfLoader
from neo4j_graphrag.experimental.components.types import (
    DocumentInfo, DocumentType, LoadedDocument
)

# S3 PDF via fsspec (requires pip install s3fs):
loader = PdfLoader()
loaded = asyncio.run(loader.run("s3://my-bucket/report.pdf", fs="s3"))

# HTML web page loader:
class WebPageLoader(DataLoader):
    async def run(self, filepath, metadata=None):
        import httpx
        from bs4 import BeautifulSoup
        html = httpx.get(filepath).text
        text = BeautifulSoup(html, "html.parser").get_text(separator="\n")
        return LoadedDocument(
            text=text,
            document_info=DocumentInfo(
                path=filepath,
                metadata=self.get_document_metadata(text, metadata),
            ),
        )

# JSON / structured text loader:
class JsonFieldLoader(DataLoader):
    def __init__(self, text_field: str):
        self.text_field = text_field

    async def run(self, filepath, metadata=None):
        import json, pathlib
        data = json.loads(pathlib.Path(filepath).read_text())
        text = data[self.text_field]
        return LoadedDocument(
            text=text,
            document_info=DocumentInfo(path=filepath, metadata=metadata),
        )
```

Pass custom loader: `SimpleKGPipeline(..., file_loader=WebPageLoader(), from_file=True)`.

---

## LLM Graph Builder — Chunking Strategy Options

Via Graph Enhancement UI → Entity Extraction Settings:
- **Token-based**: fixed size (default)
- **Page-based**: one chunk per PDF page
- **Semantic**: embedding similarity boundaries
- **Paragraph**: `\n\n` boundaries

Also configurable via the Graph Builder API.
