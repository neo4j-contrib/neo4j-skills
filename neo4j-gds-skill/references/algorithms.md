# GDS Algorithm Reference

Core catalog of commonly used GDS procedures. Mode availability varies by algorithm; check `CALL gds.list()` or the algorithm syntax page before assuming `stream` / `stats` / `mutate` / `write`.

Python client: prefer `gds.v2.*` endpoints and snake_case parameters. Procedure tables show Cypher procedure names.

## Centrality

| Algorithm | Procedure | Best For |
|---|---|---|
| PageRank | `gds.pageRank` | Network influence via incoming links |
| Betweenness Centrality | `gds.betweenness` | Bottleneck/bridge nodes |
| Degree Centrality | `gds.degree` | Most-connected nodes (fast) |
| ArticleRank | `gds.articleRank` | PageRank variant dampening high-degree nodes |
| Eigenvector | `gds.eigenvector` | Influence via well-connected neighbors |
| Closeness | `gds.closeness` | Average distance to all other nodes |
| HITS | `gds.hits` | Authority/hub scores (web-like graphs) |

### PageRank — key parameters
| V2 parameter | Cypher/v1 parameter | Default | Notes |
|---|---|---|---|
| `damping_factor` | `dampingFactor` | 0.85 | Probability of following a link; lower = more teleportation |
| `max_iterations` | `maxIterations` | 20 | |
| `tolerance` | `tolerance` | 1e-7 | Convergence threshold |
| `relationship_weight_property` | `relationshipWeightProperty` | — | Optional weight property |

Spider traps (closed groups, no outlinks) inflate scores — increase `dampingFactor`. Negative weights silently ignored.

---

## Community Detection

| Algorithm | Procedure | Notes |
|---|---|---|
| Louvain | `gds.louvain` | Best general-purpose; modularity maximization |
| Leiden | `gds.leiden` | Refinement of Louvain; avoids poorly connected communities |
| WCC | `gds.wcc` | Weakly connected components; run first to partition graph |
| SCC | `gds.scc` | Strongly connected components (directed graphs only) |
| Label Propagation | `gds.labelPropagation` | Fast, large graphs; non-deterministic |
| K-Core Decomposition | `gds.kcore` | Dense subgraphs by degree threshold |
| Triangle Count | `gds.triangleCount` | Counts triangles per node; prerequisite for LCC |
| Local Clustering Coefficient | `gds.localClusteringCoefficient` | Ratio of closed triangles |
| K-Means | `gds.kmeans` | Requires node embedding properties as input |
| HDBSCAN | `gds.hdbscan` | Density-based; finds variable-density communities |

### WCC parameters
| Parameter | Notes |
|---|---|
| `threshold` | Only traverse rels with weight >= threshold |
| `min_component_size` / `minComponentSize` | Only return nodes in components >= N nodes |

---

## Similarity

| Algorithm | Procedure | Input | Notes |
|---|---|---|---|
| KNN | `gds.knn` | Node properties | Defaults metric by type; override with `{embedding: 'COSINE'}` |
| Node Similarity | `gds.nodeSimilarity` | Bipartite graph topology | Jaccard / Overlap / Cosine from common neighbors; no node properties needed |
| Filtered Node Similarity | `gds.nodeSimilarity` | Bipartite graph topology | With `sourceNodeFilter`/`targetNodeFilter` |

### KNN — key parameters
| V2 parameter | Cypher/v1 parameter | Default | Notes |
|---|---|---|---|
| `node_properties` | `nodeProperties` | required | String, map, or list of strings/maps |
| `top_k` | `topK` | 10 | Neighbors per node |
| `sample_rate` | `sampleRate` | 0.5 | Accuracy vs speed; 1.0 = exact |
| `similarity_cutoff` | `similarityCutoff` | 0.0 | Only return pairs above threshold |
| `write_relationship_type` | `writeRelationshipType` | required for write | Relationship type to create |
| `write_property` | `writeProperty` | required for write | Property name for similarity score |
| `mutate_relationship_type` | `mutateRelationshipType` | required for mutate | Relationship type to add to in-memory graph |
| `mutate_property` | `mutateProperty` | required for mutate | Relationship property for similarity score |

