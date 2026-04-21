# JavaScript / TypeScript driver (`neo4j-driver`)

Install: `npm install neo4j-driver`.

## Canonical example

```javascript
import neo4j from 'neo4j-driver'

const driver = neo4j.driver(
  'neo4j://localhost:7687',
  neo4j.auth.basic('neo4j', 'password')
)

try {
  await driver.verifyConnectivity()

  const { records, summary } = await driver.executeQuery(
    'MATCH (p:Person {name: $name}) RETURN p.name AS name, p.age AS age',
    { name: 'Alice' },
    { database: 'neo4j', routing: neo4j.routing.READ }
  )

  const rows = records.map(r => r.toObject())   // array of plain objects
} finally {
  await driver.close()
}
```

Signature: `driver.executeQuery(cypher, params, { database, routing, impersonatedUser, auth, bookmarkManager, resultTransformer })`.

## Accessing fields

- `record.get('name')` — one field
- `record.toObject()` — whole record as plain object
- `record.keys` — array of column names

## Bulk writes

```javascript
await driver.executeQuery(
  'UNWIND $rows AS row MERGE (p:Person {id: row.id}) SET p += row',
  { rows: [{ id: 1, name: 'Alice' }, { id: 2, name: 'Bob' }] },
  { database: 'neo4j' }
)
```

## Integers

Neo4j's `INTEGER` is 64-bit; a plain JS `Number` is 53-bit. Integer handling works differently on **results** vs **parameters**, and the driver-level config options only affect results.

### Results (reading INTEGER columns)

By default the driver returns integer-typed columns as its own `neo4j.Integer` class, so precision is never silently lost. Two driver options change that:

```javascript
// return JS Number — lossless only when values fit in 53 bits
const driver = neo4j.driver(uri, auth, { disableLosslessIntegers: true })

// return native BigInt — lossless for all 64-bit ints (takes precedence over disableLosslessIntegers)
const driver = neo4j.driver(uri, auth, { useBigInt: true })
```

With neither option, convert explicitly: `value.toNumber()` or `value.toString()`.

### Parameters (writing values into a query)

**Neither `disableLosslessIntegers` nor `useBigInt` change parameter encoding.** A plain JS `Number` is always sent as a Cypher `FLOAT`, even when its value looks like an integer — so `{ id: 12345 }` arrives on the server as `12345.0`. Symptoms: IDs rendering as `12345.0` in Browser, and `WHERE n.id = $id` failing to match nodes whose `id` was stored as INTEGER.

To send a Cypher `INTEGER`, wrap the value:

```javascript
await driver.executeQuery(
  'MATCH (u:User {id: $id}) RETURN u',
  { id: neo4j.int(12345) },   // INTEGER — matches stored INTEGER ids
  { database: 'neo4j' }
)
```

- `neo4j.int(value)` — preferred. Accepts a `Number`, a `string` (use for values outside ±2^53), or another `Integer`.
- `BigInt(value)` — also accepted and sent as INTEGER.

## Result transformers

```javascript
const { resultTransformers } = neo4j

const people = await driver.executeQuery(
  'MATCH (p:Person) RETURN p.name AS name',
  {},
  { database: 'neo4j',
    resultTransformer: resultTransformers.mappedResultTransformer({
      map: record => record.toObject()
    })
  }
)
```

## When to drop to a session

```javascript
const session = driver.session({ database: 'neo4j' })
try {
  await session.executeWrite(async tx => {
    const r = await tx.run('MATCH (a:Account {id:$id}) RETURN a.balance AS b', { id: from })
    const balance = r.records[0].get('b').toNumber()
    if (balance < amount) throw new Error('insufficient funds')
    await tx.run('MATCH (a:Account {id:$id}) SET a.balance = a.balance - $amt', { id: from, amt: amount })
    await tx.run('MATCH (a:Account {id:$id}) SET a.balance = a.balance + $amt', { id: to,   amt: amount })
  })
} finally {
  await session.close()
}
```

Transaction callbacks must be idempotent — the driver retries on transient failures.
