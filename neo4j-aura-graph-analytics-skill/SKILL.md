---
name: neo4j-aura-graph-analytics-skill
description: Serverless Aura Graph Analytics (AGA) GDS Sessions — covers GdsSessions,
  AuraGraphDataScience, AuraAPICredentials, DbmsConnectionInfo, SessionMemory, get_or_create,
  remote graph projection with gds.graph.project.cypher, gds.graph.project.native and
  gds.graph.project.remote, gds.graph.construct, AuraDB Cypher API memory/sessionId projection, algorithms,
  write-back, and session lifecycle. Use for AuraDB-connected, self-managed Neo4j, or standalone
  DataFrame/Spark session workloads.
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

- `graphdatascience 2.0` required for the endpoints below; `>= 1.15` (`gds.v2.*` prefix) for legacy code
- Endpoints: `gds.graph.project.cypher(...)`, `gds.graph.project.native(...)`, `gds.page_rank.*`, `gds.graph.node_properties.*`
- snake_case parameters end-to-end; typed result objects, `stream` returns a DataFrame
- Call `gds.verify_connectivity()` after session creation — checks session health and, for connected sessions, the DB
- Estimate memory before large sessions
- Set TTL; default 1h idle, max 7d
- Close session when done: `gds.delete()` or `sessions.delete(name)` stops billing
- Use `AuraAPICredentials.from_env()` — never hardcode credentials

---

## Installation

```bash
pip install graphdatascience     # 2.0, GA 2026-09-18; sessions always run the latest GDS server
```

2.0 requirements: Python >= 3.10 and < 3.15, `neo4j` driver >= 5.26 and < 7.0, pandas >= 2.0 and < 4.0, pyarrow >= 21 and < 26, numpy < 3.

### 1.x → 2.0 endpoint map

| 1.x | 2.0 |
|---|---|
| `gds.v2.<endpoint>`, camelCase untyped endpoints | `gds.<endpoint>` — prefix gone, 1.x endpoints removed |
| `gds.graph.project(graph_name, query)` (AGA) | `gds.graph.project.cypher(graph_name, query)` |
| `gds.graph.project_native(...)` (AGA) | `gds.graph.project.native(...)` |
| `gds.v2.verify_session_connectivity()` + `verify_db_connectivity()` | `gds.verify_connectivity()` |
| `gds.v2.pipeline.node_classification` | `gds.pipeline.node_classification` |
| `GraphV2` / `ModelV2` | `Graph` / `Model` — `from graphdatascience import Graph` |
| `Graph.drop(failIfMissing=)` / `Model.drop(failIfMissing=)` | `fail_if_missing=` |
| `run_cypher(..., retryable=)` | removed — always retries |
| `ArrowEndpointVersion.from_arrow_info` | `check_version_compatibility` |
| `ServerVersion`, `SemanticVersion` from top level | `graphdatascience.versions` |
| `gds.graph.node_labels.mutate(write_concurrency=, job_id=)` | parameters removed |
| `gds.graph.project.cypher(database=...)` | parameter removed — `gds.set_database("mydb")` before projecting |
| `gds.graph.drop(G)` → Series | accepts a list; returns `list[GraphInfo]` |

2.0 additions: `sessions.estimate(algorithms=[...])` for per-algorithm memory; `sessions.get_or_create(show_progress=...)`; `gds.pipeline.get`; `overwrite=True` on `gds.graph.project.*` / `generate` / `construct` / `filter` / `sample` drops a same-named graph first; `sessions.delete(session_id=...)` returns `False` when nothing was deleted; `gds.hits`, `gds.topological_link_prediction.*` and `gds.fast_path` now available in sessions; `aura_ds=` optional — client derives Aura hosting.

2.0 error surface: Arrow endpoint version is checked at client creation — unsupported version raises an error asking to upgrade `graphdatascience`. Getting an already-expired session raises `RuntimeError`; sessions expiring within the hour warn. Session out-of-memory and other session failures report the session status, not a bare connection error; `close()` also closes the Arrow Flight client.

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
# Fixed tiers: m_2GB … m_512GB — see references/limitations.md

# Finer estimate per algorithm + config [client 2.0]; exclusive with algorithm_categories
memory = sessions.estimate(
    node_count=1_000_000,
    relationship_count=5_000_000,
    algorithms={"wcc": {}, "fast_rp": {"embedding_dimension": 1024}},
)
```

Category estimates size for the heaviest algorithm in the category — pass `algorithms=` when the algorithm set is known.

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
Remote query uses `gds.graph.project.remote(...)`; pass graph name to `gds.graph.project.cypher(...)`, not query. Extra Cypher params go in `query_parameters={...}`.
Only numeric node properties project into a session — fetch strings such as `name` with `db_node_properties` when streaming.

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
Attached and self-managed sessions only. Wildcards allowed: `node_label_filter=["*"]`. Use `project.native` for label/type-filtered projections; use `project.cypher` for transformations, computed properties, or `UNION` heterogeneous patterns.

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

G = gds.graph.construct("my-graph", nodes_df, rels_df)
# Multiple DataFrames: gds.graph.construct("g", [nodes1, nodes2], [rels1, rels2])
```

