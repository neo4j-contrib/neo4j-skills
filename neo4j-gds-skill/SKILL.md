---
name: neo4j-gds-skill
description: Neo4j Graph Data Science (GDS) embedded plugin via Python client or Cypher —
  covers GraphDataScience, graphdatascience 2.0 endpoints (gds.page_rank,
  gds.graph.project.native), gds.version, native projection, Cypher
  projection, graph catalog operations, stream/stats/mutate/write modes, memory estimation,
  PageRank, Louvain, WCC, FastRP, KNN, Node Similarity, ML pipelines, and cleanup. Use for
  Aura Pro, self-managed, local, or offline Neo4j DBMS with the GDS plugin installed. Does
  NOT cover Aura Graph Analytics GDS Sessions, AuraGraphDataScience, GdsSessions,
  gds.graph.project.remote, or AuraDB Cypher API projection/session management — use neo4j-aura-graph-analytics-skill.
  Does NOT handle Cypher authoring — use neo4j-cypher-skill.
  Does NOT cover driver setup — use neo4j-driver-python-skill or other driver skill.
version: 1.0.17
allowed-tools: Bash WebFetch
---

## When to Use
- Running GDS algorithms against embedded GDS plugin through Python client (`graphdatascience`)
- Running GDS algorithms through `CALL gds.*` Cypher procedures
- Aura Pro, self-managed Neo4j, local Neo4j, or offline DBMS with GDS plugin installed
- Projecting named in-memory graphs, running centrality/community/similarity/path/embedding algorithms
- Chaining algorithms via `mutate` mode; building FastRP → KNN pipelines
- Writing node embeddings for Neo4j vector indexes / structural similarity search
- Memory estimation before large graph operations

## When NOT to Use
- **Aura Graph Analytics Sessions / AGA / `GdsSessions` / `AuraGraphDataScience`** → `neo4j-aura-graph-analytics-skill`
- **AuraDB Cypher API with `{ memory: ... }` or `{ sessionId: ... }`** → `neo4j-aura-graph-analytics-skill`
- **Cypher query authoring** → `neo4j-cypher-skill`
- **Driver/connection setup** → `neo4j-driver-python-skill`
- **GraphRAG retrieval** → `neo4j-graphrag-skill`
- **Creating/querying vector indexes over written embeddings** → `neo4j-vector-index-skill`

| Context | Use |
|---|---|
| Aura Pro with GDS plugin | This skill |
| Self-managed/local/offline Neo4j with GDS plugin | This skill |
| AuraDB serverless analytics session | `neo4j-aura-graph-analytics-skill` |
| Self-managed Neo4j attached to AGA session | `neo4j-aura-graph-analytics-skill` |
| Non-Neo4j data source | `neo4j-aura-graph-analytics-skill` |

---

## Pre-flight

Use only with embedded GDS plugin.

```python
from graphdatascience import GraphDataScience

gds = GraphDataScience("neo4j+s://xxx.databases.neo4j.io", auth=("neo4j", "pw"))  # aura_ds derived
gds = GraphDataScience("bolt://localhost:7687", auth=("neo4j", "password"))
print(gds.server_version())
```

```cypher
RETURN gds.version() AS gds_version
```

If `Unknown function 'gds.version'` → GDS plugin unavailable. AuraDB serverless analytics → `neo4j-aura-graph-analytics-skill`. Self-managed/local → install or enable GDS plugin.

```bash
pip install graphdatascience               # Python client 2.0
pip install "graphdatascience[rust_ext]"   # 3–10× faster serialization
```

Compatibility: graphdatascience 2.0 [GA 2026-09-18] — GDS >= 2.13 and < 2.28 / < 2026.9, Python >= 3.10 and < 3.15, Neo4j Python driver >= 5.26 and < 7.0, pandas >= 2.0 and < 4.0, pyarrow >= 21 and < 26, numpy < 3.
Pin `graphdatascience<2` only when stuck on GDS server < 2.13 or Neo4j driver 4.4; 1.22 supports GDS < 2026.6 only — for newer servers upgrade to 2.0 or call GDS from Cypher.

### 1.x → 2.0 endpoint map

