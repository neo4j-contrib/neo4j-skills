---
name: neo4j-driver-python-skill
description: >
 Comprehensive guide to using the official Neo4j Python Driver (v6, current stable) — covering
  installation, driver lifecycle, all three query APIs (execute_query, managed transactions via
  execute_read/write, implicit transactions via session.run), async patterns with AsyncGraphDatabase,
  result handling and consumption, data type mapping (including temporal and graph types), UNWIND
  batching, null safety, performance tuning, causal consistency/bookmarks, and connection
  configuration. Use this skill whenever writing Python code that talks to Neo4j, whenever
  reviewing or debugging Neo4j driver usage in Python, or whenever questions arise about sessions,
  transactions, result handling, bookmarks, driver configuration, or async/concurrent patterns.
  Also triggers on neo4j-python-driver, GraphDatabase.driver, execute_query, execute_read,
  execute_write, AsyncGraphDatabase, neo4j.Result, RoutingControl, or any Neo4j Bolt/Aura
  connection work in Python.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  
status: draft
version: 0.1.1
allowed-tools: Bash, WebFetch
---

# Neo4j Python Driver

**Package**: `neo4j`  
**Current stable**: v6  
**Docs**: https://neo4j.com/docs/python-manual/current/  
**API ref**: https://neo4j.com/docs/api/python-driver/current/

---

## 1. Installation

```bash
pip install neo4j
```

For async support, no additional packages are needed — `asyncio` is in the standard library. For Pandas integration, install `pandas` separately.

---

## 2. Driver Lifecycle

`Driver` is **thread-safe and expensive to create** — create exactly one instance per application, share it everywhere, and close it on shutdown. Use it as a context manager or call `.close()` explicitly.

```python
from neo4j import GraphDatabase

URI  = "neo4j+s://xxx.databases.neo4j.io"  # Aura
AUTH = ("neo4j", "password")

# Preferred: context manager handles close automatically
with GraphDatabase.driver(URI, auth=AUTH) as driver:
    driver.verify_connectivity()   # fail fast if unreachable
    # ... do work ...

# Long-lived singleton (e.g. in a service class):
driver = GraphDatabase.driver(URI, auth=AUTH)
driver.verify_connectivity()
# ... later, on shutdown:
driver.close()
```

### URI Schemes

| Scheme | When to use |
|--------|-------------|
| `neo4j://` | Unencrypted, cluster-routing |
| `neo4j+s://` | TLS, cluster-routing — **use for Aura** |
| `bolt://` | Unencrypted, single instance |
| `bolt+s://` | TLS, single instance |

### Auth Options

```python
from neo4j import GraphDatabase, basic_auth, bearer_auth, kerberos_auth

GraphDatabase.driver(URI, auth=("user", "password"))   # basic — tuple shorthand
GraphDatabase.driver(URI, auth=basic_auth("user", "password"))
GraphDatabase.driver(URI, auth=bearer_auth("jwt-token"))
GraphDatabase.driver(URI, auth=kerberos_auth("base64ticket"))
```

---

## 3. Choosing the Right API

| API | When to use | Auto-retry? | Streaming? |
|-----|-------------|-------------|------------|
| `driver.execute_query()` | Most queries — simple, safe default | ✅ | ❌ (eager) |
| `session.execute_read/write()` | Large results, need lazy streaming | ✅ | ✅ |
| `session.run()` | `LOAD CSV`, quick scripts, `CALL {} IN TRANSACTIONS` | ❌ | ✅ |
| `AsyncGraphDatabase` | asyncio applications | ✅ | ✅ |

---

## 4. `execute_query` — Recommended Default

The highest-level API. Manages sessions, transactions, retries, and bookmarks automatically.

### `EagerResult` — Three Ways to Access the Return Value

`execute_query` returns an `EagerResult` object. It supports **three access patterns** — understanding all three prevents common confusion:

```python
from neo4j import GraphDatabase, RoutingControl

# Pattern 1: Tuple unpacking (most common)
records, summary, keys = driver.execute_query(
    "MATCH (p:Person) RETURN p.name AS name",
    database_="neo4j",
)

# Pattern 2: Attribute access on the returned object
result = driver.execute_query(
    "MATCH (p:Person) RETURN p.name AS name",
    database_="neo4j",
)
records = result.records    # list[Record]
summary = result.summary    # ResultSummary
keys    = result.keys       # list[str], e.g. ['name']

# Pattern 3: Direct iteration — EagerResult is iterable over its records
for record in driver.execute_query("MATCH (p:Person) RETURN p.name AS name", database_="neo4j"):
    print(record["name"])   # ✅ works — iterates over records directly

# Pattern 4: Index access — also supported
result = driver.execute_query("MATCH (p:Person) RETURN p.name AS name", database_="neo4j")
first = result[0]           # ✅ first Record — same as result.records[0]
```

**What NOT to do:**

