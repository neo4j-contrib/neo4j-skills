# GDS Graph Projection Reference

## Projection Types — When to Use Each

| Type | Procedure | When |
|---|---|---|
| Cypher | Python: `gds.graph.project.cypher(query)` with `RETURN gds.graph.project` clause inside | Current GDS-doc default; filtering, transformation, computed properties, heterogeneous |
| Native | Python: `gds.graph.project.native(...)` | Simple labels + relationship types; shortest Python-client path |

Prefer native projection. Use Cypher projection for filtering, transformations, computed properties, or heterogeneous projections that native projection cannot express. 1.x client fallbacks: `gds.v2.graph.project(...)`, `gds.graph.cypher.project(query, database=...)`. For Aura Graph Analytics sessions, use `neo4j-aura-graph-analytics-skill`.

---

## Native Projection — Full Syntax

```cypher
CALL gds.graph.project(
  'graphName',
  nodeProjection,      // '*', label string, list of labels, or map with properties
  relationshipProjection  // '*', type string, list of types, or map with orientation/properties
)
YIELD graphName, nodeCount, relationshipCount, projectMillis
```

### Node projection variants

```cypher
// All nodes
'*'

// Single label
'Person'

// Multiple labels (no properties)
['Person', 'City']

// With properties per label
{
  Person: { properties: ['age', 'score'] },
  City:   { properties: { population: { defaultValue: 0 } } }
}
```

`VECTOR`-type properties projectable as node properties [GDS 2026.05].

### Relationship projection variants

```cypher
// All relationships
'*'

// Single type
'KNOWS'

// Multiple types
['KNOWS', 'LIVES_IN']

// With orientation and properties
{
  KNOWS: {
    orientation: 'UNDIRECTED',    // NATURAL (default), UNDIRECTED, REVERSE
    properties: ['weight']
  },
  LIVES_IN: {
    properties: {
      since: { defaultValue: 0 }
    }
  }
}
```

### Orientation options

| Orientation | Effect |
|---|---|
| `NATURAL` | As stored in DB (default) |
| `UNDIRECTED` | Adds reverse direction — doubles relationship count |
| `REVERSE` | Flips direction |

`UNDIRECTED` required: Leiden, Triangle Count, Local Clustering Coefficient, K-Core (fail on NATURAL). Directed required: HITS. `UNDIRECTED` fine: Louvain, WCC, FastRP. `NATURAL` for directed algorithms: PageRank, Betweenness.
Bipartite Node Similarity (e.g. user→item): NATURAL gives user-user pairs, REVERSE gives item-item pairs; UNDIRECTED silently mixes both. KNN uses node properties, not topology.

### Default values

```cypher
// Nodes with missing property get defaultValue 0.0 instead of null
{
  Person: {
    properties: {
      score: { property: 'score', defaultValue: 0.0 }
    }
  }
}
```

Missing node property → projected as NaN; projection does not fail. Algorithms that read the property as a feature (e.g. `fastRP` `featureProperties`) fail: `invalid feature property value NaN`. Set `defaultValue` for optional feature properties.

---

## Python Client — Projection

```python
from graphdatascience import GraphDataScience
gds = GraphDataScience("bolt://localhost:7687", auth=("neo4j", "pw"))

# Simple native projection — plugin/simple client only
G, result = gds.graph.project.native("myGraph", "Person", "KNOWS")
print(result.node_count, result.relationship_count)

# Multi-label, multi-rel, properties
G, result = gds.graph.project.native(
    "myGraph",
    {"Person": {"properties": ["age", "score"]},
     "City":   {"properties": {"population": {"defaultValue": 0}}}},
    {"KNOWS":    {"orientation": "UNDIRECTED", "properties": ["weight"]},
     "LIVES_IN": {"properties": ["since"]}}
)

# 1.x fallback:
G, result = gds.graph.project("myGraph", "Person", "KNOWS")
```

---

## Cypher Projection — Full Pattern

