# GDS Algorithm Reference

Core catalog of commonly used GDS procedures. Mode availability varies by algorithm; check `CALL gds.list()` or the algorithm syntax page before assuming `stream` / `stats` / `mutate` / `write`.

Python client 2.0: plain endpoints (no `v2` prefix) and snake_case parameters. Procedure tables show Cypher procedure names. Client 1.x (GDS server < 2.13): prefix with `gds.v2.`.

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
| Client parameter | Cypher parameter | Default | Notes |
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
| K-Means | `gds.kmeans` | Requires node embedding properties as input; `computeSilhouette` + `numberOfRestarts` together fail before GDS 2026.08.1 |
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
| Client parameter | Cypher parameter | Default | Notes |
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
| Client parameter | Cypher parameter | Default | Notes |
|---|---|---|---|
| `embedding_dimension` | `embeddingDimension` | required | 128–512 typical |
| `iteration_weights` | `iterationWeights` | `[0.0, 1.0, 1.0]` | `[self, 1-hop, 2-hop]` neighborhood weights |
| `feature_properties` | `featureProperties` | `[]` | Node properties to incorporate |
| `property_ratio` | `propertyRatio` | 0.0 | Fraction of dims for node properties (requires `feature_properties`) |
| `normalization_strength` | `normalizationStrength` | 0.0 | Negative = downplay high-degree hubs |
| `random_seed` | `randomSeed` | — | Set for reproducibility |

### Node2Vec — key parameters
| Client parameter | Cypher parameter | Default | Notes |
|---|---|---|---|
| `embedding_dimension` | `embeddingDimension` | 128 | |
| `walk_length` | `walkLength` | 80 | Steps per random walk |
| `walks_per_node` | `walksPerNode` | 10 | Random walks per node |
| `in_out_factor` | `inOutFactor` | 1.0 | DFS bias (>1) vs BFS bias (<1) |
| `return_factor` | `returnFactor` | 1.0 | Probability of returning to previous node |

---

## ML Pipelines

Pipelines: `gds.pipeline.node_classification` / `link_prediction` / `node_regression` — the only API in client 2.0. Get pipelines: `gds.pipeline.node_classification.get(name)`; trained models: `gds.pipeline.node_classification.get_model(name)`.

### Node Classification

```python
pipe, _ = gds.pipeline.node_classification.create("myPipeline")
pipe.add_node_property("fastRP", mutate_property="emb", embedding_dimension=128, random_seed=42)
pipe.select_features("emb")
pipe.add_logistic_regression(max_epochs=100)

model, train_result = pipe.train(G, target_property="label", metrics=["ACCURACY"])
predictions = model.predict_stream(G)
model.predict_write(G, write_property="predicted_label")
```

### Link Prediction

```python
pipe, _ = gds.pipeline.link_prediction.create("lpPipeline")
pipe.add_node_property("fastRP", mutate_property="emb", embedding_dimension=128, random_seed=42)
pipe.add_feature("hadamard", node_properties=["emb"])
pipe.add_logistic_regression(max_epochs=100)

model, result = pipe.train(G, source_node_label="Person", target_node_label="Person",
                           target_relationship_type="KNOWS", metrics=["AUCPR"])
model.predict_stream(G, top_n=10, threshold=0.5)
```

---

## Built-in Test Datasets

```python
G = gds.graph.datasets.load_cora()         # 2,708 Paper nodes, 5,429 CITES edges
G = gds.graph.datasets.load_karate_club()  # 34 Person nodes, 78 KNOWS edges
G = gds.graph.datasets.load_imdb()         # 12,772 nodes, heterogeneous
G = gds.graph.datasets.load_lastfm()       # 19,914 nodes, user-artist graph
```

---

## Listing Available Procedures

```cypher
CALL gds.list() YIELD name, description
RETURN name ORDER BY name
```

Verify which algorithms are available on the current GDS installation and license tier.
