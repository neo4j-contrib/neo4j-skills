---
name: neo4j-driver-javascript-skill
description: >
  Comprehensive guide to using the official Neo4j JavaScript/TypeScript Driver (v6) — covering
  installation, driver lifecycle, all three query APIs (executeQuery, managed transactions via
  executeRead/Write, auto-commit via session.run), Integer handling and JSON serialization,
  temporal and graph types, result consumption, async/Promise error handling and session closure,
  UNWIND batching, performance, causal consistency, TypeScript usage, and browser/WebSocket
  support. Use this skill whenever writing JavaScript or TypeScript code that talks to Neo4j,
  or when questions arise about sessions, transactions, result handling, Integer types, bookmarks,
  or browser/Node.js targeting. Also triggers on neo4j-driver, neo4j.driver, executeQuery,
  executeRead, executeWrite, neo4j.int, record.get, or any Neo4j Bolt/Aura connection work
  in JavaScript or TypeScript.

  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
status: draft
version: 0.1.1
allowed-tools: Bash, WebFetch
---
# Neo4j JavaScript Driver

**Package**: `neo4j-driver`  
**Current stable**: v6  
**Docs**: https://neo4j.com/docs/javascript-manual/current/  
**API ref**: https://neo4j.com/docs/api/javascript-driver/current/

---

## 1. Installation

```bash
# Node.js
npm install neo4j-driver

# or with yarn
yarn add neo4j-driver
```

For browser usage see section 12 — a different URI scheme is required.

---

## 2. Driver Lifecycle

`Driver` is **thread-safe, connection-pooled, and expensive to create** — create exactly one instance per application and share it everywhere. Close it on application shutdown.

```javascript
const neo4j = require('neo4j-driver')         // CommonJS
// import neo4j from 'neo4j-driver'           // ESM / TypeScript

// URI examples:
//   'neo4j://localhost'                — unencrypted, cluster-routing
//   'neo4j+s://xxx.databases.neo4j.io' — TLS, cluster-routing (Aura)
//   'bolt://localhost:7687'            — unencrypted, single instance
//   'bolt+s://localhost:7687'          — TLS, single instance
const URI      = 'neo4j+s://xxx.databases.neo4j.io'
const USER     = 'neo4j'
const PASSWORD = 'password'

const driver = neo4j.driver(URI, neo4j.auth.basic(USER, PASSWORD))

// Verify connection at startup — fail fast if unreachable
await driver.getServerInfo()

// On application shutdown:
await driver.close()
```

### Auth Options

```javascript
neo4j.auth.basic(user, password)          // username + password
neo4j.auth.bearer(token)                  // SSO / JWT
neo4j.auth.kerberos(base64Ticket)         // Kerberos
neo4j.auth.none()                         // unauthenticated (dev only)
```

### Singleton Pattern — Web Frameworks

```javascript
// db.js — create once, import everywhere
import neo4j from 'neo4j-driver'

let _driver = null

export function getDriver() {
  if (!_driver) {
    _driver = neo4j.driver(
      process.env.NEO4J_URI,
      neo4j.auth.basic(process.env.NEO4J_USER, process.env.NEO4J_PASSWORD)
    )
  }
  return _driver
}

export async function closeDriver() {
  if (_driver) {
    await _driver.close()
    _driver = null
  }
}

// In Express: call closeDriver() on SIGTERM
// In Next.js: export getDriver() and call in API routes
```

### ⚠ Serverless Environments (Lambda, Vercel, Cloudflare Workers)

The singleton pattern above assumes a **long-lived process**. Serverless functions have a different execution model that changes how the driver should be managed:

- **Cold starts**: each new function instance creates a fresh module scope, so `_driver` starts as `null` and a new Driver is created — incurring the connection pool setup and TLS handshake cost on every cold start.
- **Warm reuse**: within the same warm instance, the module-level `_driver` persists between invocations, so the pool is reused (this is the intended benefit).
- **Connection pool sizing**: a serverless function that runs many concurrent invocations spawns many separate instances, each with its own pool. `maxConnectionPoolSize` should be kept small (e.g. 5–10) to avoid overwhelming the database with connections.
- **No guaranteed shutdown**: `SIGTERM` handlers may not fire in all serverless runtimes, so `closeDriver()` may never be called. Design for connections being dropped by the platform rather than cleanly closed.

```javascript
// Serverless-appropriate driver config
const driver = neo4j.driver(URI, auth, {
  maxConnectionPoolSize: 5,              // small pool per function instance
  connectionAcquisitionTimeout: 5000,   // fail fast rather than queue up
  maxConnectionLifetime: 300000,        // 5 min — shorter than typical Lambda timeout
})
```

---

## 3. Choosing the Right API

| API | When to use | Auto-retry? | Streaming? |
|-----|-------------|-------------|------------|
| `driver.executeQuery()` | Most queries — simple, safe default | ✅ | ❌ (eager) |
| `session.executeRead/Write()` | Large results, lazy streaming, complex logic | ✅ | ✅ |
| `session.run()` | `LOAD CSV`, `CALL {} IN TRANSACTIONS`, scripting | ❌ | ✅ |

