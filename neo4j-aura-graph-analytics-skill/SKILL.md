---
name: neo4j-aura-graph-analytics-skill
description: Serverless GDS sessions on Neo4j Aura — covers GdsSessions, AuraAPICredentials,
  DbmsConnectionInfo, SessionMemory, get_or_create, remote graph projection, gds.graph.project.remote,
  gds.graph.construct, algorithm execution (mutate/stream/write), async job polling,
  result retrieval, and session lifecycle. Use when running graph algorithms on Aura
  Business Critical or VDC, processing graph data from Pandas/Spark, or using the
  graphdatascience Python client in AGA (serverless) mode. Covers all three data source
  three source modes (AuraDB-connected, self-managed Neo4j, standalone from DataFrames).
  Does NOT cover the embedded GDS plugin on Aura Pro or self-managed Neo4j — use neo4j-gds-skill.
  Does NOT handle Cypher authoring — use neo4j-cypher-skill.
  Does NOT cover Snowflake Graph Analytics — use neo4j-snowflake-graph-analytics-skill.
version: 1.0.0
allowed-tools: Bash WebFetch
---

## When to Use
- Running GDS algorithms on **Aura Business Critical (BC)** or **Virtual Dedicated Cloud (VDC)**
- Processing graph data from non-Neo4j sources (Pandas, Spark, CSV)
- On-demand / pipeline workloads — ephemeral sessions, pay per session-minute
- Full isolation from the live database during analytics

## When NOT to Use
- **Aura Pro with embedded GDS plugin** → `neo4j-gds-skill`
- **Self-managed Neo4j with embedded GDS plugin** → `neo4j-gds-skill`
- **Writing Cypher queries** → `neo4j-cypher-skill`
- **Snowflake Graph Analytics** → `neo4j-snowflake-graph-analytics-skill`

---

## Deployment Decision Table

| Deployment | Skill |
|---|---|
| Aura Free | ❌ AGA not available |
| Aura Pro | `neo4j-gds-skill` (embedded plugin) |
| Aura Business Critical | **this skill** |
| Aura Virtual Dedicated Cloud | **this skill** |
| Non-Neo4j data (Pandas, Spark) | **this skill** (standalone mode) |

---

## Defaults

- `graphdatascience >= 1.15` required; `>= 1.18` for Spark
- Always call `gds.verify_connectivity()` after session creation
- Always estimate memory before creating a session for large graphs
- Always set TTL; default is 1 hour idle, max 7 days
- Close session when done — `gds.delete()` or `sessions.delete(name)` stops billing
- Use `AuraAPICredentials.from_env()` — never hardcode credentials

---

## Installation

```bash
pip install "graphdatascience>=1.15"
```

---

## Key Patterns

### Step 1 — Authenticate

```python
import os
from graphdatascience.session import AuraAPICredentials, GdsSessions

sessions = GdsSessions(api_credentials=AuraAPICredentials.from_env())
# Reads: AURA_CLIENT_ID, AURA_CLIENT_SECRET, AURA_PROJECT_ID (optional)
# Create API credentials in Aura Console → Account → API credentials
```

If member of multiple projects, set `AURA_PROJECT_ID` or pass `project_id=` explicitly.

### Step 2 — Estimate Memory

```python
from graphdatascience.session import AlgorithmCategory, SessionMemory

memory = sessions.estimate(
    node_count=1_000_000,
    relationship_count=5_000_000,
    algorithm_categories=[
        AlgorithmCategory.CENTRALITY,
        AlgorithmCategory.NODE_EMBEDDING,
        AlgorithmCategory.COMMUNITY_DETECTION,
    ],
)
# Returns a SessionMemory tier, e.g. SessionMemory.m_8GB
# Fixed tiers: m_2GB … m_256GB — see references/limitations.md
```

### Step 3 — Create Session

