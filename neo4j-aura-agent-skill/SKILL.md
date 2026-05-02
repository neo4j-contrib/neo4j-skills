---
name: neo4j-aura-agent-skill
description: Manages Neo4j Aura Agents via the v2beta1 REST API — create, list, get, update, delete,
  and invoke GraphRAG agents backed by an AuraDB instance. Use when configuring Aura Agent tools
  (CypherTemplate, SimilaritySearch, Text2Cypher), setting system prompts, deploying agents to REST
  or MCP endpoints, or invoking agents with natural language queries. Covers OAuth2 auth,
  organization/project scoping, tool parameter schemas, and InvokeAgentResponse format.
  Does NOT cover AuraDB instance provisioning — use neo4j-aura-provisioning-skill.
  Does NOT cover vector index creation — use neo4j-vector-index-skill.
version: 1.0.0
allowed-tools: Bash WebFetch
---

## When to Use
- Creating or configuring an Aura Agent on an existing AuraDB instance
- Adding/updating tools (CypherTemplate, SimilaritySearch, Text2Cypher) to an agent
- Deploying an agent for external access (REST API endpoint or MCP server)
- Invoking an agent with natural language queries via REST API
- Listing, reading, or deleting existing agents in a project

## When NOT to Use
- **Creating/managing AuraDB instances** → `neo4j-aura-provisioning-skill`
- **Creating vector indexes** → `neo4j-vector-index-skill`
- **Running Cypher directly** → `neo4j-cypher-skill`
- **Building Aura Graph Analytics sessions** → `neo4j-aura-graph-analytics-skill`

---

## Prerequisites
- Running AuraDB instance with knowledge graph loaded
- "Generative AI assistance" enabled in Organization settings
- "Aura Agent" toggled on in the project
- "Tool authentication" enabled at project/Security level
- Project admin access
- `AURA_CLIENT_ID` and `AURA_CLIENT_SECRET` from console.neo4j.io → Account Settings → API Credentials
- `AURA_ORG_ID`, `AURA_PROJECT_ID` — see Step 2; `AURA_INSTANCE_ID` — resolved interactively in Step 2 if not already set
- Python env: `uv sync` in skill directory (or `pip install neo4j neo4j-graphrag requests python-dotenv`)
- `.env` and `schema.json` in `.gitignore`

---

## Step 1 — Verify Auth

Scripts call `get_token()` internally — this step is for manual credential verification only.

```bash
TOKEN=$(curl -s --request POST 'https://api.neo4j.io/oauth/token' \
  --user "${AURA_CLIENT_ID}:${AURA_CLIENT_SECRET}" \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=client_credentials' \
  | jq -r '.access_token')
echo "Token: ${TOKEN:0:20}..."
```

If blank token: verify `AURA_CLIENT_ID`/`AURA_CLIENT_SECRET` in `.env`. **Stop and report.**
Token TTL: 3600 s. Re-run on 401/403.

---

## Step 2 — Resolve Organization & Project IDs

**From console URL** (fastest): open console.neo4j.io → navigate to a project. URL pattern:
`/organizations/{AURA_ORG_ID}/projects/{AURA_PROJECT_ID}`

**Programmatic fallback**:
```bash
curl -s https://api.neo4j.io/v1/tenants \
  -H "Authorization: Bearer $TOKEN" | jq '.data[] | {id, name}'
# tenant id maps to AURA_PROJECT_ID
```

Set in `.env`:
```
AURA_ORG_ID=<organization-id>
AURA_PROJECT_ID=<project-id>
```

**Check `AURA_INSTANCE_ID`** — if it is already set in `.env`, skip the rest of this step.

If not set, list available instances and ask the user to choose:

```bash
curl -s "https://api.neo4j.io/v1/instances?tenantId=${AURA_PROJECT_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.data[] | {id, name, status, region, type}'
```

Show the output to the user. Ask: **"Which instance should the agent connect to?"** Wait for the user to select one, then write to `.env`:

```
AURA_INSTANCE_ID=<chosen-instance-id>
NEO4J_URI=neo4j+s://<chosen-instance-id>.databases.neo4j.io
```

If the list is empty: no AuraDB instances exist in this project — an Aura Agent cannot be created without one. **Stop and report.**
If `401`: re-run Step 1. If `404`: verify `AURA_PROJECT_ID`. **Stop and report.**

---

## Step 3 — List Existing Agents

Validates API connectivity and shows what is already deployed.

```bash
uv run python3 scripts/manage_agent.py list
```

```powershell
uv run python scripts\manage_agent.py list
```

Output: agent IDs, names, enabled status, endpoint URLs.

If `401`: re-run Step 1. If `404`: verify `AURA_ORG_ID`/`AURA_PROJECT_ID`. **Stop and report.**

---

## Step 4 — Fetch Graph Schema

Requires `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` in `.env`.

```bash
uv run python3 scripts/fetch_schema.py
```

```powershell
uv run python scripts\fetch_schema.py
```

Saves `schema.json`. Output: node/rel-type counts, node labels + typed properties (with Aura `data_type`), relationship patterns, VECTOR indexes.

