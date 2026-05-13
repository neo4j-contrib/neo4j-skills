---
name: neo4j-aura-graph-analytics-skill
description: Serverless Aura Graph Analytics (AGA) GDS Sessions — covers GdsSessions,
  AuraGraphDataScience, AuraAPICredentials, DbmsConnectionInfo, SessionMemory, get_or_create,
  remote graph projection with gds.v2.graph.project and gds.graph.project.remote, gds.v2
  session endpoints, gds.v2.graph.construct, AuraDB Cypher API memory/sessionId projection, algorithms,
  write-back, and session lifecycle. Use for AuraDB-connected, self-managed Neo4j, or standalone
  DataFrame/Spark session workloads.
  Does NOT cover the embedded GDS plugin on Aura Pro or self-managed Neo4j — use neo4j-gds-skill.
  Does NOT handle Cypher authoring — use neo4j-cypher-skill.
  Does NOT cover Snowflake Graph Analytics — use neo4j-snowflake-graph-analytics-skill.
version: 1.0.0
allowed-tools: Bash WebFetch
---

## When to Use
- Running GDS algorithms in Aura Graph Analytics GDS Sessions
- Creating `GdsSessions` or using `AuraGraphDataScience`
- Remote projecting connected Neo4j data with `gds.graph.project.remote(...)`
- Using AuraDB Cypher API projection with `{ memory: ... }` or `{ sessionId: ... }`
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

| Deployment | Use |
|---|---|
| Aura Free | ❌ AGA not available |
| Aura Pro | `neo4j-gds-skill` (embedded plugin) |
| AuraDB + Python client sessions | **this skill** |
| AuraDB + Cypher API | **this skill** for AGA-specific projection/session notes; `neo4j-cypher-skill` for query authoring |
| Self-managed Neo4j + AGA session | **this skill** |
| Self-managed Neo4j + embedded plugin | `neo4j-gds-skill` |
| Non-Neo4j data (Pandas, Spark) | **this skill** (standalone mode) |

---

## Defaults

- `graphdatascience >= 1.15` required; `>= 1.18` for Spark
- Prefer v2 endpoints: `gds.v2.graph.project(...)`, `gds.v2.page_rank.*`, `gds.v2.graph.node_properties.*`
- Use snake_case parameters end-to-end; never mix v2 with camelCase params
- Use v1 if v2 endpoint missing/incompatible; label fallback
- Call `gds.v2.verify_session_connectivity()` after session creation
- Connected sessions: call `gds.v2.verify_db_connectivity()` when source DB access required
- Estimate memory before large sessions
- Set TTL; default 1h idle, max 7d
- Close session when done: `gds.delete()` or `sessions.delete(name)` stops billing
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

If member of multiple projects: set `AURA_PROJECT_ID` or pass `project_id=`.

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
# Returns SessionMemory tier, e.g. SessionMemory.m_8GB
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
gds.v2.verify_session_connectivity()
gds.v2.verify_db_connectivity()
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
gds.v2.verify_session_connectivity()
gds.v2.verify_db_connectivity()
```

**Mode C — Standalone (no Neo4j DB):**
```python
gds = sessions.get_or_create(
    session_name="my-standalone",
    memory=SessionMemory.m_4GB,
    ttl=timedelta(hours=1),
    cloud_location=CloudLocation("gcp", "europe-west1"),
)
gds.v2.verify_session_connectivity()
```

`get_or_create()` is idempotent; reconnects to existing session by name.

### Step 4 — Project Graph

**From connected Neo4j (remote projection):**
```python
query = """
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
"""

G, result = gds.v2.graph.project(
    graph_name="my-graph",
    query=query,
    undirected_relationship_types=["KNOWS"],
)
print(f"Projected {G.node_count()} nodes, {G.relationship_count()} relationships")
```

`CALL () { ... }` required for multi-pattern MATCH. Use `UNION` inside `CALL` for multiple labels/rel types.
Remote query uses `gds.graph.project.remote(...)`; pass graph name to `gds.v2.graph.project(...)`, not query.
V1 fallback: `gds.graph.project(graph_name="my-graph", query=query, undirected_relationship_types=["KNOWS"])`.

**AuraDB Cypher API projection:**
```cypher
CYPHER runtime=parallel
MATCH (source)
OPTIONAL MATCH (source)-->(target)
RETURN gds.graph.project(
  'my-graph',
  source,
  target,
  {},
  { memory: '2GB' }
)
```

Existing explicit session:
```cypher
CYPHER runtime=parallel
MATCH (source)
OPTIONAL MATCH (source)-->(target)
RETURN gds.graph.project(
  'my-graph',
  source,
  target,
  {},
  { sessionId: '00000000-11111111' }
)
```

Cypher API uses `gds.graph.project(...)`, not `gds.graph.project.remote(...)`. Put `memory`, `ttl`, `sessionId`, `batchSize` in fifth config argument.

Session management via Cypher API:
```cypher
CALL gds.session.getOrCreate('test-session', '2GB', duration({minutes: 30}))
YIELD id, name, status
RETURN id, name, status

