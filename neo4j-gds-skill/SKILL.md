---
name: neo4j-gds-skill
description: Neo4j Graph Data Science (GDS) embedded plugin via Python client or Cypher —
  covers GraphDataScience, gds.v2 plugin endpoints, gds.version, native projection, Cypher
  projection, graph catalog operations, stream/stats/mutate/write modes, memory estimation,
  PageRank, Louvain, WCC, FastRP, KNN, Node Similarity, ML pipelines, and cleanup. Use for
  Aura Pro, self-managed, local, or offline Neo4j DBMS with the GDS plugin installed. Does
  NOT cover Aura Graph Analytics GDS Sessions, AuraGraphDataScience, GdsSessions,
  gds.graph.project.remote, or AuraDB Cypher API projection/session management — use neo4j-aura-graph-analytics-skill.
  Does NOT handle Cypher authoring — use neo4j-cypher-skill.
  Does NOT cover driver setup — use neo4j-driver-python-skill or other driver skill.
version: 1.0.1
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

gds = GraphDataScience("neo4j+s://xxx.databases.neo4j.io", auth=("neo4j", "pw"), aura_ds=True)
gds = GraphDataScience("bolt://localhost:7687", auth=("neo4j", "password"))
print(gds.server_version())
```

```cypher
RETURN gds.version() AS gds_version
```

If `Unknown function 'gds.version'` → GDS plugin unavailable. AuraDB serverless analytics → `neo4j-aura-graph-analytics-skill`. Self-managed/local → install or enable GDS plugin.

```bash
pip install graphdatascience              # Python client
pip install graphdatascience[rust_ext]    # 3–10× faster serialization
```

Compatibility: graphdatascience v1.22 — GDS >= 2.6 and < 2.28 / < 2026.6, Python >= 3.10 and < 3.15, Neo4j Driver >= 4.4.12 and < 7.0.

V2 rules:
- Prefer `gds.v2.*` when endpoint exists.
- Use snake_case endpoints and parameters: `page_rank`, `fast_rp`, `mutate_property`, `write_property`.
- Use typed result attributes: `result.write_millis`, not `result["writeMillis"]`.
- Use v1 if v2 endpoint missing/incompatible; label fallback.

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
G, result = gds.v2.graph.project("myGraph", "Person", "KNOWS")
print(result.node_count, result.relationship_count)

G, result = gds.v2.graph.project(
    "myGraph",
    {"Person": {"properties": ["age", "score"]}, "City": {}},
    {"KNOWS": {"orientation": "UNDIRECTED"}, "LIVES_IN": {"properties": ["since"]}}
)
```

Native projection: plugin/simple Python-client workflow only. AGA Sessions → `neo4j-aura-graph-analytics-skill`.
V1 fallback: `gds.graph.project(...)`.

### Cypher Projection (use for new Cypher workflows, filters, transforms)

```python
G, result = gds.graph.cypher.project(
    """
    MATCH (source:Person)-[r:KNOWS]->(target:Person)
    WHERE source.active = true
    RETURN gds.graph.project($graph_name, source, target,
        { sourceNodeProperties: source { .score }, relationshipType: 'KNOWS' })
    """,
    database="neo4j", graph_name="activeGraph"
)
```

`gds.graph.cypher.project` must end with one `RETURN gds.graph.project(...)` clause. If validation fails: use `gds.run_cypher(...)`, then `gds.graph.get("graphName")`.
Use v1 `gds.graph.cypher.project(...)` if v2 graph projection cannot express required filter/transform.

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
gds.v2.graph.drop(G)        # frees JVM heap

G = gds.v2.graph.get("myGraph")       # re-attach to existing projection

gds.v2.graph.list()
```

### Memory Estimation — run before large projections and algorithms

```cypher
CALL gds.graph.project.estimate(['Person'], 'KNOWS')
YIELD requiredMemory, bytesMin, bytesMax, nodeCount, relationshipCount
```

```python
G, project_result = gds.v2.graph.project("myGraph", "Person", "KNOWS")
print(project_result.node_count)

# Algorithm estimation:
est = gds.v2.page_rank.estimate(G, damping_factor=0.85)
print(est.required_memory)
```

Projection estimate fallback: use v1 `gds.graph.project.estimate(...)` if v2 estimate endpoint unavailable.

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
pr_df = gds.v2.page_rank.stream(G, damping_factor=0.85)
mutate_result = gds.v2.page_rank.mutate(G, mutate_property="pagerank", damping_factor=0.85)
write_result = gds.v2.page_rank.write(G, write_property="pagerank", damping_factor=0.85)
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
louvain_df = gds.v2.louvain.stream(G)
write_result = gds.v2.louvain.write(G, write_property="community")
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
wcc_df = gds.v2.wcc.stream(G)
write_result = gds.v2.wcc.write(G, write_property="componentId")
print(write_result.node_properties_written)
```

