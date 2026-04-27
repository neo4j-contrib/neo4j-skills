---
name: neo4j-driver-javascript-skill
description: >
  Use when writing JavaScript or TypeScript code that connects to Neo4j: installing
  neo4j-driver, configuring neo4j.driver(), executeQuery() patterns, session and
  transaction management, handling the 64-bit integer footgun (neo4j.Integer vs plain
  JS numbers), or result serialization. Covers both Node.js and browser environments.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT handle driver version upgrades — use neo4j-migration-skill.
  Does NOT handle GraphRAG pipelines — use neo4j-graphrag-skill.
status: draft
version: 0.1.0
allowed-tools: Bash, WebFetch
---

# Neo4j JavaScript / TypeScript Driver Skill

> **Status: Draft / WIP** — Content is a placeholder. Reference files and extended patterns to be added.

## When to Use

- Setting up the Neo4j JS driver (`npm install neo4j-driver`)
- Writing `neo4j.driver()` singleton and `executeQuery()` patterns
- Handling the 64-bit integer footgun (`neo4j.Integer` vs plain JS numbers)
- Session and write-transaction patterns in Node.js or browser
- TypeScript typing for driver results

## When NOT to Use

- **Writing or optimizing Cypher queries** → use `neo4j-cypher-skill`
- **Upgrading from an older driver version** → use `neo4j-migration-skill`
- **GraphRAG pipelines** → use `neo4j-graphrag-skill`

---

## Setup

```bash
npm install neo4j-driver
# or: yarn add neo4j-driver
```

---

## Core Patterns

### Driver singleton

```javascript
import neo4j from 'neo4j-driver'

const driver = neo4j.driver(
  process.env.NEO4J_URI,
  neo4j.auth.basic(process.env.NEO4J_USERNAME, process.env.NEO4J_PASSWORD),
  { disableLosslessIntegers: true }  // plain JS numbers instead of neo4j.Integer
)
await driver.verifyConnectivity()

// close on shutdown:
await driver.close()
```

### executeQuery (recommended)

```javascript
const { records } = await driver.executeQuery(
  'MATCH (p:Person {name: $name})-[:KNOWS]->(f) RETURN f.name AS friend',
  { name: 'Alice' },
  { database: 'neo4j' }
)
records.forEach(r => console.log(r.get('friend')))
```

### Session + write transaction

```javascript
const session = driver.session({ database: 'neo4j' })
try {
  await session.executeWrite(tx =>
    tx.run('MERGE (p:Person {id: $id}) SET p.name = $name', { id: '1', name: 'Alice' })
  )
} finally {
  await session.close()
}
```

### TypeScript typing

```typescript
import neo4j, { Driver, Session, Record } from 'neo4j-driver'

interface Friend { name: string }

const friends: Friend[] = records.map(r => ({ name: r.get('friend') as string }))
```

---

## Integer Footgun

Neo4j integers are 64-bit; JavaScript `number` is a 64-bit float (safe up to 2^53 = 9,007,199,254,740,991). Large IDs returned from Neo4j arrive as `neo4j.Integer` objects by default.

**`disableLosslessIntegers: true`**: returns plain JS numbers. Safe **only if all integer values fit below 2^53**. If Neo4j node IDs or your data contains integers larger than 2^53, setting this flag silently truncates them — producing wrong results with no error.

**Safe alternative**: leave the default (`false`) and call `.toNumber()` only on values you know are in range, or `.toString()` to preserve precision as a string:

```javascript
// safe for known-small values
const count = record.get('count').toNumber()

// safe for large IDs (preserves full precision as string)
const id = record.get('id').toString()
```

---

## Checklist

- [ ] One driver instance per process (singleton)
- [ ] Credentials loaded from env vars, not hardcoded
- [ ] `disableLosslessIntegers: true` set if using integer IDs in JS
- [ ] Session always closed in `finally` block
- [ ] `executeQuery` used for simple queries (auto-retries transient errors)
- [ ] `session.executeWrite` used for writes (not `session.run` directly)

---

## Fetching Current Docs

```
https://neo4j.com/docs/llms.txt     ← full documentation index
https://neo4j.com/llms-full.txt     ← rich reference with code examples
```

## References

- [JavaScript Driver Manual](https://neo4j.com/docs/javascript-manual/)
- [GraphAcademy: Building Neo4j Applications with TypeScript](https://graphacademy.neo4j.com/courses/app-typescript/)
- [GraphAcademy: Building Neo4j Applications with Node.js](https://graphacademy.neo4j.com/courses/app-nodejs/)
