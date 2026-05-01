# Aura Agent API Reference (v2beta1)

## Base URL

```
https://api.neo4j.io/v2beta1
```

## Auth

All requests require a Bearer token obtained via:
```
POST https://api.neo4j.io/oauth/token
Authorization: Basic base64(CLIENT_ID:CLIENT_SECRET)
Content-Type: application/x-www-form-urlencoded
Body: grant_type=client_credentials
```

Token TTL: 3600 s. On 401/403: re-authenticate.

---

## Agent Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/organizations/{orgId}/projects/{projectId}/agents` | List agents |
| `POST` | `/organizations/{orgId}/projects/{projectId}/agents` | Create agent |
| `GET` | `/organizations/{orgId}/projects/{projectId}/agents/{agentId}` | Get agent |
| `PUT` | `/organizations/{orgId}/projects/{projectId}/agents/{agentId}` | Full replace |
| `PATCH` | `/organizations/{orgId}/projects/{projectId}/agents/{agentId}` | Partial update |
| `DELETE` | `/organizations/{orgId}/projects/{projectId}/agents/{agentId}` | Delete agent |
| `POST` | `/organizations/{orgId}/projects/{projectId}/agents/{agentId}/invoke` | Invoke agent |

---

## CreateAgentRequest Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✅ | Max 100 chars |
| `description` | string | ✅ | |
| `dbid` | string | ✅ | AuraDB instance ID |
| `is_private` | boolean | ✅ | `false` = accessible to project members; `true` = creator only |
| `tools` | array | ✅ | Min 1 tool; see Tool Schemas |
| `system_prompt` | string | ❌ | Custom instructions for the LLM |
| `is_mcp_enabled` | boolean | ❌ | Enable MCP server endpoint |
| `enabled` | boolean | ❌ | Default: `true` |

## PatchAgentRequest Schema

All fields optional: `name`, `description`, `system_prompt`, `dbid`, `is_private`, `is_mcp_enabled`, `tools`, `enabled`.

---

## Tool Schemas

### CypherTemplate

```json
{
  "type": "cypherTemplate",
  "name": "string (required)",
  "description": "string",
  "enabled": true,
  "config": {
    "template": "MATCH (n {id: $id}) RETURN n",
    "parameters": [
      {
        "name": "id",
        "data_type": "string",
        "description": "Node ID to look up (max 2000 chars)"
      }
    ]
  }
}
```

`data_type` enum: `string` | `number` | `boolean` | `integer`

### SimilaritySearch

```json
{
  "type": "similaritySearch",
  "name": "string (required)",
  "description": "string",
  "enabled": true,
  "config": {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "index": "vector_index_name",
    "top_k": 5,
    "dimension": 1536,
    "post_processing_cypher": "OPTIONAL MATCH (node)<-[:HAS_EXCERPT]-(cc) RETURN node, score, cc"
  }
}
```

`dimension` must match the vector index dimension (`vector.dimensions` in `schema.json → metadata.vector_index[].options.indexConfig`). `post_processing_cypher` is optional — use it to traverse from matched nodes to related context nodes.

### Text2Cypher

```json
{
  "type": "text2cypher",
  "name": "string (required)",
  "description": "string",
  "enabled": true
}
```

---

## Embedding Provider Options

### OpenAI (also via Azure OpenAI)

| Model | Dimensions |
|---|---|
| `text-embedding-3-small` | 1536 |
| `text-embedding-3-large` | 3072 |
| `text-embedding-ada-002` | 1536 |

### Vertex AI (Google)

| Model | Notes |
|---|---|
| `gemini-embedding-001` | General purpose |
| `text-embedding-005` | Optimized for retrieval |
| `text-multi-lingual-embedding-002` | Multilingual |

---