Available metrics by property type: `Float[]` → `COSINE`, `EUCLIDEAN`, `PEARSON`; `Integer[]` → `JACCARD`, `OVERLAP`; scalar numbers → default inverse distance metric only.

---

## Path Finding

| Algorithm | Procedure | Use Case |
|---|---|---|
| Dijkstra source-target | `gds.shortestPath.dijkstra` | Shortest path, positive weights |
| Dijkstra single-source | `gds.allShortestPaths.dijkstra` | All shortest paths from one source |
| A* | `gds.shortestPath.astar` | Spatial graphs with lat/lon heuristic |
| Yen's k-Shortest | `gds.shortestPath.yens` | k alternative shortest paths |
| Bellman-Ford | `gds.bellmanFord` | Graphs with negative weights |
| Random Walk | `gds.randomWalk` | Sample graph neighborhoods |
| BFS | `gds.bfs` | Breadth-first traversal order |
| DFS | `gds.dfs` | Depth-first traversal order |

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

| Algorithm | Procedure | Inductive? | Best For |
|---|---|---|---|
| FastRP | `gds.fastRP` | Yes (set `randomSeed` for reproducibility) | Fast, scalable, production ML |
| GraphSAGE | `gds.beta.graphSage` | Yes | Feature-rich nodes; generalizes to unseen nodes |
| Node2Vec | `gds.node2vec` | No (transductive) | Structural similarity; same graph train+predict |
| HashGNN | `gds.hashgnn` | Yes | GNN-style, limited compute, fast |

### FastRP — key parameters
| V2 parameter | Cypher/v1 parameter | Default | Notes |
|---|---|---|---|
| `embedding_dimension` | `embeddingDimension` | required | 128–512 typical |
| `iteration_weights` | `iterationWeights` | `[0.0, 1.0, 1.0]` | `[self, 1-hop, 2-hop]` neighborhood weights |
| `feature_properties` | `featureProperties` | `[]` | Node properties to incorporate |
| `property_ratio` | `propertyRatio` | 0.0 | Fraction of dims for node properties (requires `feature_properties`) |
| `normalization_strength` | `normalizationStrength` | 0.0 | Negative = downplay high-degree hubs |
| `random_seed` | `randomSeed` | — | Set for reproducibility |

### Node2Vec — key parameters
| V2 parameter | Cypher/v1 parameter | Default | Notes |
|---|---|---|---|
| `embedding_dimension` | `embeddingDimension` | 128 | |
| `walk_length` | `walkLength` | 80 | Steps per random walk |
| `walks_per_node` | `walksPerNode` | 10 | Random walks per node |
| `in_out_factor` | `inOutFactor` | 1.0 | DFS bias (>1) vs BFS bias (<1) |
| `return_factor` | `returnFactor` | 1.0 | Probability of returning to previous node |

---

## ML Pipelines

Pipeline APIs may lag v2 coverage. Prefer v2 pipeline endpoints when available; otherwise use v1 fallback and keep camelCase parameters.

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
G = gds.v2.graph.datasets.load_cora()         # 2,708 Paper nodes, 5,429 CITES edges
G = gds.v2.graph.datasets.load_karate_club()  # 34 Person nodes, 78 KNOWS edges
G = gds.v2.graph.datasets.load_imdb()         # 12,772 nodes, heterogeneous
G = gds.v2.graph.datasets.load_lastfm()       # 19,914 nodes, user-artist graph
```

---

## Listing Available Procedures

```cypher
CALL gds.list() YIELD name, description
RETURN name ORDER BY name
```

Verify which algorithms are available on the current GDS installation and license tier.
