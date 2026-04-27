---
name: neo4j-driver-python-skill
description: >
  Use when writing Python code that connects to Neo4j: installing the neo4j package,
  configuring GraphDatabase.driver() or AsyncGraphDatabase, execute_query() patterns,
  session and transaction management, connection pooling, error handling, or result
  serialization (.data()). Also covers FastAPI/asyncio async driver usage.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT handle driver version upgrades — use neo4j-migration-skill.
  Does NOT handle GraphRAG pipelines — use neo4j-graphrag-skill.
status: draft
version: 0.1.0
allowed-tools: Bash, WebFetch
---

# Neo4j Python Driver Skill

> **Status: Draft / WIP** — Content is a placeholder. Reference files and extended patterns to be added.

## When to Use

- Setting up the Neo4j Python driver in a new project (`pip install neo4j`)
- Writing `GraphDatabase.driver()` singleton, `execute_query()`, session/transaction patterns
- Configuring async driver (`AsyncGraphDatabase`) for FastAPI or asyncio applications
- Handling connection pooling, retry policies, or error types
- Serializing Neo4j `Record`/`Node`/`Relationship` objects to JSON (`.data()`)
- Configuring credentials from `.env` (python-dotenv)

## When NOT to Use

- **Writing or optimizing Cypher queries** → use `neo4j-cypher-skill`
- **Upgrading from an older driver version** → use `neo4j-migration-skill`
- **GraphRAG pipelines (neo4j-graphrag package)** → use `neo4j-graphrag-skill`
- **GDS Python client (graphdatascience)** → use `neo4j-gds-skill`

---

## Setup

> **Package name**: install `neo4j`, NOT `neo4j-driver`. The `neo4j-driver` package is deprecated since 6.0 and may install an outdated version.

```bash
pip install neo4j python-dotenv   # Python >= 3.10 required
# pip install neo4j-driver  ← WRONG — deprecated, use `neo4j` only
```

```
# .env
NEO4J_URI=neo4j+s://<instance>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password>
NEO4J_DATABASE=neo4j
```

---

## Core Patterns

### Sync driver (singleton)

> **`database_` note**: the trailing underscore in `execute_query(..., database_='neo4j')` is intentional — it disambiguates from user-supplied query parameters named `database`. Omitting it routes to the server's default home database, which may differ from what you expect in multi-database setups.

> **`.data()` note**: `.data()` converts a single `Record` to a plain dict. For a list of records use `[r.data() for r in records]`. Raw `Record`, `Node`, and `Relationship` objects do not JSON-serialize.

```python
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()  # MUST be called before os.getenv() — reads .env file into environment

with GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD"))
) as driver:
    driver.verify_connectivity()
    records, summary, keys = driver.execute_query(
        "MATCH (p:Person {name: $name})-[:KNOWS]->(f) RETURN f.name AS friend",
        name="Alice",
        database_=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    data = [r.data() for r in records]  # serialize to plain dicts
```

### Async driver (FastAPI / asyncio)

```python
from neo4j import AsyncGraphDatabase

driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

async def get_friends(name: str):
    records, _, _ = await driver.execute_query(
        "MATCH (p:Person {name: $name})-[:KNOWS]->(f) RETURN f.name AS friend",
        name=name, database_="neo4j"
    )
    return [r["friend"] for r in records]

# close on shutdown:
await driver.close()
```

### Explicit session + write transaction

```python
def transfer(tx, from_id, to_id, amount):
    tx.run("MATCH (a:Account {id: $id}) SET a.balance = a.balance - $amt",
           id=from_id, amt=amount)
    tx.run("MATCH (a:Account {id: $id}) SET a.balance = a.balance + $amt",
           id=to_id, amt=amount)

with driver.session(database="neo4j") as session:
    session.execute_write(transfer, "acc-1", "acc-2", 100)
```

### Error handling

```python
from neo4j.exceptions import AuthError, ServiceUnavailable, ConstraintError, TransientError

try:
    records, _, _ = driver.execute_query("MATCH (p:Person {id: $id}) RETURN p", id="1")
except AuthError:
    # wrong credentials
except ServiceUnavailable:
    # database unreachable
except ConstraintError:
    # unique constraint violated
except TransientError:
    # automatically retried inside execute_write/execute_read
```

---

## Checklist

- [ ] One driver instance per process (singleton), not per request
- [ ] `load_dotenv()` called before reading env vars; credentials never hardcoded
- [ ] `.env` in `.gitignore`
- [ ] `database_` (trailing underscore) used to specify database in `execute_query()`
- [ ] `.data()` called on records when JSON serialization is needed
- [ ] `AsyncGraphDatabase` used with FastAPI/asyncio (not sync driver)
- [ ] `driver.close()` / `await driver.close()` called on shutdown (or use context manager)

---

## Fetching Current Docs

If you need up-to-date driver API details not covered here, fetch the docs index:
```
https://neo4j.com/docs/llms.txt  ← full documentation index (all doc sets, all drivers)
https://neo4j.com/llms-full.txt  ← rich reference with code examples
```

## References

- [Python Driver Manual](https://neo4j.com/docs/python-manual/)
- [execute_query API](https://neo4j.com/docs/python-manual/current/query-simple/)
- [Transaction management](https://neo4j.com/docs/python-manual/current/transactions/)
- [GraphAcademy: Using Neo4j with Python](https://graphacademy.neo4j.com/courses/drivers-python/)
