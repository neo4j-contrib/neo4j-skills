# AGENTS.md — neo4j-getting-started-skill

## Project Purpose

This skill guides a user (or coding agent) from zero to a running Neo4j application.
It covers 8 stages: prerequisites → context → provision → model → load → explore → query → build.

Target: ≤15 min autonomous, ≤90 min HITL. Designed for Claude Code, Cursor, Windsurf.

## Commands

```bash
# Run skill manually (interactive)
claude --append-system-prompt SKILL.md

# Validate a generated query library against a live DB
python3 scripts/validate_queries.py queries/queries.cypher

# Quick connectivity test (assumes .env exists)
python3 -c "from neo4j import GraphDatabase; import os; from dotenv import load_dotenv; load_dotenv(); d=GraphDatabase.driver(os.getenv('NEO4J_URI'),auth=(os.getenv('NEO4J_USERNAME'),os.getenv('NEO4J_PASSWORD'))); d.verify_connectivity(); print('OK')"
```

No persona test harness ships in this repository.

## Directory Layout

```
neo4j-getting-started-skill/
├── SKILL.md                        ← Main skill (8-stage orchestrator)
├── AGENTS.md                       ← This file
├── README.md
├── references/
│   ├── 0-prerequisites.md … 7-build.md  ← one file per stage
│   ├── domain-patterns.md          ← Pre-built models: social, ecommerce, finance, etc.
│   ├── quick-reference.md
│   └── capabilities/               ← cypher-authoring, execute-cypher, kg-from-documents, mcp-config
└── scripts/
    └── validate_queries.py         ← batch query validator (stage 6)
```

## Conventions

- `SKILL.md` frontmatter: `name`, `description`, `version`, `allowed-tools`, `compatibility`
- References in `references/` named `<N>-<stage>.md`, `<domain>-patterns.md`, or `capabilities/<capability>.md`
- Persona YAML: `persona`, `inputs`, `expected_outputs`, `success_gates`, `test_config`
- All Cypher in reference files must start with `CYPHER 25`
- All generated `.env` files go in the working directory, never committed
- Gate IDs: `db_running`, `model_valid`, `data_present`, `queries_work`, `app_generated`, `mcp_configured`, `time_budget`

## Gotchas

- **Aura Free is 1GB** — synthetic data should stay under 100K nodes to avoid OOM
- **neo4j driver 6.x**: package is `neo4j` (not `neo4j-driver`), requires Python ≥3.10
- **CYPHER 25 pragma**: every generated query must start with `CYPHER 25`
- **aura-cli polling**: use `aura-cli instance get <id> --output json` to check status; parse `.status` field
- **Docker startup**: wait ≥20s after `docker run` before attempting connection
- **MCP config location**: Claude Desktop = `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS); Claude Code = `claude mcp add` (stored in `~/.claude.json`) or project `.mcp.json` — never `settings.json`
- **Notebook validation**: `python -m json.tool notebook.ipynb` checks JSON validity; `jupyter nbconvert --to script` checks cell syntax
- **Official Neo4j MCP server**: binary `neo4j-mcp` from https://github.com/neo4j/mcp. MCP tool names: `get-schema`, `read-cypher`, `write-cypher`, `list-gds-procedures`. Config: `"command": "neo4j-mcp"` + env `NEO4J_MCP_URI/USERNAME/PASSWORD/DATABASE` (2.0+ accepts only `NEO4J_MCP_*`; `NEO4J_MCP_DATABASE` required in STDIO). May be at `$HOME/bin/neo4j-mcp` or `./neo4j-mcp`.
- **Aura provisioning**: Aura REST API (see `references/2-provision.md`) with Bearer token from `https://api.neo4j.io/oauth/token` (HTTP Basic + form-encoded `grant_type=client_credentials`; NOT `/oauth2/token`). Do NOT use `mcp-neo4j-cloud-aura-api`.
- **Connectivity check options**: (1) Python `driver.verify_connectivity()`, (2) `cypher-shell -a ... "RETURN 1"`, (3) Neo4j Query API (HTTP): `POST /db/<db>/query/v2` with `{"statement": "RETURN 1"}` and Basic Auth. Use HTTP fallback when neither driver nor cypher-shell available.
- **neo4j-rust-ext**: always add to Python `requirements.txt` — `neo4j-rust-ext>=0.0.1` only; do not add `neo4j` separately (see `references/7-build.md`).
- **Password hard stop**: write `.env` immediately from provisioning JSON response. Hard stop + tell user to verify `grep PASSWORD .env`.
- **MERGE order**: MERGE all nodes first (per label), then MERGE relationships. Never MERGE a rel before its endpoint nodes exist.
- **Time budget**: 15-min clock starts after DB is RUNNING. Use provisioning wait for Stage 2 design.
- **GDS availability**: Aura Free has NO GDS. Check with `RETURN gds.version() AS gdsVersion` or `list-gds-procedures` MCP tool before generating GDS queries.
- **Query gate**: ≥2 traversal queries required (relationship pattern in MATCH). Count-only queries do not satisfy.
- **Graph visibility gate (hard)**: must print standalone browser URL or add notebook viz cell.
- **App gate**: app must return non-empty results for the use-case question, not just compile.
- **reset.cypher**: always generate — allows clean re-runs of import scripts.
- **Schema first**: always call the `get-schema` MCP tool or `CALL db.schema.visualization()` before generating Cypher
- **MERGE not CREATE**: all data generation must use MERGE for idempotency
- **Parameter defaults for testing**: when executing queries with `$param`, substitute defaults (`LIMIT 20`, string `'test'`) in the validator

## Related Repos

- `/Users/mh/d/llm/neo4j-skills/` — parent skill collection, test harness patterns
- `/Users/mh/d/llm/aura-onboarding-assistant/` — UI onboarding app (10-phase spec in `spec/spec.md`)
- `/Users/mh/d/llm/mcp-neo4j/` — MCP servers: cypher, cloud-aura-api, data-modeling, memory
- `/Users/mh/d/llm/neo4j-mcp/` — standalone Aura MCP server

## Success Gate Definitions

| Gate | What it checks | Pass condition |
|------|---------------|----------------|
| `db_running` | DB connectivity | `driver.verify_connectivity()` no exception |
| `model_valid` | Schema completeness | ≥2 node labels, ≥1 relationship type |
| `data_present` | Data loaded | `MATCH (n) RETURN count(n)` ≥ persona `min_nodes` |
| `queries_work` | Query correctness | ≥3 of 5 queries return ≥1 row |
| `app_generated` | App file exists + valid | File exists + syntax check passes |
| `mcp_configured` | MCP connected | `claude mcp get neo4j` shows the server (or `.mcp.json` has a neo4j entry) |
| `time_budget` | Within time limit | elapsed ≤ `timeout_seconds` from persona YAML |

## Dependencies (pyproject.toml — to be created)

```toml
[project]
name = "neo4j-getting-started-skill-tests"
requires-python = ">=3.10"
dependencies = [
    "neo4j>=6.0.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
]
```
