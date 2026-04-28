---
name: neo4j-aura-graph-analytics-skill
description: Comprehensive guide to Aura Graph Analytics (AGA) — Neo4j's serverless,
  on-demand GDS compute environment. Covers session lifecycle (create, list, delete),
  memory sizing and estimation, all three data source modes (AuraDB-connected,
  self-managed Neo4j, standalone from Pandas/Spark), remote graph projection,
  algorithm execution, streaming and writing results back, and key differences
  from the embedded GDS plugin. Use when running graph algorithms without an
  embedded GDS plugin, when working on AuraDB Business Critical or VDC tiers,
  or when processing graph data from non-Neo4j sources. Also triggers on
  GdsSessions, AuraAPICredentials, SessionMemory, DbmsConnectionInfo,
  get_or_create, gds.graph.project.remote, or any serverless GDS session work.
  Does NOT cover the embedded GDS plugin on Aura Pro or self-managed Neo4j —
  use neo4j-gds-skill. Does NOT handle Cypher authoring — use neo4j-cypher-skill.
version: 1.0.0
allowed-tools: Bash, WebFetch
---

# Aura Graph Analytics (AGA)

**What it is**: Serverless, on-demand GDS compute sessions — isolated ephemeral instances
that connect to your data source, run graph algorithms, and write results back.  
**Python package**: `graphdatascience` (same package as GDS, version ≥ 1.15)  
**Docs**: https://neo4j.com/docs/graph-data-science-client/current/aura-graph-analytics/  
**Notebooks**: https://github.com/neo4j/graph-data-science-client/tree/main/examples

---

## When to Use

- Running GDS algorithms on **Aura Business Critical (BC)** or **Virtual Dedicated Cloud (VDC)** — the embedded GDS plugin is not available on these tiers
- Processing graph data from **non-Neo4j sources** (Pandas DataFrames, Spark, any tabular source)
- Needing **full isolation** from the database during analytics (no performance impact on the live DB)
- **On-demand / pipeline workloads** — pay per session-minute, no persistent plugin overhead
- Connecting a **self-managed Neo4j** instance to cloud-managed GDS compute

## When NOT to Use

- **Aura Pro with GDS plugin** — use `neo4j-gds-skill` instead (simpler, no session management)
- **Embedded GDS on self-managed Neo4j** — use `neo4j-gds-skill`
- **Writing or optimizing Cypher queries** → use `neo4j-cypher-skill`
- **Snowflake Graph Analytics** → use `neo4j-snowflake-graph-analytics-skill`

---

## Availability

| Deployment | AGA Available |
|---|---|
| Aura Free | ❌ No |
| Aura Pro | ❌ No (use embedded GDS plugin instead) |
| Aura Business Critical (BC) | ✅ Yes |
| Aura Virtual Dedicated Cloud (VDC) | ✅ Yes |
| Non-Neo4j data sources (standalone) | ✅ Yes — no AuraDB needed |

> AGA must be **enabled for your Aura project** — check the Aura Console under your project settings.

---

## Key Concepts

| Concept | Description |
|---|---|
| **GDS Session** | Ephemeral compute instance; spun up on demand, billed per minute |
| **Session name** | Stable identifier — `get_or_create()` reconnects to an existing session by name |
| **TTL** | Inactivity timeout (default 1 hour, max 7 days). Session auto-deletes when idle. |
| **Memory** | Fixed at creation — estimate first or pick a `SessionMemory` tier |
| **Cloud location** | Must match or be near your data source for low latency |
| **Remote projection** | Loads data from a connected Neo4j DB into the session's in-memory graph |
| **Graph construct** | Loads data from Pandas DataFrames (standalone mode — no Neo4j DB) |

---

## Installation

```bash
pip install "graphdatascience>=1.15"        # core
pip install "graphdatascience>=1.15" "neo4j_viz[gds]"   # + visualization
pip install "graphdatascience>=1.18" pyspark  # + Spark support
```

---

## 1. Authentication — Aura API Credentials

All AGA work starts with `GdsSessions`, which authenticates against the Aura API (not the database).

```python
import os
from graphdatascience.session import AuraAPICredentials, GdsSessions

# Option A: explicit
api_credentials = AuraAPICredentials(
    client_id=os.environ["CLIENT_ID"],
    client_secret=os.environ["CLIENT_SECRET"],
    project_id=os.environ.get("PROJECT_ID", None),  # required if member of multiple projects
)

# Option B: load from environment variables automatically
api_credentials = AuraAPICredentials.from_env()

sessions = GdsSessions(api_credentials=api_credentials)
```

