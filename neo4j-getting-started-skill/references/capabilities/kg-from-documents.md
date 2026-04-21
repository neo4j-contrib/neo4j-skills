# Capability — kg-from-documents
# Build a knowledge graph from unstructured documents using neo4j-graphrag SimpleKGPipeline.
# Used in the `load` stage when DATA_SOURCE=documents.

## Overview

The `neo4j-graphrag` library's `SimpleKGPipeline` handles the full ETL from raw text to a
graph of entities and relationships, with embeddings for vector search. It requires:
- An LLM for entity/relation extraction
- An embedder for chunk embeddings
- A running Neo4j database with vector + fulltext indexes

## Installation

```bash
.venv/bin/pip install neo4j-rust-ext "neo4j-graphrag[openai]>=1.13.0" python-dotenv

# Embedding/LLM provider (pick one):
.venv/bin/pip install openai          # OpenAI text-embedding-3-small / gpt-5.4-mini
.venv/bin/pip install cohere          # Cohere embed-english-v3.0
# Ollama: no extra install — uses HTTP API at localhost:11434
```

## Step K1 — Schema (model stage output)

The `model` stage should have produced `schema.cypher`. For KG/documents, it typically includes:

```cypher
CYPHER 25
CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;
// SimpleKGPipeline stores all extracted entities under :__KGBuilder__ — always add this constraint
CREATE CONSTRAINT kgbuilder_name IF NOT EXISTS FOR (e:__KGBuilder__) REQUIRE e.name IS NOT NULL;

CREATE FULLTEXT INDEX entity_search IF NOT EXISTS
  FOR (e:__KGBuilder__) ON EACH [e.name];
```

**Note**: Do NOT add `CREATE VECTOR INDEX` in schema.cypher for the documents path. The vector index must be created **after** ingestion using `create_vector_index()` from `neo4j_graphrag.indexes` (see Step K2). The `apply_schema()` Cypher parser can mishandle the `OPTIONS { ... }` block.

Apply this before running the pipeline (`load` step L0).

## Step K1b — Optional: extract schema from a sample document first

If you're unsure what entity/relationship types to use, let the LLM infer them from a
sample document by passing `schema=None` (the default). Run on **one file only**, inspect
the result, refine if needed, then commit to a `schema={}` dict for the full run.

```python
import asyncio, os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.llm import OpenAILLM
from pathlib import Path

load_dotenv()
driver   = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]))
embedder = OpenAIEmbeddings(model=os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"))
llm      = OpenAILLM(model_name=os.environ.get("LLM_MODEL", "gpt-5.4-mini"))

# schema=None → LLM infers entity/relationship types from the first document
pipeline = SimpleKGPipeline(llm=llm, driver=driver, embedder=embedder, schema=None,
                             neo4j_database=os.environ.get("NEO4J_DATABASE", "neo4j"))

sample = next(Path("data/").glob("**/*.txt"))   # pick first file
asyncio.run(pipeline.run_async(text=sample.read_text(encoding="utf-8", errors="replace")))

# Inspect what was extracted — then refine into a schema={} dict for the full run
```

After running, inspect the graph:
```cypher
CYPHER 25
CALL db.schema.visualization()
```

Review the extracted labels and relationship types. If they look right, use them as
`NODE_TYPES` / `RELATIONSHIP_TYPES` / `PATTERNS` in Step K2. If they're too noisy or
too generic, adjust and re-run on the sample before processing all documents.

## Step K2 — Configure the pipeline

Generate `import/ingest_docs.py`. Adapt entity types, relationship types, and patterns to
the domain — the schema below is illustrative; replace with domain-appropriate types:

