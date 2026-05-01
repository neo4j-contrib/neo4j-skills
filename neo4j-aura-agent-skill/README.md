# neo4j-aura-agent-skill

Create, configure, and invoke [Neo4j Aura Agents](https://neo4j.com/docs/aura/aura-agent/) — GraphRAG agents backed by an AuraDB knowledge graph.

## What this skill does

- Fetches the graph schema from AuraDB and annotates property types for tool design
- Guides tool selection (CypherTemplate, SimilaritySearch, Text2Cypher) based on use cases and schema
- Creates and manages Aura Agents via the v2beta1 REST API
- Sets system prompts and agent visibility (private/public, REST/MCP)
- Invokes agents with natural language queries and parses responses

## Requirements

- Running AuraDB instance with knowledge graph loaded
- "Generative AI assistance" + "Aura Agent" enabled in Aura org settings
- Project admin access
- `AURA_CLIENT_ID` and `AURA_CLIENT_SECRET` from console.neo4j.io → API Credentials
- Organization ID and Project ID from the Aura console URL

## Install dependencies

```bash
uv sync
```

## Quick start

```bash
# Fetch graph schema and detect vector indexes
uv run python3 scripts/fetch_schema.py

# List existing agents
uv run python3 scripts/manage_agent.py list

# Create an agent from a config file
uv run python3 scripts/manage_agent.py create --config agent-config.json

# Invoke the agent
uv run python3 scripts/invoke_agent.py --agent-id "$AURA_AGENT_ID" "What can you help me with?"
```

## Files

| File | Purpose |
|---|---|
| `SKILL.md` | Agent-readable operational playbook |
| `scripts/fetch_schema.py` | Fetch graph schema from AuraDB; save to `schema.json` |
| `scripts/manage_agent.py` | CRUD operations (list/create/get/update/delete) |
| `scripts/invoke_agent.py` | Send queries to a deployed agent |
| `references/REFERENCE.md` | Full API schema, embedding providers, response formats |
