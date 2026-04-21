# Stage 5 — explore
# Give the user a visual view of their graph — the "it clicks" moment.
# This is a hard success gate. Do not skip.

## Why this matters

For first-time Neo4j users, seeing nodes and edges rendered is often the defining moment when graph databases make sense. Always deliver a visual entry point after import.

## Option A — Neo4j Browser standalone (always available, zero install)

Generate and print the URL:

```python
import os, urllib.parse
from dotenv import load_dotenv
load_dotenv()

uri = os.environ.get("NEO4J_URI", "")
user = os.environ.get("NEO4J_USERNAME", "neo4j")

# Strip scheme prefix to get host
host = uri
for prefix in ["neo4j+s://", "neo4j://", "bolt+s://", "bolt://"]:
    host = host.replace(prefix, "")

# Encode the connectURL parameter
connect_url = f"neo4j+s://{user}@{host}"
encoded = urllib.parse.quote(connect_url, safe="")
browser_url = f"https://browser.neo4j.io/?connectURL={encoded}"

print(f"\n🔍 See your graph:")
print(f"   {browser_url}")
print(f"\n   Run this query after connecting:")
print(f"   MATCH (n)-[r]->(m) RETURN n,r,m LIMIT 50")
```

Tell the user: "Open the URL above, connect with your password from `.env`, then run the query to see your data as a graph."

## Option B — Notebook visualization (for APP_TYPE=notebook)

Use **neo4j-viz** — the official Neo4j Python graph visualization library:

```python
# %pip install -q neo4j-viz
from neo4j_viz.neo4j import from_neo4j
from neo4j import GraphDatabase, RoutingControl
import os
from dotenv import load_dotenv
load_dotenv()

driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
)
result = driver.execute_query(
    "CYPHER 25 MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50",
    routing_=RoutingControl.READ
)
vg = from_neo4j(result)
vg.color_nodes(field="caption")
vg.render()
```

## Option C — VS Code Neo4j extension

Tell the user: "If you're in VS Code, install the **Neo4j extension** — it connects to your DB and renders Cypher query results as an interactive graph directly in the editor."

## Sample visualization queries by domain

Include one of these in the browser suggestion, adapted to the user's schema:

```cypher
// Social: show follow network
CYPHER 25
MATCH (p:Person)-[:FOLLOWS]->(friend:Person)
RETURN p, friend LIMIT 50;

// E-commerce: show customer orders and products
CYPHER 25
MATCH (c:Customer)-[:PLACED]->(o:Order)-[:CONTAINS]->(p:Product)
RETURN c, o, p LIMIT 50;

// Finance: show transaction network
CYPHER 25
MATCH (a:Account)-[t:TRANSFERRED_TO]->(b:Account)
RETURN a, t, b LIMIT 50;

// KG/RAG: show document-chunk-entity structure (SimpleKGPipeline)
CYPHER 25
MATCH (e:__KGBuilder__)-[:FROM_CHUNK]->(c:Chunk)-[:FROM_DOCUMENT]->(d)
RETURN e, c, d LIMIT 50;
```

## On Completion — write to progress.md

**CRITICAL: This write is a hard gate. Do it immediately after generating the URL — before moving to stage 6.**

```markdown
### 5-explore
status: done
browser_url=<the generated https://browser.neo4j.io/... URL>
viz_method=<browser|notebook-neo4j-viz|vscode>
```

The `browser_url` line in the `### 5-explore` section is validated by the test harness.
Write it to `progress.md` even if APP_TYPE=streamlit or APP_TYPE=notebook — the browser URL is always useful.

## Completion condition

- Browser URL printed to stdout (Option A) AND written to progress.md, OR
- Notebook visualization cell added (Option B) AND browser_url written to progress.md, OR
- VS Code extension suggested (Option C) AND browser_url written to progress.md

**Option A (browser_url) must always be delivered and recorded, regardless of APP_TYPE.**
