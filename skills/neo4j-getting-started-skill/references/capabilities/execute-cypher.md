# Capability — execute-cypher
# Three options for running Cypher statements against Neo4j.

Detect and record `EXEC_METHOD` in the `context` stage — priority order:
1. `mcp` — if neo4j-mcp is running as an MCP server in this session
2. `cypher-shell` — if `cypher-shell` is on PATH
3. `query-api` — HTTP fallback, always available when DB is reachable

Store as `EXEC_METHOD=mcp|cypher-shell|query-api` and use it consistently across all stages.

---

## Option 1 — neo4j-mcp (MCP tools)

Use when: neo4j-mcp is configured as an MCP server in this agent session.

**Read query**:
```
use tool: read-cypher
params: { query: "CYPHER 25 MATCH (n) RETURN count(n) AS total", params: {} }
```

**Write query**:
```
use tool: write-cypher
params: { query: "CYPHER 25 MERGE (n:Label {id: $id}) SET n.name = $name", params: { "id": "1", "name": "Test" } }
```

**Schema inspection**:
```
use tool: get-schema
```

---

## Option 2 — cypher-shell

Use when: `which cypher-shell` succeeds.

```bash
source .env

# Read query
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
  --database "${NEO4J_DATABASE:-neo4j}" \
  "CYPHER 25 MATCH (n) RETURN count(n) AS total"

# Run a .cypher file
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
  --database "${NEO4J_DATABASE:-neo4j}" \
  --file schema.cypher

# Write query
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
  "CYPHER 25 MERGE (n:Label {id: '1'}) SET n.name = 'Test'"
```

---

## Option 3 — Neo4j Query API (HTTP)

Use when neither MCP nor cypher-shell is available. Works with `curl` only — no Neo4j client needed.

```bash
source .env
# Derive HTTPS host from bolt URI
HOST=$(echo "$NEO4J_URI" | sed 's|neo4j+s://||;s|bolt://||;s|neo4j://||;s|bolt+s://||')
DB="${NEO4J_DATABASE:-neo4j}"
AUTH="$NEO4J_USERNAME:$NEO4J_PASSWORD"

# Read query
curl -s -X POST "https://${HOST}/db/${DB}/query/v2" \
  -H "Content-Type: application/json" \
  -u "$AUTH" \
  -d '{"statement": "CYPHER 25 MATCH (n) RETURN count(n) AS total"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(r) for r in d.get('data',{}).get('values',[])]"

# Write query
curl -s -X POST "https://${HOST}/db/${DB}/query/v2" \
  -H "Content-Type: application/json" \
  -u "$AUTH" \
  -d '{"statement": "CYPHER 25 MERGE (n:Label {id: $id}) SET n.name = $name", "parameters": {"id": "1", "name": "Test"}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin))"
```

Note: for local Docker, use `http://localhost:7474` instead of `https://${HOST}`.

---

## Python driver (always available when neo4j package installed)

```python
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()
driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
)

# Read
records, summary, keys = driver.execute_query(
    "CYPHER 25 MATCH (n:<Label>) RETURN n LIMIT $limit",
    limit=20,
    database_=os.environ.get("NEO4J_DATABASE", "neo4j")
)

# Write (use write-transaction for mutations)
driver.execute_query(
    "CYPHER 25 MERGE (n:<Label> {id: $id}) SET n.name = $name",
    id="1", name="Test",
    database_=os.environ.get("NEO4J_DATABASE", "neo4j")
)

driver.close()
```