---

## 4. `executeQuery` — Recommended Default

The highest-level API. Manages sessions, transactions, retries, and bookmarks automatically.

```javascript
// Read query
const { records, summary, keys } = await driver.executeQuery(
  'MATCH (p:Person {name: $name})-[:KNOWS]->(friend) RETURN friend.name AS name',
  { name: 'Alice' },                         // parameters — second positional arg
  {
    database: 'neo4j',                        // always specify — avoids a round-trip
    routing: neo4j.routing.READ,              // route reads to replicas
  }
)

for (const record of records) {
  console.log(record.get('name'))             // ✅ use .get() — see section 9
}

console.log(`Returned ${records.length} records in ${summary.resultAvailableAfter} ms`)
console.log(`Keys: ${keys}`)                  // ['name']

// Write query
const { summary: writeSummary } = await driver.executeQuery(
  'CREATE (p:Person {name: $name, age: $age})',
  { name: 'Bob', age: 30 },
  { database: 'neo4j' }
)
console.log(`Created ${writeSummary.counters.updates().nodesCreated} nodes`)
```

### Reading Query Counters — `.updates()` Is Required

`summary.counters` is not a flat object — you must call `.updates()` to get the statistics object. Accessing properties directly on `counters` returns `undefined` silently:

```javascript
// ❌ Wrong — undefined silently, no error thrown
summary.counters.nodesCreated        // undefined
summary.counters.relationshipsCreated // undefined

// ✅ Correct — call .updates() first
const stats = summary.counters.updates()
stats.nodesCreated                   // number
stats.nodesDeleted                   // number
stats.relationshipsCreated           // number
stats.relationshipsDeleted           // number
stats.propertiesSet                  // number
stats.labelsAdded                    // number

// ✅ Or inline:
summary.counters.updates().nodesCreated

// Two timing properties also exist on summary directly (no .updates() needed):
summary.resultAvailableAfter   // ms until first record was available from server
summary.resultConsumedAfter    // ms until all records were consumed — use this for
                               // total query wall-clock time in your app
```
```

### `executeQuery` Argument Shape

```javascript
driver.executeQuery(
  query,        // string — Cypher
  parameters,   // object — $param values (pass {} if none, not omitted)
  config        // object — { database, routing, resultTransformer, bookmarkManager, auth }
)
```

**⚠ Never template-literal or concatenate Cypher.** Always use `$param` placeholders — prevents injection and enables server-side query plan caching.

```javascript
// ❌ Injection risk and disables plan caching
const name = req.body.name
await driver.executeQuery(`MATCH (p:Person {name: '${name}'}) RETURN p`)

// ✅ Parameterised
await driver.executeQuery('MATCH (p:Person {name: $name}) RETURN p', { name })
```

### Result Transformers

```javascript
// Built-in: map records to custom objects
const people = await driver.executeQuery(
  'MATCH (p:Person) RETURN p.name AS name, p.age AS age',
  {},
  {
    database: 'neo4j',
    resultTransformer: neo4j.resultTransformers.mappedResultTransformer({
      map(record) {
        return { name: record.get('name'), age: record.get('age').toNumber() }
      },
      collect(mapped) {
        return mapped   // array of mapped objects
      }
    })
  }
)
// people is whatever collect() returns — no need to unpack { records }
```

---

## 5. Managed Transactions (`executeRead` / `executeWrite`)

Use when you need lazy result streaming or want to run multiple queries inside one transaction.

```javascript
const session = driver.session({ database: 'neo4j' })
try {
  // Read — routes to replicas; callback auto-retried on transient failure
  const names = await session.executeRead(async tx => {
    const result = await tx.run(
      'MATCH (p:Person) WHERE p.name STARTS WITH $prefix RETURN p.name AS name',
      { prefix: 'Al' }
    )
    // ✅ Consume records INSIDE the callback — result is a stream tied to the tx
    return result.records.map(r => r.get('name'))
  })

  // Write — routes to leader
  await session.executeWrite(async tx => {
    await tx.run('CREATE (p:Person {name: $name})', { name: 'Carol' })
  })
} finally {
  await session.close()   // ✅ always close in finally — see section on async error paths
}
```

### Critical: `result` vs `result.records` in a Callback

Inside a managed transaction callback, `tx.run()` returns a `Result` — a **lazy stream** object, not an array. Records are fetched from the server as you consume the stream. `result.records` is only populated after the stream has been fully consumed by iterating, calling `.collect()`, or similar. The transaction closes the moment the callback's Promise resolves, after which the stream is gone.

```javascript
// ❌ WRONG — returns the un-awaited Result promise; transaction closes immediately,
// stream is destroyed, result.records will be []
const badResult = await session.executeRead(async tx => {
  return tx.run('MATCH (p:Person) RETURN p.name AS name')
})
console.log(badResult.records)   // [] — cursor closed before any records were fetched

