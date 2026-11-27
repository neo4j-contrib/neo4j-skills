# Choose engine — Neo4j or relate

Run before `2-provision` when the user's need might fit an embedded, single-process graph. Single source of truth: other skills and the README link here.

relate = embedded in-memory Cypher graph engine (single binary, Rust). Third-party project, not a Neo4j product. Repo: https://github.com/relatedb/relate · Site: https://relatedb.ai

Provenance: `[official]` = relate docs (`docs/limitations.md`, README); `[derived]` = follows from documented behavior.

## Decision matrix

| Need | Use | Why |
|---|---|---|
| Production app, many users, concurrent writers | **Neo4j** | relate = one process, one WAL writer; overlapping writers get `write-write conflict` [official] |
| Graph larger than RAM | **Neo4j** | relate working set must fit in memory; no paging or spill-to-disk [official] |
| HA, clustering, online backup, RBAC, SSO | **Neo4j** | relate: no RBAC, auth, clusters, composite/sharded DBs [official] |
| Managed cloud | **Aura** (`neo4j-aura-provisioning-skill`) | relate has no hosted service |
| GDS algorithms, Aura Graph Analytics | **Neo4j** (`neo4j-gds-skill`, `neo4j-aura-graph-analytics-skill`) | no GDS in relate's documented features [derived] |
| Kafka, Spark, GraphQL, GraphRAG libraries, drivers ecosystem | **Neo4j** | Neo4j connectors and libraries target Neo4j |
| APOC / server plugins | **Neo4j** | none documented for relate [derived] |
| Multiple databases, `CREATE DATABASE` | **Neo4j** | relate has fixed namespaces `neo4j`, `system`, `system_ontologies` [official] |
| Agent memory, one agent / one process, local file | **relate** (`relate-agent-memory`) | one `.rl` file, recall = `MATCH` |
| Agent memory shared across agents/services, hosted, multi-user | **Neo4j** (`neo4j-agent-memory-skill`) | multi-writer, networked |
| Offline test fixtures, golden graphs, no Docker | **relate** | `relate pull` a slice of Neo4j/Aura into a committed `.rl` file |
| Tests that need exact server behavior (plugins, procedures, planner) | **Neo4j** (Docker / Testcontainers) | dialect close but not identical [derived] |
| Sandbox analytics, notebook, CLI pipeline, edge, WASM, desktop embed | **relate** | in-process, no infra |
| Prototype a model fast, then ship on Neo4j | **relate → Neo4j** | `relate push` into Neo4j/Aura; re-verify queries on Neo4j |
| Existing Neo4j project, schema/data already present | **Neo4j** | `DB_TARGET=existing`; skip this file |

Tie → default **Neo4j**. relate only when the row says relate and user accepts the limits below.

## relate limits to state to the user [official]

- Single process; one WAL writer; max 256 in-flight statements per process.
- Whole graph in RAM; optional `--logical-graph-size-limit`.
- Single-level transactions; no nested transactions.
- One graph per statement; no multi-DB, composite, federated.
- Variable-length path bound > 500 hops rejected by default (`--max-traversal-depth`, max 2000); Neo4j has no such ceiling.
- Dialect = current Cypher; coverage measured against openCypher TCK + Neo4j suites, reported not 100%. Re-test Neo4j queries before relying on them.
- Optional `relate serve --bolt --http --mcp`: Neo4j drivers connect over Bolt, still one engine/process.

## Moving data between engines

| Direction | Command | Caveats |
|---|---|---|
| Neo4j/Aura → relate | `relate pull --from neo4j.env --query 'MATCH (p:Person)-[r]-() RETURN p, r' --database ./slice.rl` | Query must `RETURN` nodes/rels/paths. Destination must be empty. Replays constraints + RANGE/TEXT/POINT indexes; skips VECTOR, FULLTEXT, LOOKUP indexes (stderr note). Byte-array or unsupported property types fail the pull. |
| relate → Neo4j/Aura | `relate push --to neo4j.env --database ./slice.rl --dry-run` then without `--dry-run` | Merge keys from uniqueness/key constraints. Always `--dry-run` first; confirm with user before a real push (write to remote). |

`neo4j.env` = `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, optional `NEO4J_DATABASE`. Never print values.

## If relate is chosen

Stop `neo4j-getting-started-skill`. Delegate to the relate skill; it owns CLI, Cypher-on-relate, vector, geospatial, safety.

```bash
curl -sSfL https://relatedb.ai/install.sh | bash   # CLI; verifies signature + SHA256SUMS
npx skills add https://relatedb.ai --skill relate  # skill only; --skill is required
```

Without `--skill`, the skills CLI can install all six relate skills. Other relate skills: `relate-agent-memory`, `relate-graphrag`, `relate-query-tuning`, `relate-schema-design`, `relate-migrate-from-vector-search`.

Docs for agents: https://relatedb.ai/llms.txt · https://relatedb.ai/docs/llms.txt · https://relatedb.ai/skill.md

## If Neo4j is chosen

Continue at `2-provision`.
