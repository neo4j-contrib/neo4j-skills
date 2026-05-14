# neo4j-driver-go-skill

Skill for writing Go code with the Neo4j Go Driver v6.

## What this skill covers

- Driver setup, lifecycle, and connection verification
- `neo4j.ExecuteQuery` — the recommended default for most queries
- Managed transactions (`session.ExecuteRead/Write`) for lazy streaming
- Explicit transactions (`session.BeginTransaction`) for multi-function coordination
- Error handling (`Neo4jError`, `ConnectivityError`, retry behavior)
- Data type mapping (Go ↔ Cypher) and safe record extraction
- Context propagation and timeout patterns
- Batch write pattern with `UNWIND`
- Causal consistency and bookmark management

## Version / compatibility

- Neo4j Go Driver **v6** (current stable)
- Go >= 1.21 recommended
- v5 aliases still compile in v6; migrate before v7

## Not covered

- **Cypher query authoring** → `neo4j-cypher-skill`
- **v5→v6 migration steps** → `neo4j-migration-skill`
- Advanced connection pool tuning → `references/advanced-config.md`
- Repository wrapper pattern → `references/repository-pattern.md`

## Install

```bash
go get github.com/neo4j/neo4j-go-driver/v6
```