## AgentDetails Response Schema

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "system_prompt": "string",
  "dbid": "string",
  "project_id": "string",
  "organization_id": "string",
  "created_by": "string",
  "created_at": "datetime",
  "updated_at": "datetime",
  "is_private": false,
  "is_mcp_enabled": false,
  "enabled": true,
  "endpoint_link": "https://api.neo4j.io/v2beta1/organizations/.../invoke",
  "mcp_endpoint_link": "https://api.neo4j.io/v2beta1/organizations/.../mcp",
  "tools": [...]
}
```

---

## InvokeAgentRequest

```json
{ "input": "How many contracts are in the database?" }
```

Or multi-turn:
```json
{
  "input": [
    { "role": "user", "content": "What contracts does Acme Corp have?" }
  ]
}
```

Note: Aura Agent does NOT store conversation history between requests. Include prior context in `input` array for multi-turn.

## InvokeAgentResponse

```json
{
  "id": "string",
  "type": "message",
  "role": "assistant",
  "content": [
    { "type": "text", "text": "There are 510 contracts in the database." },
    { "type": "tool_use", "name": "Aggregation and Discovery Tool", "input": {...} },
    { "type": "tool_result", "content": [...] }
  ],
  "end_reason": "end_turn",
  "status": "completed",
  "usage": {
    "request_tokens": 245,
    "response_tokens": 87,
    "total_tokens": 332
  }
}
```

`type` enum: `message` | `error`

Error response:
```json
{
  "type": "error",
  "error": {
    "message": "Agent not found",
    "type": "not_found",
    "status_code": 404
  }
}
```

---

## HTTP Status Codes

| Code | Meaning |
|---|---|
| `200` | Success (list, get, update, invoke) |
| `201` | Agent created |
| `202` | Delete accepted |
| `400` | Invalid request body or parameters |
| `401` | Token expired or missing |
| `403` | Insufficient permissions (not project admin) |
| `404` | Agent/project/org not found |
| `500` | Server error — retry with backoff |

---

## Neo4j → Aura Agent Type Mapping

Used when reading `schema.json` to set `data_type` in CypherTemplate parameters.
`fetch_schema.py` pre-computes the `aura_data_type` field on every property.

| Neo4j Property Type | Aura `data_type` | Notes |
|---|---|---|
| `STRING` | `string` | |
| `INTEGER` | `integer` | |
| `LONG` | `integer` | Neo4j internal; maps to integer |
| `FLOAT` | `number` | |
| `DOUBLE` | `number` | |
| `BOOLEAN` | `boolean` | |
| `DATE` | `string` | Pass as ISO 8601: `"2024-01-15"` |
| `DATE_TIME` | `string` | Pass as ISO 8601: `"2024-01-15T10:00:00Z"` |
| `LOCAL_DATE_TIME` | `string` | Pass as `"2024-01-15T10:00:00"` |
| `LOCAL_TIME` | `string` | Pass as `"10:00:00"` |
| `TIME` | `string` | Pass as `"10:00:00+01:00"` |
| `DURATION` | `string` | Pass as ISO 8601 duration: `"P1Y2M"` |
| `POINT` | `string` | Pass as WKT: `"POINT(1.0 2.0)"` |
| `LIST` | `string` | Serialize as JSON string |
| `MAP` | `string` | Serialize as JSON string |
| `ANY` | `string` | Fallback |

---

## schema.json Structure

Output of `scripts/fetch_schema.py`. Extends `get_structured_schema()` with type annotations, cardinality enrichment, and index metadata.

```json
{
  "node_props": {
    "Agreement": [
      {
        "property": "contract_id", "type": "INTEGER", "aura_data_type": "integer",
        "low_cardinality": false, "has_fulltext_index": false
      },
      {
        "property": "agreement_type", "type": "STRING", "aura_data_type": "string",
        "low_cardinality": true,
        "values": ["Distributor Agreement", "License Agreement", "NDA"],
        "has_fulltext_index": false
      }
    ],
    "ContractClause": [
      {
        "property": "type", "type": "STRING", "aura_data_type": "string",
        "low_cardinality": true,
        "values": ["Anti-Assignment", "Exclusivity", "Governing Law"],
        "has_fulltext_index": true
      }
    ]
  },
  "rel_props": {
    "IS_PARTY_TO": [
      {
        "property": "role", "type": "STRING", "aura_data_type": "string",
        "low_cardinality": true, "values": ["Buyer", "Seller"],
        "has_fulltext_index": false
      }
    ]
  },
  "relationships": [
    {"start": "Agreement", "type": "HAS_CLAUSE", "end": "ContractClause"},
    {"start": "Organization", "type": "IS_PARTY_TO", "end": "Agreement"}
  ],
  "metadata": {
    "node_count": 1240,
    "constraint": [...],
    "index": [...],
    "vector_index": [
      {
        "name": "excerpt_embedding",
        "type": "VECTOR",
        "labelsOrTypes": ["Excerpt"],
        "properties": ["embedding"],
        "state": "ONLINE",
        "options": {
          "indexConfig": {"vector.dimensions": 3072},
          "indexProvider": "vector-2.0"
        }
      }
    ],
    "fulltext_index": [
      {
        "name": "clause_type_fulltext",
        "type": "FULLTEXT",
        "labelsOrTypes": ["ContractClause"],
        "properties": ["type"],
        "state": "ONLINE"
      }
    ]
  }
}
```

Key fields:
- `aura_data_type` — Aura-compatible `data_type` value; use directly in CypherTemplate parameters
- `low_cardinality` — `true` if ≤50 distinct values; `description` MUST list valid values when true
- `values` — sorted list of distinct values; only present when `low_cardinality: true`
- `has_fulltext_index` — `true` if a FULLTEXT index covers this property; priority filter target
- `metadata.vector_index` — usable in SimilaritySearch; filter by `state == "ONLINE"`; use `name` as `index`, `options.indexConfig["vector.dimensions"]` as `dimension`
- `metadata.fulltext_index` — cross-referenced to set `has_fulltext_index` on matching properties

---

## Geography Constraint

All Aura Agents run in `europe-west1` (Belgium, GCP). Regardless of AuraDB instance region, agent inference happens in EU. Consider data residency requirements before storing PII in agent queries.

---

## External Access (REST + MCP)

Enable via `is_private: false` and optionally `is_mcp_enabled: true` in the agent config.

External endpoint URL format:
```
https://api.neo4j.io/v2beta1/organizations/{orgId}/projects/{projectId}/agents/{agentId}/invoke
```

MCP server URL format:
```
https://api.neo4j.io/v2beta1/organizations/{orgId}/projects/{projectId}/agents/{agentId}/mcp
```

Both require the same OAuth2 bearer token. Use Aura API credentials (`AURA_CLIENT_ID` / `AURA_CLIENT_SECRET`) — not Neo4j database credentials.
