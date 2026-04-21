# Python driver (`neo4j`)

Install: `pip install neo4j`. For 3–10× speedup with the same API, install `neo4j-rust-ext`.

## Canonical example

```python
from neo4j import GraphDatabase, RoutingControl

URI = "neo4j://localhost:7687"
AUTH = ("neo4j", "password")

with GraphDatabase.driver(URI, auth=AUTH) as driver:
    driver.verify_connectivity()

    records, summary, keys = driver.execute_query(
        "MATCH (p:Person {name: $name}) RETURN p.name AS name, p.age AS age",
        name="Alice",
        database_="neo4j",
        routing_=RoutingControl.READ,   # or the string "r"
    )

    for r in records:
        name, age = r["name"], r["age"]
```

By default `execute_query` returns an `EagerResult` unpackable as `(records, summary, keys)`. Access fields by key (`r["name"]`) or index (`r[0]`). When `result_transformer_` is set, the call returns whatever the transformer returns instead.

`record.data()` returns a `dict` of the whole record and is handy for prototyping or interactive sessions — the Python driver docs explicitly call it "convenient but opinionated", not a general-purpose serializer. It materializes every field, flattens `Node`/`Relationship`/`Path` into nested dicts/lists (losing type info), and leaves temporal types as driver objects. Prefer reading the fields you need; reach for `.data()` only when that trade-off is fine.

If you do want `.data()` semantics, skip the list comprehension and pass `Result.data` as the transformer — one pass, no intermediate `Record` list:

```python
from neo4j import GraphDatabase, Result, RoutingControl

rows, summary, keys = driver.execute_query(
    "MATCH (p:Person {name: $name}) RETURN p.name AS name, p.age AS age",
    name="Alice",
    database_="neo4j",
    routing_=RoutingControl.READ,
    result_transformer_=Result.data,
)
# rows is list[dict]
```

## Parameters

Pass as kwargs (any name not ending in `_`) or as `parameters_={...}`:

```python
driver.execute_query("MERGE (:Person {name: $name})", name="Alice", database_="neo4j")
driver.execute_query("MERGE (:Person {name: $name})", parameters_={"name": "Alice"}, database_="neo4j")
```

Config kwargs end in `_`: `database_`, `routing_`, `auth_`, `impersonated_user_`, `result_transformer_`, `bookmark_manager_`.

## Bulk writes — one round-trip

```python
driver.execute_query(
    "UNWIND $rows AS row MERGE (p:Person {id: row.id}) SET p += row",
    rows=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
    database_="neo4j",
)
```

## Result transformers

```python
import neo4j

df = driver.execute_query(
    "MATCH (p:Person) RETURN p.name AS name, p.age AS age",
    database_="neo4j",
    result_transformer_=neo4j.Result.to_df,      # pandas DataFrame
)

graph = driver.execute_query(
    "MATCH (a)-[r]->(b) RETURN a, r, b",
    database_="neo4j",
    result_transformer_=neo4j.Result.graph,      # nodes + relationships
)
```

A transformer receives a `Result` and must not return it — consume it (`result.single()`, `list(result)`, etc.).

## When to drop to a session

Use only when you need multiple queries + client logic in **one** transaction, or want to stream large results:

```python
def transfer(tx, from_id, to_id, amount):
    balance = tx.run("MATCH (a:Account {id:$id}) RETURN a.balance AS b", id=from_id).single()["b"]
    if balance < amount:
        raise ValueError("insufficient funds")
    tx.run("MATCH (a:Account {id:$id}) SET a.balance = a.balance - $amt", id=from_id, amt=amount)
    tx.run("MATCH (a:Account {id:$id}) SET a.balance = a.balance + $amt", id=to_id,   amt=amount)

with driver.session(database="neo4j") as session:
    session.execute_write(transfer, 1, 2, 100)
```

The transaction function **must be idempotent** — the driver retries on transient failures.

## Async

`from neo4j import AsyncGraphDatabase` — same API with `await`, `async with`, `async for`.
