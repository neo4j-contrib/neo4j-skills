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

Neo4j integers are 64-bit; JS numbers are 53-bit. Default return is a `neo4j.Integer`. For the common case where values fit in `Number`:

```javascript
const driver = neo4j.driver(uri, auth, { disableLosslessIntegers: true })
```

Otherwise convert explicitly with `value.toNumber()` or `value.toString()`.

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