| 1.x | 2.0 |
|---|---|
| `gds.v2.<endpoint>`, `gds.alpha.*`, `gds.beta.*`, camelCase untyped endpoints | `gds.<endpoint>` — snake_case, typed results; 1.x endpoints removed |
| `gds.graph.project(...)` | `gds.graph.project.native(...)` |
| `gds.graph.cypher.project(query)` | `gds.graph.project.cypher(query)` — legacy 1.x `gds.graph.project.cypher` procedure removed |
| `gds.graph.project.cypher(database=...)` | parameter removed — `gds.set_database("mydb")` before projecting |
| `result["writeMillis"]` | `result.write_millis` |
| `gds.beta.graphSage.train`, `gds.model.get` | `gds.graph_sage.train`, `gds.graph_sage.get` |
| `gds.model.store/load/drop(model)` | `model.store()`, `model.load()`, `model.drop()` |
| `gds.beta.pipeline.nodeClassification.create`, `gds.nc_pipe` | `gds.pipeline.node_classification.create` |
| `gds.graph.nodeProperty.stream`, `gds.graph.streamNodeProperties` | `gds.graph.node_property.stream`, `gds.graph.node_properties.stream` |
| `gds.graph.relationshipProperties.stream(..., separate_property_columns=True)` | `gds.graph.relationship_properties.stream(...)` — one column per property always |
| `gds.find_node_id` | `gds.util.find_node_id` |
| `gds.alpha.linkprediction.adamicAdar` | `gds.topological_link_prediction.adamic_adar` |
| `GraphV2` / `ModelV2` | `Graph` / `Model` — `from graphdatascience import Graph` |
| `Graph.drop(failIfMissing=)` / `Model.drop(failIfMissing=)` | `fail_if_missing=` |
| `gds.graph.drop(G)` → Series | accepts one graph or a list; returns `list[GraphInfo]` |
| `run_cypher(..., retryable=)` | removed — always retries transactionally |
| `ServerVersion`, `SemanticVersion` top-level import | `graphdatascience.versions` |
| `aura_ds=True` | optional — client derives Aura hosting from the endpoint |

