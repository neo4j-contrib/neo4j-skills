# Stage 7 — build
# Generate a runnable application, dashboard, or agent integration.
# v1: Python only. JavaScript in phase 2.

## Virtual environment (required — always use .venv)

Modern Python (3.12+) forbids global `pip install` — always use `.venv` from stage 0.

```bash
.venv/bin/pip install -r requirements.txt
```

Never use bare `pip install` or `python3` — always `.venv/bin/pip` and `.venv/bin/python3`.

## Always include in requirements.txt

```
neo4j-rust-ext>=0.0.1
python-dotenv>=1.0.0
```

**CRITICAL**: Do **not** add `neo4j` as a standalone dependency — it is a transitive dependency of `neo4j-rust-ext`.
If you write `neo4j>=...` in requirements.txt, delete it and replace with `neo4j-rust-ext>=0.0.1`.

Add `neo4j-viz>=1.0.0` to requirements.txt for **Path A (notebook) and Path B (Streamlit)** — it is used for graph visualization and must be listed explicitly.

## Path selection

```
APP_TYPE=notebook      → Path A: Jupyter notebook
APP_TYPE=streamlit     → Path B: Streamlit dashboard
APP_TYPE=fastapi       → Path C: FastAPI backend
APP_TYPE=graphrag      → Path D: GraphRAG pipeline
APP_TYPE=explore-only  → skip build; output queries.cypher + README only
APP_TYPE=mcp           → Path E: neo4j-mcp configuration
```

## Path A — Jupyter Notebook

**Two-step: test Python snippets first, then compose into notebook.** Avoids writing a large notebook only to discover connection or query errors.

### Step A0 — Smoke-test key snippets in isolation

Before writing the notebook, verify the critical pieces work:

```python
# Test: connection + use-case query (run with python3, not jupyter)
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os, pandas as pd

load_dotenv()
driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
)
driver.verify_connectivity()
print("✓ Connected")

# Test the core use-case query (adapt to domain)
records, _, _ = driver.execute_query("""
    CYPHER 25
    MATCH (me:Person {id: $id})-[:FOLLOWS]->(f)-[:FOLLOWS]->(fof)
    WHERE NOT exists { (me)-[:FOLLOWS]->(fof) } AND me <> fof
    WITH fof, count(DISTINCT f) AS mutual
    ORDER BY mutual DESC LIMIT 10
    RETURN fof.name AS recommendation, mutual
""", id="p1", database_="neo4j")
df = pd.DataFrame([r.data() for r in records])
assert len(df) > 0, "No recommendations returned — check data and query"
print(f"✓ Use-case query works: {len(df)} recommendations")
driver.close()
```

Run: `.venv/bin/python3 /tmp/smoke_test.py`. **Only proceed to notebook composition once this passes.**

### Step A1 — Compose `notebook.ipynb`

Required cells (one focus per cell):

1. **Setup** — imports + `.env` loading via `python-dotenv`
2. **Connection** — create driver, verify connectivity
3. **Schema** — `CALL db.labels()` etc., display as DataFrame
4. **Per-query cells** — one cell per query from `queries/queries.cypher`, display as DataFrame
5. **Graph visualization — REQUIRED, do not skip** — interactive graph using `neo4j-viz`
6. **Use-case answer cell** — use the query verified in Step A0; include assertion + plot

```python
# Cell: Setup (run once if packages are missing)
# %pip install -q neo4j-rust-ext python-dotenv pandas matplotlib neo4j-viz
```

```python
# Cell: Graph Visualization  ← REQUIRED — this is the "it clicks" moment for users
from neo4j_viz.neo4j import from_neo4j
from neo4j import RoutingControl

result = driver.execute_query(
    "CYPHER 25 MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50",
    routing_=RoutingControl.READ,
    database_=os.environ.get("NEO4J_DATABASE", "neo4j")
)
vg = from_neo4j(result)
vg.color_nodes(field="caption")
vg.render()
```

```python
# Cell: Connection
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os, pandas as pd

load_dotenv()
driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
)
driver.verify_connectivity()
print("✓ Connected")

def run_query(q, params={}):
    records, _, _ = driver.execute_query(q, parameters_=params,
                                          database_=os.environ.get("NEO4J_DATABASE","neo4j"))
    return pd.DataFrame([r.data() for r in records])
```

```python
# Cell: Use-case answer (adapt to domain)
df = run_query("""
    CYPHER 25
    MATCH (me:Person {id: $id})-[:FOLLOWS]->(f)-[:FOLLOWS]->(fof)
    WHERE NOT exists { (me)-[:FOLLOWS]->(fof) } AND me <> fof
    WITH fof, count(DISTINCT f) AS mutual
    ORDER BY mutual DESC LIMIT 10
    RETURN fof.name AS recommendation, mutual
""", {"id": "1"})
assert len(df) > 0, "No recommendations — check import and traversal query"
df.plot(kind='barh', x='recommendation', y='mutual', title='Recommendations')
```

Validate: `python3 -m json.tool notebook.ipynb > /dev/null && echo "✓ Valid notebook"`

