# neo4j-gds-skill

Agent skill for Neo4j Graph Data Science (GDS) through the Python client — prefer Aura Graph Analytics GDS Sessions for AuraDB when available; use embedded GDS plugin for local/self-managed cases.

## What this skill covers

- Aura Graph Analytics GDS Sessions: create, remote project, run algorithms, write back, delete
- Graph projection: session remote projection, native projection, and Cypher projection
- Execution modes: stream / stats / mutate / write and when to use each
- Core algorithms: PageRank, Louvain, WCC, Betweenness Centrality, Node Similarity, FastRP, KNN
- FastRP → KNN recommendation pipeline pattern
- Writing node embeddings for Neo4j vector indexes / structural similarity search
- Memory estimation before large projections and algorithm runs
- GDS Python client (`graphdatascience`) — sessions, connection, projection, algorithm calls
- Graph catalog operations: project, list, drop, subgraph filter
- Common errors and mitigations (OOM, missing properties, unlicensed algorithms)

## Compatibility

- GDS Python client v1.21: GDS >= 2.6 and < 2.28 / < 2026.4
- Aura Graph Analytics Sessions for AuraDB when available
- Embedded GDS plugin: Neo4j >= 5.x self-managed/local or Aura Pro plugin workflows
- Python >= 3.10 and < 3.15
- Neo4j Python Driver >= 4.4.12 and < 7.0

## Not covered

- **Cypher query authoring** → `neo4j-cypher-skill`
- **Driver/connection setup** → `neo4j-driver-python-skill`
- **Creating/querying vector indexes over written embeddings** → `neo4j-vector-index-skill`

## Install

```bash
pip install graphdatascience
```

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-gds-skill
```
