# Algorithm Parameter Reference

Compute and write configuration for all Neo4j Graph Analytics for Snowflake algorithms. Every algorithm shares the same `project` config structure (see SKILL.md). Only algorithm-specific `compute` and `write` parameters listed here.

---

## Community Detection

### WCC (`wcc`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resultProperty` | String | `'component'` | Node property written back |
| `relationshipWeightProperty` | String | null | Relationship property for weights |
| `seedProperty` | String | null | Initial component assignment (numeric) |
| `threshold` | Float | null | Only traverse rels with weight > threshold |
| `consecutiveIds` | Boolean | false | Map component IDs to consecutive integers |

**Write:** `nodeLabel`, `nodeProperty` (default `'component'`), `outputTable`

---

### Louvain (`louvain`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resultProperty` | String | `'community'` | Node property written back |
| `relationshipWeightProperty` | String | null | Relationship property for weights |
| `seedProperty` | String | null | Initial community assignment (non-negative) |
| `maxLevels` | Integer | 10 | Max hierarchical clustering levels |
| `maxIterations` | Integer | 10 | Max modularity optimization iterations per level |
| `tolerance` | Float | 0.0001 | Min modularity change to continue |
| `includeIntermediateCommunities` | Boolean | false | Write intermediate community assignments |
| `consecutiveIds` | Boolean | false | Map to consecutive IDs (incompatible with `includeIntermediateCommunities`) |

**Write:** `nodeLabel`, `nodeProperty` (default `'community'`), `outputTable`

---

### Leiden (`leiden`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resultProperty` | String | `'community'` | Node property written back |
| `relationshipWeightProperty` | String | null | Relationship property for weights |
| `seedProperty` | String | null | Initial community (non-negative) |
| `maxLevels` | Integer | 10 | Max hierarchical levels |
| `tolerance` | Float | 0.0001 | Min modularity change to continue |
| `includeIntermediateCommunities` | Boolean | false | Write intermediate communities |
| `gamma` | Float | 1.0 | Resolution parameter — higher → more communities |
| `theta` | Float | 0.01 | Randomness when splitting communities |

**Write:** `nodeLabel`, `nodeProperty` (default `'community'`), `outputTable`

---

### Label Propagation (`label_propagation`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resultProperty` | String | `'community'` | Node property written back |
| `nodeWeightProperty` | String | null | Node property for node weights |
| `relationshipWeightProperty` | String | null | Relationship property for weights |
| `seedProperty` | String | null | Initial community (non-negative) |
| `maxIterations` | Integer | 10 | Max iterations |

**Write:** `nodeLabel`, `nodeProperty` (default `'community'`), `outputTable`

---

### K-Means (`kmeans`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resultProperty` | String | `'community'` | Node property written back |
| `nodeProperty` | String | *required* | Numeric array property to cluster on |
| `k` | Integer | 10 | Number of clusters |
| `maxIterations` | Integer | 10 | Max iterations |
| `deltaThreshold` | Float | 0.05 | Convergence threshold (% change) |
| `numberOfRestarts` | Integer | 1 | Runs with different initializations; keeps best |
| `randomSeed` | Integer | — | Seed for reproducibility |
| `computeSilhouette` | Boolean | false | Compute silhouette score (adds overhead) |
| `seedCentroids` | List | — | Initial centroids; `k` must match list length |

**Write:** `nodeLabel`, `nodeProperty` (default `'community'`), `outputTable`

---

### Triangle Count (`triangle_count`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resultProperty` | String | `'triangles'` | Node property written back |
| `relationshipWeightProperty` | String | null | Relationship property for weights |
| `maxDegree` | Integer | 2^63-1 | Max degree to consider (higher → excluded, assigned -1) |
| `labelFilter` | List of String | [] | Up to 3 node labels; only count triangles with these |

**Write:** `nodeLabel`, `nodeProperty` (default `'triangles'`), `outputTable`

**Note:** Only finds triangles in undirected graphs — project relationships with `UNDIRECTED` orientation.

