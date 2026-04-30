# Driver Batch Write Pattern (Python)

Use when source is not a file: API responses, database migrations, programmatic generation.

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("neo4j+s://xxx.databases.neo4j.io",
                              auth=("neo4j", "password"))

BATCH_SIZE = 10_000

def import_batch(tx, rows):
    tx.run("""
        UNWIND $rows AS row
        MERGE (p:Person {id: row.id})
        ON CREATE SET p.name = row.name, p.age = row.age
    """, rows=rows)

all_rows = [...]  # your source data

with driver.session(database="neo4j") as session:
    batch = []
    for row in all_rows:
        batch.append(row)
        if len(batch) == BATCH_SIZE:
            session.execute_write(import_batch, batch)
            batch.clear()
    if batch:
        session.execute_write(import_batch, batch)

driver.close()
```

UNWIND-based batching: ~10x faster than one-at-a-time — network round-trips are the bottleneck.

## JavaScript / Node.js

```javascript
const neo4j = require('neo4j-driver');
const driver = neo4j.driver('neo4j+s://xxx.databases.neo4j.io',
  neo4j.auth.basic('neo4j', 'password'));

const BATCH_SIZE = 10_000;
const session = driver.session({ database: 'neo4j' });

const rows = [...]; // your source data
for (let i = 0; i < rows.length; i += BATCH_SIZE) {
  const batch = rows.slice(i, i + BATCH_SIZE);
  await session.executeWrite(tx =>
    tx.run('UNWIND $rows AS row MERGE (p:Person {id: row.id}) SET p += row',
           { rows: batch })
  );
}
await session.close();
await driver.close();
```
