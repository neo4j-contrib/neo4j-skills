---
name: neo4j-gds-skill
description: >
  Use when running Graph Data Science algorithms in Neo4j: graph projection
  (gds.graph.project), algorithm execution (PageRank, Louvain, Betweenness,
  FastRP, Node2Vec, shortest paths), writing results back to the graph (mutate/write),
  memory estimation, GDS Python client (graphdatascience), or streaming algorithm
  results. Also covers GDS availability (Aura Pro/Enterprise only, not Aura Free).
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT handle driver setup — use a driver skill.
  Does NOT handle GraphRAG retrieval — use neo4j-graphrag-skill.
status: draft
version: 0.1.0
allowed-tools: Bash, WebFetch
---

# Neo4j Graph Data Science Skill

> **Status: Draft / WIP** — Content is a placeholder. Algorithm reference files to be added.
> GDS is available on Aura Professional and Enterprise only — **not Aura Free**.

## When to Use

- Projecting a named graph into GDS memory (`gds.graph.project`)
- Running GDS algorithms: centrality, community detection, path finding, node embeddings
- Writing algorithm results back to the graph (`mutate`, `write` modes)
- Estimating memory before running on large graphs (`estimate` mode)
- Using the GDS Python client (`graphdatascience` package)
- Checking available procedures (`gds.list()`)

## When NOT to Use

- **Cypher query authoring** → use `neo4j-cypher-skill`
- **Driver/application setup** → use a driver skill
- **GraphRAG retrieval pipelines** → use `neo4j-graphrag-skill`
- **GDS on Aura Free** — GDS is not available on Aura Free; suggest upgrading to Pro

---

## MCP Tool Usage

When the Neo4j MCP server is available:

| Operation | MCP tool | Notes |
|---|---|---|
| `RETURN gds.version()` (pre-flight) | `read-cypher` | First call — fail fast if GDS unavailable |
| Cypher projection (alternative to native) | `read-cypher` | `gds.graph.project.cypher()` |
| `gds.pageRank.write(...)` | `write-cypher` | Write mode modifies the DB |
| `gds.graph.drop(...)` | `write-cypher` | Required cleanup |

GDS Python client bypasses MCP and uses the driver directly — both approaches work.

---

## GDS Availability

| Deployment | GDS Available |
|---|---|
| Aura Free | No |
| Aura Professional | Yes |
| Aura Enterprise | Yes |
| Self-managed (with GDS plugin) | Yes |

Check: `CALL gds.list() YIELD name RETURN count(*) AS procedures`

---

## Pre-flight: Verify GDS Availability

Run this before any GDS operation:
```cypher
RETURN gds.version() AS gds_version
```
If this fails with `Unknown function 'gds.version'`: GDS is not installed or not available on this tier. Stop and inform the user. On Aura Free, GDS is unavailable — user must upgrade to Professional or Enterprise.

---

## Execution Modes

Every GDS algorithm supports four modes — choose deliberately:

| Mode | Side effect | When to use |
|---|---|---|
| `stream` | None (read-only) | Inspect results; verify algorithm is working |
| `stats` | None (read-only) | Summary statistics only (faster than stream) |
| `mutate` | Adds property to in-memory graph only | Chain algorithms without writing to DB |
| `write` | Persists property to Neo4j database | Final step — make results queryable |

**Always `stream` first to verify results before `write`.** The `mutate` + `write` pattern: `gds.pageRank.mutate(G, mutateProperty='pr')` then `gds.graph.nodeProperties.write(G, ['pr'])`.

---

## Algorithm Decision Tree

```
Centrality (who is important?)
  ├── Influence propagation        → PageRank / ArticleRank
  ├── Bottleneck detection         → Betweenness Centrality
  └── Direct connections           → Degree Centrality

Community Detection (who clusters together?)
  ├── Large-scale                  → Louvain
  ├── Overlapping communities      → Label Propagation
  └── Hierarchical                 → Leiden

Path Finding
  ├── Single shortest path         → Dijkstra / A*
  └── All shortest paths           → Yen's K-Shortest Paths

Node Embeddings (ML features)
  ├── Fast, scalable               → FastRP
  └── Random walk-based            → Node2Vec
```

---

## Core Patterns (GDS Python Client)

### Setup

```bash
pip install graphdatascience   # requires GDS-enabled Neo4j
```

```python
from graphdatascience import GraphDataScience

gds = GraphDataScience(
    "bolt://localhost:7687",
    auth=("neo4j", "password"),
    database="neo4j"
)
```

### Project + run + drop

```python
# 1. Estimate memory before projecting large graphs
res = gds.graph.project.estimate("Person", "KNOWS")
print(res["requiredMemory"])

# 2. Project
G, result = gds.graph.project("myGraph", "Person", "KNOWS")

# 3. Run PageRank (stream mode)
pagerank = gds.pageRank.stream(G)
print(pagerank.sort_values("score", ascending=False).head(10))

# 4. Write results back to graph nodes
gds.pageRank.write(G, writeProperty="pagerank")

# 5. Always drop when done
G.drop()
```

### Node embeddings (FastRP → write for later use)

```python
gds.fastRP.write(G,
    embeddingDimension=128,
    writeProperty="embedding",
    randomSeed=42
)
```

---

## Checklist

- [ ] GDS availability confirmed before proceeding (not Aura Free)
- [ ] Memory estimated before projecting large graphs
- [ ] Named graph dropped (`G.drop()`) after use to free memory
- [ ] Algorithm mode chosen deliberately: stream (inspect) → mutate (chain) → write (persist)
- [ ] `writeProperty` name checked for collision with existing node properties

---

## Fetching Current Docs

```
https://neo4j.com/docs/llms.txt     ← full documentation index (includes GDS algorithm reference)
https://neo4j.com/llms-full.txt     ← rich reference with GDS Python client examples
```

## References

- [GDS Library Docs](https://neo4j.com/docs/graph-data-science/)
- [GDS Python Client Docs](https://neo4j.com/docs/graph-data-science/python-client/)
- [Algorithm reference](https://neo4j.com/docs/graph-data-science/current/algorithms/)
- [GraphAcademy: Get Started with GDS](https://graphacademy.neo4j.com/courses/gds-fundamentals/)