---

## Centrality

### PageRank (`page_rank`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resultProperty` | String | `'pageRank'` | Node property written back |
| `dampingFactor` | Float | 0.85 | Probability of following a link; must be in [0, 1) |
| `maxIterations` | Integer | 20 | Max iterations |
| `tolerance` | Float | 1e-7 | Convergence threshold |
| `relationshipWeightProperty` | String | null | Relationship property for weights |
| `sourceNodes` | List | [] | Nodes/IDs for Personalized PageRank; supports `[[id, bias], ...]` |
| `sourceNodesTable` | String | null | Table containing source nodes (required when `sourceNodes` specified) |
| `scaler` | String or Map | None | Score normalization: `MinMax`, `Max`, `Mean`, `Log`, `StdScore`, `L1Norm`, `L2Norm` |

**Write:** `nodeLabel`, `nodeProperty` (default `'pageRank'`), `outputTable`

---

### Article Rank (`article_rank`)

**Compute:** Same parameters as PageRank but with `resultProperty` default `'articleRank'`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resultProperty` | String | `'articleRank'` | Node property written back |
| `dampingFactor` | Float | 0.85 | Must be in [0, 1) |
| `maxIterations` | Integer | 20 | Max iterations |
| `tolerance` | Float | 1e-7 | Convergence threshold |
| `relationshipWeightProperty` | String | null | Relationship property for weights |
| `sourceNodes` | List | [] | For Personalized Article Rank |
| `sourceNodesTable` | String | null | Required when `sourceNodes` specified |
| `scaler` | String or Map | None | Score normalization |

**Write:** `nodeLabel`, `nodeProperty` (default `'articleRank'`), `outputTable`

---

### Betweenness Centrality (`betweenness`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resultProperty` | String | `'betweenness'` | Node property written back |
| `samplingSize` | Integer | node count | Number of source nodes to sample |
| `samplingSeed` | Integer | null | Seed for random source selection |
| `relationshipWeightProperty` | String | null | Relationship property for weights |

**Write:** `nodeLabel`, `nodeProperty` (default `'betweenness'`), `outputTable`

---

### Degree Centrality (`degree`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resultProperty` | String | `'degree'` | Node property written back |
| `relationshipWeightProperty` | String | null | Relationship property for weights |
| `orientation` | String | `'NATURAL'` | `NATURAL`, `REVERSE`, or `UNDIRECTED` |

**Write:** `nodeLabel`, `nodeProperty` (default `'degree'`), `outputTable`

---

## Pathfinding

### Dijkstra Source-Target (`dijkstra`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sourceNode` | Integer/String | *required^1^* | Source node identifier |
| `sourceNodeTable` | String | *required^1^* | Table for mapping source node |
| `targetNode` | Integer/String | *required^1^* | Target node identifier |
| `targetNodeTable` | String | *required^1^* | Table for mapping target node |
| `targetNodes` | List | *required^1^* | Multiple target node IDs |
| `targetNodesTable` | String | *required^1^* | Table for mapping target nodes |
| `sourceTargetNodePairsTable` | String | *required^1^* | Table with `SOURCENODEID`/`TARGETNODEID` columns |
| `resultProperty` | String | `'total_cost'` | Relationship property written back |
| `resultRelationshipType` | String | `'PATH'` | Relationship type written back |
| `relationshipWeightProperty` | String | null | Relationship property for weights |

^1^ Specify one of: (a) `sourceNode`+`sourceNodeTable`+`targetNode`+`targetNodeTable`, (b) `sourceNode`+`sourceNodeTable`+`targetNodes`+`targetNodesTable`, or (c) `sourceTargetNodePairsTable`+`sourceNodeTable`+`targetNodeTable`.

**Write:** `sourceLabel`, `targetLabel`, `outputTable`, `relationshipType` (default `'PATH'`), `relationshipProperty` (default `'total_cost'`)

---

### Dijkstra Single-Source (`dijkstra_single_source`)

