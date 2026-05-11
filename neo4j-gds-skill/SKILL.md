---
name: neo4j-gds-skill
description: Neo4j Graph Data Science (GDS) via Python client — prefer Aura Graph Analytics
  GDS Sessions for AuraDB when available; use embedded GDS plugin for self-managed Neo4j
  or Aura Pro plugin workflows. Covers GdsSessions, AuraGraphDataScience, remote projection
  with gds.graph.project.remote, graph projection, algorithm execution, stream/stats/mutate/write
  modes, memory/session sizing, FastRP, KNN, PageRank, Louvain, WCC, ML pipelines, and graph
  catalog cleanup. Use when running gds.pageRank, gds.louvain, gds.wcc, gds.fastRP, gds.knn,
  gds.nodeSimilarity, graphdatascience, or any gds.* workload.
  Does NOT handle Cypher authoring — use neo4j-cypher-skill.
  Does NOT cover driver setup — use neo4j-driver-python-skill or other driver skill.
version: 1.0.0
allowed-tools: Bash WebFetch
---

## When to Use
- Running GDS algorithms through Python client (`graphdatascience`)
- AuraDB available and GDS workload fits Aura Graph Analytics Sessions
- Running GDS algorithms on self-managed Neo4j or Aura Pro (embedded plugin)
- Projecting named in-memory graphs, running centrality/community/similarity/path/embedding algorithms
- Chaining algorithms via `mutate` mode; building FastRP → KNN pipelines
- Writing node embeddings for Neo4j vector indexes / structural similarity search
- Memory estimation before large graph operations

## When NOT to Use
- **Cypher query authoring** → `neo4j-cypher-skill`
- **Driver/connection setup** → `neo4j-driver-python-skill`
- **GraphRAG retrieval** → `neo4j-graphrag-skill`
- **Creating/querying vector indexes over written embeddings** → `neo4j-vector-index-skill`

| Context | Prefer |
|---|---|
| AuraDB + Aura API credentials | Aura Graph Analytics attached GDS Session via Python client |
| AuraDB + no Aura API credentials | Aura Graph Analytics Cypher API if plan supports it; otherwise get API credentials |
| Self-managed Neo4j + cloud/on-demand acceptable | Aura Graph Analytics self-managed GDS Session via Python client |
| Self-managed/local/offline Neo4j | Embedded GDS plugin via Python client |
| Non-Neo4j data source | Standalone GDS Session + `gds.graph.construct` |

---

## Pre-flight

Use Python client first. Choose runtime before projecting:

Aura Graph Analytics Session for AuraDB — preferred when available:
see [references/gds-sessions.md](references/gds-sessions.md) for full `GdsSessions` setup.

```python
# Embedded GDS plugin
from graphdatascience import GraphDataScience

gds = GraphDataScience("neo4j+s://xxx.databases.neo4j.io", auth=("neo4j", "pw"), aura_ds=True)
gds = GraphDataScience("bolt://localhost:7687", auth=("neo4j", "password"))
print(gds.server_version())
```

```cypher
RETURN gds.version() AS gds_version
```

For plugin pre-flight only. Fails with `Unknown function 'gds.version'` → GDS plugin not installed or wrong tier. Prefer Aura Graph Analytics Session for AuraDB.

```bash
pip install graphdatascience              # Python client
pip install graphdatascience[rust_ext]    # 3–10× faster serialization
```

Compatibility: graphdatascience v1.21 — GDS >= 2.6 and < 2.28 / < 2026.4, Python >= 3.10 and < 3.15, Neo4j Driver >= 4.4.12 and < 7.0.

Session rules:
- Attached/self-managed sessions: remote projection from Neo4j source; remote write-back supported.
- Standalone sessions: use `gds.graph.construct`; stream results back and persist manually.
- Default TTL: 1h idle; max lifetime: 7d. Always call `gds.delete()` or `sessions.delete(...)` when done.
- `gds.run_cypher(...)` runs on source Neo4j DB, not inside the GDS Session.

For session details → [references/gds-sessions.md](references/gds-sessions.md)

---

## Graph Catalog Operations

### Aura Graph Analytics Remote Projection

