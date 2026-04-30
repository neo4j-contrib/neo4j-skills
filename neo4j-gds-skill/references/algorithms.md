# GDS Algorithm Reference

Full catalog of GDS procedures. All support stream/stats/mutate/write modes unless noted.

## Centrality

| Algorithm | Procedure | Tier | Best For |
|---|---|---|---|
| PageRank | `gds.pageRank` | Community | Network influence via incoming links |
| Betweenness Centrality | `gds.betweenness` | Community | Bottleneck/bridge nodes |
| Degree Centrality | `gds.degree` | Community | Most-connected nodes (fast) |
| ArticleRank | `gds.articleRank` | Community | PageRank variant dampening high-degree nodes |
| Eigenvector | `gds.eigenvector` | Community | Influence via well-connected neighbors |
| Closeness | `gds.closeness` | Community | Average distance to all other nodes |
| HITS | `gds.hits` | Community | Authority/hub scores (web-like graphs) |

### PageRank — key parameters
| Parameter | Default | Notes |
|---|---|---|
| `dampingFactor` | 0.85 | Probability of following a link; lower = more teleportation |
| `maxIterations` | 20 | |
| `tolerance` | 1e-7 | Convergence threshold |
| `relationshipWeightProperty` | — | Optional weight property |

Spider traps (closed groups, no outlinks) inflate scores — increase `dampingFactor`. Negative weights silently ignored.

---

## Community Detection

| Algorithm | Procedure | Tier | Notes |
|---|---|---|---|
| Louvain | `gds.louvain` | Community | Best general-purpose; modularity maximization |
| Leiden | `gds.leiden` | Community | Refinement of Louvain; avoids poorly connected communities |
| WCC | `gds.wcc` | Community | Weakly connected components; run first to partition graph |
| SCC | `gds.scc` | Community | Strongly connected components (directed graphs only) |
| Label Propagation | `gds.labelPropagation` | Community | Fast, large graphs; non-deterministic |
| K-Core Decomposition | `gds.kcore` | Community | Dense subgraphs by degree threshold |
| Triangle Count | `gds.triangleCount` | Community | Counts triangles per node; prerequisite for LCC |
| Local Clustering Coefficient | `gds.localClusteringCoefficient` | Community | Ratio of closed triangles |
| K-Means | `gds.kmeans` | Community | Requires node embedding properties as input |
| HDBSCAN | `gds.hdbscan` | Community | Density-based; finds variable-density communities |

### WCC parameters
| Parameter | Notes |
|---|---|
| `threshold` | Only traverse rels with weight >= threshold |
| `minComponentSize` | Only return nodes in components >= N nodes |

---

## Similarity

| Algorithm | Procedure | Tier | Input | Notes |
|---|---|---|---|---|
| KNN | `gds.knn` | Community | Node properties (Float[]) | Cosine/Euclidean/Pearson auto-selected for Float[] |
| Node Similarity | `gds.nodeSimilarity` | Community | Graph topology | Jaccard from common neighbors; no properties needed |
| Filtered Node Similarity | `gds.nodeSimilarity` | Community | Graph topology | With `sourceNodeFilter`/`targetNodeFilter` |

### KNN — key parameters
| Parameter | Default | Notes |
|---|---|---|
| `nodeProperties` | required | List of Float[] property names |
| `topK` | 10 | Neighbors per node |
| `sampleRate` | 0.5 | Accuracy vs speed; 1.0 = exact |
| `similarityCutoff` | 0.0 | Only return pairs above threshold |
| `writeRelationshipType` | required for write | Relationship type to create |
| `writeProperty` | required for write | Property name for similarity score |

Similarity metric auto-selected by property type: `Float[]` → cosine/Euclidean/Pearson; `Integer[]` → Jaccard/Overlap; scalar → inverse distance.

---

## Path Finding