Shortest paths from one source node to all reachable nodes.

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sourceNode` | Integer/String | *required* | Source node identifier |
| `sourceNodeTable` | String | *required* | Table for mapping the source node |
| `resultProperty` | String | `'total_cost'` | Relationship property written back |
| `resultRelationshipType` | String | `'PATH'` | Relationship type written back |
| `relationshipWeightProperty` | String | null | Relationship property for weights (unweighted if unset) |

**Write:** `sourceLabel`, `targetLabel`, `outputTable`, `relationshipType` (default `'PATH'`), `relationshipProperty` (default `'total_cost'`)

---

### Delta-Stepping SSSP (`delta_stepping`)

Parallel single-source shortest paths (positive weights only).

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sourceNode` | Integer/String | *required* | Source node identifier |
| `sourceNodeTable` | String | *required* | Table for mapping the source node |
| `delta` | Float | 2.0 | Bucket width grouping nodes by tentative distance. Small (~2) for power-law graphs; large (~10000) for high-diameter graphs (e.g. transport) |
| `resultProperty` | String | `'total_cost'` | Relationship property written back |
| `resultRelationshipType` | String | `'PATH'` | Relationship type written back |
| `relationshipWeightProperty` | String | null | Relationship property for weights |

**Write:** `sourceLabel`, `targetLabel`, `outputTable`, `relationshipType` (default `'PATH'`), `relationshipProperty` (default `'total_cost'`)

**Note:** With multiple shortest paths of equal cost, the returned path may differ between runs.

---

### Breadth First Search (`bfs`)

Traversal from a source node, optionally stopping at target nodes.

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sourceNode` | Integer/String | *required* | Node where traversal starts |
| `sourceNodeTable` | String | *required* | Node table containing `sourceNode` in its `NODEID` |
| `targetNodes` | List | `[]` | Target node IDs; traversal stops when any is reached |
| `targetNodesTable` | String | null | Node table containing `targetNodes` (optional if `targetNodes` empty) |
| `maxDepth` | Integer | -1 | Max distance from source to visit; -1 = unbounded |
| `resultRelationshipType` | String | `'NEXT'` | Relationship type written back |

**Write:** `outputTable`, `relationshipType` (default `'NEXT'`)

**Note:** Output is written in heterogeneous form — the table has `SOURCENODEID`, `TARGETNODEID`, `SOURCELABEL`, `TARGETLABEL` (node IDs as strings). Each row is one link `source → target` of consecutive nodes on the BFS path; row order does not necessarily match visitation order, and links may include back-tracking jumps that aren't original relationships.

---

### Yen's K-Shortest Paths (`yens`)

Top-K shortest loopless paths between a source and target node.

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sourceNode` | Integer/String | *required* | Source node identifier |
| `sourceNodeTable` | String | *required* | Table for mapping the source node |
| `targetNode` | Integer/String | *required* | Target node identifier |
| `targetNodeTable` | String | *required* | Table for mapping the target node |
| `k` | Integer | *required* | Number of shortest paths to compute |
| `resultProperty` | String | `'total_cost'` | Relationship property written back |
| `resultRelationshipType` | String | `'PATH'` | Relationship type written back |
| `relationshipWeightProperty` | String | null | Relationship property for weights |

**Write:** `sourceLabel`, `targetLabel`, `outputTable`, `relationshipType` (default `'PATH'`), `relationshipProperty` (default `'total_cost'`)

**Note:** With `k=1` behaves like Dijkstra Source-Target. Respects parallel relationships between the same node pair.

---

### Max Flow (`max_flow`)