```python
"""
import/ingest_docs.py — Build knowledge graph from documents using SimpleKGPipeline.
Usage: .venv/bin/python3 import/ingest_docs.py [--docs-dir ./data/]
"""
import asyncio
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

# ── Embedding provider selection ──────────────────────────────────────────────
# Set EMBEDDING_PROVIDER in .env: openai | cohere | ollama
provider = os.environ.get("EMBEDDING_PROVIDER", "openai")
embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

if provider == "openai":
    from neo4j_graphrag.embeddings import OpenAIEmbeddings
    embedder = OpenAIEmbeddings(model=embedding_model)
    dimensions = int(os.environ.get("EMBEDDING_DIMENSIONS", "1536"))

elif provider == "cohere":
    from neo4j_graphrag.embeddings import CohereEmbeddings
    embedder = CohereEmbeddings(model=embedding_model or "embed-english-v3.0")
    dimensions = 1024

elif provider == "ollama":
    from neo4j_graphrag.embeddings import OllamaEmbeddings
    embedder = OllamaEmbeddings(
        model=embedding_model or "nomic-embed-text",
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    dimensions = 768  # nomic-embed-text default

else:
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider}. Use openai, cohere, or ollama.")

# ── LLM selection ─────────────────────────────────────────────────────────────
llm_provider = os.environ.get("LLM_PROVIDER", "openai")
llm_model = os.environ.get("LLM_MODEL", "gpt-5.4-mini")

if llm_provider == "openai":
    from neo4j_graphrag.llm import OpenAILLM
    llm = OpenAILLM(model_name=llm_model)
elif llm_provider == "anthropic":
    from neo4j_graphrag.llm import AnthropicLLM
    llm = AnthropicLLM(model_name=llm_model or "claude-haiku-4-5-20251001")
else:
    raise ValueError(f"Unknown LLM_PROVIDER: {llm_provider}. Use openai or anthropic.")

# ── Neo4j connection ──────────────────────────────────────────────────────────
driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
)

# ── Domain schema ─────────────────────────────────────────────────────────────
# Adapt these to the domain. Use descriptive labels; add properties where useful.
# For schema=None (default), the LLM infers types automatically from the text.
# For a guided extraction, define node_types, relationship_types, and patterns.
NODE_TYPES = [
    # Simple string → just a label; or dict → label + description + required properties
    "Person",
    "Organization",
    "Location",
    {"label": "Topic", "description": "A subject, concept, or theme mentioned in the text"},
]

RELATIONSHIP_TYPES = [
    "MENTIONS",
    "RELATED_TO",
    {"label": "WORKS_FOR", "description": "A person is employed by an organization"},
]

PATTERNS = [
    ("Person", "WORKS_FOR", "Organization"),
    ("Organization", "MENTIONS", "Topic"),
    ("Person", "MENTIONS", "Topic"),
]

# ── Pipeline setup ────────────────────────────────────────────────────────────
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.indexes import create_vector_index

pipeline = SimpleKGPipeline(
    llm=llm,
    driver=driver,
    embedder=embedder,
    from_pdf=False,  # set True if processing PDF files
    neo4j_database=os.environ.get("NEO4J_DATABASE", "neo4j"),
    schema={
        "node_types": NODE_TYPES,
        "relationship_types": RELATIONSHIP_TYPES,
        "patterns": PATTERNS,
    },
    perform_entity_resolution=True,  # merge nodes with same label+name
)

# ── Document loading ──────────────────────────────────────────────────────────
def load_documents(docs_dir: str) -> list[tuple[str, str]]:
    """Return (filename, text) pairs for .txt, .md, and .pdf files in docs_dir."""
    results = []
    for path in sorted(Path(docs_dir).glob("**/*")):
        if not path.is_file():
            continue
        if path.suffix in (".txt", ".md"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if len(text.strip()) >= 100:
                results.append((path.name, text, path.suffix))
            else:
                print(f"  ⚠ Skipping {path.name} — too short ({len(text)} chars)")
        elif path.suffix == ".pdf":
            results.append((path.name, None, ".pdf"))
    return results

async def ingest(docs_dir: str):
    docs = load_documents(docs_dir)
    if not docs:
        print(f"  ✗ No documents found in {docs_dir}")
        return

    print(f"\nIngesting {len(docs)} document(s) from {docs_dir}...\n")
    for i, (name, text, suffix) in enumerate(docs, 1):
        print(f"  [{i}/{len(docs)}] {name} ({len(text) if text else '?'} chars)")
        try:
            if suffix == ".pdf":
                await pipeline.run_async(file_path=str(Path(docs_dir) / name))
            else:
                await pipeline.run_async(text=text)
            print(f"         ✓ done")
        except Exception as e:
            print(f"         ✗ error: {e}")

    # ── Create vector index (SimpleKGPipeline does NOT create it automatically) ─
    db = os.environ.get("NEO4J_DATABASE", "neo4j")
    create_vector_index(
        driver,
        name="chunk_embeddings",
        label="Chunk",
        embedding_property="embedding",
        dimensions=dimensions,
        similarity_fn="cosine",
        neo4j_database=db,
    )
    print("  ✓ Vector index 'chunk_embeddings' created (or already exists)")

    # ── Graph summary ─────────────────────────────────────────────────────────
    records, _, _ = driver.execute_query(
        "MATCH (n) RETURN labels(n)[0] AS l, count(n) AS c ORDER BY c DESC",
        database_=db,
    )
    print("\nGraph summary:")
    for r in records:
        print(f"  {r['l']}: {r['c']}")

    records, _, _ = driver.execute_query(
        "SHOW VECTOR INDEXES YIELD name, state, populationPercent RETURN name, state, populationPercent",
        database_=db,
    )
    print("\nVector indexes:")
    for r in records:
        print(f"  {r['name']}: {r['state']} ({r['populationPercent']:.0f}%)")

    driver.close()
    print("\n✓ Ingestion complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-dir", default="./data/")
    args = parser.parse_args()
    asyncio.run(ingest(args.docs_dir))
```

