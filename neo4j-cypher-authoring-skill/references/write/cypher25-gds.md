> Source: manual — neo4j-cypher-authoring-skill v2026.02.0  generated: 2026-03-23

# Graph Data Science (GDS) Library — Cypher 25 Patterns

> **Availability**: GDS is NOT bundled with Neo4j. It is an optional plugin installable on Neo4j 5+ and Neo4j Enterprise. It is NOT available on demo.neo4jlabs.com or standard Aura instances unless explicitly enabled. **Only use `gds.*` calls when the injected schema context states `gds: true`.**

## GDS Workflow: Project → Run → Write (or Stream)

GDS operates on **in-memory projections** (subgraphs loaded from the database). Every GDS workflow has three phases:

1. **Project** — load nodes/relationships into a named in-memory graph
2. **Run algorithm** — stream or mutate on the projection
3. **Write back** — persist results to the database

## 1. Graph Projection

```cypher
// Native projection (most common)
CYPHER 25
CALL gds.graph.project(
  'myGraph',                         // projection name (must be unique)
  ['Person', 'Organization'],        // node labels to include
  {
    KNOWS: { orientation: 'UNDIRECTED' },  // rel type + orientation
    WORKS_AT: { orientation: 'NATURAL' }
  }
)
YIELD graphName, nodeCount, relationshipCount;

// Project with node properties (for weighted algorithms)
CYPHER 25
CALL gds.graph.project(
  'weightedGraph',
  'Transaction',
  {
    SENT: {
      orientation: 'NATURAL',
      properties: ['amount']         // include relationship property as weight
    }
  }
)
YIELD graphName, nodeCount, relationshipCount;
```

**Drop projection when done** (projections consume heap memory):
```cypher
CYPHER 25 CALL gds.graph.drop('myGraph') YIELD graphName;
```

## 2. Core Algorithm Patterns

### PageRank (node importance by in-link count)

```cypher
// Stream (no DB write — returns results in-query)
CYPHER 25
CALL gds.pageRank.stream('myGraph', { maxIterations: 20, dampingFactor: 0.85 })
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS n, score
RETURN n.name AS name, score
ORDER BY score DESC LIMIT 10;

// Write back to node property
CYPHER 25
CALL gds.pageRank.write('myGraph', { writeProperty: 'pagerank' })
YIELD nodePropertiesWritten, ranIterations;
```

### Betweenness Centrality (nodes on most shortest paths)

```cypher
CYPHER 25
CALL gds.betweenness.stream('myGraph')
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS n, score
RETURN n.name AS name, score
ORDER BY score DESC LIMIT 10;
```

### Community Detection — Louvain

```cypher
// Stream community IDs
CYPHER 25
CALL gds.louvain.stream('myGraph', { maxLevels: 10 })
YIELD nodeId, communityId, intermediateCommunityIds
WITH gds.util.asNode(nodeId) AS n, communityId
RETURN communityId, collect(n.name) AS members
ORDER BY size(members) DESC LIMIT 10;

// Write community IDs to nodes
CYPHER 25
CALL gds.louvain.write('myGraph', { writeProperty: 'louvainCommunity' })
YIELD nodePropertiesWritten, communityCount;
```

### Weakly Connected Components (WCC)

```cypher
CYPHER 25
CALL gds.wcc.stream('myGraph')
YIELD nodeId, componentId
WITH componentId, collect(gds.util.asNode(nodeId).name) AS members
RETURN componentId, size(members) AS size, members
ORDER BY size DESC LIMIT 10;
```

### Shortest Path — Dijkstra (weighted single-source)

```cypher
// Project with weight property first (see section 1)
CYPHER 25
MATCH (src:Person {name: 'Alice'})
CALL gds.shortestPath.dijkstra.stream('weightedGraph', {
  sourceNode: id(src),
  relationshipWeightProperty: 'amount'
})
YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs
RETURN gds.util.asNode(targetNode).name AS target, totalCost
ORDER BY totalCost LIMIT 5;
```

### Node Similarity (Jaccard — shared neighbor overlap)