**Data gate** — script exits with error and does NOT write `schema.json` if:
- fewer than 2 nodes, OR
- zero relationship types

If gate fails: load data into the database before proceeding. **Stop and report.**
If `ServiceUnavailable`: check `NEO4J_URI` uses `neo4j+s://`; instance must be `running`. **Stop and report.**
If `neo4j-graphrag not found`: `uv add neo4j-graphrag`. **Stop and report.**

Read `schema.json` before Step 5.

---

## Step 5 — Discover Use Cases

Before designing tools, read [references/authoring-guide.md](references/authoring-guide.md).

**Ask the user these questions. Do NOT guess tool types or parameters.**

1. "What questions should this agent answer?"
2. "Which nodes or relationships matter most?" — match against `schema.json → node_props`
3. "Do users search by a specific property value?" → CypherTemplate
4. "Any counting, grouping, or date-range questions?" → Text2Cypher
5. "Search for semantically similar text?" → check `schema.json → metadata → vector_index`
   - No VECTOR index found: inform user; skip SimilaritySearch; delegate to `neo4j-vector-index-skill` first
   - VECTOR index found: ask the user — **"Which embedding provider and model should be used? What output dimension?"** See supported models in `references/REFERENCE.md → Embedding Provider Options`. Do NOT guess or default.

Tool selection:

| Use Case | Tool |
|---|---|
| Lookup by specific property value | `cypherTemplate` |
| Semantic text search | `similaritySearch` |
| Aggregation, counting, open-ended | `text2cypher` |

**CypherTemplate parameters**: for each parameter, read `aura_data_type` from `schema.json → node_props` or `rel_props` and use it as `data_type`. If the property has `low_cardinality: true`, the parameter `description` MUST list the valid values — copy them from the `values` array in `schema.json`. Example: `"description": "Agreement type to filter by. Valid values: \"Distributor Agreement\", \"License Agreement\", \"NDA\""`. Properties with `has_fulltext_index: true` are especially likely to be filter targets and must include valid values when low cardinality.

**SimilaritySearch configuration** — ask the user for all three before drafting the tool config:

| Field | What to ask | Source |
|---|---|---|
| `provider` | "openai" or "vertexai"? | User confirms |
| `model` | Which model? | User picks from `references/REFERENCE.md → Embedding Provider Options` |
| `dimension` | What output dimension? | Required if model is configurable (see table); fixed models use the table value |

`index`: use `name` from `schema.json → metadata → vector_index` where `state = ONLINE`. `dimension` must match `vector.dimensions` in the same index entry.

**Signals inventory**: for each label or relationship that appears in a tool or the user's stated questions, write a signal block in the system prompt. See `references/authoring-guide.md → Signals inventory` for the template and rules.

Draft config JSON → show to user for review → confirm → proceed to Step 6.

---

## Step 6 — Create Agent

Minimum required config:
```json
{
  "name": "My Agent",
  "description": "Answers questions about the graph",
  "dbid": "<AURA_INSTANCE_ID>",
  "is_private": false,
  "tools": [
    {
      "type": "text2cypher",
      "name": "Query Graph",
      "description": "Translates natural language questions into Cypher queries"
    }
  ]
}
```

**Show config to user and confirm before running:**
```bash
uv run python3 scripts/manage_agent.py create --config agent-config.json
```

Response includes `id` (save as `AURA_AGENT_ID`), `endpoint_link`, `mcp_endpoint_link`.

---

## Step 7 — Invoke Agent (Test)

```bash
uv run python3 scripts/invoke_agent.py --agent-id "$AURA_AGENT_ID" "What can you help me with?"
```

`--raw` prints full JSON including reasoning chain and token usage.

Direct curl (uses token from Step 1):
```bash
curl -s -X POST \
  "https://api.neo4j.io/v2beta1/organizations/${AURA_ORG_ID}/projects/${AURA_PROJECT_ID}/agents/${AURA_AGENT_ID}/invoke" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"input": "What can you help me with?"}'
```

---

## Step 8 — Update Agent (Partial PATCH)

Create patch JSON with only the fields to change:
```json
{ "system_prompt": "Updated instructions.", "is_mcp_enabled": true }
```

**Show to user and confirm before running:**
```bash
uv run python3 scripts/manage_agent.py update --agent-id "$AURA_AGENT_ID" --config patch.json
```

---

## Step 9 — Delete Agent

IRREVERSIBLE. Configuration permanently removed.

**Show to user and wait for explicit confirmation before running:**
```bash
uv run python3 scripts/manage_agent.py delete --agent-id "$AURA_AGENT_ID"
```

Returns 202 Accepted.

---

## Tool Configuration

### CypherTemplate
Pre-defined parameterized queries. Use for repeated, predictable lookups.

```json
{
  "type": "cypherTemplate",
  "name": "<descriptive name>",
  "description": "<what it looks up and when to use it>",
  "enabled": true,
  "config": {
    "template": "MATCH (n:Label {prop: $param}) RETURN n",
    "parameters": [
      {
        "name": "param",
        "data_type": "<string|integer|number|boolean — from schema.json aura_data_type>",
        "description": "<what the parameter represents. If low_cardinality=true in schema.json, append: Valid values: \"val1\", \"val2\", ...>"
      }
    ]
  }
}
```