## Step K3 — .env additions needed

```bash
# Add to .env (already created by provision stage):
EMBEDDING_PROVIDER=openai          # openai | cohere | ollama
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
LLM_PROVIDER=openai                # openai | anthropic
LLM_MODEL=gpt-5.4-mini
OPENAI_API_KEY=sk-...              # required for openai provider
# COHERE_API_KEY=...               # required for cohere provider
# OLLAMA_BASE_URL=http://localhost:11434  # only for ollama
```

## Step K4 — Run the pipeline

```bash
# Documents should already be in ./data/
# (placed there by the user, copied from fixture, or downloaded)
.venv/bin/python3 import/ingest_docs.py --docs-dir ./data/
```

## Step K5 — Post-ingestion: verify graph and vector index

**Run ingestion synchronously — never in background.** Wait for "✓ Ingestion complete" before proceeding.

Check what was actually created (entity labels may differ from the schema you specified):

```cypher
CYPHER 25
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC
```
```cypher
CYPHER 25
MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS cnt ORDER BY cnt DESC
```

**SimpleKGPipeline default graph structure:**

| Neo4j element | Description |
|--------------|-------------|
| `:Chunk` | Text chunk nodes with `.embedding` vector property |
| `:__KGBuilder__` | Extracted entity nodes (Party, Jurisdiction, etc. stored here) |
| `[:FROM_CHUNK]` | `(:__KGBuilder__)-[:FROM_CHUNK]->(:Chunk)` — entity came from this chunk |
| `[:FROM_DOCUMENT]` | `(:Chunk)-[:FROM_DOCUMENT]->(:__KGBuilder__ {label:"Document"})` |
| `[:NEXT_CHUNK]` | Sequential chunk chain |
| Custom rels | `IMPOSES`, `PARTY_TO`, `GOVERNS` etc. as specified in PATTERNS |

The vector index is on `:Chunk` nodes. The `retrieval_query` for `VectorCypherRetriever` must traverse from `node` (a `Chunk`) to `__KGBuilder__` entities via `FROM_CHUNK`:

```cypher
CYPHER 25
SHOW VECTOR INDEXES YIELD name, state, populationPercent
RETURN name, state, populationPercent
```

Wait for `state=ONLINE` and `populationPercent=100` before running vector queries.

## Step K6 — Test retrieval

```python
# Quick smoke test: does vector search return anything?
from neo4j_graphrag.retrievers import VectorRetriever
from neo4j_graphrag.embeddings import OpenAIEmbeddings

embedder = OpenAIEmbeddings(model="text-embedding-3-small")
retriever = VectorRetriever(
    driver=driver,
    index_name="chunk_embeddings",
    embedder=embedder,
)
# Use a representative question from the domain
results = retriever.search(query_text="<representative question for this domain>", top_k=3)
assert results.items, "No results — check vector index is ONLINE and documents were embedded"
for item in results.items:
    print(item.content[:200])
```

## Step K7 — Streamlit GraphRAG chatbot (APP_TYPE=streamlit)

When the user wants a Streamlit Q&A chatbot over their documents, generate `app.py`.
This template works for any domain — adapt the title, placeholder text, and
`retrieval_query` to the domain schema produced by stage 3.