Install and run:
```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/jupyter notebook notebook.ipynb
```

Add to `requirements.txt`:
```
jupyter>=1.0.0
ipykernel>=6.0.0
pandas>=2.0.0
matplotlib>=3.0.0
neo4j-viz>=1.0.0
```

## Path B — Streamlit Dashboard

**If DATA_SOURCE=documents**: use the GraphRAG chatbot template from `${CLAUDE_SKILL_DIR}/references/capabilities/kg-from-documents.md` Step K7 — it uses `VectorCypherRetriever` to ground answers in ingested document chunks.

Generate `app.py` (generic dashboard for non-documents data sources):

```python
import streamlit as st
from neo4j import GraphDatabase, RoutingControl
from neo4j_viz.neo4j import from_neo4j
from dotenv import load_dotenv
import os, pandas as pd

load_dotenv()

@st.cache_resource
def get_driver():
    return GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
    )

def run_query(q, params={}):
    records, _, _ = get_driver().execute_query(
        q, parameters_=params,
        database_=os.environ.get("NEO4J_DATABASE", "neo4j")
    )
    return pd.DataFrame([r.data() for r in records])

st.title(f"{DOMAIN} — {USE_CASE}")

# Sidebar controls
limit = st.sidebar.slider("Results limit", 5, 100, 20)

# Section 1: Overview
st.header("Database Overview")
df = run_query("CYPHER 25 MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count")
st.bar_chart(df.set_index("label"))

# Section 2: Graph visualization — REQUIRED, do not skip
st.header("Graph Visualization")
result = get_driver().execute_query(
    "CYPHER 25 MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50",
    routing_=RoutingControl.READ,
    database_=os.environ.get("NEO4J_DATABASE", "neo4j")
)
vg = from_neo4j(result)
vg.color_nodes(field="caption")
# render() returns IPython.display.HTML — extract .data for Streamlit
st.components.v1.html(vg.render().data, height=500, scrolling=True)

# Section 3: Use-case answer (adapt to domain)
st.header("<Use-case headline>")
df2 = run_query("<traversal query from queries.cypher>", {"limit": limit})
st.dataframe(df2)
assert not df2.empty, "Query returned no results"
```

Add to `requirements.txt`:
```
streamlit>=1.30.0
pandas>=2.0.0
neo4j-viz>=1.0.0
```

Install and run:
```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```
Validate: `.venv/bin/python3 -m py_compile app.py && echo "✓ Syntax OK"`

## Path C — FastAPI Backend

### Step C0 — Smoke-test connection before writing the app

```python
# Save as /tmp/smoke_test.py and run: .venv/bin/python3 /tmp/smoke_test.py
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()
driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
)
driver.verify_connectivity()
records, _, _ = driver.execute_query(
    "MATCH (n) RETURN count(n) AS total",
    database_=os.environ.get("NEO4J_DATABASE", "neo4j")
)
assert records[0]["total"] > 0, "Database is empty — check load stage"
print(f"✓ Connected. {records[0]['total']} nodes in DB")
driver.close()
```

**Only proceed once this passes.**

### Step C1 — Generate `main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

_driver = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _driver
    _driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
    )
    _driver.verify_connectivity()
    yield
    _driver.close()

app = FastAPI(title=f"{DOMAIN} API — {USE_CASE}", lifespan=lifespan)

def driver():
    return _driver

@app.get("/health")
def health():
    records, _, _ = driver().execute_query(
        "MATCH (n) RETURN count(n) AS total",
        database_=os.environ.get("NEO4J_DATABASE", "neo4j")
    )
    return {"status": "ok", "total_nodes": records[0]["total"]}

@app.get("/<entities>")
def list_entities(limit: int = 20):
    records, _, _ = driver().execute_query(
        "CYPHER 25 MATCH (n:<Label>) RETURN n.id AS id, n.name AS name LIMIT $limit",
        limit=limit, database_=os.environ.get("NEO4J_DATABASE", "neo4j")
    )
    return [dict(r) for r in records]

@app.get("/<entities>/{id}/recommendations")
def recommendations(id: str, limit: int = 10):
    records, _, _ = driver().execute_query(
        "<traversal query from queries.cypher>",
        id=id, limit=limit,
        database_=os.environ.get("NEO4J_DATABASE", "neo4j")
    )
    return [dict(r) for r in records]
```

**IMPORTANT — Cypher query parameter rule**: Named query parameters (`$limit`, `$id`, etc.) are passed as **keyword arguments** directly to `execute_query()`. Do NOT use `limit_=` (that is a driver keyword for the built-in `limit_` option, not a Cypher parameter). Use `limit=limit`, `id=id`, etc.

**IMPORTANT — Avoid cross-product inflation in aggregate queries**: When computing counts across multiple optional relationships, use COUNT subqueries instead of sequential OPTIONAL MATCH:

```cypher
// BAD — inflates counts via cross-product:
MATCH (c:Customer {id: $id})
OPTIONAL MATCH (c)-[:PLACED]->(o:Order)
OPTIONAL MATCH (o)-[:CONTAINS]->(p:Product)
RETURN count(o) AS orders, count(p) AS products

