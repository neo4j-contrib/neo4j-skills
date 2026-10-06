# neo4j-gds-skill

Agent skill for Neo4j Graph Data Science (GDS) embedded plugin through the Python client or Cypher. Use for Aura Pro, self-managed, local, or offline Neo4j DBMS with the GDS plugin installed.

## What this skill covers

- Graph projection: native projection and Cypher projection
- Execution modes: stream / stats / mutate / write and when to use each
- Core algorithms: PageRank, Louvain, WCC, Betweenness Centrality, Node Similarity, FastRP, KNN
- FastRP → KNN recommendation pipeline pattern
- Writing node embeddings for Neo4j vector indexes / structural similarity search
- Memory estimation before large projections and algorithm runs
- GDS Python client (`graphdatascience`) 2.x — connection, projection, algorithm calls; client 1.x mapping for GDS server < 2.13
- Graph catalog operations: project, list, drop, subgraph filter
- Common errors and mitigations (OOM, missing properties, unlicensed algorithms)

## Compatibility

- GDS Python client 2.1: GDS >= 2.13 and < 2.28 / < 2026.10 (2.0: < 2026.9); client 1.22 (pin `graphdatascience<2`) for GDS server < 2.13
- Embedded GDS plugin: Neo4j >= 5.x self-managed/local or Aura Pro plugin workflows
- Python >= 3.10 and < 3.15
- Neo4j Python Driver >= 5.26 and < 7.0

## Not covered

- **Cypher query authoring** → `neo4j-cypher-skill`
- **Driver/connection setup** → `neo4j-driver-python-skill`
- **Creating/querying vector indexes over written embeddings** → `neo4j-vector-index-skill`
- **Aura Graph Analytics Sessions / AGA** → `neo4j-aura-graph-analytics-skill`

## Install

```bash
pip install graphdatascience
```

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-gds-skill
```