```python
result = driver.execute_query("MATCH (p:Person) RETURN p.name AS name", database_="neo4j")

# ❌ Treating the result as a single record
result["name"]          # AttributeError — EagerResult has no key access; index into .records first

# ❌ Assuming len() gives record count directly
len(result)             # actually works (returns len of records), but surprising — be explicit:
len(result.records)     # ✅ clear intent
```

```python
# Full example with read routing
records, summary, keys = driver.execute_query(
    "MATCH (p:Person {name: $name})-[:KNOWS]->(friend) RETURN friend.name AS name",
    name="Alice",
    routing_=RoutingControl.READ,   # route reads to replicas
    database_="neo4j",              # always specify — avoids a round-trip
)

for record in records:
    print(record["name"])

print(f"Returned {len(records)} records in {summary.result_available_after} ms")
print(f"Keys projected: {keys}")    # ['name']

# Write query — access summary via attribute or unpacking
summary = driver.execute_query(
    "CREATE (p:Person {name: $name, age: $age})",
    name="Bob", age=30,
    database_="neo4j",
).summary
print(f"Created {summary.counters.nodes_created} nodes")
```

### ⚠ Trailing Underscore Convention — Critical Gotcha

Config kwargs to `execute_query` **must end with a single underscore** to distinguish them from query parameters. This includes `database_`, `routing_`, `auth_`, `result_transformer_`, `bookmark_manager_`, and `impersonated_user_`.

**No query parameter name may end with a single underscore** — the driver will raise `ValueError` if it detects this collision. Pass such parameters via the `parameters_` dict instead:

```python
# ❌ Fails — 'name_' clashes with the driver's config namespace
driver.execute_query("MATCH (p:Person {name: $name_}) RETURN p", name_="Alice")

# ✅ Use parameters_ dict for any parameter whose name ends with _
driver.execute_query(
    "MATCH (p:Person {name: $name_}) RETURN p",
    parameters_={"name_": "Alice"},
    database_="neo4j",
)

# ✅ Or rename the Cypher parameter to avoid the underscore
driver.execute_query(
    "MATCH (p:Person {name: $name}) RETURN p",
    name="Alice",
    database_="neo4j",
)
```

**⚠ Never f-string or format Cypher.** Always use `$param` placeholders — prevents injection and enables query plan caching on the server.

### Result Transformers

`execute_query` accepts a `result_transformer_` callable to reshape the result before it's returned:

```python
import neo4j

# Built-in: return a Pandas DataFrame (requires pandas installed)
df = driver.execute_query(
    "MATCH (p:Person) RETURN p.name AS name, p.age AS age",
    database_="neo4j",
    result_transformer_=neo4j.Result.to_df,
)

# Built-in: return a single record — behaviour depends on result count (see below)
record = driver.execute_query(
    "MATCH (p:Person {name: $name}) RETURN p",
    name="Alice",
    database_="neo4j",
    result_transformer_=neo4j.Result.single,
)

# Custom transformer — receives the raw Result, must consume it here
def first_names(result: neo4j.Result) -> list[str]:
    return [record["name"] for record in result]

names = driver.execute_query(
    "MATCH (p:Person) RETURN p.name AS name",
    database_="neo4j",
    result_transformer_=first_names,
)
```

### `result.single()` — Raises on Zero, Not Just Multiple

`result.single()` is **not** like SQLAlchemy's `.scalar_one_or_none()`. It raises `ResultNotSingleError` when the result contains **zero records** as well as when it contains **two or more**. Many models assume it returns `None` for zero results — it does not, by default.

```python
# ❌ Common misconception — assuming single() returns None for zero results
def find_person(tx):
    result = tx.run("MATCH (p:Person {name: $name}) RETURN p", name="Nobody")
    record = result.single()    # raises ResultNotSingleError, not returns None
    if record is None:          # never reached
        return None
    return record["p"]

# ✅ strict=False — returns None for zero results, still raises for 2+
def find_person_safe(tx):
    result = tx.run("MATCH (p:Person {name: $name}) RETURN p", name="Alice")
    record = result.single(strict=False)   # None if 0 results, Record if 1, raises if 2+
    if record is None:
        return None
    return record["p"]

# ✅ In execute_query with result_transformer_ — same two-mode behaviour applies
# Default (strict=True): raises for 0 or 2+ results
record = driver.execute_query(
    "MATCH (p:Person {name: $name}) RETURN p",
    name="Alice",
    database_="neo4j",
    result_transformer_=neo4j.Result.single,   # raises if Alice not found
)

# For "find or None" semantics: write a custom transformer
def single_or_none(result):
    return result.single(strict=False)   # None if not found

record = driver.execute_query(
    "MATCH (p:Person {name: $name}) RETURN p",
    name="Alice",
    database_="neo4j",
    result_transformer_=single_or_none,
)
```

**Summary of `single()` modes:**

| Result count | `single()` (strict=True, default) | `single(strict=False)` |
|---|---|---|
| 0 records | raises `ResultNotSingleError` | returns `None` |
| 1 record | returns the `Record` | returns the `Record` |
| 2+ records | raises `ResultNotSingleError` | raises `ResultNotSingleError` |