Maximum flow from source(s) to target(s) under relationship capacities.

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sourceNodes` | List/String/Integer | *required* | Source node(s) flow originates from |
| `sourceNodesTable` | String | *required* | Table containing the source nodes |
| `targetNodes` | List/String/Integer | *required* | Target node(s) flow is deposited to |
| `targetNodesTable` | String | *required* | Table for mapping the target nodes |
| `capacityProperty` | String | *required* | Relationship property to use as capacity |
| `nodeCapacityProperty` | String | null | Node property limiting total flow through a node (omit for unrestricted nodes) |
| `resultProperty` | String | `'flow'` | Relationship property written back |
| `resultRelationshipType` | String | `'FLOW_RELATIONSHIP'` | Relationship type written back |

**Write:** `sourceLabel`, `targetLabel`, `outputTable`, `relationshipType` (default `'FLOW_RELATIONSHIP'`), `relationshipProperty` (default `'flow'`)

---

### Min-Cost Max Flow (`max_flow_min_cost`)

Maximum flow that minimises total cost. Same parameters as Max Flow plus cost.

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sourceNodes` | List/String/Integer | *required* | Source node(s) |
| `sourceNodesTable` | String | *required* | Table containing the source nodes |
| `targetNodes` | List/String/Integer | *required* | Target node(s) |
| `targetNodesTable` | String | *required* | Table for mapping the target nodes |
| `capacityProperty` | String | *required* | Relationship property to use as capacity |
| `costProperty` | String | *required* | Relationship property to use as per-unit cost |
| `nodeCapacityProperty` | String | null | Node property limiting total flow through a node |
| `alpha` | Integer | 6 | Cost-scaling rate in the refinement phase; tuning can improve speed |
| `resultProperty` | String | `'flow'` | Relationship property written back |
| `resultRelationshipType` | String | `'FLOW_RELATIONSHIP'` | Relationship type written back |

**Write:** `sourceLabel`, `targetLabel`, `outputTable`, `relationshipType` (default `'FLOW_RELATIONSHIP'`), `relationshipProperty` (default `'flow'`)

**Note:** Optimal solution guaranteed for integer costs/capacities; also runs with double values within the same bounds.

---

### FastPath (`fastpath`)

Temporal node embeddings over base nodes and their related events. Produces a `VECTOR` embedding per base node.

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `baseNodeLabel` | String | *required* | Node label for which embeddings are produced |
| `eventNodeLabel` | String | *required* | Node label of events related to base nodes |
| `contextNodeLabel` | String | None | Node label of context nodes describing events |
| `timeNodeProperty` | String | None | Node property representing time on event nodes (int or float) |
| `nextRelationshipType` | String | None | Relationship type between event nodes indicating event order |
| `firstRelationshipType` | String | None | Relationship type from base node to its first event |
| `eventFeatures` | String | None | Node property on event nodes holding numerical features (vector form) |
| `categoricalEventProperties` | List of String | None | Event node properties holding categorical value(s) |
| `ignoredEventCategory` | Integer | -1 | Category value treated as missing and ignored |
| `outputTime` | Float | None | Timestamp at which embeddings are produced; events at/after this are not processed |
| `outputTimeProperty` | String | None | Base-node property giving a per-node output timestamp |
| `numElapsedTimes` | Integer | *required* | Number of times in the elapsed-time grid; 1 means event timestamps have no effect |
| `decayFactor` | Float | 1.0 | Speed of decay of influence of older events |
| `maxElapsedTime` | Integer | *required* | Max age of events (relative to output time) considered |
| `smoothingWindow` | Integer | 0 | Aggregate event embeddings over up to `2*smoothingWindow + 1` grid times |
| `smoothingRate` | Float | 0.0 | How fast expected event similarity decays with time-distance |
| `dimension` | Integer | *required* | Output embedding dimension |
| `randomSeed` | Integer | random | Seed for all randomness |
| `resultProperty` | String | `'embedding'` | Node property written back |

**Write:** `nodeLabel`, `outputTable`

**Note:** Two supported schemas — path-based (`firstRelationshipType` + `nextRelationshipType`) or direct base→event relationships. Equivariant over time (shifting all events and output time by a constant leaves embeddings unchanged).

---

## Similarity

