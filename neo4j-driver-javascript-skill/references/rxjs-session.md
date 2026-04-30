# RxJS Session API — Neo4j JavaScript Driver

RxJS-based session via `driver.rxSession()`. Requires RxJS v7+.

```javascript
import { map, toArray } from 'rxjs/operators'

const rxSession = driver.rxSession({ database: 'neo4j' })

// Simple read — Observable of records
rxSession
  .run('MATCH (p:Person) WHERE p.name STARTS WITH $prefix RETURN p.name AS name', { prefix: 'Al' })
  .records()
  .pipe(
    map(record => record.get('name')),
    toArray()
  )
  .subscribe({
    next: names => console.log(names),
    error: err => console.error(err),
    complete: () => rxSession.close().subscribe()
  })
```

## Managed Transactions with RxJS

```javascript
import { concat, EMPTY } from 'rxjs'
import { catchError, toArray } from 'rxjs/operators'

rxSession.executeRead(txFn =>
  txFn.run('MATCH (p:Person) RETURN p.name AS name')
    .records()
    .pipe(map(r => r.get('name')))
).pipe(toArray()).subscribe({ ... })
```

Always close after use:

```javascript
rxSession.close().subscribe()
```

## When to Use

Use when the rest of the app is already RxJS-based. For most Node.js apps, `async/await` (see SKILL.md) is simpler.