---

## 5. Managed Transactions (`execute_read` / `execute_write`)

Use when you need **lazy streaming** over large results, or when you want to run multiple queries inside one transaction.

```python
with driver.session(database="neo4j") as session:

    # Read — routes to replicas; callback auto-retried on transient failure
    def get_people(tx):
        result = tx.run(
            "MATCH (p:Person) WHERE p.name STARTS WITH $prefix RETURN p.name AS name",
            prefix="Al",
        )
        # ✅ Consume the Result INSIDE the callback — it is invalid after the tx closes
        return [record["name"] for record in result]

    names = session.execute_read(get_people)

    # Write — routes to leader
    def create_person(tx):
        tx.run("CREATE (p:Person {name: $name})", name="Carol")

    session.execute_write(create_person)
```

### Critical: Result Lifetime in Transaction Functions

`Result` is a **lazy cursor backed by the open transaction**. The transaction closes the moment the callback returns. Reading a `Result` after that raises `ResultConsumedError`.

```python
# ❌ WRONG — leaks the Result out of the transaction
def bad_tx(tx):
    return tx.run("MATCH (p:Person) RETURN p.name AS name")
    # Result returned here; tx closes immediately after

result = session.execute_read(bad_tx)
list(result)   # raises ResultConsumedError — the cursor is already closed

# ✅ CORRECT — fully consume the result before the function returns
def good_tx(tx):
    result = tx.run("MATCH (p:Person) RETURN p.name AS name")
    return [record["name"] for record in result]   # consumed while tx is open
```

### Multiple `tx.run()` Calls

If you call `tx.run()` a second time before the first `Result` is consumed, the driver automatically **buffers the first result in memory** before running the next query. This is safe, but means you can accidentally pull a large result into RAM. Consume each result before the next call when working with large datasets:

```python
def multi_query_tx(tx):
    # First result — consume it immediately
    people = [r["name"] for r in tx.run("MATCH (p:Person) RETURN p.name AS name")]

    # Second query — safe, first result is already consumed
    for name in people:
        tx.run("MERGE (p:Person {name: $name})-[:VISITED]->(:City {name: 'London'})",
               name=name)

    return len(people)
```

### Retry Safety

The callback **may execute more than once** on transient failures. Keep callbacks idempotent:

```python
# ❌ Side effect runs on every retry
def dangerous_tx(tx):
    requests.post("https://api.example.com/notify")  # fires on every retry
    tx.run("CREATE (p:Person {name: $name})", name="Alice")

# ✅ Pure database work; HTTP call made only on confirmed success
def safe_tx(tx):
    tx.run("MERGE (p:Person {name: $name})", name="Alice")  # MERGE is idempotent

session.execute_write(safe_tx)
# Make the HTTP call here, outside the callback, once write is confirmed
requests.post("https://api.example.com/notify")
```

### TransactionConfig — Timeouts & Metadata

Use `@unit_of_work` to attach a timeout and metadata to a managed transaction function:

```python
from neo4j import unit_of_work

@unit_of_work(timeout=5.0, metadata={"app": "myService", "user": user_id})
def get_people(tx):
    return [r["name"] for r in tx.run("MATCH (p:Person) RETURN p.name AS name")]

session.execute_read(get_people)
```

The `@unit_of_work` decorator attaches the config to the function. Metadata appears in `SHOW TRANSACTIONS` and server query logs.

### ⚠ `@unit_of_work` Cannot Be Applied to Lambdas

Python does not allow decorating a lambda expression. This is a common trap — if you use a lambda for a simple transaction (which is convenient), you silently lose the ability to set a timeout or metadata:

```python
# ❌ Syntax error — cannot decorate a lambda
session.execute_write(
    @unit_of_work(timeout=5.0)
    lambda tx: tx.run("MERGE (p:Person {name: $name})", name="Alice")
)

# ❌ Also wrong — @unit_of_work has no effect when called after the fact
fn = lambda tx: tx.run("MERGE (p:Person {name: $name})", name="Alice")
unit_of_work(timeout=5.0)(fn)   # wraps fn, but the session.execute_write call
session.execute_write(fn)       # still uses the original fn, not the wrapped version

# ✅ Correct — define a named function and decorate it
@unit_of_work(timeout=5.0, metadata={"app": "myService"})
def create_person(tx):
    tx.run("MERGE (p:Person {name: $name})", name="Alice")

session.execute_write(create_person)

# ✅ Also correct — assign the decorated version explicitly
create_person = unit_of_work(timeout=5.0)(lambda tx: tx.run(
    "MERGE (p:Person {name: $name})", name="Alice"
))
session.execute_write(create_person)
```

The practical rule: **use named functions whenever you need a timeout or metadata; lambdas are fine for fire-and-forget callbacks where server-default timeouts are acceptable**.

---

## 6. Implicit Transactions (`session.run`)