CALL gds.session.list()
YIELD id, name, status, memory
RETURN id, name, status, memory
```

Implicit Cypher API sessions delete when all projected graphs in session are dropped.

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

G = gds.v2.graph.construct("my-graph", nodes_df, rels_df)
# Multiple DataFrames: gds.v2.graph.construct("g", [nodes1, nodes2], [rels1, rels2])
```

Required columns — nodes: `nodeId` (int), `labels` (str). Relationships: `sourceNodeId`, `targetNodeId`, `relationshipType`. Drop string node properties before `construct()`.

### Step 5 — Run Algorithms

```python
# Mutate — chain results without writing to DB
gds.v2.page_rank.mutate(G, mutate_property="pagerank", damping_factor=0.85)
gds.v2.fast_rp.mutate(G,
    mutate_property="embedding",
    embedding_dimension=128,
    feature_properties=["pagerank"],
    random_seed=42,
)

# Stream — inspect results as DataFrame
df = gds.v2.page_rank.stream(G)
print(df.sort_values("score", ascending=False).head(10))

# Write — persist to connected Neo4j DB (connected modes only)
gds.v2.louvain.write(G, write_property="community")
```

V1 fallback: `gds.pageRank.mutate(..., mutateProperty="pagerank")`. Plugin algorithm reference → `neo4j-gds-skill`; AGA limitations differ.

### Step 6 — Async Job Polling

Long-running algorithms may return job handle. Poll until done:

```python
import time

job = gds.v2.page_rank.mutate(G, mutate_property="pagerank")

# If job object returned (async mode), poll explicitly:
if hasattr(job, "status"):
    while job.status() not in ("RUNNING_DONE", "FAILED", "CANCELLED"):
        time.sleep(5)
        print(f"Job status: {job.status()}")
    if job.status() != "RUNNING_DONE":
        raise RuntimeError(f"Algorithm job failed: {job.status()}")
```

Large graphs: check `.status()` before reading results.

### Step 7 — Retrieve Results

```python
# Stream node properties
result_df = gds.v2.graph.node_properties.stream(
    G,
    node_properties=["pagerank", "embedding"],
    db_node_properties=["name"],   # connected modes only
)
result_df.head(10)
```

Standalone mode: no `db_node_properties`; join source DataFrame:
```python
result_df = gds.v2.graph.node_properties.stream(G, ["pagerank"])
result_df.merge(nodes_df[["nodeId", "name"]], how="left")
```

### Step 8 — Write Back and Clean Up

```python
# Write node properties to connected Neo4j
gds.v2.graph.node_properties.write(G, ["pagerank", "embedding"])

# Write relationship properties
gds.v2.graph.relationships.write(G, "SIMILAR", ["score"])

# Query connected DB from session
gds.run_cypher("MATCH (n:Person) RETURN count(n)")

# Drop projected graph
gds.v2.graph.drop(G)

# Delete session
sessions.delete(session_name="my-analysis")
# or: gds.delete()
```

Write before delete; unwritten results lost when session closes.

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
| `GraphNotFoundError` | Projection dropped or session reconnected without re-projecting | Re-run `gds.v2.graph.project()` or `gds.v2.graph.construct()` |
| Algorithm job `FAILED` | Memory limit exceeded or unsupported algorithm | Increase `SessionMemory`; check topological link prediction not used |
| `MemoryEstimationExceeded` | Graph larger than estimated | Re-estimate with actual counts; pick next tier up |
| Results empty after session reconnect | Results not written before session was closed | Always write/stream before `gds.delete()` |
| `String node properties not supported` | String column in nodes DataFrame | Drop string columns before `gds.v2.graph.construct()` |
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
| AGA Cypher API docs | `https://neo4j.com/docs/graph-data-science/current/aura-graph-analytics/cypher/` |
| Python client v2 docs | `https://neo4j.com/docs/graph-data-science-client/current/v2_endpoints/` |
| AuraDB tutorial notebook | `https://github.com/neo4j/graph-data-science-client/blob/main/examples/graph-analytics-serverless.ipynb` |
| GDS algorithm reference | `https://neo4j.com/docs/graph-data-science/current/algorithms/` |

---

## Checklist
- [ ] Aura API credentials created and set in environment (`AURA_CLIENT_ID`, `AURA_CLIENT_SECRET`)
- [ ] AGA feature enabled for Aura project (Aura Console → project settings)
- [ ] Memory estimated before session creation (`sessions.estimate(...)`)
- [ ] Cloud location chosen near data source
- [ ] `gds.v2.verify_session_connectivity()` called after session creation
- [ ] Connected sessions call `gds.v2.verify_db_connectivity()` when source DB access required
- [ ] Remote projection uses `gds.v2.graph.project(..., query)` with `gds.graph.project.remote(...)` inside query
- [ ] Remote projection graph name passed to endpoint, not remote function
- [ ] AuraDB Cypher API projection uses fifth config map for `memory` or `sessionId`
- [ ] Explicit Cypher API sessions use `gds.session.getOrCreate(...)`; implicit sessions dropped with projected graph
- [ ] TTL set to avoid unexpected costs on idle sessions
- [ ] Async algorithm jobs polled until `RUNNING_DONE` before reading results
- [ ] Results written back (connected modes) or streamed and persisted (standalone) before deletion
- [ ] Session deleted when done (`sessions.delete(...)` or `gds.delete()`)
