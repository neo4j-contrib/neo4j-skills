---
name: neo4j-aura-graph-analytics-skill
description: Serverless Aura Graph Analytics (AGA) GDS Sessions — covers GdsSessions,
  AuraGraphDataScience, AuraAPICredentials, DbmsConnectionInfo, SessionMemory, get_or_create,
  remote graph projection with gds.graph.project.cypher and gds.graph.project.remote,
  gds.graph.project.native, gds.graph.construct, graphdatascience client 2.0 session
  endpoints, async compute and gds.jobs, AuraDB Cypher API memory/sessionId projection,
  algorithms, write-back, and session lifecycle. Use for AuraDB-connected, self-managed
  Neo4j, or standalone DataFrame/Spark session workloads.
  Does NOT cover the embedded GDS plugin on Aura Pro or self-managed Neo4j — use neo4j-gds-skill.
  Does NOT handle Cypher authoring — use neo4j-cypher-skill.
  Does NOT cover Snowflake Graph Analytics — use neo4j-snowflake-graph-analytics-skill.
version: 1.0.10
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
| AuraDB Free | **this skill** — max `m_2GB`, 1 concurrent session, unbilled |
| Aura Pro + Graph Analytics plugin enabled (lightweight exploration, shared resources) | `neo4j-gds-skill` |
| Aura Pro / Pro Trial + session (isolated compute) | **this skill** — up to 128 GB (Pro) / 8 GB (Pro Trial), 100 / 3 concurrent sessions |
| AuraDB + Python client sessions | **this skill** |
| AuraDB + Cypher API | **this skill** for AGA-specific projection/session notes; `neo4j-cypher-skill` for query authoring |
| Self-managed Neo4j + AGA session | **this skill** |
| Self-managed Neo4j + embedded plugin | `neo4j-gds-skill` |
| Non-Neo4j data (Pandas, Spark) | **this skill** (standalone mode) |

---

## Defaults

- `graphdatascience >= 2.0` required
- 2.0 endpoints: no `v2` prefix — `gds.page_rank.*`, `gds.graph.node_properties.*`, `gds.graph.construct(...)`
- Use snake_case parameters end-to-end
- Call `gds.verify_connectivity()` after session creation — verifies session and, if attached, the source DB
- Estimate memory before large sessions
- Set TTL; default 1h idle, max 7d (hard 7-day lifetime cap)
- Close session when done: `gds.delete()` or `sessions.delete(session_name=...)` stops billing
- Use `AuraAPICredentials.from_env()` and `DbmsConnectionInfo.from_env()` — never hardcode credentials

---

## Installation

```bash
pip install "graphdatascience>=2.0"     # 2.0 is the current stable release
```

2.0 requires: Python >= 3.10, `neo4j` driver 5.26–7.0, pandas 2–3, pyarrow 21–25, numpy <3.

### Client 1.x (legacy)

2.0 renamed/reorganized the client. Pinned to 1.22 (`graphdatascience<2`)? Map:

| 1.x | 2.0 |
|---|---|
| `gds.v2.<endpoint>` | `gds.<endpoint>` — `v2` prefix gone; untyped 1.x endpoints removed |
| `gds.graph.project(graph_name, query)` (remote) | `gds.graph.project.cypher(graph_name, query)` |
| `gds.graph.project_native(...)` | `gds.graph.project.native(...)` |
| `GraphV2` / `ModelV2` | `Graph` / `Model` — `from graphdatascience import Graph` |
| `Graph.drop(failIfMissing=)` / `Model.drop(failIfMissing=)` | `fail_if_missing=` |
| `gds.v2.verify_session_connectivity()` / `gds.v2.verify_db_connectivity()` | `gds.verify_connectivity()` — existed in 1.x too; `v2` namespace gone |
| `run_cypher(..., retryable=)` | removed — always retries |
| `gds.graph.project.cypher(database=...)` | removed — `gds.set_database(...)` before projecting |
| `gds.graph.node_labels.mutate(write_concurrency=, job_id=)` | parameters removed |
| `ArrowEndpointVersion.from_arrow_info` | `check_version_compatibility` |