The lowest-level, least safe API. **Not automatically retried.** Use only for:
- `LOAD CSV` imports (must use auto-commit transactions)
- `CALL { } IN TRANSACTIONS` Cypher
- Quick prototyping

```python
with driver.session(database="neo4j") as session:
    result = session.run("CREATE (p:Person {name: $name})", name="Alice")
    summary = result.consume()   # ⚠ call consume() to ensure the tx commits
    print(summary.counters.nodes_created)
```

**Commit timing is non-obvious**: an implicit transaction commits *at the latest* when the session is closed, or immediately before the next query in the same session. Do not rely on this ordering — always call `.consume()` when you need a guaranteed commit before proceeding.

```python
# ❌ Fragile — commit timing is undefined between the two runs
with driver.session(database="neo4j") as session:
    session.run("CREATE (p:Person {name: 'Alice'})")
    session.run("MATCH (p:Person {name: 'Alice'}) SET p.age = 30")  # may not see Alice

# ✅ Explicit consume ensures first tx is committed before the second runs
with driver.session(database="neo4j") as session:
    session.run("CREATE (p:Person {name: 'Alice'})").consume()
    session.run("MATCH (p:Person {name: 'Alice'}) SET p.age = 30")
```

Since the driver cannot determine whether `session.run()` requires read or write access, it defaults to **write mode**. If your implicit transaction is read-only, declare it:

```python
with driver.session(database="neo4j", default_access_mode=neo4j.READ_ACCESS) as session:
    result = session.run("MATCH (p:Person) RETURN p.name AS name")
```

---

## 7. Explicit Transactions

Use when a transaction must span multiple functions or coordinate with external systems.

```python
with driver.session(database="neo4j") as session:
    tx = session.begin_transaction()
    try:
        do_part_a(tx)
        do_part_b(tx)
        tx.commit()
    except Exception as e:
        tx.rollback()   # rollback can itself raise on network failure — see below
        raise

def do_part_a(tx):
    tx.run("CREATE (p:Person {name: $name})", name="Alice")
```

### Rollback Can Raise

`tx.rollback()` is a network call. If the connection is broken, it raises. Don't let it swallow the original exception:

```python
try:
    tx.commit()
except Exception as original:
    try:
        tx.rollback()
    except Exception as rollback_err:
        original.__suppress_context__ = False
        raise rollback_err from original   # chain both exceptions
    raise
```

### Commit Uncertainty

If `tx.commit()` raises a network-level exception, the commit may or may not have succeeded on the server. Design writes to be idempotent with `MERGE` and unique constraints so retrying is always safe.

---

## 8. Async API

For `asyncio` applications. The async API mirrors the sync API exactly — replace `GraphDatabase` with `AsyncGraphDatabase` and `await` every call.

### Async Driver Is Also a Singleton

The async driver is **just as expensive to create as the sync driver** — connection pool, DNS resolution, and TLS handshake all happen at construction time. Do not recreate it per request.

```python
# ❌ Wrong — recreates the driver (and tears down the connection pool) on every call
async def handle_request(name: str):
    async with AsyncGraphDatabase.driver(URI, auth=AUTH) as driver:
        records, _, _ = await driver.execute_query("MATCH (p:Person {name: $name}) RETURN p",
                                                    name=name, database_="neo4j")
    return records

# ✅ Correct — driver created once at app startup, shared for the lifetime of the process
driver = AsyncGraphDatabase.driver(URI, auth=AUTH)

async def handle_request(name: str):
    records, _, _ = await driver.execute_query("MATCH (p:Person {name: $name}) RETURN p",
                                                name=name, database_="neo4j")
    return records

# Close at shutdown
await driver.close()
```

### Web Framework Lifespan Pattern (FastAPI / Starlette)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from neo4j import AsyncGraphDatabase

_driver = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _driver
    _driver = AsyncGraphDatabase.driver(URI, auth=AUTH)
    await _driver.verify_connectivity()
    yield                       # app runs here
    await _driver.close()       # called on shutdown

app = FastAPI(lifespan=lifespan)

def get_driver():
    return _driver              # injected via FastAPI Depends()

@app.get("/people")
async def get_people():
    records, _, _ = await get_driver().execute_query(
        "MATCH (p:Person) RETURN p.name AS name",
        database_="neo4j",
        routing_=RoutingControl.READ,
    )
    return [r["name"] for r in records]
```

### Basic Async Usage

```python
import asyncio
from neo4j import AsyncGraphDatabase

URI  = "neo4j+s://xxx.databases.neo4j.io"
AUTH = ("neo4j", "password")

async def main():
    async with AsyncGraphDatabase.driver(URI, auth=AUTH) as driver:
        await driver.verify_connectivity()

        records, summary, keys = await driver.execute_query(
            "MATCH (p:Person) RETURN p.name AS name",
            database_="neo4j",
            routing_=RoutingControl.READ,
        )
        names = [r["name"] for r in records]
        print(names)

