# GDS Graph Projection Reference

## Projection Types — When to Use Each

| Type | Procedure | When |
|---|---|---|
| Cypher | Python: `gds.graph.cypher.project(...)` with `RETURN gds.graph.project` clause inside | Current GDS-doc default; filtering, transformation, computed properties, heterogeneous |
| Native | Python: `gds.v2.graph.project(...)` | Simple labels + relationship types; shortest Python-client path |

Prefer v2 native projection. Use v1 `gds.graph.cypher.project(...)` only for filtering, transformations, computed properties, or heterogeneous projections that v2 native projection cannot express. Avoid legacy `gds.graph.project.cypher(...)` for new work. For Aura Graph Analytics sessions, use `neo4j-aura-graph-analytics-skill`.

---

## Native Projection — Full Syntax

```cypher
CALL gds.graph.project(
  'graphName',
  nodeProjection,      -- '*', label string, list of labels, or map with properties
  relationshipProjection  -- '*', type string, list of types, or map with orientation/properties
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
    orientation: 'UNDIRECTED',    -- NATURAL (default), UNDIRECTED, REVERSE
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

Use `UNDIRECTED` for undirected algorithms: community detection, most similarity/embedding algorithms. Use `NATURAL` for directed algorithms: PageRank, Betweenness.

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

Null node properties in projection → algorithm errors. Set `defaultValue` for optional properties.

---

## Python Client — Projection

```python
from graphdatascience import GraphDataScience
gds = GraphDataScience("bolt://localhost:7687", auth=("neo4j", "pw"))

# Simple native projection — plugin/simple client only
G, result = gds.v2.graph.project("myGraph", "Person", "KNOWS")
print(result.node_count, result.relationship_count)

# Multi-label, multi-rel, properties
G, result = gds.v2.graph.project(
    "myGraph",
    {"Person": {"properties": ["age", "score"]},
     "City":   {"properties": {"population": {"defaultValue": 0}}}},
    {"KNOWS":    {"orientation": "UNDIRECTED", "properties": ["weight"]},
     "LIVES_IN": {"properties": ["since"]}}
)

# V1 fallback:
G, result = gds.graph.project("myGraph", "Person", "KNOWS")
```

---

## Cypher Projection — Full Pattern

```python
G, result = gds.graph.cypher.project(
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
    database="neo4j",
    graph_name="filteredGraph"
)
```

Use `gds.graph.project($graph_name, source, target, {...})` in `RETURN`; `$graph_name` parameter injected automatically.
Query must end with exactly one `RETURN gds.graph.project(...)`. Else use `gds.run_cypher(...)`, then `gds.graph.get("filteredGraph")`.
Never use `gds.graph.project.cypher(...)` for new Cypher projections; legacy deprecated projection procedure.
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
gds.v2.graph.drop(G)

# Re-attach to existing projection
G = gds.v2.graph.get("myGraph")

# List all projected graphs
gds.v2.graph.list()
```

---

## Memory Estimation

```python
# Project estimation
G, project_result = gds.v2.graph.project("myGraph", "Person", "KNOWS")
print(project_result.node_count)

# Algorithm estimation (requires projected graph)
est = gds.v2.page_rank.estimate(G, damping_factor=0.85)
est = gds.v2.fast_rp.estimate(G, embedding_dimension=256)
print(est.required_memory)
```

Projection estimate fallback: use v1 `gds.graph.project.estimate(...)` if v2 estimate endpoint unavailable.

If `requiredMemory` exceeds JVM heap (`dbms.memory.heap.max_size`), reduce graph or increase heap. Treat 80% heap as review threshold, not hard guarantee.

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
gds.v2.graph.list()           # list of typed graph metadata objects
gds.v2.graph.get("myGraph")   # GraphV2
gds.v2.graph.drop("myGraph")  # Drop by name
gds.v2.graph.drop(G)          # Drop via object
```

Drop graphs after use. Catalog graphs persist until dropped, source database stops/drops, or DBMS stops.

---

## Heterogeneous Graphs

Project multiple node labels/relationship types for algorithms that support them (e.g., `gds.metaPath`):

```python
G, _ = gds.v2.graph.project(
    "heteroGraph",
    ["Actor", "Movie", "Genre"],
    ["ACTED_IN", "HAS_GENRE"]
)

# Filter algorithms to specific labels/types
gds.v2.page_rank.stream(G,
    node_labels=["Actor"],
    relationship_types=["ACTED_IN"]
)
```

Most algorithms accept v2 `node_labels` and `relationship_types` to scope execution within heterogeneous projection.

---

## Subgraph Projection (filter an existing projection)

```python
# Create subgraph from existing named graph
sub_G, result = gds.v2.graph.filter(
    G,                             # source graph
    "subGraph",                    # new graph name
    "n.score > 0.5",               # node filter (Cypher predicate)
    "r.weight > 1.0"               # relationship filter
)
```

Project once; filter many times without re-reading database.
