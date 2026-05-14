# GDS Graph Projection Reference

## Projection Types — When to Use Each

| Type | Procedure | When |
|---|---|---|
| Native | `gds.graph.project` | Standard — labels + rel types; 5–10× faster than Cypher |
| Cypher | `gds.graph.cypher.project` | Filtering, transformation, computed properties, heterogeneous |

Always prefer native projection. Use Cypher projection only when native can't express the requirement.

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

Use `UNDIRECTED` for undirected algorithms (community detection, most similarity/embedding algorithms). Use `NATURAL` for directed algorithms (PageRank, Betweenness).

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

Null node properties in projection → algorithm errors. Always specify `defaultValue` for optional properties.

---

## Python Client — Projection

```python
from graphdatascience import GraphDataScience
gds = GraphDataScience("bolt://localhost:7687", auth=("neo4j", "pw"))

# Simple
G, result = gds.graph.project("myGraph", "Person", "KNOWS")

# Multi-label, multi-rel, properties
G, result = gds.graph.project(
    "myGraph",
    {"Person": {"properties": ["age", "score"]},
     "City":   {"properties": {"population": {"defaultValue": 0}}}},
    {"KNOWS":    {"orientation": "UNDIRECTED", "properties": ["weight"]},
     "LIVES_IN": {"properties": ["since"]}}
)

# Context manager — auto-drops on exit
with gds.graph.project("tmp", "Person", "KNOWS")[0] as G:
    results = gds.pageRank.stream(G)
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

Use `gds.graph.project($graph_name, source, target, {...})` in the RETURN — the `$graph_name` parameter is injected automatically.

---

## Graph Object API

```python
G.name()                   # "myGraph"
G.node_count()             # 12_043
G.relationship_count()     # 87_211
G.node_labels()            # ["Person", "City"]
G.relationship_types()     # ["KNOWS", "LIVES_IN"]
G.node_properties("Person")   # projected + mutated properties
G.relationship_properties("KNOWS")
G.memory_usage()           # "45 MiB"
G.density()                # 0.0032
G.exists()                 # True
G.drop()

# Re-attach to existing projection
G = gds.graph.get("myGraph")

# List all projected graphs
gds.graph.list()
```

---

## Memory Estimation

```python
# Project estimation
est = gds.graph.project.estimate("Person", "KNOWS")
# Multi-label/rel:
est = gds.graph.project.estimate(
    {"Person": {"properties": ["score"]}, "City": {}},
    {"KNOWS": {"orientation": "UNDIRECTED"}}
)
print(est["requiredMemory"])    # "1234 MiB"
print(est["bytesMin"])
print(est["bytesMax"])
print(est["nodeCount"])
print(est["relationshipCount"])

# Algorithm estimation (requires projected graph)
est = gds.pageRank.estimate(G, dampingFactor=0.85)
est = gds.fastRP.estimate(G, embeddingDimension=256)
```

Rule: if `requiredMemory` > 80% of available JVM heap (`dbms.memory.heap.max_size`), increase heap before projecting.

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
gds.graph.list()              # DataFrame of all projected graphs
gds.graph.exists("myGraph")   # True/False
gds.graph.drop("myGraph")     # Drop by name
G.drop()                      # Drop via object
```

Always drop graphs after use. The graph catalog persists until Neo4j restarts — leaked projections consume JVM heap permanently until restart.

---

## Heterogeneous Graphs

Project multiple node labels and relationship types for algorithms that support them (e.g., `gds.metaPath`):

```python
G, _ = gds.graph.project(
    "heteroGraph",
    ["Actor", "Movie", "Genre"],
    ["ACTED_IN", "HAS_GENRE"]
)

# Filter algorithms to specific labels/types
gds.pageRank.stream(G,
    nodeLabels=["Actor"],
    relationshipTypes=["ACTED_IN"]
)
```

Most algorithms accept `nodeLabels` and `relationshipTypes` to scope execution within a heterogeneous projection.

---

## Subgraph Projection (filter an existing projection)

```python
# Create a subgraph from an existing named graph
sub_G, result = gds.graph.filter(
    "subGraph",                    # new graph name
    G,                             # source graph
    "n.score > 0.5",               # node filter (Cypher predicate)
    "r.weight > 1.0"               # relationship filter
)
```

Project once, filter many times without re-reading the database.