### Node Similarity (`node_similarity`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resultProperty` | String | `'similarity'` | Relationship property written back |
| `resultRelationshipType` | String | `'SIMILAR_TO'` | Relationship type written back |
| `similarityCutoff` | Float | 1e-42 | Min similarity score to include (0–1) |
| `degreeCutoff` | Integer | 1 | Min node degree to be compared |
| `upperDegreeCutoff` | Integer | 2147483647 | Max node degree to be compared |
| `topK` | Integer | 10 | K most similar per node |
| `bottomK` | Integer | 10 | K least similar per node |
| `topN` | Integer | 0 | Global N most similar total (0 = no limit) |
| `bottomN` | Integer | 0 | Global N least similar total (0 = no limit) |
| `relationshipWeightProperty` | String | null | Relationship property for weights |
| `similarityMetric` | String | `'JACCARD'` | `JACCARD`, `OVERLAP`, or `COSINE` |
| `useComponents` | Boolean/String | false | Use components to skip cross-component comparisons |

**Write:** `sourceLabel`, `targetLabel`, `outputTable`, `relationshipType` (default `'SIMILAR_TO'`), `relationshipProperty` (default `'similarity'`)

**Note:** Input must be bipartite — two node sets connected by relationships. Use `NATURAL` orientation so algorithm knows source vs target side.

---

### Filtered Node Similarity (`node_similarity_filtered`)

Node Similarity restricted to chosen source/target nodes. All `node_similarity` compute parameters apply, plus the filters below.

**Additional compute parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sourceNodeFilter` | String/List | null | Node label, list of labels, single node ID, or list of IDs to use as sources |
| `sourceNodeTable` | String | null | Table for mapping source node IDs (required when filtering by ID) |
| `targetNodeFilter` | String/List | null | Node label, list of labels, single node ID, or list of IDs to use as targets |
| `targetNodeTable` | String | null | Table for mapping target node IDs (required when filtering by ID) |

**Write:** same as Node Similarity (`sourceLabel`, `targetLabel`, `outputTable`, `relationshipType` default `'SIMILAR_TO'`, `relationshipProperty` default `'similarity'`)

---

### KNN (`knn`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resultProperty` | String | `'similarity'` | Relationship property written back |
| `resultRelationshipType` | String | `'SIMILAR_TO'` | Relationship type written back |
| `nodeProperties` | String/Map/List | *required* | Node properties + metrics for similarity |
| `topK` | Integer | 10 | Neighbors per node |
| `sampleRate` | Float | 0.5 | Comparison sampling rate (0, 1] |
| `deltaThreshold` | Float | 0.001 | Early stopping threshold (% updates) |
| `maxIterations` | Integer | 100 | Hard iteration limit |
| `randomJoins` | Integer | 10 | Random connection attempts per node per iteration |
| `initialSampler` | String | `'uniform'` | `uniform` or `randomWalk` |
| `randomSeed` | Integer | — | Seed (requires concurrency=1) |
| `similarityCutoff` | Float | 0 | Min similarity to include |
| `perturbationRate` | Float | 0 | Probability of replacing equal-similarity neighbor |

**Available metrics by property type:**

| Property type | Metrics |
|---|---|
| List of Integer | `JACCARD`, `OVERLAP` |
| List of Float | `COSINE`, `EUCLIDEAN`, `PEARSON` |
| Scalar number | default only (inverse absolute difference) |

**Write:** `sourceLabel`, `targetLabel`, `outputTable`, `relationshipType` (default `'SIMILAR_TO'`), `relationshipProperty` (default `'similarity'`)

---

### Filtered KNN (`knn_filtered`)

KNN restricted to chosen source/target nodes. All `knn` compute parameters apply (including the `nodeProperties` metrics-by-type table), plus the filters below.