asyncio.run(main())
```

### Async Managed Transactions

```python
async def get_people(tx):
    result = await tx.run("MATCH (p:Person) RETURN p.name AS name")
    # ✅ Consume inside the async callback — await the collection
    return await result.values()   # returns list of lists [[name], [name], ...]

async def create_person(tx, name: str):
    await tx.run("MERGE (p:Person {name: $name})", name=name)

async def run_queries(driver):
    async with driver.session(database="neo4j") as session:
        people = await session.execute_read(get_people)
        await session.execute_write(create_person, "Carol")
```

### Async Result Methods

| Method | Returns | Notes |
|--------|---------|-------|
| `await result.values()` | `list[list]` | Each inner list is one row of values |
| `await result.data()` | `list[dict]` | Each dict is one record keyed by column name |
| `await result.single()` | one `Record` | Raises if not exactly one record |
| `await result.fetch(n)` | `list[Record]` | Up to n records |
| `await result.consume()` | `ResultSummary` | Discards remaining, returns summary |
| `async for record in result` | iterates `Record` | Lazy streaming |

### ⚠ Do Not Mix Sync and Async Drivers

Never use the sync `GraphDatabase.driver` in an `asyncio` context — it blocks the event loop. Always use `AsyncGraphDatabase.driver` in async code, even for a single query.

```python
# ❌ Blocks the event loop — other coroutines cannot run during the query
async def bad():
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        records, _, _ = driver.execute_query("MATCH (p:Person) RETURN p")

# ✅ Async driver keeps the event loop free
async def good():
    async with AsyncGraphDatabase.driver(URI, auth=AUTH) as driver:
        records, _, _ = await driver.execute_query("MATCH (p:Person) RETURN p")
```

### Concurrency with asyncio

```python
async def run_concurrent(driver):
    # Run multiple queries concurrently with asyncio.gather
    results = await asyncio.gather(
        driver.execute_query("MATCH (a:Artist) RETURN a.name AS name", database_="neo4j"),
        driver.execute_query("MATCH (v:Venue) RETURN v.name AS name",  database_="neo4j"),
    )
    artists = [r["name"] for r in results[0].records]
    venues  = [r["name"] for r in results[1].records]
```

---

## 9. Error Handling

```python
from neo4j.exceptions import (
    Neo4jError,
    DriverError,
    ServiceUnavailable,
    SessionExpired,
    TransientError,
    AuthError,
    ConstraintError,       # unique/existence constraint violation — most common app-level error
)

try:
    driver.execute_query("...", database_="neo4j")
except AuthError as e:
    print("Bad credentials:", e)
except ServiceUnavailable as e:
    print("No servers reachable:", e)
except TransientError as e:
    # execute_query and execute_read/write retry automatically;
    # this is only raised once retries are exhausted
    print(f"Transient error after retries: {e.code}")
except ConstraintError as e:
    # Unique or existence constraint violation — subclass of Neo4jError
    # Must be caught BEFORE the generic Neo4jError handler
    print(f"Constraint violation [{e.code}]: {e.message}")
except Neo4jError as e:
    # Server-side Cypher or other database error
    print(f"Neo4j error [{e.code}]: {e.message}")
    # GQL status code for stable programmatic handling:
    if e.gql_status == "42001":   # SyntaxError
        print("Fix the query syntax")
```

### `ConstraintError` — Unique Constraint Violations

`ConstraintError` is the most common application-level database error and should almost always be handled explicitly. It is a **subclass of `Neo4jError`**, so a bare `except Neo4jError` will catch it — but silently, without letting you branch on "this specific node already exists" vs "something else went wrong".

```python
from neo4j.exceptions import ConstraintError

def create_user(driver, username: str) -> bool:
    """Returns True if created, False if username already exists."""
    try:
        driver.execute_query(
            "CREATE (u:User {username: $username})",
            username=username,
            database_="neo4j",
        )
        return True
    except ConstraintError:
        # Neo4j raised Neo.ClientError.Schema.ConstraintValidationFailed
        # because a unique constraint on User.username was violated
        return False

# Constraint violation codes follow a predictable pattern:
# e.code == "Neo.ClientError.Schema.ConstraintValidationFailed"
# e.message contains the constraint name and offending value
```

**Important catch ordering**: because `ConstraintError` is a subclass of `Neo4jError`, always catch it *before* the generic `Neo4jError` handler, or it will be swallowed by the parent.

**GQL status codes** (stable across versions) are preferable to error message strings for programmatic handling. Use `e.gql_status` or `e.find_by_gql_status("42001")` rather than parsing `e.message`.

---

## 10. Record Access & Null Safety

### Accessing Values

```python
records, _, _ = driver.execute_query(
    "MATCH (p:Person) RETURN p.name AS name, p.age AS age",
    database_="neo4j",
)

record = records[0]

# By key — raises KeyError if key absent
name = record["name"]

# By index — 0-based, positional
name = record[0]

# .get() — returns None for both absent keys AND graph null (see below)
name = record.get("name")
name = record.get("name", "Unknown")   # with default

