# Data from Neo4j

When you need this: you have `neo4j-driver` results and want them on screen, styled from the data.

Each statement below ends with how it was verified: **source** (read in the NVL repository), **types** (in the shipped `.d.ts`) or **runtime** (observed in a running app).

## What `nvlResultTransformer` returns

```typescript
import { nvlResultTransformer } from '@neo4j-nvl/base'

const { nodes, relationships, recordObjectMap } = await driver.executeQuery(
  'MATCH (a)-[r]-(b) RETURN a, r, b LIMIT 100',
  {},
  { database: 'neo4j', resultTransformer: nvlResultTransformer }
)
```

- `nodes` are bare `{ id }` and `relationships` are bare `{ id, from, to }`. `id` is the driver `elementId`. No caption, colour, size or type is set. *source*
- `recordObjectMap` is a `Map<elementId, driver Node | Relationship | Path>`; it holds `labels`, `type` and `properties`. *source*
- Every `Node`, `Relationship` and `Path` in every column is collected, including nested arrays. Paths are expanded to their segments. *source*
- Output is not deduplicated. A node in several records appears several times. NVL ignores repeated ids on insert, so passing the array straight to NVL is fine. *source*

## Enrich before rendering

```typescript
const styledNodes = nodes.map((node) => {
  const record = recordObjectMap.get(node.id)
  if (!record || !('labels' in record)) return node
  const label = record.labels[0]
  return {
    ...node,
    caption: String(record.properties.name ?? label),
    color: colorByLabel[label],
    size: 20
  }
})

const styledRels = relationships.map((rel) => {
  const record = recordObjectMap.get(rel.id)
  return record && 'type' in record ? { ...rel, caption: record.type } : rel
})

new NVL(container, styledNodes, styledRels)
```

Dedupe yourself if you keep your own node store (`new Map(nodes.map((n) => [n.id, n]))`).

## Values that need converting

Driver values are not plain JS values. Convert before using them as captions or sizes. *types*

- `Integer` → `value.toNumber()` (or `toString()` for ids), or open the driver with `disableLosslessIntegers: true`.
- `Date`, `DateTime`, `Duration` → `value.toString()` or `toStandardDate()`.
- Spatial `Point` → `value.x`, `value.y`.

Driver setup, sessions and transactions belong to `neo4j-driver-javascript-skill`.

## Passing the raw result

```javascript
// ❌ records are not graph elements; NVL gets ids missing
const result = await driver.executeQuery('MATCH (a)-[r]-(b) RETURN a, r, b')
new NVL(container, result.records, [])
```

Always go through the transformer, or map the records yourself to `{ id, ... }` / `{ id, from, to, ... }`.