// ❌ ALSO WRONG — awaiting tx.run() gives you the Result stream object,
// but does NOT fetch any records. result.records is still [] at this point.
// Returning the stream out of the callback means it will be consumed AFTER
// the transaction closes — records will be empty or the stream will error.
const alsoWrong = await session.executeRead(async tx => {
  const result = await tx.run('MATCH (p:Person) RETURN p.name AS name')
  // result.records is [] here — awaiting tx.run() only gives you the stream object,
  // it does not eagerly fetch records
  return result   // stream returned; tx closes; stream is dead
})
console.log(alsoWrong.records)   // [] — never fetched

// ✅ CORRECT — consume the stream fully inside the callback using .collect(),
// then return plain data
const names = await session.executeRead(async tx => {
  const result = await tx.run('MATCH (p:Person) RETURN p.name AS name')
  const records = await result.collect()          // ← fetches all records while tx is open
  return records.map(r => r.get('name'))          // plain array — safe to return
})

// ✅ ALSO CORRECT — result.records is populated after subscribing/consuming via for-await
const names2 = await session.executeRead(async tx => {
  const result = await tx.run('MATCH (p:Person) RETURN p.name AS name')
  const names = []
  for await (const record of result) {            // ← streams records while tx is open
    names.push(record.get('name'))
  }
  return names
})
```

**The key mental model**: `await tx.run()` gives you a stream handle, not the data. You must consume the stream (`.collect()`, `for await`, or `.subscribe()`) while still inside the callback. Any data you want to use after the callback must be extracted into a plain JS array or object before returning.

### Multiple `tx.run()` Calls

Each `await tx.run(...)` gives you a stream. Consume it with `.collect()` or `for await` before starting the next run — otherwise the first stream is implicitly consumed in one go by the driver when the second query starts, which can pull a large result unexpectedly into memory:

```javascript
const count = await session.executeWrite(async tx => {
  // First run — consume with .collect() before the second run
  const peopleResult = await tx.run('MATCH (p:Person) RETURN p.name AS name')
  const names = (await peopleResult.collect()).map(r => r.get('name'))

  // Second run — safe, first stream is fully consumed
  for (const name of names) {
    await tx.run(
      'MERGE (p:Person {name: $name})-[:VISITED]->(:City {name: $city})',
      { name, city: 'London' }
    )
  }

  return names.length
})
```

### Retry Safety

The callback **may execute more than once** on transient failures. Keep callbacks idempotent:

```javascript
// ❌ Side effect fires on every retry attempt
await session.executeWrite(async tx => {
  await fetch('https://api.example.com/notify')   // called on every retry!
  await tx.run('CREATE (p:Person {name: $name})', { name: 'Alice' })
})

// ✅ Database work only inside the callback; side effects outside
await session.executeWrite(async tx => {
  await tx.run('MERGE (p:Person {name: $name})', { name: 'Alice' })  // MERGE is idempotent
})
await fetch('https://api.example.com/notify')   // only runs once, after confirmed commit
```

### TransactionConfig — Timeouts and Metadata

```javascript
await session.executeRead(
  async tx => {
    const result = await tx.run('MATCH (p:Person) RETURN p.name AS name')
    return result.records.map(r => r.get('name'))
  },
  {
    timeout: 5000,                              // milliseconds
    metadata: { app: 'myService', user: userId }  // visible in SHOW TRANSACTIONS
  }
)
```

---

## 6. Implicit Transactions (`session.run`)

Lowest-level API — **not automatically retried**. Use only for:
- `LOAD CSV` imports
- `CALL { } IN TRANSACTIONS` Cypher
- Quick scripting

```javascript
const session = driver.session({ database: 'neo4j' })
try {
  const result = await session.run(
    'CREATE (p:Person {name: $name}) RETURN p',
    { name: 'Alice' }
  )
  const summary = result.summary
  console.log(`Created ${summary.counters.updates().nodesCreated} nodes`)
} finally {
  await session.close()
}
```

Since the driver cannot determine read/write intent from `session.run()`, it defaults to write mode. For read-only implicit transactions:

```javascript
const session = driver.session({
  database: 'neo4j',
  defaultAccessMode: neo4j.session.READ
})
```

---

## 7. Explicit Transactions

Use when a transaction must span multiple functions or coordinate with external systems. **Not automatically retried.**

```javascript
const session = driver.session({ database: 'neo4j' })
const tx = await session.beginTransaction()
try {
  await doPartA(tx)
  await doPartB(tx)
  await tx.commit()
} catch (err) {
  await tx.rollback()   // rollback can itself throw — see below
  throw err
} finally {
  await session.close()
}
```

### Rollback Can Throw

`tx.rollback()` is a network call. If the server is unreachable, it rejects. Don't let it swallow the original error:

```javascript
} catch (err) {
  try {
    await tx.rollback()
  } catch (rollbackErr) {
    // Log the rollback failure but re-throw the original error
    console.error('Rollback failed:', rollbackErr)
  }
  throw err   // original error still propagates
}
```

### Commit Uncertainty

If `tx.commit()` rejects with a network error, the commit may or may not have succeeded. Design writes to be idempotent using `MERGE` and unique constraints so retrying is safe.

---

## 8. Async Error Handling and Session Closure

Session closure in error paths is the most common resource leak in JavaScript driver code. **Always close sessions in a `finally` block**, not in `.then()` chains, which silently swallow exceptions from the session work itself:

```javascript
// ❌ Wrong — if the executeRead rejects, the .then() never runs; session leaks
session.executeRead(async tx => { ... })
  .then(result => doSomething(result))
  .then(() => session.close())   // never reached on error

