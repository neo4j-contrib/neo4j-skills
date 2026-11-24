# Other Ingestion Paths

Moved from SKILL.md to keep it under the 500-line budget.

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

Local file: `apoc.load.json("file:///data.json")` — path is relative to the import directory (`server.directories.import`); put the file in `$NEO4J_HOME/import/`. Requires `apoc.import.file.enabled=true` in `conf/apoc.conf` (default false). HTTP URLs need neither.

Check APOC available: `RETURN apoc.version()`. APOC is included on all Aura tiers.

---

## LangChain Integration Pattern

```python
from langchain_neo4j import Neo4jGraph
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
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

## LexicalGraphConfig — Customize Labels

Override default lexical layer labels (keep defaults unless integrating with existing graph):
```python
from neo4j_graphrag.components.types import LexicalGraphConfig
# All fields have sensible defaults — only override what differs from your graph's conventions
config = LexicalGraphConfig(
    document_node_label="Article",             # default: "Document"
    chunk_node_label="Passage",                # default: "Chunk"
    node_to_chunk_relationship_type="HAS_ENTITY",  # default: "FROM_CHUNK" (Entity→Chunk)
    chunk_text_property="content",             # default: "text"
)
pipeline = SimpleKGPipeline(..., lexical_graph_config=config)
```

---

## Custom Document Loaders

Default `file_loader` auto-dispatches by extension (`.pdf`→`PdfLoader`, `.md`→`MarkdownLoader`).
Supports fsspec URIs (`s3://`, `gcs://`). Subclass `DataLoader` for HTML/web/custom formats:

```python
from neo4j_graphrag.components.data_loader import DataLoader
from neo4j_graphrag.components.types import DocumentInfo, LoadedDocument

class WebPageLoader(DataLoader):
    async def run(self, filepath: str, metadata=None) -> LoadedDocument:  # annotation required, else ComponentDefinitionError
        import httpx
        text = httpx.get(filepath).text   # strip HTML in real impl
        return LoadedDocument(text=text,
            document_info=DocumentInfo(path=filepath, metadata=metadata))

pipeline = SimpleKGPipeline(..., file_loader=WebPageLoader(), from_file=True)
```

Chunking strategy by use-case and full resolver config: [references/kg-construction.md](kg-construction.md).

---