**Mode A — AuraDB connected:**
```python
from graphdatascience.session import DbmsConnectionInfo, SessionMemory, CloudLocation
from datetime import timedelta

db_connection = DbmsConnectionInfo(
    username=os.environ["NEO4J_USERNAME"],
    password=os.environ["NEO4J_PASSWORD"],
    aura_instance_id=os.environ["AURA_INSTANCEID"],  # from Aura Console URL
)

gds = sessions.get_or_create(
    session_name="my-analysis",
    memory=memory,
    db_connection=db_connection,
    ttl=timedelta(hours=2),
)
gds.verify_connectivity()
```

**Mode B — Self-managed Neo4j:**
```python
db_connection = DbmsConnectionInfo(
    uri=os.environ["NEO4J_URI"],          # e.g. "bolt://my-server:7687"
    username=os.environ["NEO4J_USERNAME"],
    password=os.environ["NEO4J_PASSWORD"],
)
gds = sessions.get_or_create(
    session_name="my-analysis-sm",
    memory=SessionMemory.m_8GB,
    db_connection=db_connection,
    ttl=timedelta(hours=2),
    cloud_location=CloudLocation("gcp", "europe-west1"),
)
gds.verify_connectivity()
```

**Mode C — Standalone (no Neo4j DB):**
```python
gds = sessions.get_or_create(
    session_name="my-standalone",
    memory=SessionMemory.m_4GB,
    ttl=timedelta(hours=1),
    cloud_location=CloudLocation("gcp", "europe-west1"),
)
gds.verify_connectivity()
```

`get_or_create()` is idempotent — reconnects to existing session by name.

### Step 4 — Project Graph

**From connected Neo4j (remote projection):**
```python
G, result = gds.graph.project(
    "my-graph",
    """
    CALL () {
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[r:KNOWS]->(p2:Person)
        RETURN p AS source, r AS rel, p2 AS target,
               p {.age, .score} AS sourceNodeProperties,
               p2 {.age, .score} AS targetNodeProperties
    }
    RETURN gds.graph.project.remote(source, target, {
        sourceNodeLabels:     labels(source),
        targetNodeLabels:     labels(target),
        sourceNodeProperties: sourceNodeProperties,
        targetNodeProperties: targetNodeProperties,
        relationshipType:     type(rel)
    })
    """,
)
print(f"Projected {G.node_count()} nodes, {G.relationship_count()} relationships")
```

`CALL () { ... }` is required for multi-pattern MATCH. Use `UNION` inside `CALL` for multiple labels/rel types.

**From Pandas DataFrames (standalone mode):**
```python
import pandas as pd

nodes_df = pd.DataFrame([
    {"nodeId": 0, "labels": "Person", "age": 30},
    {"nodeId": 1, "labels": "Person", "age": 25},
])
rels_df = pd.DataFrame([
    {"sourceNodeId": 0, "targetNodeId": 1, "relationshipType": "KNOWS"},
])

G = gds.graph.construct("my-graph", nodes_df, rels_df)
# Multiple DataFrames: gds.graph.construct("g", [nodes1, nodes2], [rels1, rels2])
```

Required columns — nodes: `nodeId` (int), `labels` (str). Relationships: `sourceNodeId`, `targetNodeId`, `relationshipType`. String node properties not supported — drop before `construct()`.

### Step 5 — Run Algorithms

```python
# Mutate — chain results without writing to DB
gds.pageRank.mutate(G, mutateProperty="pagerank", dampingFactor=0.85)
gds.fastRP.mutate(G,
    mutateProperty="embedding",
    embeddingDimension=128,
    featureProperties=["pagerank"],
    randomSeed=42,
)

# Stream — inspect results as DataFrame
df = gds.pageRank.stream(G)
print(df.sort_values("score", ascending=False).head(10))

# Write — persist to connected Neo4j DB (connected modes only)
gds.louvain.write(G, writeProperty="community")
```

All GDS algorithms work in AGA except topological link prediction. See `neo4j-gds-skill` for the full algorithm reference.

### Step 6 — Async Job Polling

Algorithm calls may return a job handle for long-running computations. Poll until done:

```python
import time

job = gds.pageRank.mutate(G, mutateProperty="pagerank")

# If job object returned (async mode), poll explicitly:
if hasattr(job, "status"):
    while job.status() not in ("RUNNING_DONE", "FAILED", "CANCELLED"):
        time.sleep(5)
        print(f"Job status: {job.status()}")
    if job.status() != "RUNNING_DONE":
        raise RuntimeError(f"Algorithm job failed: {job.status()}")
```

