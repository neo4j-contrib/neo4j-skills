# neo4j-aura-graph-analytics-skill

Guides agents through **Aura Graph Analytics (AGA)** — Neo4j's serverless, on-demand graph algorithm compute environment. AGA runs GDS algorithms in isolated ephemeral sessions, billed per minute, with no embedded plugin required.

## What this skill covers

**Session Lifecycle**
- Authentication with Aura API credentials (`GdsSessions`, `AuraAPICredentials`)
- Memory sizing and estimation (`sessions.estimate()`, `SessionMemory` tiers)
- Cloud location selection
- Session creation, reconnection, listing, and deletion (`get_or_create`, `sessions.list()`, `sessions.delete()`)
- TTL (time-to-live) configuration to avoid unexpected costs

**Three Data Source Modes**
- **AuraDB-connected**: remote projection from AuraDB via `gds.graph.project.remote()` in Cypher
- **Self-managed Neo4j**: same remote projection against a self-hosted instance
- **Standalone**: load from Pandas DataFrames via `gds.graph.construct()` — no Neo4j database needed

**Graph Projection**
- Remote projection with multi-label, multi-relationship, node properties
- `CALL () { ... }` pattern for multi-pattern MATCH clauses
- `gds.graph.construct()` from DataFrames (standalone) with required column conventions
- Spark integration via the Arrow client (`gds.arrow_client()`, `mapInArrow`)

**Algorithm Execution**
- All GDS algorithms work in AGA (mutate / write / stream / stats modes)
- Exception: topological link prediction is not supported
- ML pipelines with session-local model catalog

**Results**
- `gds.graph.nodeProperties.stream()` with `db_node_properties` context
- `gds.graph.nodeProperties.write()` — bulk write back to connected Neo4j
- Algorithm `.write()` modes — persist directly to the connected database
- `gds.run_cypher()` — query the connected Neo4j instance from within the session

## When to use this skill vs neo4j-gds-skill

| Scenario | Skill to use |
|---|---|
| AuraDB Business Critical or VDC | **this skill** |
| Non-Neo4j data source (Pandas, Spark, CSV) | **this skill** |
| On-demand / pipeline workload (pay per use) | **this skill** |
| Aura Pro with embedded GDS plugin | `neo4j-gds-skill` |
| Self-managed Neo4j with GDS plugin | `neo4j-gds-skill` |

## Install

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-aura-graph-analytics-skill
```

Or paste this link into your coding assistant:
https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-aura-graph-analytics-skill