// ❌ Also wrong — catch closes the session but re-throw is missing
session.executeRead(async tx => { ... })
  .catch(err => {
    session.close()
    // forgot to rethrow — error is swallowed
  })

// ✅ Correct — try/finally guarantees closure regardless of success or failure
try {
  const result = await session.executeRead(async tx => { ... })
  doSomething(result)
} catch (err) {
  handleError(err)
} finally {
  await session.close()   // always runs
}
```

### Promise Chain Pattern (non-async/await contexts)

```javascript
// When you must use .then() chains, attach .finally() for cleanup
session.executeRead(async tx => { ... })
  .then(result => doSomething(result))
  .catch(err => handleError(err))
  .finally(() => session.close())   // ✅ always runs
```

---

## 9. Integer Handling — JavaScript-Specific Complexity

This is the most JavaScript-specific aspect of the driver. Neo4j stores integers as 64-bit values. JavaScript's `Number` type is IEEE 754 double-precision, so it can only represent integers exactly up to `Number.MAX_SAFE_INTEGER` (2^53 − 1 = 9,007,199,254,740,991). Values above this lose precision silently.

The driver returns Neo4j integers as a custom **`Integer` class** (not a JS `number`) by default. This prevents silent precision loss but requires explicit conversion.

### The Three Integer Modes

```javascript
// Mode 1 (default): Custom Integer class — safe for all values, requires conversion
const driver1 = neo4j.driver(URI, auth)
// record.get('count') returns Integer { low: 42, high: 0 }

// Mode 2: disableLosslessIntegers — returns native JS number
// Safe ONLY if you know values will be within Number.MAX_SAFE_INTEGER
const driver2 = neo4j.driver(URI, auth, {
  disableLosslessIntegers: true
})
// record.get('count') returns 42 (JS number) — ✅ but loses precision for large values

// Mode 3: useBigInt — returns native BigInt
// Precise for all values, but BigInt breaks JSON.stringify (see below)
const driver3 = neo4j.driver(URI, auth, {
  useBigInt: true
})
// record.get('count') returns 42n (BigInt)
```

### Working with the Default `Integer` Class

```javascript
const count = record.get('count')   // Integer { low: 42, high: 0 }

neo4j.isInt(count)                  // true — check if it's a driver Integer

// Convert to JS number (only safe within Number.MAX_SAFE_INTEGER)
if (neo4j.integer.inSafeRange(count)) {
  const n = count.toNumber()        // 42
} else {
  const s = count.toString()        // '9223372036854775807' — use string for large values
}

// Convert to BigInt (always safe, any size)
const b = count.toBigInt()          // 42n

// Arithmetic with Integer class
const doubled = count.multiply(neo4j.int(2))  // Integer
const added   = count.add(10)                 // Integer

// Send an integer as a parameter
await driver.executeQuery(
  'CREATE (p:Person {age: $age})',
  { age: neo4j.int(30) },           // wraps 30 in Integer class
  { database: 'neo4j' }
)
// Note: passing a plain JS number as a parameter works too —
// the driver promotes it safely (integers within safe range are auto-converted)
```

### Integer and JSON Serialization

The `Integer` class **does not serialize to JSON correctly** — it will produce `{"low":42,"high":0}` instead of `42`:

```javascript
// ❌ Broken JSON output
const record = records[0]
const age = record.get('age')       // Integer { low: 30, high: 0 }
JSON.stringify({ age })             // '{"age":{"low":30,"high":0}}' — NOT what you want

// ❌ BigInt mode also breaks JSON.stringify
// JSON.stringify(42n) throws TypeError: Do not know how to serialize a BigInt

// ✅ Convert before serializing
const age = record.get('age').toNumber()   // 30
JSON.stringify({ age })                    // '{"age":30}'

// ✅ Or use disableLosslessIntegers if your data is within safe range
const driver = neo4j.driver(URI, auth, { disableLosslessIntegers: true })
// All returned integers are now plain JS numbers — JSON.stringify works directly

