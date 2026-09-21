---
name: neo4j-gds-skill
description: Neo4j Graph Data Science (GDS) embedded plugin via Python client or Cypher —
  covers graphdatascience client 2.0, GraphDataScience, gds.graph.project.native,
  gds.graph.project.cypher, snake_case endpoints, graph catalog operations,
  stream/stats/mutate/write modes, memory estimation, PageRank, Louvain, WCC, FastRP, KNN,
  Node Similarity, ML pipelines, and cleanup. Use for Aura Pro, self-managed, local, or
  offline Neo4j DBMS with the GDS plugin installed. Does NOT cover Aura Graph Analytics
  GDS Sessions, AuraGraphDataScience, GdsSessions, gds.graph.project.remote, or AuraDB
  Cypher API projection/session management — use neo4j-aura-graph-analytics-skill.
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

gds = GraphDataScience("neo4j+s://xxx.databases.neo4j.io", auth=("neo4j", "pw"))   # AuraDS; aura_ds auto-derived
gds = GraphDataScience("bolt://localhost:7687", auth=("neo4j", "password"))
print(gds.server_version())
```

```cypher
RETURN gds.version() AS gds_version
```

GDS plugin unavailable: client raises `GdsNotFound` at construction; Cypher raises `Unknown function 'gds.version'`. AuraDB serverless analytics → `neo4j-aura-graph-analytics-skill`. Self-managed/local → install or enable GDS plugin.

```bash
pip install graphdatascience                 # Python client 2.0+
pip install "graphdatascience[rust-ext]"     # optional: faster serialization
```

Compatibility: graphdatascience 2.0 — GDS >= 2.13 and < 2.28 / < 2026.9, Python >= 3.10 and < 3.15, Neo4j Python driver >= 5.26 and < 7.0, pandas 2–3, pyarrow 21–25. GDS server < 2.13 → `DeprecationWarning` at construction; pin `graphdatascience<2` (client 1.22) there.

### Client 1.x fallback (GDS server < 2.13)

| 2.0 | 1.x client |
|---|---|
| `gds.page_rank`, `gds.louvain`, … — no `v2` prefix | `gds.v2.page_rank`, `gds.v2.louvain`, … |
| `gds.graph.project.native(...)` | `gds.v2.graph.project(...)` |
| `gds.graph.project.cypher(query)` | `gds.graph.cypher.project(query, database=...)` |
| `Graph` / `Model` | `GraphV2` / `ModelV2` |
| `gds.graph.drop(...)` → `list[GraphInfo]` | `gds.v2.graph.drop(...)` → single `GraphInfo` |
| `Graph.drop(fail_if_missing=)` | `Graph.drop(failIfMissing=)` |
| `run_cypher(...)` — always retries | `run_cypher(..., retryable=...)` |

Migration guide: [Neo4j GDS Python client 2.0 migration](https://neo4j.com/docs/graph-data-science-client/current/migration-from-1x/)

GDS plugin releases track the server: `2026.08.1` requires Neo4j `2026.08` — check the [GDS compatibility table](https://neo4j.com/docs/graph-data-science/current/installation/supported-neo4j-versions/) before upgrading either side.

GDS plugin `2026.07.0` removed `CALL gds.userLog()` — read hints and warnings from driver result summary notifications or the Neo4j debug log; track task progress with `CALL gds.listProgress()`.

2.0 client rules:
- Plain endpoints, no `v2` prefix — untyped 1.x endpoints and `gds.v2.*` are gone
- snake_case parameters: `page_rank`, `fast_rp`, `mutate_property`, `write_property`
- Typed result attributes: `result.write_millis`, not `result["writeMillis"]` (`stream` still returns DataFrame)
- Server version via `gds.server_version()` — no `gds.version()` client method (Cypher `RETURN gds.version()` still valid)
- Procedure aliases: `gds.betweenness` ≡ `gds.betweenness_centrality`; also `gds.closeness`, `gds.degree`, `gds.eigenvector`, `gds.harmonic`, `gds.kcore`
- Pipelines: `gds.pipeline.node_classification` / `link_prediction` / `node_regression` — the only API in 2.0
- No async/job-handle API on the plugin surface — `compute()`, `*_async`, `gds.jobs` are AGA Sessions only

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
    {"KNOWS": {"orientation": "UNDIRECTED"}, "LIVES_IN": {"properties": ["since"]}},
    overwrite=True,   # drop same-named graph first
)
```

Native projection: plugin/simple Python-client workflow only. AGA Sessions → `neo4j-aura-graph-analytics-skill`.
1.x fallback: `gds.v2.graph.project(...)`.

### Cypher Projection (use for new Cypher workflows, filters, transforms)

```python
G, result = gds.graph.project.cypher(
    """
    MATCH (source:Person)-[r:KNOWS]->(target:Person)
    WHERE source.active = true
    RETURN gds.graph.project($graph_name, source, target,
        { sourceNodeProperties: source { .score }, relationshipType: 'KNOWS' })
    """,
    graph_name="activeGraph",
)
```