**Additional compute parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sourceNodeFilter` | String/List | — | Node label or list of node IDs to use as sources |
| `sourceNodeTable` | String | — | Fully-qualified table for source node ID filtering |
| `targetNodeFilter` | String/List | — | Node label or list of node IDs to use as targets |
| `targetNodeTable` | String | — | Fully-qualified table for target node ID filtering |
| `seedTargetNodes` | Boolean | false | Guarantee `topK` results per source by seeding; overrides `similarityCutoff` |

**Write:** same as KNN (`sourceLabel`, `targetLabel`, `outputTable`, `relationshipType` default `'SIMILAR_TO'`, `relationshipProperty` default `'similarity'`)

---

## Node Embeddings

### FastRP (`fast_rp`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resultProperty` | String | `'fast_rp'` | Node property written back |
| `embeddingDimension` | Integer | *required* | Dimension of output embeddings (min 1) |
| `iterationWeights` | List of Float | [0.0, 1.0, 1.0] | Weight per iteration; list length = number of iterations |
| `nodeSelfInfluence` | Float | 0.0 | How much a node's initial vector influences its own embedding |
| `normalizationStrength` | Float | 0.0 | Degree-based scaling of initial vectors |
| `propertyRatio` | Float | 0.0 | Ratio of embedding for property features (needs `featureProperties`) |
| `featureProperties` | List of String | [] | Node properties as input features (Float or List of Float) |
| `relationshipWeightProperty` | String | null | Relationship property for weights |
| `randomSeed` | Integer | — | Seed for reproducibility |

Requires either non-empty `iterationWeights` or non-zero `nodeSelfInfluence`.

**Write:** `nodeLabel`, `nodeProperty` (default `'fast_rp'`), `outputTable`

---

### Node2Vec (`node2vec`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `embeddingDimension` | Integer | 128 | Size of output embeddings |
| `walkLength` | Integer | 80 | Steps per random walk |
| `walksPerNode` | Integer | 10 | Random walks per node |
| `inOutFactor` | Float | 1.0 | Higher → stay local |
| `returnFactor` | Float | 1.0 | Below 1.0 → higher return tendency |
| `relationshipWeightProperty` | String | null | Relationship property for walk probabilities (≥0) |
| `windowSize` | Integer | 10 | Context window for neural network training |
| `negativeSamplingRate` | Integer | 5 | Negative samples per positive sample |
| `positiveSamplingFactor` | Float | 0.001 | Down-sample frequent nodes |
| `negativeSamplingExponent` | Float | 0.75 | Exponent for negative sampling distribution |
| `embeddingInitializer` | String | `'NORMALIZED'` | `NORMALIZED` or `UNIFORM` |
| `iterations` | Integer | 1 | Training iterations |
| `initialLearningRate` | Float | 0.01 | Starting learning rate |
| `minLearningRate` | Float | 0.0001 | Learning rate floor |
| `randomSeed` | Integer | — | Seed for walks (embeddings still nondeterministic) |
| `walkBufferSize` | Integer | 1000 | Walks to complete before training starts |

**Write:** `nodeLabel`, `nodeProperty` (default `'node2vec'`), `outputTable`

---

### HashGNN (`hashgnn`)

**Compute:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `featureProperties` | List of String | [] | Node properties as input (Float or List of Float) |
| `iterations` | Integer | *required* | Number of hashing iterations (≥1) |
| `embeddingDensity` | Integer | *required* | Features sampled per node per iteration (`K` in paper; ≥1) |
| `heterogeneous` | Boolean | false | Distinguish relationship types |
| `neighborInfluence` | Float | 1.0 | How often neighbors' features are sampled vs own (≥0) |
| `binarizeFeatures` | Map | — | `{dimension: N, threshold: T}` for hyperplane rounding |
| `generateFeatures` | Map | — | `{dimension: N, densityLevel: D}` — use when no `featureProperties` |
| `outputDimension` | Integer | — | Dense projection of binary output |
| `randomSeed` | Integer | — | Seed for reproducibility |

**Write:** `nodeLabel`, `nodeProperty` (default `'hashgnn'`), `outputTable`

---

## GraphSAGE (Graph ML)