// ✅ Or add a BigInt JSON replacer if you use useBigInt
BigInt.prototype.toJSON = function() { return this.toString() }
// Note: modifying built-in prototypes is generally discouraged
```

### Helper Functions

```javascript
const { isInt, integer, int } = neo4j

isInt(value)                        // true if value is a driver Integer
integer.inSafeRange(value)          // true if safe to call .toNumber()
integer.toNumber(value)             // convert Integer to JS number
integer.toString(value)             // convert Integer to string
int(42)                             // create an Integer from a JS number or string
int('9223372036854775807')          // create a large Integer from string (safe)
```

---

## 10. Record Access

### `.get()` Is Mandatory

Records are not plain JavaScript objects. You **cannot** access values with dot notation or bracket notation — you must use `.get()`:

```javascript
const record = records[0]

// ❌ Undefined — these do NOT work
record.name
record['name']

// ✅ Correct
record.get('name')                  // by key (string)
record.get(0)                       // by index (0-based)

// Other record methods
record.keys                         // ['name', 'age'] — array of projected keys
record.has('name')                  // true if key was projected
```

### `record.toObject()` Is Not JSON-Safe

`record.toObject()` returns a plain JS object keyed by column name — but **the values are still driver types** (Integers, temporals, Nodes, etc.). It is not a shortcut to a JSON-serializable object:

```javascript
// Query: MATCH (p:Person) RETURN p.name AS name, p.age AS age
const obj = record.toObject()
// obj == { name: 'Alice', age: Integer { low: 30, high: 0 } }
//                                ^^^^ still a driver Integer, not a JS number

// ❌ Broken JSON output — same failure as calling .get('age') directly
JSON.stringify(obj)
// '{"name":"Alice","age":{"low":30,"high":0}}'  — NOT what you want

// ✅ Map the values yourself while converting
const plain = {
  name: record.get('name'),            // string — fine
  age:  record.get('age').toNumber()   // Integer → number
}
JSON.stringify(plain)   // '{"name":"Alice","age":30}'

// ✅ Or project scalar fields in Cypher so .toObject() is safe:
// MATCH (p:Person) RETURN p.name AS name, toInteger(p.age) AS age
// — but note: Cypher toInteger() still returns a Neo4j Integer in JS;
//   the only fully safe approach is .toNumber() on the JS side,
//   or using disableLosslessIntegers: true on the driver

// ✅ Or use the toNative() helper from section 11 on the raw object:
const safe = Object.fromEntries(
  Object.entries(record.toObject()).map(([k, v]) => [k, toNative(v)])
)
```

### Null Safety — Absent Key vs Graph Null

```javascript
// record.get() on a key that was never projected throws:
record.get('typo')   // throws Neo4jError: This record has no field with key 'typo'

// record.get() on a key projected as null (e.g. from OPTIONAL MATCH) returns null:
// Query: OPTIONAL MATCH (p)-[:LIVES_IN]->(c:City) RETURN p.name AS name, c.name AS city
record.get('city')   // null when no City was matched

// Check before accessing:
if (record.has('city') && record.get('city') !== null) {
  const city = record.get('city')
}
```

---

## 11. Data Types

### Cypher → JavaScript Type Mapping

| Cypher type | JS type (default) | JS type (`disableLosslessIntegers`) |
|-------------|------------------|-------------------------------------|
| `Integer` | `neo4j.Integer` | `number` |
| `Float` | `number` | `number` |
| `String` | `string` | `string` |
| `Boolean` | `boolean` | `boolean` |
| `List` | `Array` | `Array` |
| `Map` | `Object` | `Object` |
| `Node` | `neo4j.types.Node` | `neo4j.types.Node` |
| `Relationship` | `neo4j.types.Relationship` | `neo4j.types.Relationship` |
| `Path` | `neo4j.types.Path` | `neo4j.types.Path` |
| `Date` | `neo4j.types.Date` | `neo4j.types.Date` |
| `DateTime` | `neo4j.types.DateTime` | `neo4j.types.DateTime` |
| `Duration` | `neo4j.types.Duration` | `neo4j.types.Duration` |
| `Point` | `neo4j.types.Point` | `neo4j.types.Point` |
| `null` | `null` | `null` |

### Graph Types

```javascript
// Node
const node = record.get('p')         // neo4j.types.Node
node.labels                          // ['Person']
node.properties                      // { name: 'Alice', age: Integer{...} }
node.properties.name                 // 'Alice'
node.properties.age.toNumber()       // 30
node.elementId                       // '4:uuid:393' — use this, not .identity (deprecated)

// Relationship
const rel = record.get('r')          // neo4j.types.Relationship
rel.type                             // 'KNOWS'
rel.properties.since                 // Integer or driver temporal type
rel.startNodeElementId
rel.endNodeElementId

// ⚠ elementId is only stable within one transaction.
// Do not use it to MATCH entities across separate transactions.
```

### Temporal Types

Neo4j temporal types are **not** native JS `Date` objects. They have nanosecond precision and support timezone IDs that JS `Date` doesn't.

```javascript
const dt = record.get('created_at')  // neo4j.types.DateTime
dt.toString()                        // '2024-01-15T10:30:00.000000000+00:00' — ISO 8601