Do NOT assume immediate completion on large graphs. Check `.status()` before reading results.

### Step 7 — Retrieve Results

```python
# Stream node properties — one column per property
result_df = gds.graph.nodeProperties.stream(
    G,
    node_properties=["pagerank", "embedding"],
    separate_property_columns=True,
    db_node_properties=["name"],   # pull from connected DB for context (connected modes only)
)
result_df.head(10)
```

Standalone mode — no `db_node_properties`; join back to source DataFrame:
```python
result_df = gds.graph.nodeProperties.stream(G, ["pagerank"], separate_property_columns=True)
result_df.merge(nodes_df[["nodeId", "name"]], how="left")
```

### Step 8 — Write Back and Clean Up

```python
# Write multiple node properties to connected Neo4j
gds.graph.nodeProperties.write(G, ["pagerank", "embedding"])

# Write relationship properties
gds.graph.relationshipProperties.write(G, G.relationship_types(), ["score"])

# Run Cypher against connected DB from within session
gds.run_cypher("MATCH (n:Person) RETURN count(n)")

# Drop projected graph (frees session memory)
G.drop()

# Delete session — stops billing
sessions.delete(session_name="my-analysis")
# or: gds.delete()
```

Write before deleting — results not written back are lost when session closes.

### Session Management

```python
# List active sessions
from pandas import DataFrame
DataFrame(sessions.list())

# Reconnect to existing session
gds = sessions.get_or_create(session_name="my-analysis", memory=..., db_connection=...)
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `AuthenticationError` / 401 | Wrong `CLIENT_ID`/`CLIENT_SECRET` | Regenerate in Aura Console → Account → API credentials |
| `SessionNotFoundError` | Session expired (TTL exceeded) or name typo | `sessions.list()` to check; recreate session |
| `GraphNotFoundError` | Projection dropped or session reconnected without re-projecting | Re-run `gds.graph.project()` or `gds.graph.construct()` |
| Algorithm job `FAILED` | Memory limit exceeded or unsupported algorithm | Increase `SessionMemory`; check topological link prediction not used |
| `MemoryEstimationExceeded` | Graph larger than estimated | Re-estimate with actual counts; pick next tier up |
| Results empty after session reconnect | Results not written before session was closed | Always write/stream before `gds.delete()` |
| `String node properties not supported` | String column in nodes DataFrame | Drop string columns before `gds.graph.construct()` |
| `AGA not enabled for project` | AGA feature not activated | Enable in Aura Console → project settings |

---

## References

Load on demand:
- [references/workflows.md](references/workflows.md) — full AuraDB and standalone workflow examples, Spark integration
- [references/limitations.md](references/limitations.md) — AGA vs embedded GDS feature table, SessionMemory tiers, cloud locations

## WebFetch

| Need | URL |
|---|---|
| AGA Python client docs | `https://neo4j.com/docs/graph-data-science-client/current/aura-graph-analytics/` |
| AuraDB tutorial notebook | `https://github.com/neo4j/graph-data-science-client/blob/main/examples/graph-analytics-serverless.ipynb` |
| GDS algorithm reference | `https://neo4j.com/docs/graph-data-science/current/algorithms/` |

---

## Checklist
- [ ] Aura API credentials created and set in environment (`AURA_CLIENT_ID`, `AURA_CLIENT_SECRET`)
- [ ] AGA feature enabled for Aura project (Aura Console → project settings)
- [ ] Memory estimated before session creation (`sessions.estimate(...)`)
- [ ] Cloud location chosen near data source
- [ ] `gds.verify_connectivity()` called after session creation
- [ ] TTL set to avoid unexpected costs on idle sessions
- [ ] Async algorithm jobs polled until `RUNNING_DONE` before reading results
- [ ] Results written back (connected modes) or streamed and persisted (standalone) before deletion
- [ ] Session deleted when done (`sessions.delete(...)` or `gds.delete()`)