| Algorithm | Procedure | Tier | Use Case |
|---|---|---|---|
| Dijkstra (single) | `gds.shortestPath.dijkstra` | Community | Shortest path, positive weights |
| Dijkstra (all) | `gds.allShortestPaths.dijkstra` | Community | All shortest from one source |
| A* | `gds.shortestPath.astar` | Community | Spatial graphs with lat/lon heuristic |
| Yen's k-Shortest | `gds.shortestPath.yens` | Community | k alternative shortest paths |
| Bellman-Ford | `gds.bellmanFord` | Community | Graphs with negative weights |
| Random Walk | `gds.randomWalk` | Community | Sample graph neighborhoods |
| BFS | `gds.bfs` | Community | Breadth-first traversal order |
| DFS | `gds.dfs` | Community | Depth-first traversal order |

```cypher
MATCH (source:Location {name: 'A'}), (target:Location {name: 'B'})
CALL gds.shortestPath.dijkstra.stream('myGraph', {
  sourceNode: source, targetNode: target,
  relationshipWeightProperty: 'distance'
})
YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
RETURN totalCost, [nodeId IN nodeIds | gds.util.asNode(nodeId).name] AS nodes
```

---

## Node Embeddings

| Algorithm | Procedure | Tier | Inductive? | Best For |
|---|---|---|---|---|
| FastRP | `gds.fastRP` | Community | Yes (with `randomSeed`) | Fast, scalable, production ML |
| GraphSAGE | `gds.graphSage` | Community | Yes | Feature-rich nodes; generalizes to unseen nodes |
| Node2Vec | `gds.node2vec` | Community | No (transductive) | Structural similarity; same graph train+predict |
| HashGNN | `gds.hashgnn` | Community | Yes | GNN-style, limited compute, fast |

### FastRP — key parameters
| Parameter | Default | Notes |
|---|---|---|
| `embeddingDimension` | required | 128–512 typical |
| `iterationWeights` | `[0.0, 1.0, 1.0]` | `[self, 1-hop, 2-hop]` neighborhood weights |
| `featureProperties` | `[]` | Node properties to incorporate |
| `propertyRatio` | 0.0 | Fraction of dims for node properties (requires `featureProperties`) |
| `normalizationStrength` | 0.0 | Negative = downplay high-degree hubs |
| `randomSeed` | — | Set for reproducibility |

### Node2Vec — key parameters
| Parameter | Default | Notes |
|---|---|---|
| `embeddingDimension` | 128 | |
| `walkLength` | 80 | Steps per random walk |
| `walksPerNode` | 10 | Random walks per node |
| `inOutFactor` | 1.0 | DFS bias (>1) vs BFS bias (<1) |
| `returnFactor` | 1.0 | Probability of returning to previous node |

---

## ML Pipelines

### Node Classification

```python
pipe, _ = gds.nc_pipe("myPipeline")
pipe.addNodeProperty("fastRP", mutateProperty="emb", embeddingDimension=128, randomSeed=42)
pipe.selectFeatures("emb")
pipe.addLogisticRegression(maxEpochs=100)

model, train_result = pipe.train(G, targetProperty="label", metrics=["ACCURACY"])
predictions = model.predict_stream(G)
model.predict_write(G, writeProperty="predicted_label")
```

### Link Prediction

```python
pipe, _ = gds.lp_pipe("lpPipeline")
pipe.addNodeProperty("fastRP", mutateProperty="emb", embeddingDimension=128, randomSeed=42)
pipe.addFeature("hadamard", nodeProperties=["emb"])
pipe.addLogisticRegression(maxEpochs=100)

model, result = pipe.train(G, sourceNodeLabel="Person", targetNodeLabel="Person",
                            targetRelationshipType="KNOWS", metrics=["AUCPR"])
model.predict_stream(G, topN=10, threshold=0.5)
```

---

## Built-in Test Datasets

```python
G = gds.graph.load_cora()         # 2,708 Paper nodes, 5,429 CITES edges
G = gds.graph.load_karate_club()  # 34 Person nodes, 78 KNOWS edges
G = gds.graph.load_imdb()         # 12,772 nodes, heterogeneous
G = gds.graph.load_lastfm()       # 19,914 nodes, user-artist graph
```

---

## Listing Available Procedures

```cypher
CALL gds.list() YIELD name, description
RETURN name ORDER BY name
```

Verify which algorithms are available on the current GDS installation and license tier.