```python
G, result = gds.graph.project(
    graph_name="product-graph",
    query="""
    CYPHER runtime=parallel
    MATCH (source:Product)-[r:BOUGHT_TOGETHER]->(target:Product)
    RETURN gds.graph.project.remote(source, target, {
      sourceNodeProperties: source { .price },
      targetNodeProperties: target { .price },
      relationshipType: type(r),
      relationshipProperties: r { .weight }
    })
    """,
    undirected_relationship_types=["BOUGHT_TOGETHER"],
)
```

Remote projection query uses `gds.graph.project.remote(...)`; graph name is passed to `gds.graph.project(...)`, not inside query.

After remote projection, algorithm calls match plugin calls:

```python
gds.pageRank.mutate(G, mutateProperty="pagerank")
gds.fastRP.mutate(G, featureProperties=["pagerank"], embeddingDimension=128,
                  randomSeed=42, mutateProperty="embedding")
gds.graph.nodeProperties.write(G, "embedding")  # attached/self-managed sessions only
```

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
G, result = gds.graph.project("myGraph", "Person", "KNOWS")

G, result = gds.graph.project(
    "myGraph",
    {"Person": {"properties": ["age", "score"]}, "City": {}},
    {"KNOWS": {"orientation": "UNDIRECTED"}, "LIVES_IN": {"properties": ["since"]}}
)
```

Native projection: plugin/simple Python-client workflow only. Not supported in Aura Graph Analytics Sessions.

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

`gds.graph.cypher.project` must end with one `RETURN gds.graph.project(...)` clause. If validation fails, use `gds.run_cypher(...)` then `gds.graph.get("graphName")`.

For Aura Graph Analytics Sessions use `gds.graph.project(..., query="... gds.graph.project.remote(...) ...")`, not `gds.graph.cypher.project(...)`.

### Undirected Projection (native syntax)

Pass `orientation: 'UNDIRECTED'` per relationship type in native projection — or use `undirectedRelationshipTypes: ['*']` in Cypher projection (second config map).

Leiden is defined for directed and undirected graphs. Project undirected relationships when community structure is naturally symmetric.

### Inspect and Drop

```python
G.node_count()            # 12_043
G.relationship_count()    # 87_211
G.node_properties("Person")  # lists projected + mutated properties
G.memory_usage()          # "45 MiB"
G.exists()
G.drop()                  # always drop after use — frees JVM heap

G = gds.graph.get("myGraph")          # re-attach to existing projection

with gds.graph.project("tmp", "Person", "KNOWS")[0] as G:
    results = gds.pageRank.stream(G)
# dropped automatically
```

### Memory Estimation — always run before large projections and algorithms

For sessions: estimate session memory before `get_or_create`.

```python
from graphdatascience.session import AlgorithmCategory

memory = sessions.estimate(
    node_count=1_000_000,
    relationship_count=5_000_000,
    algorithm_categories=[AlgorithmCategory.CENTRALITY, AlgorithmCategory.NODE_EMBEDDING],
    node_label_count=1,
    node_property_count=2,
    relationship_property_count=1,
)
```

```cypher
CALL gds.graph.project.estimate(['Person'], 'KNOWS')
YIELD requiredMemory, bytesMin, bytesMax, nodeCount, relationshipCount
```

```python
est = gds.graph.project.estimate("Person", "KNOWS")
print(est["requiredMemory"])    # e.g. "1234 MiB"

# Algorithm estimation:
est = gds.pageRank.estimate(G, dampingFactor=0.85)
print(est["requiredMemory"])
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

`mutateProperty` must not exist in the in-memory graph. Relationship algorithms such as KNN also require `mutateRelationshipType`.
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
pr_df = gds.pageRank.stream(G, dampingFactor=0.85)
gds.pageRank.mutate(G, mutateProperty="pagerank", dampingFactor=0.85)
gds.pageRank.write(G, writeProperty="pagerank", dampingFactor=0.85)
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
gds.louvain.write(G, writeProperty="community")
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
gds.wcc.write(G, writeProperty="componentId")
```

### Betweenness Centrality

```python
gds.betweenness.stream(G)          # identifies bottleneck/bridge nodes
gds.betweenness.write(G, writeProperty="betweenness")
```

### Node Similarity

Jaccard similarity from common neighbors — no node properties required.

```python
gds.nodeSimilarity.stream(G, similarityCutoff=0.1, topK=10)
gds.nodeSimilarity.write(G, writeRelationshipType="SIMILAR", writeProperty="score",
                          similarityCutoff=0.1, topK=10)
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
gds.fastRP.mutate(G, embeddingDimension=256, iterationWeights=[0.0, 1.0, 1.0],
                  randomSeed=42, mutateProperty="embedding")
