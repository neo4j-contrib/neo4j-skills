# AGENTS.md — neo4j-getting-started-skill

## Project Purpose

This skill guides a user (or coding agent) from zero to a running Neo4j application.
It covers 5 stages: DB provisioning → data modeling → data import → query generation → app/integration.

Target: ≤15 min autonomous, ≤90 min HITL. Designed for Claude Code, Cursor, Windsurf.

## Commands

```bash
# Run skill manually (interactive)
claude --append-system-prompt SKILL.md

# Run skill with persona (autonomous test)
uv run python3 tests/harness/runner.py --persona tests/personas/alex_beginner.yml --verbose

# Run all personas
uv run python3 tests/harness/runner.py --all-personas

# Quick connectivity test (assumes .env exists)
python3 -c "from neo4j import GraphDatabase; import os; from dotenv import load_dotenv; load_dotenv(); d=GraphDatabase.driver(os.getenv('NEO4J_URI'),auth=(os.getenv('NEO4J_USERNAME'),os.getenv('NEO4J_PASSWORD'))); d.verify_connectivity(); print('OK')"
```

## Directory Layout

```
neo4j-getting-started-skill/
├── SKILL.md                        ← Main skill (system prompt extension)
├── AGENTS.md                       ← This file
├── PLAN.md                         ← Implementation plan with step IDs
├── neo4j-getting-started-research.md ← Research doc, living reference
├── references/
│   ├── stage1-provisioning.md      ← aura-cli, docker, Desktop instructions
│   ├── stage2-data-modeling.md     ← model gen, DDL, arrows.app
│   ├── stage3-data-import.md       ← LOAD CSV, synthetic gen, bulk import
│   ├── stage4-queries.md           ← query templates by domain
│   ├── stage5-apps.md              ← FastAPI, Streamlit, Express, MCP templates
│   ├── domain-patterns.md          ← Pre-built models: social, ecommerce, finance, etc.
│   └── integration-patterns.md    ← LangChain, LlamaIndex, CrewAI, Mastra
└── tests/
    ├── personas/
    │   ├── alex_beginner.yml       ← Persona 1: social network, Aura Free, notebook
    │   ├── sam_developer.yml       ← Persona 2: e-commerce, CSV, FastAPI + MCP
    │   ├── jordan_ai_engineer.yml  ← Persona 3: RAG/KG, GraphRAG pipeline
    │   ├── morgan_analyst.yml      ← Persona 4: fraud detection, Streamlit
    │   └── riley_platform_engineer.yml ← Persona 5: SaaS, multi-instance
    ├── harness/
    │   ├── runner.py               ← Test executor (invokes Claude, validates gates)
    │   └── validator.py            ← 6-gate validation pipeline
    └── results/                    ← JSON + Markdown reports per run
```

## Conventions

- `SKILL.md` frontmatter: `name`, `description`, `version`, `allowed-tools`, `compatibility`
- References in `references/` named `stage{N}-<topic>.md` or `<domain>-patterns.md`
- Persona YAML: `persona`, `inputs`, `expected_outputs`, `success_gates`, `test_config`
- All Cypher in reference files must start with `CYPHER 25`
- All generated `.env` files go in the working directory, never committed
- Gate IDs: `db_running`, `model_valid`, `data_present`, `queries_work`, `app_generated`, `mcp_configured`, `time_budget`

## Gotchas

- **Aura Free is 512MB** — synthetic data should stay under 100K nodes to avoid OOM
- **neo4j driver 6.x**: package is `neo4j` (not `neo4j-driver`), requires Python ≥3.10
- **CYPHER 25 pragma**: every generated query must start with `CYPHER 25`
- **aura-cli polling**: use `aura-cli instance get <id> --output json` to check status; parse `.status` field
- **Docker startup**: wait ≥20s after `docker run` before attempting connection
- **MCP config location**: Claude Desktop = `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS); Claude Code = `~/.claude/settings.json` or `.claude/settings.json` in project
- **Notebook validation**: `python -m json.tool notebook.ipynb` checks JSON validity; `jupyter nbconvert --to script` checks cell syntax
- **Official Neo4j MCP server**: binary `neo4j-mcp` from https://github.com/neo4j/mcp. MCP tool names: `get-schema`, `read-cypher`, `write-cypher`, `list-gds-procedures`. Config: `"command": "neo4j-mcp"` + env `NEO4J_URI/USERNAME/PASSWORD/DATABASE`. May be at `$HOME/bin/neo4j-mcp` or `./neo4j-mcp`.
- **Aura provisioning**: prefer `aura-cli`. Fallback: Aura REST API at `https://api.neo4j.io/v1/` with Bearer token from `https://api.neo4j.io/oauth2/token`. Do NOT use `mcp-neo4j-cloud-aura-api`.
- **Connectivity check options**: (1) Python `driver.verify_connectivity()`, (2) `cypher-shell -a ... "RETURN 1"`, (3) Neo4j Query API (HTTP): `POST /db/<db>/query/v2` with `{"statement": "RETURN 1"}` and Basic Auth. Use HTTP fallback when neither driver nor cypher-shell available.
- **neo4j-rust-ext**: always add to Python `requirements.txt` — `neo4j-rust-ext>=0.0.1` alongside `neo4j>=6.0.0`.
- **Password hard stop**: write `.env` immediately from provisioning JSON response. Hard stop + tell user to verify `grep PASSWORD .env`.
- **MERGE order**: MERGE all nodes first (per label), then MERGE relationships. Never MERGE a rel before its endpoint nodes exist.
- **Time budget**: 15-min clock starts after DB is RUNNING. Use provisioning wait for Stage 2 design.
- **GDS availability**: Aura Free has NO GDS. Check with `CALL gds.version()` or `list-gds-procedures` MCP tool before generating GDS queries.
- **Query gate**: ≥2 traversal queries required (relationship pattern in MATCH). Count-only queries do not satisfy.
- **Graph visibility gate (hard)**: must print standalone browser URL or add notebook viz cell.
- **App gate**: app must return non-empty results for the use-case question, not just compile.
- **reset.cypher**: always generate — allows clean re-runs of import scripts.
- **Schema first**: always call `get-neo4j-schema` or `CALL db.schema.visualization()` before generating Cypher
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
| `mcp_configured` | MCP connected | Settings JSON has neo4j server entry |
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
