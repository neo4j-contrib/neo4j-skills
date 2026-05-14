---
name: neo4j-gds-skill
description: Neo4j Graph Data Science (GDS) plugin — graph projection, algorithm execution,
  execution modes (stream/stats/mutate/write), memory estimation, and the GDS Python client
  (graphdatascience v1.21). Use when running gds.pageRank, gds.louvain, gds.wcc, gds.fastRP,
  gds.knn, gds.betweenness, gds.nodeSimilarity, or any gds.* procedure; projecting named
  in-memory graphs with gds.graph.project or graph.project; chaining algorithms with mutate
  mode; computing node embeddings for ML; building recommendation systems with FastRP + KNN.
  Also triggers on GraphDataScience, GdsSessions, graph catalog operations, ML pipelines,
  node classification, link prediction.
  Does NOT cover Aura Graph Analytics serverless sessions — use neo4j-aura-graph-analytics-skill.
  Does NOT handle Cypher authoring — use neo4j-cypher-skill.
  Does NOT cover driver setup — use neo4j-driver-python-skill or other driver skill.
version: 1.0.0
allowed-tools: Bash WebFetch
---

## When to Use
- Running GDS algorithms on self-managed Neo4j or Aura Pro (embedded plugin)
- Projecting named in-memory graphs, running centrality/community/similarity/path/embedding algorithms
- Chaining algorithms via `mutate` mode; building FastRP → KNN pipelines
- Memory estimation before large graph operations
- GDS Python client (`graphdatascience`) workflows

## When NOT to Use
- **Aura BC / VDC / Free** — GDS plugin unavailable → `neo4j-aura-graph-analytics-skill`
- **Cypher query authoring** → `neo4j-cypher-skill`
- **Driver/connection setup** → `neo4j-driver-python-skill`
- **GraphRAG retrieval** → `neo4j-graphrag-skill`

| Deployment | Use |
|---|---|
| Aura Free | Upgrade to Pro or use `neo4j-aura-graph-analytics-skill` |
| Aura Pro | This skill |
| Aura BC / VDC | `neo4j-aura-graph-analytics-skill` |
| Self-managed (Community or Enterprise) | This skill (install GDS plugin) |

---

## Pre-flight

```cypher
RETURN gds.version() AS gds_version
```

Fails with `Unknown function 'gds.version'` → GDS not installed or wrong tier. Stop, inform user.

```bash
pip install graphdatascience              # Python client
pip install graphdatascience[rust_ext]    # 3–10× faster serialization
```

Compatibility: graphdatascience v1.21 — GDS >= 2.6, Python >= 3.10, Neo4j Driver >= 4.4.12

```python
from graphdatascience import GraphDataScience

gds = GraphDataScience("bolt://localhost:7687", auth=("neo4j", "password"))
gds = GraphDataScience("neo4j+s://xxx.databases.neo4j.io", auth=("neo4j", "pw"), aura_ds=True)
print(gds.server_version())
```

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
G, result = gds.graph.project("myGraph", "Person", "KNOWS")