// Convert to JS Date (lossy — drops nanoseconds, may lose timezone precision)
const jsDate = dt.toStandardDate()   // Date object

// Create from JS Date
const neo4jDt = neo4j.types.DateTime.fromStandardDate(new Date())

// Pass native JS Date as parameter — driver converts automatically
await driver.executeQuery(
  'CREATE (e:Event {at: $ts})',
  { ts: new Date() },
  { database: 'neo4j' }
)

// Temporal types also don't JSON.stringify correctly:
JSON.stringify(dt)  // '{}' — empty object, silent failure
// ✅ Use toString() before serializing
JSON.stringify({ created: dt.toString() })
```

### A Practical Type-Conversion Helper

For REST APIs that need to serialize all driver types to plain JS, a conversion helper avoids scattered `.toNumber()` and `.toString()` calls. **Call it on `.properties`, not on the Node or Relationship object itself** — or add explicit Node/Relationship handling as shown:

```javascript
import { isInt, isDate, isDateTime, isTime, isLocalDateTime,
         isLocalTime, isDuration, isPoint,
         isNode, isRelationship, isPath } from 'neo4j-driver'

function toNative(value) {
  if (value === null || value === undefined) return value
  if (Array.isArray(value))       return value.map(toNative)
  if (isInt(value))               return value.inSafeRange() ? value.toNumber() : value.toString()
  if (isDate(value) || isDateTime(value) || isTime(value) ||
      isLocalDateTime(value) || isLocalTime(value) || isDuration(value))
                                  return value.toString()
  if (isPoint(value))             return { x: toNative(value.x), y: toNative(value.y),
                                           z: toNative(value.z), srid: toNative(value.srid) }
  // ✅ Handle Node and Relationship explicitly — without this,
  // passing a Node to toNative() traverses its raw fields (labels, identity, elementId)
  // instead of just the properties, producing a structurally wrong output
  if (isNode(value))              return { labels: value.labels,
                                           properties: toNative(value.properties) }
  if (isRelationship(value))      return { type: value.type,
                                           properties: toNative(value.properties),
                                           startNodeElementId: value.startNodeElementId,
                                           endNodeElementId: value.endNodeElementId }
  if (typeof value === 'object')  return Object.fromEntries(
                                    Object.entries(value).map(([k, v]) => [k, toNative(v)])
                                  )
  return value
}

// ✅ Safe to call on a whole Node
const person = toNative(record.get('p'))
// { labels: ['Person'], properties: { name: 'Alice', age: 30 } }

// ✅ Or just on the properties if you don't need labels
const props = toNative(record.get('p').properties)
// { name: 'Alice', age: 30 }

JSON.stringify(props)   // ✅ works — all driver types converted to primitives
```

**What NOT to do:**

```javascript
// ❌ Passing a Node to the previous (incomplete) version of toNative()
// would hit the generic `typeof value === 'object'` branch and traverse
// Node's own fields: { identity: Integer, labels: [...], properties: {...},
// elementId: '...' } — the Integer fields within would be converted, but
// the output shape is unexpected and includes internal driver fields
```

---

## 12. Performance

### Always Specify the Database

Omitting `database` causes an extra round-trip to resolve the home database on every call:

```javascript
// executeQuery:
await driver.executeQuery(query, params, { database: 'neo4j' })

// Session:
driver.session({ database: 'neo4j' })
```

### Route Reads to Replicas

```javascript
// executeQuery:
await driver.executeQuery(query, params, {
  database: 'neo4j',
  routing: neo4j.routing.READ
})

// Managed transaction — executeRead routes automatically:
session.executeRead(async tx => { ... })
```

### Batch Writes with `UNWIND`

Pass an array of plain objects — each element becomes one row in the Cypher loop:

```javascript
// ❌ One transaction per item — high overhead
for (const person of people) {
  await driver.executeQuery(
    'CREATE (p:Person {name: $name, age: $age})',
    { name: person.name, age: person.age },
    { database: 'neo4j' }
  )
}

// ✅ Single transaction via UNWIND — people is an array of plain objects
const people = [
  { name: 'Alice', age: 30, city: 'London' },
  { name: 'Bob',   age: 25, city: 'Paris' },
]

await driver.executeQuery(
  `UNWIND $people AS person
   MERGE (p:Person {name: person.name})
   SET p.age = person.age
   MERGE (c:City {name: person.city})
   MERGE (p)-[:LIVES_IN]->(c)`,
  { people },
  { database: 'neo4j' }
)

// ⚠ Integer values inside the array objects must be plain JS numbers or neo4j.int(),
// not driver Integer instances (which don't serialize through the parameter layer correctly
// when nested inside plain objects):
const rows = people.map(p => ({ ...p, age: Number(p.age) }))
```

### Lazy Streaming for Large Results

```javascript
// executeQuery is always eager — fine for small/medium results
const { records } = await driver.executeQuery('MATCH (p:Person) RETURN p', {}, { database: 'neo4j' })