Required columns — nodes: `nodeId` (int), `labels` (str). Relationships: `sourceNodeId`, `targetNodeId`, `relationshipType`. Drop string node properties before `construct()`.

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

Plugin algorithm reference → `neo4j-gds-skill`; AGA limitations differ.

ML pipelines in sessions: `gds.pipeline.node_classification`, `gds.pipeline.link_prediction`, `gds.pipeline.node_regression`; retrieve with `gds.pipeline.get(name)`.
Endpoints added to sessions in client 2.0: `gds.hits.*`, `gds.topological_link_prediction.*`. Session-only: `gds.fast_path.*`, `gds.embedding.*` (preview).

### Step 6 — Async Jobs

`stream` / `mutate` / `write` block until finished. Non-blocking variants return handles: `gds.graph.project.native_async(...)` and `gds.graph.project.cypher_async(...)` → `ProjectionJobHandle`; `gds.<algo>.compute(G, ...)` → `JobHandle`; `JobHandle.write(...)` → `WriteJobHandle`.
Handle methods: `.job_id()`, `.status()`, `.done()`, `.wait()`, `.cancel()`, `.result(wait=False)` — `.result()` raises `JobNotFinishedError` when not done.

```python
projection_handle = gds.graph.project.native_async("people", ["*"], ["*"])
projection_handle.wait()
G, _ = projection_handle.result()

compute_handle = gds.page_rank.compute(G, damping_factor=0.85)
scores = compute_handle.stream()                      # blocks until done, returns DataFrame
write_handle = compute_handle.write(write_properties="pagerank")
write_result = write_handle.result()                  # WriteBackResult

gds.jobs.list()                                       # JobInfo per job: job_id, name
handle = gds.jobs.get(G, write_handle.job_id())       # recover handle after client restart
```

### Step 7 — Retrieve Results

```python
# Stream node properties
result_df = gds.graph.node_properties.stream(
    G,
    node_properties=["pagerank", "embedding"],
    db_node_properties=["name"],   # connected modes only
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
| `SessionNotFoundError` | Session expired (TTL exceeded) or name typo | `sessions.list()` to check; recreate session |
| `GraphNotFoundError` | Projection dropped or session reconnected without re-projecting | Re-run `gds.graph.project.cypher()` or `gds.graph.construct()` |
| Algorithm job `FAILED` | Memory limit exceeded or unsupported algorithm | Increase `SessionMemory`; session failures report the session status alongside the error |
| `AttributeError: 'AuraGraphDataScience' object has no attribute 'v2'` | Client 2.0 dropped the `gds.v2` prefix | Call endpoints directly: `gds.page_rank.stream(G)` |
| `RuntimeError` on `get_or_create` of an expired session | Session past TTL (max lifetime 7 days regardless of activity) | Create a session under a new name; re-project |
| `Update the graphdatascience package` raised at client creation | Arrow endpoint version unsupported by installed client | `pip install -U graphdatascience` |
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
| AGA Cypher API docs | `https://neo4j.com/docs/graph-data-science/current/aura-graph-analytics/cypher/` |
| Client 1.x → 2.0 migration | `https://neo4j.com/docs/graph-data-science-client/current/migration-from-1x/` |
| Async execution handles | `https://neo4j.com/docs/graph-data-science-client/current/async-execution/` |
| AuraDB tutorial notebook | `https://github.com/neo4j/graph-data-science-client/blob/main/examples/graph-analytics-serverless.ipynb` |
| GDS algorithm reference | `https://neo4j.com/docs/graph-data-science/current/algorithms/` |

---

## Checklist
- [ ] Aura API credentials created and set in environment (`AURA_CLIENT_ID`, `AURA_CLIENT_SECRET`)
- [ ] AGA feature enabled for Aura project (Aura Console → project settings)
- [ ] Memory estimated before session creation (`sessions.estimate(...)`)
- [ ] Cloud location chosen near data source
- [ ] `gds.verify_connectivity()` called after session creation
- [ ] Remote projection uses `gds.graph.project.cypher(graph_name, query)` with `gds.graph.project.remote(...)` inside query, or `gds.graph.project.native(...)` for label/type filters
- [ ] Remote projection graph name passed to endpoint, not remote function
- [ ] AuraDB Cypher API projection uses fifth config map for `memory` or `sessionId`
- [ ] Explicit Cypher API sessions use `gds.session.getOrCreate(...)`; implicit sessions dropped with projected graph
- [ ] TTL set to avoid unexpected costs on idle sessions
- [ ] Async algorithm jobs polled until `RUNNING_DONE` before reading results
- [ ] Results written back (connected modes) or streamed and persisted (standalone) before deletion
- [ ] Session deleted when done (`sessions.delete(...)` or `gds.delete()`)
