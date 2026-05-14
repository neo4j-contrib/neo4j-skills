# neo4j-aura-graph-analytics-skill

Guides agents through **Aura Graph Analytics (AGA)** — Neo4j's serverless, on-demand GDS compute environment. Algorithms run in isolated ephemeral sessions billed per minute; no embedded GDS plugin required.

## What this skill covers

- Authentication with Aura API credentials (`GdsSessions`, `AuraAPICredentials.from_env()`)
- Memory estimation and `SessionMemory` tier selection
- Session creation, reconnection, listing, and deletion (`get_or_create`, TTL)
- Three data source modes: AuraDB-connected, self-managed Neo4j, standalone (Pandas/Spark)
- Remote graph projection (`gds.graph.project.remote()`)
- Standalone graph construction from DataFrames (`gds.graph.construct()`)
- Algorithm execution: mutate / stream / write modes
- Async job polling pattern
- Result retrieval (`gds.graph.nodeProperties.stream()`, `db_node_properties`)
- Write-back to connected Neo4j; cleanup before session deletion
- Common errors and mitigations (session expired, graph not projected, memory exceeded)

## Compatibility

`graphdatascience >= 1.15` · Aura Business Critical and VDC tiers · Python >= 3.8

## Not covered

- **Embedded GDS plugin** (Aura Pro, self-managed Neo4j) → `neo4j-gds-skill`
- **Cypher query authoring** → `neo4j-cypher-skill`
- **Snowflake Graph Analytics** → `neo4j-snowflake-graph-analytics-skill`

## Install

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-aura-graph-analytics-skill
```