GraphSAGE trains a model in one job, then uses it to predict in a later job. Training writes a **model** (no output table); prediction writes node properties. Training is slow and a GPU pool (`GPU_NV_S`) is strongly recommended unless the dataset is small and the model shallow. Feature columns come from the projected node tables (all non-`NODEID` columns; for `gs_nc_train`, excluding `targetProperty`) and must be non-NULL and finite. Use `VECTOR(FLOAT, n)` rather than `ARRAY` for multi-valued features.

### Shared training compute parameters (`gs_nc_train`, `gs_unsup_train`)

| Parameter | Type | Default | Description |
|---|---|---|---|
| `modelname` | String | *required* | Unique name of the model to train |
| `numEpochs` | Integer | *required* | Number of epochs to train |
| `numSamples` | List of Integer | *required* | Neighbors to sample per layer; list length = number of layers |
| `hiddenChannels` | Integer | 256 | Node embedding dimension of the layer outputs |
| `activation` | String | `"relu"` | Activation function: `"relu"` or `"sigmoid"` |
| `aggregator` | String | `"mean"` | Neighborhood aggregator: `"mean"` or `"max"` |
| `learningRate` | Float | 0.001 | Optimizer learning rate |
| `dropout` | Float | 0.1 | Dropout probability per layer; `>= 0.0` and `< 1.0` |
| `layerNormalization` | Boolean | true | Apply layer normalization between layers |
| `epochsPerCheckpoint` | Integer | `max(numEpochs/10, 1)` | Epochs between saving checkpoints |
| `randomSeed` | Integer | random | Seed for all randomness |

### Node Classification — train (`gs_nc_train`)

Shared parameters above, plus:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `targetLabel` | String | *required* | Node label to train predictions on |
| `targetProperty` | String | *required* | Node property (column) to predict; NULL values mark unlabeled nodes (semi-supervised) |
| `splitRatios` | Map | `{'TRAIN':0.6,'TEST':0.2,'VALID':0.2}` | Train/test/validation split; keys `TRAIN`/`TEST`/`VALID`, values sum to 1.0 |
| `epochsPerVal` | Integer | 0 | Epochs between validation-set evaluation; 0 = never |
| `trainBatchSize` | Integer | auto-inferred | Target nodes per training batch |
| `evalBatchSize` | Integer | = `trainBatchSize` | Batch size for evaluation |
| `classWeights` | Boolean or Map | false | Balance training by class weights; `true` derives from label distribution, or supply a per-class map |

### Unsupervised embeddings — train (`gs_unsup_train`)

Shared parameters above, plus:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `numWalks` | Integer | 10 | Random walks per node |
| `walkDepth` | Integer | 3 | Steps per random walk |
| `negSamplingRatio` | Float | 1.0 | Ratio of negative to positive samples |
| `batchSize` | Integer | auto-inferred | Target nodes per training batch |
| `lossReduction` | String | auto | Loss reduction: `"mean"` or `"sum"` (defaults to `"mean"` if `batchSize` set, else `"sum"`) |

### Predict (`gs_nc_predict`, `gs_unsup_predict`)

Apply a trained model to a projected graph. Most settings are inherited from training, so only `modelname` is needed in `compute`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `modelname` | String | *required* | Name of the trained model to use |
| `batchSize` | Integer | inherited | Target nodes per prediction batch (defaults to the training eval batch size) |
| `randomSeed` | Integer | random | Seed for all randomness |

**Write:** `nodeLabel`, `outputTable`

A GPU pool is recommended for large graphs or deep models, but a CPU pool may suffice otherwise.

### Model catalog

| Procedure | Call | Purpose |
|---|---|---|
| `model_exists` | `CALL Neo4j_Graph_Analytics.graph.model_exists('<modelname>')` | Check whether a model exists |
| `show_models` | `CALL Neo4j_Graph_Analytics.graph.show_models()` | List models |
| `drop_model` | `CALL Neo4j_Graph_Analytics.graph.drop_model('<modelname>')` | Delete a model |