// For large results, stream lazily using for-await inside a managed transaction
const session = driver.session({ database: 'neo4j' })
try {
  await session.executeRead(async tx => {
    const result = await tx.run('MATCH (p:Person) RETURN p.name AS name')

    // ✅ Modern pattern: for-await iterates records one at a time as they arrive
    for await (const record of result) {
      process(record.get('name'))   // process each record without buffering all into memory
    }
    // No return value needed — side effects handled inline
  })
} finally {
  await session.close()
}

// ✅ Also correct: .subscribe() for callback-style streaming (older pattern)
await session.executeRead(async tx => {
  const result = await tx.run('MATCH (p:Person) RETURN p.name AS name')
  await new Promise((resolve, reject) => {
    result.subscribe({
      onNext(record)   { process(record.get('name')) },
      onCompleted()    { resolve() },
      onError(err)     { reject(err) }
    })
  })
})

// ❌ Don't use .subscribe() without awaiting tx.run() first —
// subscribing to the unresolved Result thenable is undefined behaviour:
await session.executeRead(async tx => {
  const result = tx.run('MATCH ...')   // NOT awaited
  await new Promise((resolve, reject) => {
    result.subscribe({ ... })          // called on thenable, not resolved Result
  })
})
```

### Connection Pool Tuning

```javascript
const driver = neo4j.driver(URI, auth, {
  maxConnectionPoolSize: 50,             // default: 100
  connectionAcquisitionTimeout: 30000,   // ms to wait for a free connection; default: 60000
  maxConnectionLifetime: 3600000,        // ms; recycle old connections
  connectionTimeout: 15000,              // ms to establish a new connection
})
```

---

## 13. Causal Consistency & Bookmarks

**Within a single session**, queries are automatically causally chained. **Across sessions**, use `executeQuery` (auto-managed via `executeQueryBookmarkManager`) or pass bookmarks explicitly:

```javascript
// Sessions A and B run concurrently; session C must see both writes
const sessionA = driver.session({ database: 'neo4j' })
try {
  await sessionA.executeWrite(async tx =>
    tx.run("MERGE (p:Person {name: 'Alice'})")
  )
} finally { await sessionA.close() }
const bookmarksA = sessionA.lastBookmarks()

const sessionB = driver.session({ database: 'neo4j' })
try {
  await sessionB.executeWrite(async tx =>
    tx.run("MERGE (p:Person {name: 'Bob'})")
  )
} finally { await sessionB.close() }
const bookmarksB = sessionB.lastBookmarks()

// sessionC waits until both Alice and Bob exist
const sessionC = driver.session({
  database: 'neo4j',
  bookmarks: [...bookmarksA, ...bookmarksB]   // spread both bookmark arrays
})
try {
  await sessionC.executeWrite(async tx =>
    tx.run("MATCH (a:Person {name:'Alice'}), (b:Person {name:'Bob'}) MERGE (a)-[:KNOWS]->(b)")
  )
} finally { await sessionC.close() }
```

`executeQuery` uses a shared `BookmarkManager` automatically — usually all you need.

---

## 14. TypeScript Usage

The driver ships with full TypeScript type definitions.

```typescript
import neo4j, {
  Driver,
  Session,
  ManagedTransaction,
  Record,
  Node,
  Relationship,
  Integer,
  QueryResult,
} from 'neo4j-driver'

const driver: Driver = neo4j.driver(URI, neo4j.auth.basic(USER, PASSWORD))

// Typed session
const session: Session = driver.session({ database: 'neo4j' })

// Typed transaction callback
const names: string[] = await session.executeRead(
  async (tx: ManagedTransaction): Promise<string[]> => {
    const result = await tx.run('MATCH (p:Person) RETURN p.name AS name')
    return result.records.map((r: Record) => r.get('name') as string)
  }
)

// Typed node access
const node = record.get('p') as Node<Integer>
const name: string = node.properties.name
const age:  number = node.properties.age.toNumber()
```

### TypeScript with `disableLosslessIntegers`

```typescript
// With disableLosslessIntegers: true, Integer fields become number
import neo4j, { Node } from 'neo4j-driver'

const driver = neo4j.driver(URI, neo4j.auth.basic(USER, PASSWORD), {
  disableLosslessIntegers: true
})

// Node generic changes: Node<number> instead of Node<Integer>
const node = record.get('p') as Node<number>
const age: number = node.properties.age   // already a number, no .toNumber() needed
```

---

## 15. Browser / WebSocket Usage

In browser environments, the driver communicates over **WebSockets**, not raw TCP. The URI scheme must reflect this:

```javascript
// ❌ Wrong in a browser — bolt:// uses TCP, not supported in browsers
neo4j.driver('bolt://localhost:7687', auth)

