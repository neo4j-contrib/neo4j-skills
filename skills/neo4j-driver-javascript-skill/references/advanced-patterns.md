# Advanced Patterns — Neo4j JavaScript Driver

## Explicit Transactions

Use when a transaction spans multiple functions or external coordination. **Not auto-retried.**

```javascript
const session = driver.session({ database: 'neo4j' })
const tx = await session.beginTransaction()
try {
  await doPartA(tx)
  await doPartB(tx)
  await tx.commit()
} catch (err) {
  try {
    await tx.rollback()   // network call — can itself throw
  } catch (rollbackErr) {
    console.error('Rollback failed:', rollbackErr)
  }
  throw err   // re-throw original
} finally {
  await session.close()
}
```

If `tx.commit()` rejects with a network error, the commit may or may not have succeeded. Design writes as idempotent (`MERGE` + unique constraints) so retrying is safe.

---

## Causal Consistency and Bookmarks

Within a single session, queries are causally chained automatically. Across sessions, pass bookmarks explicitly:

```javascript
const sessionA = driver.session({ database: 'neo4j' })
try {
  await sessionA.executeWrite(async tx => tx.run("MERGE (p:Person {name: 'Alice'})"))
} finally { await sessionA.close() }
const bookmarksA = sessionA.lastBookmarks()

const sessionB = driver.session({ database: 'neo4j' })
try {
  await sessionB.executeWrite(async tx => tx.run("MERGE (p:Person {name: 'Bob'})"))
} finally { await sessionB.close() }
const bookmarksB = sessionB.lastBookmarks()

// sessionC waits for both Alice and Bob to be visible
const sessionC = driver.session({
  database: 'neo4j',
  bookmarks: [...bookmarksA, ...bookmarksB]
})
try {
  await sessionC.executeWrite(async tx =>
    tx.run("MATCH (a:Person {name:'Alice'}), (b:Person {name:'Bob'}) MERGE (a)-[:KNOWS]->(b)")
  )
} finally { await sessionC.close() }
```

`executeQuery` uses a shared `BookmarkManager` automatically — bookmarks handled for you in most cases.

---

## TransactionConfig — Timeouts and Metadata

```javascript
await session.executeRead(
  async tx => {
    const result = await tx.run('MATCH (p:Person) RETURN p.name AS name')
    return (await result.collect()).map(r => r.get('name'))
  },
  {
    timeout: 5000,
    metadata: { app: 'myService', user: userId }   // visible in SHOW TRANSACTIONS
  }
)
```

---

## Connection Pool Tuning

```javascript
const driver = neo4j.driver(URI, auth, {
  maxConnectionPoolSize: 50,             // default: 100; use 5-10 for serverless
  connectionAcquisitionTimeout: 30000,   // ms to wait for free connection; default: 60000
  maxConnectionLifetime: 3600000,        // ms; recycle old connections
  connectionTimeout: 15000,             // ms to establish new connection
})
```

---

## Result Transformers

```javascript
const people = await driver.executeQuery(
  'MATCH (p:Person) RETURN p.name AS name, p.age AS age',
  {},
  {
    database: 'neo4j',
    resultTransformer: neo4j.resultTransformers.mappedResultTransformer({
      map(record) {
        return { name: record.get('name'), age: record.get('age').toNumber() }
      },
      collect(mapped) { return mapped }
    })
  }
)
// people is the array directly — no need to unpack { records }
```

---

## Lazy Streaming for Large Results

```javascript
const session = driver.session({ database: 'neo4j' })
try {
  await session.executeRead(async tx => {
    const result = await tx.run('MATCH (p:Person) RETURN p.name AS name')

    // for-await: one record at a time, no full buffer
    for await (const record of result) {
      process(record.get('name'))
    }
  })
} finally {
  await session.close()
}

// Callback-style .subscribe()
await session.executeRead(async tx => {
  const result = await tx.run('MATCH (p:Person) RETURN p.name AS name')
  await new Promise((resolve, reject) => {
    result.subscribe({
      onNext(record)  { process(record.get('name')) },
      onCompleted()   { resolve() },
      onError(err)    { reject(err) }
    })
  })
})
// ❌ Never call .subscribe() without awaiting tx.run() first
```

---

## Repository Pattern

```javascript
class PersonRepository {
  constructor(driver, database = 'neo4j') {
    this.driver = driver
    this.db = database
  }

  async findByNamePrefix(prefix) {
    const { records } = await this.driver.executeQuery(
      'MATCH (p:Person) WHERE p.name STARTS WITH $prefix RETURN p.name AS name, p.age AS age',
      { prefix },
      { database: this.db, routing: neo4j.routing.READ }
    )
    return records.map(r => ({ name: r.get('name'), age: r.get('age').toNumber() }))
  }

  async create(name, age) {
    await this.driver.executeQuery(
      'CREATE (p:Person {name: $name, age: $age})',
      { name, age: neo4j.int(age) },
      { database: this.db }
    )
  }

  async bulkCreate(people) {
    await this.driver.executeQuery(
      `UNWIND $people AS person
       MERGE (p:Person {name: person.name})
       SET p.age = person.age`,
      { people },
      { database: this.db }
    )
  }
}
```
