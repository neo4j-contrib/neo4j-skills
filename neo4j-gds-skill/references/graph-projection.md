# GDS Graph Projection Reference

## Projection Types — When to Use Each

| Type | Procedure | When |
|---|---|---|
| Native | Python: `gds.graph.project.native(...)` | Labels + relationship types, optional property lists; fastest bulk load |
| Cypher | Python: `gds.graph.project.cypher(query)` with `RETURN gds.graph.project(...)` inside | Filtering, transformation, computed properties, heterogeneous patterns |

Client 2.0 renames: 1.x `gds.graph.project` → `gds.graph.project.native`; 1.x `gds.graph.cypher.project` → `gds.graph.project.cypher`; the legacy 1.x `gds.graph.project.cypher` procedure is removed. For Aura Graph Analytics sessions, use `neo4j-aura-graph-analytics-skill`.

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

# Simple native projection — plugin client only
G, result = gds.graph.project.native("myGraph", "Person", "KNOWS")
print(result.node_count, result.relationship_count)

# Multi-label, multi-rel, properties
G, result = gds.graph.project.native(
    "myGraph",
    {"Person": {"properties": ["age", "score"]},
     "City":   {"properties": {"population": {"defaultValue": 0}}}},
    {"KNOWS":    {"orientation": "UNDIRECTED", "properties": ["weight"]},
     "LIVES_IN": {"properties": ["since"]}},
    read_concurrency=4,
    overwrite=True        # drops an existing graph of the same name first [client 2.0]
)

# Wildcards
G, result = gds.graph.project.native("allGraph", "*", "*")
```

---

## Cypher Projection — Full Pattern

```python
gds.set_database("neo4j")     # database= parameter removed in client 2.0

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
    graph_name="filteredGraph"    # extra kwargs pass through as Cypher parameters
)
```

Query must end with exactly one `RETURN gds.graph.project(...)`, else raises `ValueError` — for extra aggregations use `gds.run_cypher(...)`, then `gds.graph.get("filteredGraph")`.
Returns `(Graph, GraphCypherProjectResult)`; the query text is never rewritten, so all projection config belongs in the query.
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
# Projection estimation — before projecting
est = gds.graph.project.estimate("Person", "KNOWS", node_properties=["score"])
print(est.required_memory)

G, project_result = gds.graph.project.native("myGraph", "Person", "KNOWS")
print(project_result.node_count)

# Algorithm estimation (requires projected graph)
est = gds.page_rank.estimate(G, damping_factor=0.85)
est = gds.fast_rp.estimate(G, embedding_dimension=256)
print(est.required_memory)
```

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
gds.graph.list()                                   # list[GraphInfoWithDegrees]
gds.graph.get("myGraph")                           # Graph
gds.graph.drop("myGraph")                          # returns list[GraphInfo]
gds.graph.drop([G, "otherGraph"], fail_if_missing=False)
gds.graph.exists("myGraph")                        # bool
```

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

Most algorithms accept `node_labels` and `relationship_types` to scope execution within a heterogeneous projection.

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

# Random-walk-with-restart sample (also gds.graph.sample.cnarw)
sub_G, result = gds.graph.sample.rwr(G, "sampleGraph", sampling_ratio=0.2)
```

Project once; filter many times without re-reading database.