// GOOD — independent counts via subqueries:
MATCH (c:Customer {id: $id})
RETURN COUNT { (c)-[:PLACED]->(:Order) } AS orders,
       COUNT { (c)-[:PLACED]->(:Order)-[:CONTAINS]->(:Product) } AS products
```

### Step C2 — Validate and run

Add to `requirements.txt`:
```
fastapi>=0.110.0
uvicorn>=0.29.0
```

Install, validate, and run:
```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python3 -m py_compile main.py && echo "✓ Syntax OK"
.venv/bin/uvicorn main:app --reload
```
Docs: `http://localhost:8000/docs`

Smoke-test the running app:
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```
Assert `total_nodes > 0` in the response.

## Path D — GraphRAG Pipeline

**If DATA_SOURCE=documents**: full pipeline in `${CLAUDE_SKILL_DIR}/references/capabilities/kg-from-documents.md` (Steps K7/K8). Use the Streamlit chatbot template (Step K7) or ToolsRetriever (Step K8).

For a standalone smoke-test script `graphrag_app.py`:

```python
from neo4j_graphrag.retrievers import VectorCypherRetriever
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.llm import OpenAILLM
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()
driver   = GraphDatabase.driver(os.environ["NEO4J_URI"],
                                auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]))
embedder = OpenAIEmbeddings(model=os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"))
llm      = OpenAILLM(model_name=os.environ.get("LLM_MODEL", "gpt-5.4-mini"))

# SimpleKGPipeline stores entities as :__KGBuilder__ nodes connected via FROM_CHUNK.
# Always inspect actual schema after ingestion: db.schema.visualization()
retrieval_query = """
OPTIONAL MATCH (entity:__KGBuilder__)-[:FROM_CHUNK]->(node)
RETURN node.text                            AS chunk_text,
       collect(DISTINCT entity.name)[..5]   AS entities,
       score
ORDER BY score DESC
"""

retriever = VectorCypherRetriever(
    driver=driver,
    index_name="chunk_embeddings",
    retrieval_query=retrieval_query,
    embedder=embedder,
    neo4j_database=os.environ.get("NEO4J_DATABASE", "neo4j"),
)
rag = GraphRAG(retriever=retriever, llm=llm)

if __name__ == "__main__":
    query = input("Ask a question: ")
    response = rag.search(query_text=query, retriever_config={"top_k": 5}, return_context=True)
    assert response.answer, "GraphRAG returned empty — check embeddings and vector index are ONLINE"
    print(response.answer)
```

Add to `requirements.txt`:
```
neo4j-graphrag[openai]>=1.13.0
```

## Path E — MCP Integration

Install `neo4j-mcp` binary (done in prerequisites). Write config files:

**For Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS,
`%APPDATA%\Claude\claude_desktop_config.json` on Windows):
```json
{
  "mcpServers": {
    "neo4j": {
      "command": "/absolute/path/to/neo4j-mcp",
      "env": {
        "NEO4J_URI": "<from .env>",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "<from .env>",
        "NEO4J_DATABASE": "neo4j"
      }
    }
  }
}
```

**For Claude Code** (`.claude/settings.json` in project root):
```json
{
  "mcpServers": {
    "neo4j": {
      "command": "./neo4j-mcp",
      "env": {
        "NEO4J_URI": "<from .env>",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "<from .env>",
        "NEO4J_DATABASE": "neo4j"
      }
    }
  }
}
```

Available MCP tools after restart: `read-cypher`, `write-cypher`, `get-schema`, `list-gds-procedures`.

Tell user: "Restart Claude Desktop or Claude Code — the `neo4j` server will appear as available tools."

For read-only mode (recommended for production/shared DBs), add:
```json
"NEO4J_READ_ONLY": "true"
```

## On Completion — write to progress.md

```markdown
### 7-build
status: done
artifact=<filename, e.g. notebook.ipynb or app.py>
app_type=<notebook|streamlit|fastapi|graphrag|mcp>
run_command=<e.g. ".venv/bin/jupyter notebook notebook.ipynb" or ".venv/bin/streamlit run app.py">
files=<artifact filename>,requirements.txt
```

## Completion condition

- At least one artifact exists and passes syntax check (or is valid JSON for notebooks)
- At least one cell / endpoint / function returns non-empty results for the use-case query
- `requirements.txt` written
- MCP config written to correct location (if `APP_TYPE=mcp` or requested)
- **`README.md` written** — required final output; follow the README template in `SKILL.md` (Final Summary section). Fill every placeholder from `progress.md` and the actual generated files. Do not skip.

## Error recovery

- App returns empty results → verify `load` stage completed, check query parameter names match schema
- Import error → check `requirements.txt`, run `.venv/bin/pip install -r requirements.txt`
- MCP not appearing in Claude → verify absolute path to binary; for Claude Desktop restart the app; for Claude Code run `/reload` or restart Claude Code