# .data() — converts the record to a dict keyed by column name
d = record.data()   # {"name": "Alice", "age": 30}
```

### `record.data()` Is Not JSON-Serializable

`.data()` returns a `dict`, but **the values are still driver objects for graph and temporal types** — it does not recursively convert to Python primitives. Calling `json.dumps(record.data())` will raise `TypeError` if any field contains a `Node`, `Relationship`, `Path`, or `neo4j.time.*` value.

```python
# Query returning a node: MATCH (p:Person) RETURN p
record = records[0]

d = record.data()
# d == {"p": <Node element_id='4:...' labels=frozenset({'Person'}) properties={'name': 'Alice'}>}
# The value is a Node object, NOT a dict

import json
json.dumps(d)   # ❌ raises TypeError: Object of type Node is not JSON serializable

# ❌ Also fails for temporal types:
# d == {"created_at": <DateTime 2024-01-01T00:00:00.000000000+00:00>}
json.dumps(d)   # TypeError: Object of type DateTime is not JSON serializable
```

To get a fully JSON-safe dict, extract properties explicitly:

```python
# ✅ For simple scalar fields — .data() is fine
records, _, _ = driver.execute_query(
    "MATCH (p:Person) RETURN p.name AS name, p.age AS age",  # scalar projections
    database_="neo4j",
)
d = records[0].data()     # {"name": "Alice", "age": 30} — safe to json.dumps()

# ✅ For node/relationship fields — extract properties manually
records, _, _ = driver.execute_query(
    "MATCH (p:Person) RETURN p",   # returns whole node
    database_="neo4j",
)
node = records[0]["p"]            # neo4j.graph.Node
props = dict(node)                # {"name": "Alice", "age": 30} — plain dict of properties

# ✅ For temporal types — convert explicitly before serializing
from neo4j.time import DateTime
dt = records[0]["created_at"]     # neo4j.time.DateTime
iso = str(dt)                     # "2024-01-01T00:00:00.000000000+00:00" — JSON-safe string
py_dt = dt.to_native()            # datetime.datetime — also JSON-safe via isoformat()

# ✅ General pattern: project scalars in Cypher rather than returning whole nodes
records, _, _ = driver.execute_query("""
    MATCH (p:Person)
    RETURN p.name AS name, p.age AS age, toString(p.created_at) AS created_at
    """,
    database_="neo4j",
)
# Now .data() is fully JSON-safe
safe_dicts = [r.data() for r in records]
json.dumps(safe_dicts)   # ✅ works
```

### Null Safety — Absent Key vs Graph Null

These are two distinct situations that both surface as `None` when using `.get()` — which hides the difference:

| Situation | `record["key"]` | `record.get("key")` |
|-----------|-----------------|---------------------|
| Key projected, value non-null | the value | the value |
| Key projected, value is graph null | `None` | `None` |
| Key absent (typo / not in RETURN) | **raises `KeyError`** | `None` |

```python
# ❌ Typo — silent None when using .get(), explodes with [] when you least expect it
record.get("nme")       # None — no error, typo goes undetected
record["nme"]           # KeyError — caught earlier

# When a column is from OPTIONAL MATCH, graph null gives None:
# Query: OPTIONAL MATCH (p)-[:LIVES_IN]->(c:City) RETURN p.name AS name, c.name AS city
city = record.get("city")    # None when no City matched — same as an absent key via .get()
```

The safest pattern for optional columns:

```python
# Check key presence explicitly for truly optional columns:
if "city" in record.keys() and record["city"] is not None:
    city = record["city"]
else:
    city = "Unknown"

# Or rely on .get() with a sentinel and accept that it covers both cases:
city = record.get("city") or "Unknown"
```

### Graph Types

```python
# Node
node = record["p"]              # neo4j.graph.Node
node.element_id                 # stable identifier within this transaction
node.labels                     # frozenset({'Person'})
node["name"]                    # property access by key
dict(node)                      # all properties as plain dict

# Relationship
rel = record["r"]               # neo4j.graph.Relationship
rel.type                        # 'KNOWS'
rel.start_node.element_id
rel.end_node.element_id
rel["since"]                    # property

# ⚠ element_id is only guaranteed stable within one transaction.
# Do not use it to MATCH entities across separate transactions.
```

### Temporal Types

The driver returns Neo4j temporal values as `neo4j.time` types, not native Python `datetime`. Conversion is lossy:

```python
from neo4j.time import DateTime

dt = record["created_at"]       # neo4j.time.DateTime
type(dt)                        # <class 'neo4j.time.DateTime'>

# Convert to Python datetime — loses sub-microsecond precision and some timezone info
py_dt = dt.to_native()          # datetime.datetime