```python
G, result = gds.graph.project.cypher(
    """
    MATCH (source:Person)-[r:KNOWS]->(target:Person)
    WHERE source.active = true AND target.active = true
    RETURN gds.graph.project(
        $graph_name, source, target,
        {
            sourceNodeLabels: labels(source),
            targetNodeLabels: labels(target),
            sourceNodeProperties: source { .score },
            targetNodeProperties: target { .score },
            relationshipType: 'KNOWS',
            relationshipProperties: r { .weight }
        }
    )
    """,
    graph_name="filteredGraph"
)
```

No `database=` parameter — set `GraphDataScience(..., database=...)` at construction or call `gds.set_database(...)` before projecting.
Use `gds.graph.project($graph_name, source, target, {...})` in `RETURN`; pass graph name as keyword (`graph_name="x"`) — it binds to `$graph_name`. Not injected: omitting it → `ParameterMissing: Expected parameter(s): graph_name`.
Query must end with exactly one `RETURN gds.graph.project(...)`. Else use `gds.run_cypher(...)`, then `gds.graph.get("filteredGraph")`.
1.x fallback: `gds.graph.cypher.project(query, database=...)`.
AGA Sessions → `neo4j-aura-graph-analytics-skill`.

---

## Graph Object API

```python
G.name()                   # "myGraph"
G.node_count()             # 12_043
G.relationship_count()     # 87_211
G.node_labels()            # ["Person", "City"]
G.relationship_types()     # ["KNOWS", "LIVES_IN"]
G.node_properties()        # projected + mutated properties by label
G.relationship_properties()
G.size_in_bytes()
gds.graph.drop(G)

# Re-attach to existing projection
G = gds.graph.get("myGraph")

# List all projected graphs
gds.graph.list()
```

---

## Memory Estimation

```python
# Project estimation
est = gds.graph.project.estimate(node_projection=["Person"], relationship_projection=["KNOWS"])
print(est.required_memory)

G, project_result = gds.graph.project.native("myGraph", "Person", "KNOWS")
print(project_result.node_count)

# Algorithm estimation (requires projected graph)
est = gds.page_rank.estimate(G, damping_factor=0.85)
est = gds.fast_rp.estimate(G, embedding_dimension=256)
print(est.required_memory)
```

If `requiredMemory` exceeds JVM heap (`server.memory.heap.max_size`), reduce graph or increase heap. Treat 80% heap as review threshold, not hard guarantee.

---

## Catalog Management

```cypher
// List all projected graphs
CALL gds.graph.list() YIELD graphName, nodeCount, relationshipCount, memoryUsage

// Drop by name
CALL gds.graph.drop('myGraph') YIELD graphName

// Drop if exists (no error if missing)
CALL gds.graph.drop('myGraph', false) YIELD graphName
```

```python
gds.graph.list()           # list of typed graph metadata objects
gds.graph.get("myGraph")   # Graph
gds.graph.drop("myGraph")  # Drop by name
gds.graph.drop(G)          # Drop via object
```

GDS < 2026.10: `memoryUsage` / `sizeInBytes` under-report actual heap use significantly — size heap from `gds.graph.project.estimate`, not catalog numbers. Fixed in 2026.10.

Drop graphs after use. Catalog graphs persist until dropped, source database stops/drops, or DBMS stops.

---

## Heterogeneous Graphs

Project multiple node labels/relationship types for algorithms that support them (e.g., `gds.metaPath`):

```python
G, _ = gds.graph.project.native(
    "heteroGraph",
    ["Actor", "Movie", "Genre"],
    ["ACTED_IN", "HAS_GENRE"]
)

# Filter algorithms to specific labels/types
gds.page_rank.stream(G,
    node_labels=["Actor"],
    relationship_types=["ACTED_IN"]
)
```

Most algorithms accept `node_labels` and `relationship_types` to scope execution within heterogeneous projection.

---

## Subgraph Projection (filter an existing projection)

```python
# Create subgraph from existing named graph
sub_G, result = gds.graph.filter(
    G,                             # source graph
    "subGraph",                    # new graph name
    "n.score > 0.5",               # node filter (Cypher predicate)
    "r.weight > 1.0"               # relationship filter
)
```

Project once; filter many times without re-reading database.