2.0 additions: `overwrite=True` on `gds.graph.project.*` / `generate` / `construct` / `filter` / `sample` drops a same-named graph first; `gds.pipeline.get` fetches a pipeline from the catalog.
Migration guide: [GDS Python client 2.0 migration](https://neo4j.com/docs/graph-data-science-client/current/migration-from-1x/)

GDS plugin releases track the server: `2026.08.1` requires Neo4j `2026.08` — check the [GDS compatibility table](https://neo4j.com/docs/graph-data-science/current/installation/supported-neo4j-versions/) before upgrading either side.

GDS plugin `2026.07.0` removed `CALL gds.userLog()` — read hints and warnings from driver result summary notifications or the Neo4j debug log; track task progress with `CALL gds.listProgress()`.

Client rules:
- snake_case endpoints and parameters: `page_rank`, `fast_rp`, `mutate_property`, `write_property`.
- Typed result attributes: `result.write_millis`, not `result["writeMillis"]`.
- `stream` returns a DataFrame; `stats` / `mutate` / `write` / `train` return typed result objects.

---

## Graph Catalog Operations

### Native Projection

```cypher
CALL gds.graph.project(
  'myGraph',
  ['Person', 'City'],
  { KNOWS: { orientation: 'UNDIRECTED' }, LIVES_IN: {} }
)
YIELD graphName, nodeCount, relationshipCount
```

```python
G, result = gds.graph.project.native("myGraph", "Person", "KNOWS")
print(result.node_count, result.relationship_count)

G, result = gds.graph.project.native(
    "myGraph",
    {"Person": {"properties": ["age", "score"]}, "City": {}},
    {"KNOWS": {"orientation": "UNDIRECTED"}, "LIVES_IN": {"properties": ["since"]}}
)
```

Native projection: plugin Python-client workflow only. AGA Sessions → `neo4j-aura-graph-analytics-skill`.
Re-projecting the same name: pass `overwrite=True`, else `Graph already exists`.

### Cypher Projection (use for new Cypher workflows, filters, transforms)

```python
gds.set_database("neo4j")           # database= parameter removed in client 2.0

G, result = gds.graph.project.cypher(
    """
    MATCH (source:Person)-[r:KNOWS]->(target:Person)
    WHERE source.active = true
    RETURN gds.graph.project($graph_name, source, target,
        { sourceNodeProperties: source { .score }, relationshipType: 'KNOWS' })
    """,
    graph_name="activeGraph"        # extra kwargs pass through as Cypher parameters
)
```

`gds.graph.project.cypher` must end with one `RETURN gds.graph.project(...)` clause, else raises `ValueError`. Workaround for extra aggregations: `gds.run_cypher(...)`, then `gds.graph.get("graphName")`.

AGA Sessions → `neo4j-aura-graph-analytics-skill`; never use plugin Cypher projection.

### Undirected Projection

Native projection: set `orientation: 'UNDIRECTED'` per relationship type.
Plugin Cypher projection: set `undirectedRelationshipTypes: ['*']` in fifth `gds.graph.project(...)` config argument.

Leiden is defined for directed and undirected graphs. Project undirected relationships when community structure is naturally symmetric.

### Inspect and Drop

```python
G.node_count()              # 12_043
G.relationship_count()      # 87_211
G.node_properties()         # projected + mutated properties by label
G.relationship_properties() # projected + mutated properties by type
G.size_in_bytes()
gds.graph.drop(G)                      # frees JVM heap; returns list[GraphInfo]
gds.graph.drop([G, "otherGraph"], fail_if_missing=False)

G = gds.graph.get("myGraph")           # re-attach to existing projection

gds.graph.list()

with gds.graph.project.native("tmpGraph", ["City"], ["FLY_TO"])[0] as G_tmp:
    pass                               # projection dropped on block exit
```

### Memory Estimation — run before large projections and algorithms

```cypher
CALL gds.graph.project.estimate(['Person'], 'KNOWS')
YIELD requiredMemory, bytesMin, bytesMax, nodeCount, relationshipCount
```

```python
est = gds.graph.project.estimate("Person", "KNOWS")     # before projecting
print(est.required_memory)

G, project_result = gds.graph.project.native("myGraph", "Person", "KNOWS")
print(project_result.node_count)

est = gds.page_rank.estimate(G, damping_factor=0.85)    # per algorithm
print(est.required_memory)
```

---

## Execution Modes

| Mode | Side effect | Returns | Use when |
|---|---|---|---|
| `stream` | None | Row per node/pair | Inspect results; top-N |
| `stats` | None | Single aggregate row | Summary/convergence check |
| `mutate` | Adds node property or relationship type/property to in-memory graph only | Stats row | Chain algorithms |
| `write` | Persists node property or relationship to Neo4j DB | Stats row | Final step — make queryable |

Pattern: `stream` to verify → `mutate` to chain → `write` to persist.

`mutate_property` must not exist in the in-memory graph. Relationship algorithms such as KNN also require `mutate_relationship_type`.
After `write`, re-project to use written properties in subsequent GDS calls (in-memory graph does not see DB writes).

---

## gds.util.asNode() — Enrich Stream Results

`stream` mode yields `nodeId` (internal GDS integer). `gds.util.asNode(nodeId)` translates it back to the DB node so you can access properties.

```cypher
// Single property
CALL gds.pageRank.stream('myGraph', {})
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name AS name, score
ORDER BY score DESC LIMIT 10

// Multiple properties — convert once with WITH
CALL gds.pageRank.stream('myGraph', {})
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS node, score
RETURN node.name AS name, node.born AS born, score
ORDER BY score DESC LIMIT 10
```

Not needed for `write`, `mutate`, or `stats` modes — those don't return per-node data.

---

## Core Algorithms

### PageRank (centrality)

```cypher
CALL gds.pageRank.stream('myGraph', { dampingFactor: 0.85, maxIterations: 20 })
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name AS name, score ORDER BY score DESC LIMIT 10
// score: relative influence — not absolute. Compare within same run only.
// didConverge: true means score stabilized; if false, increase maxIterations.

CALL gds.pageRank.write('myGraph', { writeProperty: 'pagerank', dampingFactor: 0.85 })
YIELD nodePropertiesWritten, ranIterations, didConverge
```

```python
pr_df = gds.page_rank.stream(G, damping_factor=0.85)
mutate_result = gds.page_rank.mutate(G, mutate_property="pagerank", damping_factor=0.85)
write_result = gds.page_rank.write(G, write_property="pagerank", damping_factor=0.85)
print(write_result.write_millis)
```

### Louvain (community detection)

```cypher
CALL gds.louvain.stream('myGraph', { relationshipWeightProperty: 'weight' })
YIELD nodeId, communityId

CALL gds.louvain.write('myGraph', { writeProperty: 'community' })
YIELD communityCount, modularity
```

```python
louvain_df = gds.louvain.stream(G)
write_result = gds.louvain.write(G, write_property="community")
print(write_result.community_count)
```

Leiden is a refinement of Louvain avoiding poorly connected communities — use when community quality > raw speed.
`modularity` in stats result: range -0.5 to 1.0. [field] Values > 0.3 often indicate meaningful community structure; > 0.7 is strong.
Leiden is defined for directed and undirected graphs. Project undirected relationships when community structure is naturally symmetric.

### WCC — Weakly Connected Components

Run WCC first to understand graph structure; partition disconnected graphs before expensive algorithms.

```cypher
CALL gds.wcc.stream('myGraph', { minComponentSize: 10 })
YIELD nodeId, componentId

CALL gds.wcc.write('myGraph', { writeProperty: 'componentId' })
YIELD nodePropertiesWritten, componentCount
```

```python
wcc_df = gds.wcc.stream(G)
write_result = gds.wcc.write(G, write_property="componentId")
print(write_result.node_properties_written)
```

### Betweenness Centrality

```python
gds.betweenness_centrality.stream(G)          # identifies bottleneck/bridge nodes
gds.betweenness_centrality.write(G, write_property="betweenness")
```

### Node Similarity

Jaccard similarity from common neighbors — no node properties required.

```python
gds.node_similarity.stream(G, similarity_cutoff=0.1, top_k=10)
gds.node_similarity.write(G, write_relationship_type="SIMILAR", write_property="score",
                          similarity_cutoff=0.1, top_k=10)
```

### FastRP (node embeddings)

Fast, scalable, production ML pipelines. Set `randomSeed` for reproducibility.

```cypher
CALL gds.fastRP.mutate('myGraph', {
  embeddingDimension: 256,
  iterationWeights: [0.0, 1.0, 1.0],
  featureProperties: ['score'],
  propertyRatio: 0.5,
  normalizationStrength: -0.5,
  randomSeed: 42,
  mutateProperty: 'embedding'
})
YIELD nodePropertiesWritten
```

```python
gds.fast_rp.mutate(G, embedding_dimension=256, iteration_weights=[0.0, 1.0, 1.0],
                   random_seed=42, mutate_property="embedding")
write_result = gds.fast_rp.write(G, embedding_dimension=256, write_property="embedding",
                                 random_seed=42)
print(write_result.write_millis)
```

For ANN search over structural embeddings, after `write`, create a Neo4j vector index over the written property. Use `neo4j-vector-index-skill`.

### KNN — K-Nearest Neighbors

Finds k most similar nodes per node based on node properties (typically embeddings).

```cypher
CALL gds.knn.stream('myGraph', {
  nodeProperties: ['embedding'], topK: 10,
  sampleRate: 0.5, similarityCutoff: 0.7
})
YIELD node1, node2, similarity

CALL gds.knn.write('myGraph', {
  nodeProperties: ['embedding'], topK: 10,
  writeRelationshipType: 'SIMILAR', writeProperty: 'score'
})
YIELD relationshipsWritten
```

```python
knn_df = gds.knn.stream(G, node_properties=["embedding"], top_k=10)
gds.knn.write(G, node_properties=["embedding"], top_k=10,
              write_relationship_type="SIMILAR", write_property="score")
```

---

## FastRP → KNN Pipeline (recommendation)

```python
# 1. Project
G, _ = gds.graph.project.native("myGraph", "Product",
    {"BOUGHT_TOGETHER": {"orientation": "UNDIRECTED"}})

# 2. Estimate memory
print(gds.fast_rp.estimate(G, embedding_dimension=128).required_memory)

# 3. Embed
gds.fast_rp.mutate(G, embedding_dimension=128, random_seed=42, mutate_property="emb")

# 4. Similarity
gds.knn.write(G, node_properties=["emb"], top_k=10,
              write_relationship_type="SIMILAR", write_property="score")

# 5. Cleanup
gds.graph.drop(G)
```

---

## Algorithm Selection

| Goal | Algorithm |
|---|---|
| Influence via network links | PageRank / ArticleRank |
| Bottleneck / bridge nodes | Betweenness Centrality |
| Direct connections | Degree Centrality |
| Community (general, fast) | Louvain |
| Community (higher quality) | Leiden |
| Is graph connected? | WCC (run first) |
| Similarity from embeddings | KNN |
| Similarity from neighbors | Node Similarity |
| Shortest path (positive weights) | Dijkstra / A* |
| k alternative paths | Yen's |
| Fast scalable embeddings | FastRP |
| Feature-rich nodes | GraphSAGE (`gds.graph_sage.train`, Cypher `gds.beta.graphSage`) |

Full algorithm catalog → [references/algorithms.md](references/algorithms.md)

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Unknown function 'gds.version'` | Embedded GDS plugin unavailable | AGA → `neo4j-aura-graph-analytics-skill`; self-managed/local → install plugin |
| `Insufficient heap memory` / OOM | Graph too large for available JVM heap | Run `gds.graph.project.estimate`; increase `dbms.memory.heap.max_size` |
| `Procedure not found: gds.leiden` | Older or incompatible GDS | Check `CALL gds.list()` for available procedures; upgrade GDS or use Louvain |
| `Node property 'X' not found` after mutate | Property not projected or wrong graph name | Verify `G.node_properties()` includes the property; check `mutate_property` spelling |
| `Graph 'myGraph' already exists` | Leftover projection from failed run | `CALL gds.graph.drop('myGraph')`, `gds.graph.drop(G)`, or re-project with `overwrite=True` |
| `AttributeError: 'GraphDataScience' object has no attribute 'v2'` | Client 2.0 dropped the `gds.v2` prefix | Call endpoints directly: `gds.page_rank.stream(G)` |
| `Update the graphdatascience package` raised at client creation | Arrow endpoint version unsupported by installed client | `pip install -U graphdatascience` |
| `mutate_property already exists` | Re-running algorithm on same projection | Drop and re-project, or use different `mutate_property` name |
| `No algorithm results` | Source/target node not in projection | Verify node labels/rel types match projection; check `G.node_count()` |

---

## Full Workflow

1. Create `gds` with `GraphDataScience(...)`.
2. Verify plugin: `gds.server_version()` or `RETURN gds.version()`.
3. Estimate memory: `gds.graph.project.estimate(...)` and algorithm `.estimate(...)`.
4. Project named graph with `gds.graph.project.native(...)`.
5. Run `gds.*.stream` first; switch to `mutate`; use `write` only when satisfied.
6. Drop graph with `gds.graph.drop(G)`.

Built-in test datasets: `gds.graph.datasets.load_cora()`, `gds.graph.datasets.load_karate_club()`, `gds.graph.datasets.load_imdb()`

---

## MCP Tool Mapping

| Operation | MCP tool |
|---|---|
| `RETURN gds.version()` | `read-cypher` |
| `gds.pageRank.stream(...)` | `read-cypher` |
| `gds.pageRank.write(...)` | `write-cypher` |
| `gds.graph.drop(...)` | `write-cypher` |
| List available procedures | `read-cypher` → `CALL gds.list()` |

Before any `write-cypher`: show exact Cypher, expected nodes/relationships affected, and ask for confirmation. For algorithm `write` mode, estimate or run `stats` first when available.

---

## References

- [references/algorithms.md](references/algorithms.md) — full algorithm catalog: all procedures, parameters, tiers, Cypher + Python examples
- [references/graph-projection.md](references/graph-projection.md) — projection deep-dive: filtering, heterogeneous graphs, relationship orientation, property types
- [GDS Manual](https://neo4j.com/docs/graph-data-science/current/)
- [Python Client Docs](https://neo4j.com/docs/graph-data-science-client/current/)

---

## Checklist
- [ ] Embedded GDS plugin confirmed with `gds.version()` or `gds.server_version()`
- [ ] Graph/algorithm memory estimated before large work
- [ ] Python examples use unprefixed `gds.*` endpoints (client 2.0), snake_case params, typed result attributes
- [ ] Projection uses native or plugin Cypher projection; no `gds.graph.project.remote(...)`
- [ ] Named graph dropped after use (`gds.graph.drop(G)`)
- [ ] Execution mode chosen: `stream` (inspect) → `mutate` (chain) → `write` (persist)
- [ ] `write_property`/`mutate_property` checked for collision with existing properties
- [ ] `randomSeed` set for reproducible embeddings
- [ ] WCC run first on graphs that may be disconnected