G, result = gds.graph.project(
    "myGraph",
    {"Person": {"properties": ["age", "score"]}, "City": {}},
    {"KNOWS": {"orientation": "UNDIRECTED"}, "LIVES_IN": {"properties": ["since"]}}
)
```

### Cypher Projection (use when native can't express filter/transform)

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

Native projection over Cypher projection whenever possible — 5–10× faster on large graphs.

### Weighted Projection (Cypher projection syntax)

```cypher
MATCH (source:User)-[r:RATED]->(target:Movie)
WITH gds.graph.project(
  'user-movie-weighted',
  source, target,
  { relationshipProperties: r { .rating } },
  { undirectedRelationshipTypes: ['*'] }
) AS g
RETURN g.graphName, g.nodeCount, g.relationshipCount
```

### Relationship Aggregation (collapse parallel relationships into a weighted edge)

```cypher
MATCH (source:Actor)-[r:ACTED_IN]->(:Movie)<-[:ACTED_IN]-(target:Actor)
WITH source, target, count(r) AS collabCount
WITH gds.graph.project(
  'actor-network',
  source, target,
  { relationshipProperties: { collabCount: collabCount } },
  { undirectedRelationshipTypes: ['*'] }
) AS g
RETURN g.graphName, g.nodeCount, g.relationshipCount
```

Use `count(r)` to aggregate multiple parallel relationships into a single weighted edge. Reduces graph size; enables weight-based algorithms.

### Undirected Projection (native syntax)

Pass `orientation: 'UNDIRECTED'` per relationship type — or use `undirectedRelationshipTypes: ['*']` in Cypher projection (second config map).

Leiden **requires** undirected relationships. Community detection and similarity algorithms generally work better on undirected graphs.

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
| `mutate` | Adds property to in-memory graph only | Stats row | Chain algorithms |
| `write` | Persists property to Neo4j DB | Stats row | Final step — make queryable |

Pattern: `stream` to verify → `mutate` to chain → `write` to persist.

`mutateProperty` must not already exist in the in-memory graph.
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
`modularity` in stats result: range -0.5 to 1.0; values > 0.3 indicate meaningful community structure; > 0.7 = strong.
Leiden **requires** undirected relationships in the projection.

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
| Feature-rich nodes | GraphSAGE (Beta) |

Full algorithm catalog → [references/algorithms.md](references/algorithms.md)

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Unknown function 'gds.version'` | GDS not installed / wrong tier | Install plugin; on Aura BC/VDC use `neo4j-aura-graph-analytics-skill` |
| `Insufficient heap memory` / OOM | Graph too large for available JVM heap | Run `gds.graph.project.estimate` first; increase `dbms.memory.heap.max_size` |
| `Procedure not found: gds.leiden` | Algorithm not licensed / older GDS | Check `CALL gds.list()` for available procedures; upgrade GDS or use Louvain |
| `Node property 'X' not found` after mutate | Property not projected or wrong graph name | Verify `G.node_properties("Label")` includes the property; check `mutateProperty` spelling |
| `Graph 'myGraph' already exists` | Leftover projection from failed run | `CALL gds.graph.drop('myGraph')` or `G.drop()` |
| `mutateProperty already exists` | Re-running algorithm on same projection | Drop and re-project, or use different `mutateProperty` name |
| `No algorithm results` | Source/target node not in projection | Verify node labels/rel types match projection; check `G.node_count()` |

---

## Full Workflow

```python
# 0. Verify
print(gds.server_version())

# 1. Estimate
est = gds.graph.project.estimate("Person", "KNOWS")
print(est["requiredMemory"])

# 2. Project
G, _ = gds.graph.project("myGraph", "Person",
    {"KNOWS": {"orientation": "UNDIRECTED"}})
print(G.node_count(), G.relationship_count())

# 3. Stream to verify
df = gds.pageRank.stream(G)
print(df.sort_values("score", ascending=False).head(10))

# 4. Write when satisfied
gds.pageRank.write(G, writeProperty="pagerank", dampingFactor=0.85)

# 5. Drop — frees JVM heap
G.drop()
```

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

---

## References

- [references/algorithms.md](references/algorithms.md) — full algorithm catalog: all procedures, parameters, tiers, Cypher + Python examples
- [references/graph-projection.md](references/graph-projection.md) — projection deep-dive: filtering, heterogeneous graphs, relationship orientation, property types
- [GDS Manual](https://neo4j.com/docs/graph-data-science/current/)
- [Python Client Docs](https://neo4j.com/docs/graph-data-science-client/current/)

---

## Checklist
- [ ] `gds.version()` confirmed — GDS installed and licensed
- [ ] Memory estimated before large projections and expensive algorithms
- [ ] Named graph dropped after use (`G.drop()` or context manager)
- [ ] Execution mode chosen: `stream` (inspect) → `mutate` (chain) → `write` (persist)
- [ ] `writeProperty`/`mutateProperty` checked for collision with existing properties
- [ ] `randomSeed` set for reproducible embeddings
- [ ] WCC run first on graphs that may be disconnected
- [ ] Native projection used over Cypher projection unless filtering/transformation required