`gds.graph.project.cypher(query)` takes no `database=` — set `GraphDataScience(..., database=...)` at construction or call `gds.set_database(...)` before projecting.
Query must end with exactly one `RETURN gds.graph.project(...)`. If validation fails: use `gds.run_cypher(...)`, then `gds.graph.get("graphName")`.
1.x fallback: `gds.graph.cypher.project(query, database=...)`.

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
gds.graph.drop(G)           # frees JVM heap; returns list[GraphInfo]

G = gds.graph.get("myGraph")       # re-attach to existing projection

gds.graph.list()
```

### Memory Estimation — run before large projections and algorithms

```cypher
CALL gds.graph.project.estimate(['Person'], 'KNOWS')
YIELD requiredMemory, bytesMin, bytesMax, nodeCount, relationshipCount
```

```python
est = gds.graph.project.estimate(node_projection=["Person"], relationship_projection=["KNOWS"])
print(est.required_memory)

G, project_result = gds.graph.project.native("myGraph", "Person", "KNOWS")
print(project_result.node_count)

# Algorithm estimation:
est = gds.page_rank.estimate(G, damping_factor=0.85)
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
gds.betweenness.stream(G)          # alias of betweenness_centrality; identifies bottleneck/bridge nodes
gds.betweenness.write(G, write_property="betweenness")
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
| Feature-rich nodes | GraphSAGE (client: `gds.graph_sage`; Cypher: `gds.beta.graphSage`) |

Full algorithm catalog → [references/algorithms.md](references/algorithms.md)

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Unknown function 'gds.version'` | Embedded GDS plugin unavailable | AGA → `neo4j-aura-graph-analytics-skill`; self-managed/local → install plugin |
| `GdsNotFound` at client construction | GDS plugin not installed on target DB | Install/enable GDS plugin; AuraDS endpoint only with GDS |
| `AttributeError: ... no attribute 'version'` | `gds.version()` does not exist in client 2.0 | Use `gds.server_version()` |
| `DeprecationWarning` at client construction | GDS server < 2.13 | Upgrade GDS server, or pin `graphdatascience<2` and use the 1.x mapping table |
| `Insufficient heap memory` / OOM | Graph too large for available JVM heap | Run `gds.graph.project.estimate`; increase `dbms.memory.heap.max_size` |
| `Procedure not found: gds.leiden` | Older or incompatible GDS | Check `CALL gds.list()` for available procedures; upgrade GDS or use Louvain |
| `Node property 'X' not found` after mutate | Property not projected or wrong graph name | Verify `G.node_properties()` includes the property; check `mutate_property` spelling |
| `Graph 'myGraph' already exists` | Leftover projection from failed run | `overwrite=True`, `CALL gds.graph.drop('myGraph')`, or `gds.graph.drop(G)` |
| `mutate_property already exists` | Re-running algorithm on same projection | Drop and re-project, or use different `mutate_property` name |
| `No algorithm results` | Source/target node not in projection | Verify node labels/rel types match projection; check `G.node_count()` |
| `AttributeError: 'list' object ...` after `gds.graph.drop(...)` | 2.0 returns `list[GraphInfo]` | Index the result; 1.x client returns a single `GraphInfo` |

---

## Full Workflow

1. Create `gds` with `GraphDataScience(...)`.
2. Verify plugin: `gds.server_version()` or `RETURN gds.version()`.
3. Estimate memory: `gds.graph.project.estimate(...)` and algorithm `.estimate(...)`.
4. Project named graph with `gds.graph.project.native(...)` or `gds.graph.project.cypher(query)`.
5. Run `gds.*.stream` first; switch to `mutate`; use `write` only when satisfied.
6. Drop graph with `gds.graph.drop(G)`.
7. GDS server < 2.13 → client 1.22 via the mapping table above.

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
- [ ] Embedded GDS plugin confirmed with `gds.server_version()` or `RETURN gds.version()`
- [ ] Graph/algorithm memory estimated before large work
- [ ] Python examples use 2.0 endpoints (no `v2` prefix), snake_case params, typed result attributes
- [ ] Client 1.x used only with GDS server < 2.13, via the mapping table
- [ ] Projection uses native or plugin Cypher projection; no `gds.graph.project.remote(...)`
- [ ] Named graph dropped after use (`gds.graph.drop(G)`; 1.x: `gds.v2.graph.drop(G)`)
- [ ] Execution mode chosen: `stream` (inspect) → `mutate` (chain) → `write` (persist)
- [ ] `write_property`/`mutate_property` checked for collision with existing properties
- [ ] `overwrite=True` when re-projecting an existing graph name
- [ ] `randomSeed` set for reproducible embeddings
- [ ] WCC run first on graphs that may be disconnected