### Betweenness Centrality

```python
gds.v2.betweenness_centrality.stream(G)          # identifies bottleneck/bridge nodes
gds.v2.betweenness_centrality.write(G, write_property="betweenness")
```

### Node Similarity

Jaccard similarity from common neighbors — no node properties required.

```python
gds.v2.node_similarity.stream(G, similarity_cutoff=0.1, top_k=10)
gds.v2.node_similarity.write(G, write_relationship_type="SIMILAR", write_property="score",
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
gds.v2.fast_rp.mutate(G, embedding_dimension=256, iteration_weights=[0.0, 1.0, 1.0],
                      random_seed=42, mutate_property="embedding")
write_result = gds.v2.fast_rp.write(G, embedding_dimension=256, write_property="embedding",
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
knn_df = gds.v2.knn.stream(G, node_properties=["embedding"], top_k=10)
gds.v2.knn.write(G, node_properties=["embedding"], top_k=10,
                 write_relationship_type="SIMILAR", write_property="score")
```

---

## FastRP → KNN Pipeline (recommendation)

```python
# 1. Project
G, _ = gds.v2.graph.project("myGraph", "Product",
    {"BOUGHT_TOGETHER": {"orientation": "UNDIRECTED"}})

# 2. Estimate memory
print(gds.v2.fast_rp.estimate(G, embedding_dimension=128).required_memory)

# 3. Embed
gds.v2.fast_rp.mutate(G, embedding_dimension=128, random_seed=42, mutate_property="emb")

# 4. Similarity
gds.v2.knn.write(G, node_properties=["emb"], top_k=10,
                 write_relationship_type="SIMILAR", write_property="score")

# 5. Cleanup
gds.v2.graph.drop(G)
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
| Feature-rich nodes | GraphSAGE (`gds.beta.graphSage`) |

Full algorithm catalog → [references/algorithms.md](references/algorithms.md)

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Unknown function 'gds.version'` | Embedded GDS plugin unavailable | AGA → `neo4j-aura-graph-analytics-skill`; self-managed/local → install plugin |
| `Insufficient heap memory` / OOM | Graph too large for available JVM heap | Run `gds.graph.project.estimate`; increase `dbms.memory.heap.max_size` |
| `Procedure not found: gds.leiden` | Older or incompatible GDS | Check `CALL gds.list()` for available procedures; upgrade GDS or use Louvain |
| `Node property 'X' not found` after mutate | Property not projected or wrong graph name | Verify `G.node_properties()` includes the property; check `mutate_property` spelling |
| `Graph 'myGraph' already exists` | Leftover projection from failed run | `CALL gds.graph.drop('myGraph')` or `gds.v2.graph.drop(G)` |
| `mutate_property already exists` | Re-running algorithm on same projection | Drop and re-project, or use different `mutate_property` name |
| `No algorithm results` | Source/target node not in projection | Verify node labels/rel types match projection; check `G.node_count()` |

---

## Full Workflow

1. Create `gds` with `GraphDataScience(...)`.
2. Verify plugin: `gds.server_version()` or `RETURN gds.version()`.
3. Estimate memory: `gds.graph.project.estimate(...)` and algorithm `.estimate(...)`.
4. Project named graph with `gds.v2.graph.project(...)`.
5. Run `gds.v2.*.stream` first; switch to `mutate`; use `write` only when satisfied.
6. Drop graph with `gds.v2.graph.drop(G)`.
7. Use v1 only for endpoints missing in v2, such as plugin Cypher projection.

Built-in test datasets: `gds.v2.graph.datasets.load_cora()`, `gds.v2.graph.datasets.load_karate_club()`, `gds.v2.graph.datasets.load_imdb()`

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
- [ ] Python examples prefer `gds.v2.*`, snake_case params, typed result attributes
- [ ] v1 APIs used only as explicit fallback
- [ ] Projection uses native or plugin Cypher projection; no `gds.graph.project.remote(...)`
- [ ] Named graph dropped after use (`gds.v2.graph.drop(G)` or v1 fallback)
- [ ] Execution mode chosen: `stream` (inspect) → `mutate` (chain) → `write` (persist)
- [ ] `write_property`/`mutate_property` checked for collision with existing properties
- [ ] `randomSeed` set for reproducible embeddings
- [ ] WCC run first on graphs that may be disconnected