```python
"""
app.py — GraphRAG chatbot using VectorCypherRetriever + Streamlit.
Run: .venv/bin/streamlit run app.py
"""
import os
from dotenv import load_dotenv
import streamlit as st
from neo4j import GraphDatabase
from neo4j_graphrag.retrievers import VectorCypherRetriever
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.generation import GraphRAG

load_dotenv()

# ── Cached resources — created once per Streamlit session ────────────────────
@st.cache_resource
def get_graphrag():
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
    )
    embedder = OpenAIEmbeddings(model=os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"))
    llm = OpenAILLM(model_name=os.environ.get("LLM_MODEL", "gpt-5.4-mini"))

    # retrieval_query: Cypher fragment executed after the vector search.
    # `node` = matched Chunk, `score` = cosine similarity.
    # SimpleKGPipeline stores extracted entities under :__KGBuilder__ label.
    # Entities connect back to their source chunk via FROM_CHUNK (direction: entity→chunk).
    # IMPORTANT: after ingestion run db.schema.visualization() and adapt patterns to match.
    retrieval_query = """
    OPTIONAL MATCH (entity:__KGBuilder__)-[:FROM_CHUNK]->(node)
    RETURN
        node.text                              AS chunk_text,
        collect(DISTINCT entity.name)[..5]     AS entities,
        score
    ORDER BY score DESC
    """

    retriever = VectorCypherRetriever(
        driver=driver,
        index_name="chunk_embeddings",
        embedder=embedder,
        retrieval_query=retrieval_query,
        neo4j_database=os.environ.get("NEO4J_DATABASE", "neo4j"),
    )
    return GraphRAG(llm=llm, retriever=retriever)


# ── UI ─────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Document Q&A", layout="wide")
st.title("Document Knowledge Graph — Q&A")
st.caption("Ask questions about your documents. Answers are grounded in the graph.")

query = st.text_input(
    "Your question",
    placeholder="Ask anything about your documents...",
)
top_k = st.sidebar.slider("Chunks to retrieve", min_value=3, max_value=15, value=5)

if query:
    with st.spinner("Searching the knowledge graph..."):
        try:
            graphrag = get_graphrag()
            result = graphrag.search(
                query_text=query,
                retriever_config={"top_k": top_k},
                return_context=True,   # populate result.retriever_result
            )

            st.subheader("Answer")
            st.write(result.answer)

            if result.retriever_result and result.retriever_result.items:
                with st.expander(f"Source chunks ({len(result.retriever_result.items)} retrieved)"):
                    for i, item in enumerate(result.retriever_result.items, 1):
                        st.markdown(f"**Chunk {i}**")
                        st.text(item.content[:500] + ("..." if len(item.content) > 500 else ""))
                        st.divider()
        except Exception as e:
            st.error(f"Error: {e}")
            st.info("Check that OPENAI_API_KEY is set in .env and the vector index is ONLINE.")
```

Requirements for this app (`requirements.txt`):

```
neo4j-rust-ext>=0.0.1
neo4j-graphrag[openai]>=1.13.0
streamlit>=1.35.0
python-dotenv>=1.0.0
```

## Step K8 — ToolsRetriever: multi-tool agent (optional upgrade)

`ToolsRetriever` wraps multiple retrievers as LLM tools. The LLM inspects the query,
picks the best tool(s), runs them, and combines results — a built-in mini agent loop.
Good for domains where some questions need semantic search and others need precise
entity/relationship lookups:

```python
from neo4j_graphrag.retrievers import ToolsRetriever, VectorCypherRetriever, Text2CypherRetriever

# Vector search over chunks (semantic — open-ended questions about content)
vector_retriever = VectorCypherRetriever(
    driver=driver,
    index_name="chunk_embeddings",
    embedder=embedder,
    retrieval_query=retrieval_query,   # same as K7; uses __KGBuilder__ + FROM_CHUNK
)

# Text-to-Cypher (precise — entity lookups, relationship counts, filtering)
text2cypher_retriever = Text2CypherRetriever(
    driver=driver,
    llm=llm,
    neo4j_schema=None,   # auto-fetched from the DB
)

tools_retriever = ToolsRetriever(
    driver=driver,
    llm=llm,
    tools=[
        vector_retriever.convert_to_tool(
            name="semantic_search",
            description="Find relevant text chunks using semantic similarity. "
                        "Use for open-ended questions about content, topics, or descriptions.",
        ),
        text2cypher_retriever.convert_to_tool(
            name="graph_query",
            description="Query the knowledge graph for specific entities and relationships. "
                        "Use for precise lookups: which documents mention X, how entities relate.",
        ),
    ],
)

rag = GraphRAG(llm=llm, retriever=tools_retriever)
result = rag.search(query_text=query, return_context=True)
```

Swap `tools_retriever` for the single `retriever` in the `@st.cache_resource` function
above — the Streamlit app code is otherwise identical.

## Completion condition

- Documents ingested (each doc processed by pipeline)
- Vector index state = ONLINE
- `VectorRetriever.search()` returns ≥1 result on a test query
- `import/ingest_docs.py` saved in `import/` directory
- (if APP_TYPE=streamlit) `app.py` generated with VectorCypherRetriever

## Common issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Vector index `POPULATING` | Index still building | Wait and re-check `populationPercent` |
| `EmbeddingError` / `AuthenticationError` | Missing API key | Set `OPENAI_API_KEY` / `COHERE_API_KEY` in `.env` |
| Empty chunks | Documents too short | Ensure each doc has ≥100 chars |
| Slow ingestion | Large docs + many entities | Use `gpt-5.4-mini` for extraction; run docs sequentially |
| Dimensions mismatch | Wrong `vector.dimensions` in index | Drop and recreate vector index matching your model's output |
| `retrieval_query` returns no source | Wrong relationship type | Inspect schema with `CALL db.schema.visualization()` and adjust MATCH |
