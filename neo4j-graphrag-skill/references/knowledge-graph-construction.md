# Knowledge Graph Construction — Advanced Reference

Supplements [SKILL.md Step 11](../SKILL.md#step-11--kg-pipeline-customization).

---

## Text Splitting Strategies

### FixedSizeSplitter

```python
from neo4j_graphrag.experimental.components.text_splitters.fixed_size_splitter import FixedSizeSplitter

splitter = FixedSizeSplitter(chunk_size=500, chunk_overlap=100)
```

`chunk_size` = max characters per chunk. `chunk_overlap` = chars shared between consecutive chunks — preserves context across boundaries.

### Custom TextSplitter (section-aware)

```python
from neo4j_graphrag.experimental.components.text_splitters.base import TextSplitter, TextChunk, TextChunks

class SectionSplitter(TextSplitter):
    def run(self, text: str) -> TextChunks:
        sections = re.split(r"^== ", text, flags=re.MULTILINE)
        chunks = [TextChunk(uid=i, text=s.strip()) for i, s in enumerate(sections) if s.strip()]
        return TextChunks(chunks=chunks)

pipeline = SimpleKGPipeline(..., text_splitter=SectionSplitter())
```

### LangChain Adapter

```python
from neo4j_graphrag.experimental.components.text_splitters.langchain import LangChainTextSplitterAdapter
from langchain_text_splitters import CharacterTextSplitter

lc_splitter = CharacterTextSplitter(separator="\n\n", chunk_size=500, chunk_overlap=100)
splitter = LangChainTextSplitterAdapter(lc_splitter)
pipeline = SimpleKGPipeline(..., text_splitter=splitter)
```

Install: `pip install langchain-text-splitters`

---

## LexicalGraphConfig — Rename Graph Labels

Default graph model: `Document -[:FROM_DOCUMENT]-> Chunk -[:FROM_CHUNK]-> __Entity__`

Override any label or relationship name:

```python
from neo4j_graphrag.experimental.components.kg_writer import LexicalGraphConfig

config = LexicalGraphConfig(
    id_prefix="lesson",                              # prefix for generated IDs
    document_node_label="Lesson",                    # default: "Document"
    chunk_node_label="Section",                      # default: "Chunk"
    chunk_to_document_relationship_type="PART_OF",   # default: "FROM_DOCUMENT"
    next_chunk_relationship_type="NEXT_SECTION",     # default: "NEXT_CHUNK"
    node_to_chunk_relationship_type="FROM_SECTION",  # default: "FROM_CHUNK"
    chunk_embedding_property="vector",               # default: "embedding"
)
pipeline = SimpleKGPipeline(..., lexical_graph_config=config)
```

Inspect constructed graph:
```cypher
MATCH (d:Document)<-[:FROM_DOCUMENT]-(c:Chunk)
RETURN d.path, c.index, c.text, size(c.text)
ORDER BY d.path, c.index
```

---

## Entity Resolution — Strategies

### Default (inline, identical name merge)

`perform_entity_resolution=True` (default): merges nodes sharing same label + identical `name` property during ingestion. Fast, exact-match only.

### Disable (keep all duplicates)

```python
pipeline = SimpleKGPipeline(..., perform_entity_resolution=False)
```

Use during development for speed. Risk: duplicate entity nodes for same real-world entity.

### Post-Processing Resolvers (run after ingestion)

#### FuzzyMatchResolver

Merges entities with same label + similar name using RapidFuzz edit distance:

```python
from neo4j_graphrag.experimental.components.resolver import FuzzyMatchResolver

resolver = FuzzyMatchResolver(
    driver=driver,
    neo4j_database="neo4j",
    # Optional: filter_query to restrict which nodes to resolve
)
asyncio.run(resolver.run())
```

Install: `pip install neo4j-graphrag[fuzzy]` (adds `rapidfuzz`)

#### SpacySemanticMatchResolver

Merges entities with same label + semantically similar textual properties via spaCy:

```python
from neo4j_graphrag.experimental.components.resolver import SpacySemanticMatchResolver

resolver = SpacySemanticMatchResolver(driver=driver, neo4j_database="neo4j")
asyncio.run(resolver.run())
```

Install: `pip install neo4j-graphrag[spacy]` + `python -m spacy download en_core_web_lg`

Risk of over-merging: "Apple" (company) and "Apple" (fruit) may merge. Apply domain `filter_query` to restrict by label.

---

## Custom Document Loaders

### Extend PdfLoader (pre-process text)

```python
from neo4j_graphrag.experimental.components.pdf_loader import PdfLoader
import re

class CustomPDFLoader(PdfLoader):
    async def run(self, filepath: str):
        doc = await super().run(filepath)
        # Strip AsciiDoc attribute lines
        doc.text = re.sub(r"^:[\w-]+:.*$", "", doc.text, flags=re.MULTILINE)
        return doc

pipeline = SimpleKGPipeline(..., pdf_loader=CustomPDFLoader())
```

### Custom DataLoader (load from any source)

```python
from neo4j_graphrag.experimental.components.pdf_loader import DataLoader, PdfDocument, DocumentInfo

class TextFileLoader(DataLoader):
    async def run(self, filepath: str) -> PdfDocument:
        with open(filepath) as f:
            text = f.read()
        return PdfDocument(
            text=text,
            document_info=DocumentInfo(path=filepath, metadata={"source": "text_file"}),
        )

pipeline = SimpleKGPipeline(..., pdf_loader=TextFileLoader(), from_file=True)
asyncio.run(pipeline.run_async(file_path="data/document.txt"))
```

---

## KG Builder Prompt Customization

### Prepend domain instructions

```python
from neo4j_graphrag.experimental.components.entity_relation_extractor import (
    LLMEntityRelationExtractor,
)

# Simple approach: pass domain prefix to pipeline's prompt_template
domain_instructions = (
    "Extract ONLY technology companies, products, and people. "
    "Ignore financial data, dates, and locations."
)
pipeline = SimpleKGPipeline(
    ...,
    prompt_template=domain_instructions,  # prepended to default extraction prompt
)
```

### Full custom extraction prompt

```python
from neo4j_graphrag.experimental.components.entity_relation_extractor import (
    LLMEntityRelationExtractor,
    EntityExtractionPromptTemplate,
)

custom_prompt = EntityExtractionPromptTemplate(
    template="""You are a KG extractor. Extract entities from:
{text}
Schema: {schema}
Output JSON only."""
)
extractor = LLMEntityRelationExtractor(llm=llm, prompt_template=custom_prompt)
```

### LLM adapter for local/custom providers

```python
from neo4j_graphrag.llm import OpenAILLM

# LM Studio local model
llm = OpenAILLM(
    model_name="openai/gpt-oss-20b",
    model_params={"temperature": 0},
    base_url="http://localhost:1234/v1",
)
```

Custom provider: inherit from `neo4j_graphrag.llm.base.LLMInterface`, implement `invoke()` and `ainvoke()`.

---

## Explore Extracted Graph (Cypher)

```cypher
// View entities per chunk
MATCH p = (c:Chunk)<-[:FROM_CHUNK]-(e1:__Entity__)-[*1..2]->(e2:__Entity__)
RETURN p

// Count entity types
MATCH (e:__Entity__)
RETURN labels(e) AS types, count(*) AS n ORDER BY n DESC

// Find duplicate entities (pre-resolution check)
MATCH (e:__Entity__)
WITH e.name AS name, labels(e) AS lbl, count(*) AS cnt
WHERE cnt > 1
RETURN name, lbl, cnt ORDER BY cnt DESC
```