gds.fastRP.write(G, embeddingDimension=256, writeProperty="embedding", randomSeed=42)
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
knn_df = gds.knn.stream(G, nodeProperties=["embedding"], topK=10)
gds.knn.write(G, nodeProperties=["embedding"], topK=10,
              writeRelationshipType="SIMILAR", writeProperty="score")
```

---

## FastRP → KNN Pipeline (recommendation)

```python
# 1. Project
G, _ = gds.graph.project("myGraph", "Product",
    {"BOUGHT_TOGETHER": {"orientation": "UNDIRECTED"}})

# 2. Estimate memory
print(gds.fastRP.estimate(G, embeddingDimension=128)["requiredMemory"])

# 3. Embed
gds.fastRP.mutate(G, embeddingDimension=128, randomSeed=42, mutateProperty="emb")

# 4. Similarity
gds.knn.write(G, nodeProperties=["emb"], topK=10,
              writeRelationshipType="SIMILAR", writeProperty="score")

# 5. Cleanup — always
G.drop()
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
| `Unknown function 'gds.version'` | Embedded GDS plugin unavailable | Use Aura Graph Analytics Session for AuraDB; install plugin only for self-managed/local |
| `Native projections ... not supported` | Session projection used native syntax | Use remote projection with `gds.graph.project.remote(...)` |
| Session expired / unavailable | TTL or 7-day max lifetime reached | Recreate with `sessions.get_or_create`; re-project graph |
| `Insufficient heap memory` / OOM | Graph too large for available JVM heap | Run `gds.graph.project.estimate` first; increase `dbms.memory.heap.max_size` |
| `Procedure not found: gds.leiden` | Older or incompatible GDS | Check `CALL gds.list()` for available procedures; upgrade GDS or use Louvain |
| `Node property 'X' not found` after mutate | Property not projected or wrong graph name | Verify `G.node_properties("Label")` includes the property; check `mutateProperty` spelling |
| `Graph 'myGraph' already exists` | Leftover projection from failed run | `CALL gds.graph.drop('myGraph')` or `G.drop()` |
| `mutateProperty already exists` | Re-running algorithm on same projection | Drop and re-project, or use different `mutateProperty` name |
| `No algorithm results` | Source/target node not in projection | Verify node labels/rel types match projection; check `G.node_count()` |

---

## Full Workflow

1. Create `gds`: prefer Aura Graph Analytics Session for AuraDB; use `GraphDataScience(...)` for plugin.
2. Estimate: `sessions.estimate(...)` for sessions; `gds.graph.project.estimate(...)` for plugin.
3. Project: remote projection for sessions; native/Cypher projection for plugin.
4. Run `stream` first; switch to `mutate` for chaining; use `write` only when satisfied.
5. Drop graph with `G.drop()`.
6. Session only: delete compute with `gds.delete()` or `sessions.delete(...)`.

Built-in test datasets: `gds.graph.load_cora()`, `gds.graph.load_karate_club()`, `gds.graph.load_imdb()`

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
- [references/gds-sessions.md](references/gds-sessions.md) — Aura Graph Analytics Sessions: create, project, run, write back, delete
- [GDS Manual](https://neo4j.com/docs/graph-data-science/current/)
- [Python Client Docs](https://neo4j.com/docs/graph-data-science-client/current/)

---

## Checklist
- [ ] Runtime chosen: Aura Graph Analytics Session preferred for AuraDB; plugin used only when appropriate
- [ ] Session memory or graph/algorithm memory estimated before large work
- [ ] Session remote projection uses `gds.graph.project.remote(...)`; plugin projection uses native/Cypher projection
- [ ] Named graph dropped after use (`G.drop()` or context manager)
- [ ] Session deleted after use (`gds.delete()` or `sessions.delete(...)`)
- [ ] Execution mode chosen: `stream` (inspect) → `mutate` (chain) → `write` (persist)
- [ ] `writeProperty`/`mutateProperty` checked for collision with existing properties
- [ ] `randomSeed` set for reproducible embeddings
- [ ] WCC run first on graphs that may be disconnected
