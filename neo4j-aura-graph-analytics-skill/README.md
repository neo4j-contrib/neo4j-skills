# neo4j-aura-graph-analytics-skill

Guides agents through **Aura Graph Analytics (AGA)** — Neo4j's serverless, on-demand GDS compute environment. Algorithms run in isolated ephemeral sessions billed per minute; no embedded GDS plugin required.

## What this skill covers

- Authentication with Aura API credentials (`GdsSessions`, `AuraAPICredentials.from_env()`)
- Memory estimation and `SessionMemory` tier selection — per-algorithm `sessions.estimate(algorithms=[...])`
- Session creation, reconnection, listing, and deletion (`get_or_create`, TTL)
- Three data source modes: AuraDB-connected, self-managed Neo4j, standalone (Pandas/Spark)
- Remote graph projection (`gds.graph.project.cypher(graph_name, query)` with `gds.graph.project.remote()`)
- Native remote projection (`gds.graph.project.native(...)` with label/type filters)
- graphdatascience client 2.0 endpoint shape; client 1.x mapping for pinned environments
- AuraDB Cypher API projection with `memory` or `sessionId`
- Standalone graph construction from DataFrames (`gds.graph.construct()`)
- Algorithm execution: mutate / stream / write modes
- Async execution — `compute()` / `JobHandle`, `gds.graph.project.*_async`, `gds.jobs`
- Result retrieval (`gds.graph.node_properties.stream()`, `db_node_properties`)
- Write-back to connected Neo4j; cleanup before session deletion
- Common errors and mitigations (session expired, graph not projected, memory exceeded)

## Compatibility

`graphdatascience >= 2.0` · AuraDB Free, Professional, Business Critical, and VDC tiers · Python >= 3.10

## Not covered

- **Embedded GDS plugin** (Aura Pro, self-managed Neo4j) → `neo4j-gds-skill`
- **Cypher query authoring** → `neo4j-cypher-skill`
- **Snowflake Graph Analytics** → `neo4j-snowflake-graph-analytics-skill`

## Install

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-aura-graph-analytics-skill
```