Migration guide: [Neo4j GDS Python client 2.0 migration](https://neo4j.com/docs/graph-data-science-client/current/migration-from-1x/)

2.0 additions: `GdsSessions.estimate(algorithms=[...])` per-algorithm memory; `GdsSessions.get_or_create(show_progress=...)`; keyword-only `GdsSessions.delete(session_name=|session_id=)` returns `False` when nothing deleted; `overwrite=True` on `gds.graph.project` / `generate` / `construct` / `filter` / `sample` drops a same-named graph first; `gds.graph.drop(...)` accepts multiple graphs → `list[GraphInfo]`;

---

## Key Patterns

### Step 1 — Authenticate

```python
from graphdatascience.session import AuraAPICredentials, GdsSessions

sessions = GdsSessions(api_credentials=AuraAPICredentials.from_env())
# Reads: AURA_CLIENT_ID, AURA_CLIENT_SECRET, AURA_PROJECT_ID (optional)
# Create API credentials in Aura Console → Account → API credentials
```

If member of multiple projects: set `AURA_PROJECT_ID` or pass `project_id=`.

### Step 2 — Estimate Memory

```python
from graphdatascience.session import AlgorithmCategory, SessionMemory

# Per-algorithm + config — preferred
memory = sessions.estimate(
    node_count=1_000_000,
    relationship_count=5_000_000,
    algorithms=["wcc", "louvain", "fast_rp"],
)
# or with config:
memory = sessions.estimate(
    node_count=1_000_000,
    relationship_count=5_000_000,
    algorithms={"fast_rp": {"embedding_dimension": 128}},
)
# Coarse category estimate — 1.x style, still available
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
# Fixed tiers: m_2GB … m_512GB — see references/limitations.md
```

### Step 3 — Create Session

**Mode A — AuraDB connected:**
```python
from graphdatascience.session import DbmsConnectionInfo, SessionMemory, CloudLocation
from datetime import timedelta

# Reads: AURA_INSTANCEID (takes precedence) or NEO4J_URI, plus NEO4J_USERNAME,
# NEO4J_PASSWORD, NEO4J_DATABASE
db_connection = DbmsConnectionInfo.from_env()
# Explicit: DbmsConnectionInfo(aura_instance_id=..., username=..., password=...)

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
# Same from_env() — set NEO4J_URI (e.g. "bolt://my-server:7687"), no AURA_INSTANCEID
gds = sessions.get_or_create(
    session_name="my-analysis-sm",
    memory=SessionMemory.m_8GB,
    db_connection=DbmsConnectionInfo.from_env(),
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

G, result = gds.graph.project.cypher(
    graph_name="my-graph",
    query=query,
    undirected_relationship_types=["KNOWS"],
)
print(f"Projected {G.node_count()} nodes, {G.relationship_count()} relationships")
```

`CALL () { ... }` required for multi-pattern MATCH. Use `UNION` inside `CALL` for multiple labels/rel types.
Remote query must use `gds.graph.project.remote(...)`; graph name goes to `gds.graph.project.cypher(...)`, not the query. Query containing `gds.graph.project` without `.remote` is auto-rewritten with a warning. `undirectedRelationshipTypes` / `inverseIndexedRelationshipTypes` inside the query → `ValueError` — pass as method args.
Only numeric node properties can be projected into a session; fetch string properties via `db_node_properties` when streaming.
Standalone sessions cannot remote-project — `ValueError: Remote projection is only supported for attached Sessions.`
1.x fallback: `gds.graph.project(graph_name=..., query=...)`.

**Native remote projection (no Cypher query)** — `gds.graph.project.native(...)` projects from the attached DB by label/type filter:
```python
G, result = gds.graph.project.native(
    "my-graph",
    ["Person"],                              # node_label_filter
    ["KNOWS"],                               # relationship_type_filter
    node_properties=["age", "score"],
    undirected_relationship_types=["KNOWS"],
)
```
Attached sessions only. Use `project.native` for label/type-filtered projections; use `project.cypher` for transformations, computed properties, or `UNION` heterogeneous patterns.

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

G = gds.graph.construct("my-graph", [nodes_df], [rels_df])
```

Required columns — nodes: `nodeId` (int), `labels` (str). Relationships: `sourceNodeId`, `targetNodeId`, `relationshipType`. Drop string node properties before `construct()` — sessions accept numeric properties only.

### Step 5 — Run Algorithms

```python
# Mutate — chain results without writing to DB
gds.page_rank.mutate(G, mutate_property="pagerank", damping_factor=0.85)
gds.fast_rp.mutate(G,
    mutate_property="embedding",
    embedding_dimension=128,
    feature_properties=["pagerank"],
    random_seed=42,
)

# Stream — inspect results as DataFrame
df = gds.page_rank.stream(G)
print(df.sort_values("score", ascending=False).head(10))

# Write — persist to connected Neo4j DB (connected modes only)
gds.louvain.write(G, write_property="community")
```

ML pipelines: `gds.pipeline.node_classification` / `link_prediction` / `node_regression` — the only API in 2.0.
1.x fallback: `gds.v2.page_rank.mutate(...)`; untyped 1.x endpoints like `gds.pageRank.mutate(...)` are gone in 2.0.
Plugin algorithm reference → `neo4j-gds-skill`; AGA limitations differ.

### Step 6 — Async Job Polling

Long-running algorithms — non-blocking `compute()` returns a `JobHandle`:

```python
import time

job = gds.page_rank.compute(G, mutate_property="pagerank")
while not job.done():
    time.sleep(5)
    print(f"Job status: {job.status()}")
if job.status() != "RUNNING_DONE":
    raise RuntimeError(f"Algorithm job failed: {job.status()}")
result = job.result(wait=False)   # raises JobNotFinishedError if not done
```

Handle methods: `.job_id()`, `.status()`, `.done()`, `.wait(*, termination_flag=None)`, `.cancel()`, `.summary(...)`, `.result(wait=False)`.
Async projections return `ProjectionJobHandle` (`gds.graph.project.native_async(...)`, `cypher_async(...)`); write-backs yield `WriteJobHandle`. List/recover jobs:

```python
gds.jobs.list()                     # JobInfo per job: job_id, name
handle = gds.jobs.get(G, job_id)    # concrete handle type for the job
```

### Step 7 — Retrieve Results

```python
# Stream node properties
result_df = gds.graph.node_properties.stream(
    G,
    node_properties=["pagerank", "embedding"],
    db_node_properties=["name"],   # connected modes only — fetches string props from DB
)
result_df.head(10)
```

Standalone mode: no `db_node_properties`; join source DataFrame:
```python
result_df = gds.graph.node_properties.stream(G, ["pagerank"])
result_df.merge(nodes_df[["nodeId", "name"]], how="left")
```

### Step 8 — Write Back and Clean Up

```python
# Write node properties to connected Neo4j
gds.graph.node_properties.write(G, ["pagerank", "embedding"])

# Write relationship properties
gds.graph.relationships.write(G, "SIMILAR", ["score"])

# Query connected DB from session
gds.run_cypher("MATCH (n:Person) RETURN count(n)")

# Drop projected graph
gds.graph.drop(G)

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
| `RuntimeError` getting an already-expired session | TTL exceeded | `sessions.list()` to check; recreate session |
| `SessionNotFoundError` | Session expired (TTL exceeded) or name typo | `sessions.list()` to check; recreate session |
| `GraphNotFoundError` | Projection dropped or session reconnected without re-projecting | Re-run `gds.graph.project.cypher()` or `gds.graph.construct()` |
| `ValueError: Remote projection is only supported for attached Sessions.` | Standalone session cannot remote-project | Use `gds.graph.construct(...)` from DataFrames instead |
| `NotAvailableInStandaloneSessions` | Feature needs an attached DB (e.g. `gds.topological_link_prediction`, remote projection) | Attach a DB or pick another algorithm |
| Algorithm job `FAILED` | Memory limit exceeded or unsupported algorithm | Increase `SessionMemory`; check `NotAvailableOutsideAura` for attached-only features |
| `MemoryEstimationExceeded` | Graph larger than estimated | Re-estimate with actual counts; pick next tier up |
| Results empty after session reconnect | Results not written before session was closed | Always write/stream before `gds.delete()` |
| `String node properties not supported` | String column in nodes DataFrame | Drop string columns before `gds.graph.construct()`; fetch strings later via `db_node_properties` |
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
| Client migration guide 1.x → 2.0 | `https://neo4j.com/docs/graph-data-science-client/current/migration-from-1x/` |
| AuraDB tutorial notebook | `https://github.com/neo4j/graph-data-science-client/blob/main/examples/graph-analytics-serverless.ipynb` |
| GDS algorithm reference | `https://neo4j.com/docs/graph-data-science/current/algorithms/` |

---

## Checklist
- [ ] Aura API credentials created and set in environment (`AURA_CLIENT_ID`, `AURA_CLIENT_SECRET`)
- [ ] Connected sessions: `AURA_INSTANCEID` or `NEO4J_URI`, plus `NEO4J_USERNAME`, `NEO4J_PASSWORD` set for `DbmsConnectionInfo.from_env()`
- [ ] AGA feature enabled for Aura project (Aura Console → project settings)
- [ ] Memory estimated before session creation (`sessions.estimate(..., algorithms=[...])`)
- [ ] Cloud location chosen near data source
- [ ] `gds.verify_connectivity()` called after session creation
- [ ] Remote projection uses `gds.graph.project.cypher(graph_name, query)` with `gds.graph.project.remote(...)` inside query
- [ ] Remote projection graph name passed to the endpoint, not the remote function
- [ ] `undirected_relationship_types` passed as method args, never inside the query
- [ ] AuraDB Cypher API projection uses fifth config map for `memory` or `sessionId`
- [ ] Explicit Cypher API sessions use `gds.session.getOrCreate(...)`; implicit sessions dropped with projected graph
- [ ] TTL set to avoid unexpected costs on idle sessions
- [ ] Async algorithm jobs polled until `RUNNING_DONE` before reading results
- [ ] Results written back (connected modes) or streamed and persisted (standalone) before deletion
- [ ] Session deleted when done (`sessions.delete(session_name=...)` or `gds.delete()`)
