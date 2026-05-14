# neo4j-gds-skill

Agent skill for Neo4j Graph Data Science (GDS) — running graph algorithms on self-managed Neo4j or Aura Pro.

## What this skill covers

- Graph projection: native and Cypher, with properties and relationship orientation
- Execution modes: stream / stats / mutate / write and when to use each
- Core algorithms: PageRank, Louvain, WCC, Betweenness Centrality, Node Similarity, FastRP, KNN
- FastRP → KNN recommendation pipeline pattern
- Memory estimation before large projections and algorithm runs
- GDS Python client (`graphdatascience`) — connection, projection, algorithm calls
- Graph catalog operations: project, list, drop, subgraph filter
- Common errors and mitigations (OOM, missing properties, unlicensed algorithms)

## Compatibility

- GDS >= 2.6 (Python client v1.21)
- Neo4j >= 5.x (self-managed) or Aura Pro
- Python >= 3.10

## Not covered

- **Aura Graph Analytics** (BC/VDC/serverless) → `neo4j-aura-graph-analytics-skill`
- **Cypher query authoring** → `neo4j-cypher-skill`
- **Driver/connection setup** → `neo4j-driver-python-skill`

## Install

```bash
pip install graphdatascience
```

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-gds-skill
```