Low-cardinality rule: if `schema.json → node_props[Label][prop].low_cardinality` is `true`, the `description` field must end with the exact values from `schema.json → node_props[Label][prop].values`. This applies to relationship properties in `rel_props` too.

### SimilaritySearch
Requires a VECTOR index (`state = ONLINE`). Get index name from `schema.json → metadata → vector_index`.

```json
{
  "type": "similaritySearch",
  "name": "<descriptive name>",
  "description": "<what text it searches and when to use it>",
  "enabled": true,
  "config": {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "index": "<name from schema.json metadata.vector_index[state=ONLINE].name>",
    "top_k": 5,
    "dimension": "<vector.dimensions from schema.json metadata.vector_index options.indexConfig>",
    "post_processing_cypher": "<optional: Cypher to enrich similarity results with related nodes>"
  }
}
```

`provider`/`model` combinations: see [references/REFERENCE.md](references/REFERENCE.md).

### Text2Cypher
Natural language → Cypher. Use as fallback for aggregation and discovery.

```json
{
  "type": "text2cypher",
  "name": "<descriptive name>",
  "description": "<what questions it handles — and explicitly what it should NOT handle>",
  "enabled": true
}
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Token expired | Re-run Step 1 |
| `403 Forbidden` on create | Not a project admin | Request admin access |
| `400 Bad Request` | Invalid tool config or missing required field | Check `type` spelling: `cypherTemplate`, `similaritySearch`, `text2cypher` |
| `404 Not Found` | Wrong org/project/agent ID | Re-run `list` to verify IDs |
| `400` on create with SimilaritySearch | Vector index missing | Create index first — use `neo4j-vector-index-skill` |
| Agent returns no results | `top_k` too low or index empty | Increase `top_k`; verify index is populated |

---

## Scripts

All scripts load credentials from `.env` automatically. Run with `uv run python3 <script>`.

| Script | Purpose |
|---|---|
| `scripts/fetch_schema.py` | Fetch graph schema from AuraDB; save to `schema.json` |
| `scripts/manage_agent.py` | CRUD: list, create, get, update, delete agents |
| `scripts/invoke_agent.py` | Send a natural language query to an agent |

**fetch_schema.py parameters:**

| Parameter | Type | Required | Default |
|---|---|---|---|
| `NEO4J_URI` | env | Yes | — |
| `NEO4J_USERNAME` | env | No | `neo4j` |
| `NEO4J_PASSWORD` | env | Yes | — |
| `NEO4J_DATABASE` | env | No | `neo4j` |

**manage_agent.py parameters:**

| Parameter | Type | Required | Env fallback |
|---|---|---|---|
| `AURA_CLIENT_ID` | env | Yes | — |
| `AURA_CLIENT_SECRET` | env | Yes | — |
| `--org-id` | arg | No | `AURA_ORG_ID` |
| `--project-id` | arg | No | `AURA_PROJECT_ID` |
| `--agent-id` | arg | get/update/delete | `AURA_AGENT_ID` |
| `--config` | arg | create/update | — |

**invoke_agent.py parameters:**

| Parameter | Type | Required | Env fallback |
|---|---|---|---|
| `AURA_CLIENT_ID` | env | Yes | — |
| `AURA_CLIENT_SECRET` | env | Yes | — |
| `--org-id` | arg | No | `AURA_ORG_ID` |
| `--project-id` | arg | No | `AURA_PROJECT_ID` |
| `--agent-id` | arg | Yes | `AURA_AGENT_ID` |
| `query` | positional | Yes | — |
| `--raw` | flag | No | — |

---

## Checklist
- [ ] AuraDB instance `running`, knowledge graph loaded
- [ ] "Generative AI assistance" + "Aura Agent" enabled in org/project settings
- [ ] `.env` populated: `AURA_CLIENT_ID`, `AURA_CLIENT_SECRET`, `AURA_ORG_ID`, `AURA_PROJECT_ID`, `AURA_INSTANCE_ID`, `NEO4J_URI`, `NEO4J_PASSWORD`
- [ ] `.env` and `schema.json` in `.gitignore`
- [ ] Auth verified (Step 1)
- [ ] Org/Project IDs confirmed (Step 2)
- [ ] API connectivity confirmed via `list` (Step 3)
- [ ] `schema.json` fetched and reviewed (Step 4) — data gate passed (≥2 nodes, ≥1 rel type)
- [ ] Use cases confirmed with user (Step 5)
- [ ] CypherTemplate `data_type` taken from `schema.json aura_data_type`
- [ ] SimilaritySearch `index` from `schema.json metadata.vector_index` (state=ONLINE)
- [ ] Agent config shown to user and confirmed (Step 6)
- [ ] Required fields present: `name`, `description`, `dbid`, `is_private`, `tools` (min 1)
- [ ] `AURA_AGENT_ID` saved from create response
- [ ] Agent invoked and response verified (Step 7)
- [ ] Update/Delete confirmed by user before execution