# Pass Python datetime as a parameter — driver converts automatically
from datetime import datetime, timezone
driver.execute_query(
    "CREATE (e:Event {at: $ts})",
    ts=datetime.now(timezone.utc),
    database_="neo4j",
)
```

---

## 11. Data Types & Parameter Mapping

### Allowed Parameter Types

Only these types (and `None`) are valid as query parameter values:

| Python type | Cypher type |
|-------------|-------------|
| `str` | String |
| `int` | Integer |
| `float` | Float |
| `bool` | Boolean |
| `list` / `tuple` | List |
| `dict` | Map |
| `None` | null |
| `datetime.date` | Date |
| `datetime.datetime` | DateTime |
| `datetime.time` | Time |
| `datetime.timedelta` | Duration |
| `neo4j.time.*` types | Corresponding Cypher temporal |

Custom classes, dataclasses, Pydantic models, and enums are **not** automatically serialised. Convert to `dict` or primitive values before passing as parameters.

```python
from dataclasses import dataclass, asdict

@dataclass
class Person:
    name: str
    age: int

p = Person("Alice", 30)

# ❌ Fails — driver can't serialise a dataclass
driver.execute_query("CREATE (p:Person $props)", props=p, database_="neo4j")

# ✅ Convert to dict first
driver.execute_query("CREATE (p:Person $props)", props=asdict(p), database_="neo4j")
# or pass fields individually:
driver.execute_query("CREATE (p:Person {name: $name, age: $age})",
                     name=p.name, age=p.age, database_="neo4j")
```

---

## 12. Performance

### Always Specify the Database

Omitting `database_` causes the driver to resolve the home database with an extra network round-trip on every call.

```python
# execute_query:
driver.execute_query("...", database_="neo4j")

# Session:
driver.session(database="neo4j")
```

### Route Reads to Replicas

```python
from neo4j import RoutingControl

# execute_query:
driver.execute_query("MATCH ...", routing_=RoutingControl.READ, database_="neo4j")

# Managed transaction — execute_read routes automatically:
session.execute_read(my_read_fn)
```

### Batch Writes with UNWIND

Pass a `list[dict]` — each dict becomes one row in the Cypher loop. This is the only shape the driver serialises correctly for `UNWIND`.

```python
# ❌ Wrong — passing a list of dataclass instances or custom objects
people = [Person("Alice", 30), Person("Bob", 25)]
driver.execute_query("UNWIND $people AS p MERGE (:Person {name: p.name})",
                     people=people, database_="neo4j")   # raises at runtime

# ✅ Correct — list of plain dicts
people = [
    {"name": "Alice", "age": 30, "city": "London"},
    {"name": "Bob",   "age": 25, "city": "Paris"},
]
driver.execute_query("""
    UNWIND $people AS person
    MERGE (p:Person {name: person.name})
    SET p.age = person.age
    MERGE (c:City {name: person.city})
    MERGE (p)-[:LIVES_IN]->(c)
    """,
    people=people,
    database_="neo4j",
)
```

### Group Multiple Writes in One Transaction

```python
# Bad: one transaction per item — high overhead
for item in items:
    driver.execute_query("CREATE (n:Node {id: $id})", id=item["id"], database_="neo4j")

# Good: all in one managed transaction
def bulk_create(tx):
    for item in items:
        tx.run("CREATE (n:Node {id: $id})", id=item["id"])

with driver.session(database="neo4j") as session:
    session.execute_write(bulk_create)
```

### Lazy vs Eager Loading

```python
# execute_query is always eager — fine for small/medium result sets
records, _, _ = driver.execute_query("MATCH (p:Person) RETURN p", database_="neo4j")

# For large results, iterate lazily inside a managed transaction
def process_large_result(tx):
    result = tx.run("MATCH (p:Person) RETURN p.name AS name")
    for record in result:          # streams one record at a time
        process(record["name"])    # don't build a list

with driver.session(database="neo4j") as session:
    session.execute_read(process_large_result)
```

### Concurrency — The GIL Matters

The Python GIL means that **threads do not give true parallelism** for CPU-bound work, but they do overlap on I/O (network waits). For heavy parallel database work, `asyncio` with `AsyncGraphDatabase` is the better approach:

```python
# Sync threading — helps with I/O overlap, but GIL limits true parallelism
from concurrent.futures import ThreadPoolExecutor

def query(name):
    records, _, _ = driver.execute_query(
        "MATCH (p:Person {name: $name}) RETURN p", name=name, database_="neo4j"
    )
    return records

with ThreadPoolExecutor(max_workers=10) as pool:
    results = list(pool.map(query, names))

# Async — preferred for high-concurrency read workloads
async def run_all(names):
    async with AsyncGraphDatabase.driver(URI, auth=AUTH) as driver:
        tasks = [
            driver.execute_query("MATCH (p:Person {name: $name}) RETURN p",
                                  name=name, database_="neo4j")
            for name in names
        ]
        return await asyncio.gather(*tasks)