```cypher
CYPHER 25
CALL gds.nodeSimilarity.stream('myGraph', { similarityCutoff: 0.5 })
YIELD node1, node2, similarity
WITH gds.util.asNode(node1).name AS a, gds.util.asNode(node2).name AS b, similarity
RETURN a, b, similarity
ORDER BY similarity DESC LIMIT 10;
```

## 3. Utility Functions

```cypher
gds.util.asNode(nodeId)     // convert GDS internal nodeId → Neo4j node
gds.util.nodeProperty(nodeId, 'prop')  // read property from GDS node by internal ID
```

## 4. Native Cypher Fallbacks (when GDS is NOT available)

When `gds: true` is absent from schema context, use these pure-Cypher equivalents:

| GDS Algorithm | Native Cypher Approximation |
|---|---|
| `gds.degree.stream` | `MATCH (n)-[r]->() RETURN n, count(r) AS degree` |
| `gds.pageRank.stream` | `MATCH (n)<-[r]-() RETURN n, count(r) AS approxPageRank ORDER BY approxPageRank DESC` |
| `gds.betweenness.stream` | Not expressible in pure Cypher — use stored `betweenness` property if pre-computed |
| `gds.louvain.stream` | Not expressible — use stored `louvainCommunity` property if available |
| `gds.wcc.stream` | `MATCH path=(n)-[*0..10]-(m) RETURN …` (expensive — use SHORTEST instead) |
| `gds.shortestPath.*` | `CYPHER 25 SHORTEST 1 (a)(()-[:REL]->()){1,}(b)` |

## 5. GDS Availability Check

```cypher
// Check if GDS is installed
CYPHER 25
SHOW PROCEDURES WHERE name STARTS WITH 'gds.'
YIELD name RETURN count(name) AS gdsProcs;
// 0 → GDS not installed; > 0 → GDS available
```

## 6. Streaming vs Write-Back — Critical Distinction

> **IMPORTANT**: GDS algorithm `.stream` procedures return results **only during query execution** — they do NOT store any properties on database nodes. Assume no GDS-computed properties exist on nodes unless the schema context explicitly confirms a write-back was previously performed.

### DO-NOT / DO examples

```cypher
// WRONG — assumes louvainCommunity is a stored node property (it is NOT unless written back)
CYPHER 25
MATCH (c:Customer)
WHERE c.louvainCommunity = $community
RETURN c.name AS name;

// CORRECT — stream results from GDS algorithm at query time
CYPHER 25
CALL gds.louvain.stream('myGraph', { maxLevels: 10 })
YIELD nodeId, communityId
WHERE communityId = $community
WITH gds.util.asNode(nodeId) AS c
RETURN c.name AS name;
```

```cypher
// WRONG — assumes pageRank is a stored node property
CYPHER 25
MATCH (p:Person)
WHERE p.pageRank > 0.5
RETURN p.name ORDER BY p.pageRank DESC LIMIT 10;

// CORRECT — stream PageRank scores at query time
CYPHER 25
CALL gds.pageRank.stream('myGraph')
YIELD nodeId, score
WHERE score > 0.5
WITH gds.util.asNode(nodeId) AS p, score
RETURN p.name, score ORDER BY score DESC LIMIT 10;
```

**When stored properties are acceptable**: only when the schema context notes that a GDS write-back was performed (e.g., `"gds_written_properties": ["louvainCommunity", "pageRank"]`). Otherwise always stream.

## Key Rules

- **Always drop the projection** after use: `CALL gds.graph.drop('name')` — projections consume JVM heap
- **`gds.util.asNode(nodeId)`** — required to convert integer node IDs back to Neo4j nodes in `RETURN`
- **Orientation choices**: `NATURAL` (directed as stored), `REVERSE` (flipped), `UNDIRECTED` (both directions)
- **`stream` vs `write`**: `stream` returns results without touching the DB; `write` persists results as node/rel properties and returns statistics
- **`mutate`**: like `write` but only to the in-memory projection — use before chaining algorithms
- **Weight properties** must be declared in the projection (`properties: ['weight']`) before algorithms can use them
- **Never assume stored GDS properties** — properties like `louvainCommunity`, `pageRank`, `betweenness` do NOT exist on nodes unless a `.write` call was previously executed and confirmed in schema context