Create Aura API credentials in the [Aura Console](https://console.neo4j.io) under **Account → API credentials**.

---

## 2. Memory Sizing

Always estimate before creating a session to avoid over- or under-provisioning:

```python
from graphdatascience.session import AlgorithmCategory, SessionMemory

# Estimate based on graph size and algorithm categories
memory = sessions.estimate(
    node_count=1_000_000,
    relationship_count=5_000_000,
    algorithm_categories=[
        AlgorithmCategory.CENTRALITY,
        AlgorithmCategory.NODE_EMBEDDING,
        AlgorithmCategory.COMMUNITY_DETECTION,
    ],
)
print(f"Recommended: {memory}")  # e.g. "SessionMemory.m_8GB"

# Or specify explicitly:
memory = SessionMemory.m_2GB   # also: m_4GB, m_8GB, m_16GB, m_24GB, m_32GB, m_48GB, m_64GB, m_128GB, m_192GB, m_256GB
```

`AlgorithmCategory` values: `CENTRALITY`, `COMMUNITY_DETECTION`, `SIMILARITY`, `PATH_FINDING`, `NODE_EMBEDDING`.

---

## 3. Cloud Location

```python
from graphdatascience.session import CloudLocation

cloud_location = CloudLocation("gcp", "europe-west1")

# List available locations:
print(sessions.available_cloud_locations())
```

Choose a location close to your Neo4j database to minimize projection latency.

---

## 4. Session Modes

### Mode A — Connected to AuraDB

```python
from datetime import timedelta
from graphdatascience.session import DbmsConnectionInfo, SessionMemory

db_connection = DbmsConnectionInfo(
    username=os.environ["NEO4J_USERNAME"],
    password=os.environ["NEO4J_PASSWORD"],
    aura_instance_id=os.environ["AURA_INSTANCEID"],  # found in Aura Console URL
)

gds = sessions.get_or_create(
    session_name="my-analysis",
    memory=SessionMemory.m_8GB,
    db_connection=db_connection,
    ttl=timedelta(hours=2),           # auto-delete after 2 hours idle
)

gds.verify_connectivity()             # always verify after creation
```

### Mode B — Connected to Self-Managed Neo4j

```python
db_connection = DbmsConnectionInfo(
    uri=os.environ["NEO4J_URI"],         # e.g. "bolt://my-server:7687"
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
```

### Mode C — Standalone (No Neo4j DB)

```python
gds = sessions.get_or_create(
    session_name="my-standalone-analysis",
    memory=SessionMemory.m_8GB,
    ttl=timedelta(hours=1),
    cloud_location=CloudLocation("gcp", "europe-west1"),
    # no db_connection — session starts empty
)
```

---

## 5. Session Management

```python
# List all active sessions
from pandas import DataFrame
DataFrame(sessions.list())

# Reconnect to an existing session (idempotent — safe to call again)
gds = sessions.get_or_create(session_name="my-analysis", memory=..., db_connection=...)

# Delete a session (releases resources, stops billing)
sessions.delete(session_name="my-analysis")
# or: gds.delete()

# Check connection
gds.verify_connectivity()
```

---

## 6. Loading Data into the Session

### From a Connected Neo4j DB — Remote Projection

Use `gds.graph.project.remote()` inside a Cypher `RETURN` clause:

```python
G, result = gds.graph.project(
    "my-graph",
    """
    CALL () {
        MATCH (p1:Person)
        OPTIONAL MATCH (p1)-[r:KNOWS]->(p2:Person)
        RETURN
            p1 AS source, r AS rel, p2 AS target,
            p1 {.age, .score} AS sourceNodeProperties,
            p2 {.age, .score} AS targetNodeProperties
    }
    RETURN gds.graph.project.remote(source, target, {
        sourceNodeLabels:       labels(source),
        targetNodeLabels:       labels(target),
        sourceNodeProperties:   sourceNodeProperties,
        targetNodeProperties:   targetNodeProperties,
        relationshipType:       type(rel)
    })
    """,
)
print(f"Projected {G.node_count()} nodes, {G.relationship_count()} relationships")
```

**`CALL () { ... }` is required** to wrap multi-pattern MATCH clauses in a single Cypher unit.  
Use `UNION` inside the `CALL` block to project multiple node/relationship types.

Run plain Cypher against the connected database:

```python
gds.run_cypher("MATCH (n:Person) RETURN count(n)")
```

### From Pandas DataFrames — Standalone Mode

```python
import pandas as pd

nodes_df = pd.DataFrame([
    {"nodeId": 0, "labels": "Person", "age": 30},
    {"nodeId": 1, "labels": "Person", "age": 25},
    {"nodeId": 2, "labels": "Fruit",  "sweetness": 0.9},
])

rels_df = pd.DataFrame([
    {"sourceNodeId": 0, "targetNodeId": 1, "relationshipType": "KNOWS"},
    {"sourceNodeId": 0, "targetNodeId": 2, "relationshipType": "LIKES"},
])

G = gds.graph.construct("my-graph", nodes_df, rels_df)
# Multiple node/rel DataFrames: gds.graph.construct("g", [nodes1, nodes2], [rels1, rels2])
```

**Required columns**:
- Nodes: `nodeId` (int), `labels` (str)
- Relationships: `sourceNodeId`, `targetNodeId`, `relationshipType`
- String node properties are not supported — drop them before calling `construct()`

---

## 7. Running Algorithms

Once you have a graph object `G`, algorithms work **identically** to the standard GDS Python client:

```python
# Mutate — chain algorithms without writing to DB
gds.pageRank.mutate(G, mutateProperty="pagerank", dampingFactor=0.85)
gds.fastRP.mutate(G,
    mutateProperty="embedding",
    embeddingDimension=128,
    featureProperties=["pagerank"],
    propertyRatio=0.2,
    randomSeed=42,
)

# Stream — inspect results
df = gds.pageRank.stream(G)
print(df.sort_values("score", ascending=False).head(10))

# Write — persist to the connected Neo4j DB (connected modes only)
gds.louvain.write(G, writeProperty="community")
```

See `neo4j-gds-skill` for the full algorithm reference (centrality, community detection, similarity, path finding, embeddings, ML pipelines). All algorithms available in GDS work in AGA **except topological link prediction**.

---

## 8. Streaming Results Back

```python
# Stream specific node properties — includes db_node_properties for context
result_df = gds.graph.nodeProperties.stream(
    G,
    node_properties=["pagerank", "embedding"],
    separate_property_columns=True,    # one column per property (not dict)
    db_node_properties=["name"],       # pull these from the connected DB for context
)

result_df.head(10)
```

For standalone mode, `db_node_properties` is not available — join back to your source DataFrame by `nodeId` instead:

```python
result_df = gds.graph.nodeProperties.stream(G, ["pagerank"], separate_property_columns=True)
result_df.merge(nodes_df[["nodeId", "name"]], how="left")
```

---

## 9. Writing Results Back to Neo4j

```python
# Write multiple properties in one call
gds.graph.nodeProperties.write(G, ["pagerank", "embedding"])

# Write relationship properties
gds.graph.relationshipProperties.write(G, G.relationship_types(), ["score"])

# Or use algorithm write mode directly (also persists to DB)
gds.louvain.write(G, writeProperty="community")
gds.knn.write(G,
    nodeProperties=["embedding"],
    topK=10,
    writeRelationshipType="SIMILAR",
    writeProperty="score",
)
```

> Write operations persist to the **connected AuraDB/self-managed instance**. In standalone mode there is no target database — stream results and persist them yourself.

---

## 10. Full Workflow Examples

### AuraDB — PageRank + FastRP → Write Back

```python
from graphdatascience.session import AuraAPICredentials, GdsSessions, DbmsConnectionInfo, SessionMemory, AlgorithmCategory
from datetime import timedelta
import os

# 1. Auth
sessions = GdsSessions(api_credentials=AuraAPICredentials.from_env())

# 2. Size
memory = sessions.estimate(
    node_count=500_000,
    relationship_count=2_000_000,
    algorithm_categories=[AlgorithmCategory.CENTRALITY, AlgorithmCategory.NODE_EMBEDDING],
)

# 3. Session
gds = sessions.get_or_create(
    session_name="prod-analysis",
    memory=memory,
    db_connection=DbmsConnectionInfo.from_env(),
    ttl=timedelta(hours=4),
)
gds.verify_connectivity()

# 4. Project
G, _ = gds.graph.project(
    "social",
    """
    CALL () {
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[r:KNOWS]->(p2:Person)
        RETURN p AS source, r AS rel, p2 AS target,
               p {.score} AS sourceNodeProperties,
               p2 {.score} AS targetNodeProperties
    }
    RETURN gds.graph.project.remote(source, target, {
        sourceNodeLabels: labels(source),
        targetNodeLabels: labels(target),
        sourceNodeProperties: sourceNodeProperties,
        targetNodeProperties: targetNodeProperties,
        relationshipType: type(rel)
    })
    """,
)

# 5. Analyse
gds.pageRank.mutate(G, mutateProperty="pagerank")
gds.fastRP.mutate(G, embeddingDimension=128, mutateProperty="embedding",
                  featureProperties=["pagerank"], randomSeed=42)

# 6. Write back
gds.graph.nodeProperties.write(G, ["pagerank", "embedding"])

# 7. Cleanup
sessions.delete(session_name="prod-analysis")
```

### Standalone — Pandas DataFrame → Community Detection

```python
import pandas as pd
from graphdatascience.session import AuraAPICredentials, GdsSessions, SessionMemory, CloudLocation
from datetime import timedelta

sessions = GdsSessions(api_credentials=AuraAPICredentials.from_env())

gds = sessions.get_or_create(
    session_name="csv-analysis",
    memory=SessionMemory.m_4GB,
    ttl=timedelta(hours=1),
    cloud_location=CloudLocation("gcp", "europe-west1"),
)

# Load from any tabular source (CSV, Parquet, database query, etc.)
nodes = pd.read_csv("nodes.csv")      # must have: nodeId, labels
edges = pd.read_csv("edges.csv")      # must have: sourceNodeId, targetNodeId, relationshipType

G = gds.graph.construct("my-graph", nodes, edges)

# Run Louvain community detection
gds.louvain.mutate(G, mutateProperty="community")

# Stream results — join back to source data for context
result = gds.graph.nodeProperties.stream(G, ["community"], separate_property_columns=True)
output = result.merge(nodes[["nodeId", "name"]], how="left")
print(output.sort_values("community"))

gds.delete()
```

---

## 11. Limitations vs Embedded GDS

| Feature | AGA (serverless) | GDS plugin (embedded) |
|---|---|---|
| Topological link prediction | ❌ Not supported | ✅ |
| ML model persistence across sessions | ❌ Session-local only | ✅ Persistent in model catalog |
| Cypher procedures (`CALL gds.*`) | ❌ Python client only | ✅ |
| Non-Neo4j data sources | ✅ Pandas, Spark, Arrow | ❌ |
| Aura BC / VDC | ✅ | ❌ |
| Aura Pro | ❌ | ✅ |
| Billing | Per session-minute | Included in AuraDB |
| DB performance isolation | ✅ Full isolation | ❌ Shares DB resources |

---

## Checklist

- [ ] Aura API credentials created and set in environment (`CLIENT_ID`, `CLIENT_SECRET`)
- [ ] AGA feature enabled for your Aura project (check Aura Console)
- [ ] Memory estimated before session creation (`sessions.estimate(...)`)
- [ ] Cloud location chosen near data source
- [ ] `gds.verify_connectivity()` called after session creation
- [ ] TTL set to avoid unexpected costs on idle sessions
- [ ] Results written back (connected modes) or streamed and persisted (standalone) before session deletion
- [ ] Session deleted when done (`sessions.delete(...)` or `gds.delete()`)

---

## Resources

- [AGA Python Client Docs](https://neo4j.com/docs/graph-data-science-client/current/aura-graph-analytics/)
- [AuraDB Tutorial Notebook](https://github.com/neo4j/graph-data-science-client/blob/main/examples/graph-analytics-serverless.ipynb)
- [Standalone Tutorial Notebook](https://github.com/neo4j/graph-data-science-client/blob/main/examples/graph-analytics-serverless-standalone.ipynb)
- [Self-Managed Tutorial Notebook](https://github.com/neo4j/graph-data-science-client/blob/main/examples/graph-analytics-serverless-self-managed.ipynb)
- [Spark Tutorial Notebook](https://github.com/neo4j/graph-data-science-client/blob/main/examples/graph-analytics-serverless-spark.ipynb)
- [GDS Algorithm Reference](https://neo4j.com/docs/graph-data-science/current/algorithms/) — all algorithms work in AGA except topological link prediction
- [Aura API Credentials](https://neo4j.com/docs/aura/api/authentication)