```

### Connection Pool Tuning

```python
driver = GraphDatabase.driver(
    URI, auth=AUTH,
    max_connection_pool_size=50,              # default: 100
    connection_acquisition_timeout=30,        # seconds to wait for a free connection
    max_connection_lifetime=3600,             # seconds; recycle old connections
    connection_timeout=15,                    # seconds to establish a new connection
    keep_alive=True,                          # TCP keepalive
)
```

**Session exhaustion**: each open session holds a connection. If sessions are not closed promptly, the pool is exhausted and new sessions block for up to `connection_acquisition_timeout` seconds then raise `ClientError`. Always use sessions as context managers.

---

## 13. Causal Consistency & Bookmarks

**Within a single session**, queries are automatically causally chained — nothing to do.

**Across sessions**, use `execute_query` (auto-managed) or pass bookmarks explicitly:

```python
from neo4j import Bookmarks

# Sessions A and B run concurrently; session C must see both writes
with driver.session(database="neo4j") as session_a:
    session_a.execute_write(lambda tx: tx.run("MERGE (p:Person {name: 'Alice'})"))
    bookmarks_a = session_a.last_bookmarks()

with driver.session(database="neo4j") as session_b:
    session_b.execute_write(lambda tx: tx.run("MERGE (p:Person {name: 'Bob'})"))
    bookmarks_b = session_b.last_bookmarks()

combined = Bookmarks.from_raw_values(
    *bookmarks_a.raw_values, *bookmarks_b.raw_values
)

# Session C waits until both Alice and Bob exist
with driver.session(database="neo4j", bookmarks=combined) as session_c:
    session_c.execute_write(
        lambda tx: tx.run("MATCH (a:Person {name:'Alice'}), (b:Person {name:'Bob'}) "
                          "MERGE (a)-[:KNOWS]->(b)")
    )
```

`execute_query` shares a `BookmarkManager` automatically across calls — usually all you need.

---

## 14. Repository Pattern — Recommended Structure

```python
from neo4j import Driver, RoutingControl
from dataclasses import dataclass

@dataclass
class Person:
    name: str
    age: int

class PersonRepository:
    def __init__(self, driver: Driver, database: str = "neo4j"):
        self._driver = driver
        self._db = database

    def find_by_name_prefix(self, prefix: str) -> list[Person]:
        records, _, _ = self._driver.execute_query(
            "MATCH (p:Person) WHERE p.name STARTS WITH $prefix RETURN p.name AS name, p.age AS age",
            prefix=prefix,
            routing_=RoutingControl.READ,
            database_=self._db,
        )
        return [Person(name=r["name"], age=r["age"]) for r in records]

    def create(self, person: Person) -> None:
        self._driver.execute_query(
            "CREATE (p:Person {name: $name, age: $age})",
            name=person.name, age=person.age,
            database_=self._db,
        )

    def bulk_create(self, people: list[Person]) -> None:
        rows = [{"name": p.name, "age": p.age} for p in people]
        self._driver.execute_query(
            "UNWIND $rows AS row MERGE (p:Person {name: row.name}) SET p.age = row.age",
            rows=rows,
            database_=self._db,
        )
```

---

## 15. Quick Reference: Common Mistakes

| Mistake | Fix |
|---------|-----|
| f-string / format Cypher params | Use `$param` placeholders always |
| Param name ending with `_` | Pass via `parameters_={"name_": val}` dict |
| Omitting `database_` | Always set — saves a round-trip every call |
| Returning `Result` from a tx function | Consume to `list` / `dict` inside the function |
| Buffering large results before second `tx.run()` | Consume eagerly or restructure to avoid parallel cursors |
| Side effects inside `execute_read/write` callbacks | Move outside — callback may be retried |
| Passing dataclass/Pydantic objects as params | Convert to `dict` or primitive fields first |
| Passing custom objects to UNWIND | `list[dict]` is the only supported shape |
| Using `record.get()` to detect absent vs graph null | They both return `None`; use `"key" in record.keys()` for absent key detection |
| Not calling `.consume()` after `session.run()` | Commit timing undefined; call `.consume()` for guaranteed commit |
| Using sync driver inside `asyncio` | Use `AsyncGraphDatabase.driver` — sync driver blocks the event loop |
| Recreating async driver per request | Async driver is a singleton — create once at app startup |
| Not closing sessions | Use `with driver.session(...) as session` — leaked sessions exhaust the pool |
| Creating a new `Driver` per request | Create once at startup; share everywhere |
| One transaction per write in a loop | Batch with `UNWIND` or group in one `execute_write` callback |
| `MERGE` for guaranteed-new data | Use `CREATE` — `MERGE` does an internal match first |
| Using `execute_write` for reads | Use `execute_read` — routes to replicas |
| Calling `json.dumps(record.data())` with graph/temporal fields | Project scalar fields in Cypher or convert driver objects explicitly |
| `result["name"]` on an `EagerResult` | Index into `result.records` first, or unpack: `records, _, _ = ...` |
| Assuming `result.single()` returns `None` for zero results | It raises — use `result.single(strict=False)` for None-on-empty behaviour |
| `@unit_of_work` on a lambda | Assign the decorated version: `fn = unit_of_work(timeout=5)(lambda tx: ...)` |
| Catching `Neo4jError` before `ConstraintError` | Catch `ConstraintError` first — it's a subclass of `Neo4jError` |