// ✅ Correct — neo4j+s:// uses WebSocket (WSS) in browser builds
neo4j.driver('neo4j+s://xxx.databases.neo4j.io', auth)
// For local dev without TLS: neo4j:// (uses WS)
neo4j.driver('neo4j://localhost:7687', auth)
```

**Bundling**: the `neo4j-driver` npm package works in the browser when bundled with webpack, Vite, Rollup, etc. No separate browser-specific package is needed for modern bundlers.

**CORS**: Bolt/WebSocket connections bypass CORS (they are not HTTP). The browser connects directly to Neo4j's Bolt port (default 7687). Ensure the Neo4j server allows WebSocket connections from your origin via its connector config.

**Security**: never embed production credentials in client-side JavaScript. Use a backend API as a proxy to the database when building browser applications.

---

## 16. Repository Pattern — Recommended Structure

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
    return records.map(r => ({
      name: r.get('name'),
      age:  r.get('age').toNumber()
    }))
  }

  async create(name, age) {
    await this.driver.executeQuery(
      'CREATE (p:Person {name: $name, age: $age})',
      { name, age: neo4j.int(age) },
      { database: this.db }
    )
  }

  async bulkCreate(people) {
    // people = [{ name, age }] — plain objects
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

---

## 17. Error Handling

```javascript
import { Neo4jError, SERVICE_UNAVAILABLE, SESSION_EXPIRED } from 'neo4j-driver'

try {
  await driver.executeQuery('...', {}, { database: 'neo4j' })
} catch (err) {
  if (err instanceof Neo4jError) {
    switch (err.code) {
      case 'Neo.ClientError.Schema.ConstraintValidationFailed':
        // Unique or existence constraint violation
        console.error('Constraint violated:', err.message)
        break
      case SERVICE_UNAVAILABLE:      // 'ServiceUnavailable'
        console.error('Database unreachable')
        break
      case SESSION_EXPIRED:          // 'SessionExpired'
        console.error('Session expired — open a new session')
        break
      default:
        if (err.retriable) {
          // Transient — executeQuery already retried; this is after exhaustion
          console.error('Transient error exhausted retries:', err.code)
        } else {
          console.error(`Neo4j error [${err.code}]:`, err.message)
        }
    }
  }
}
```

Constraint violation codes follow the pattern `Neo.ClientError.Schema.ConstraintValidationFailed`. GQL status codes (on `err.gqlStatus`) are stable across versions and preferable to string-matching error messages.

---

## 18. Quick Reference: Common Mistakes

| Mistake | Fix |
|---------|-----|
| Template literal / string concat Cypher | Use `$param` placeholders always |
| `record.name` or `record['name']` | Use `record.get('name')` — records are not plain objects |
| `record.toObject()` then `JSON.stringify()` | Values are still driver types — convert with `toNative()` or map manually |
| `JSON.stringify(record.get('age'))` on an Integer | Call `.toNumber()` first, or use `disableLosslessIntegers` |
| `JSON.stringify` on temporal types | Call `.toString()` first — temporals serialise to `{}` silently |
| `JSON.stringify` with `useBigInt: true` | Add a replacer or use `.toString()` — BigInt breaks JSON |
| `summary.counters.nodesCreated` | Must call `.updates()` first: `summary.counters.updates().nodesCreated` |
| `summary.resultAvailableAfter` for total query time | Use `summary.resultConsumedAfter` for wall-clock query duration |
| Omitting `database` on every query | Always set `{ database: 'neo4j' }` — saves a round-trip |
| Assuming `await tx.run()` populates `result.records` | It returns a stream — use `.collect()` or `for await` to fetch records |
| Returning `result` from tx callback | Return `await result.collect()` or mapped data — not the stream object |
| `toNative(record.get('p'))` on a whole Node | `toNative()` must handle Node explicitly; or pass `record.get('p').properties` |
| `result.subscribe()` without awaiting `tx.run()` first | Always `await tx.run()` before calling `.subscribe()` |
| `.then(() => session.close())` for cleanup | Use `try/finally { await session.close() }` |
| Side effects inside `executeRead/Write` callbacks | Move them outside — the callback may be retried |
| One transaction per write in a loop | Batch with `UNWIND` |
| Using `MERGE` for guaranteed-new data | Use `CREATE` — `MERGE` costs an extra match round-trip |
| `executeWrite` for a read query | Use `executeRead` — routes to replicas |
| `neo4j://` or `bolt://` URI in browser | Use `neo4j+s://` (WSS) or `neo4j://` (WS) for browser/WebSocket |
| Embedding credentials in browser JS | Use a backend proxy — never expose DB credentials client-side |
| Creating a new `Driver` per request | Create once at startup, share across requests |
| `maxConnectionPoolSize` default (100) in serverless | Use 5–10 per function instance to avoid connection storms |
| `integer.toNumber()` without range check | Use `integer.inSafeRange(value)` first for large integers |