# Data Types — Neo4j JavaScript Driver

## Cypher → JavaScript Type Mapping

| Cypher type | JS type (default) | JS type (`disableLosslessIntegers`) |
|---|---|---|
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
| `LocalDateTime` | `neo4j.types.LocalDateTime` | same |
| `LocalTime` | `neo4j.types.LocalTime` | same |
| `Duration` | `neo4j.types.Duration` | same |
| `Point` | `neo4j.types.Point` | same |
| `null` | `null` | `null` |

---

## Graph Types

```javascript
// Node
const node = record.get('p')        // neo4j.types.Node
node.labels                         // ['Person']
node.properties                     // { name: 'Alice', age: Integer{...} }
node.elementId                      // '4:uuid:393' — use this, not .identity (deprecated)

// Relationship
const rel = record.get('r')         // neo4j.types.Relationship
rel.type                            // 'KNOWS'
rel.properties.since
rel.startNodeElementId
rel.endNodeElementId

// ⚠ elementId is only stable within one transaction.
// Do not MATCH by elementId across separate transactions.
```

---

## Temporal Types

Neo4j temporals are **not** JS `Date` — nanosecond precision, timezone ID support.

```javascript
const dt = record.get('created_at')  // neo4j.types.DateTime
dt.toString()                        // '2024-01-15T10:30:00.000000000+00:00'
dt.toStandardDate()                  // JS Date (lossy — drops nanoseconds)

// Create from JS Date
const neo4jDt = neo4j.types.DateTime.fromStandardDate(new Date())

// Pass native JS Date as parameter — driver converts automatically
await driver.executeQuery('CREATE (e:Event {at: $ts})', { ts: new Date() })

// ❌ temporals don't JSON.stringify correctly
JSON.stringify(dt)   // '{}' — silent failure
// ✅
JSON.stringify({ created: dt.toString() })
```

---

## Spatial Types

`neo4j.types.Point` — Cartesian and WGS-84 points.

```javascript
// Read point from query result
const pt = record.get('location')    // neo4j.types.Point
pt.srid                              // 4326 (WGS-84 2D), 4979 (WGS-84 3D), 7203 (Cartesian 2D), 9157 (Cartesian 3D)
pt.x                                 // longitude (WGS-84) or x (Cartesian)
pt.y                                 // latitude (WGS-84) or y (Cartesian)
pt.z                                 // height/z — undefined for 2D points

// Create and pass as parameter
import { types } from 'neo4j-driver'
const londonWgs84  = new types.Point(4326, -0.118092, 51.509865)          // 2D WGS-84
const shardWgs84   = new types.Point(4979, -0.086500, 51.504501, 310)     // 3D WGS-84
const cartesian2d  = new types.Point(7203, 1.23, 4.56)                    // 2D Cartesian
const cartesian3d  = new types.Point(9157, 1.23, 4.56, 7.89)             // 3D Cartesian

await driver.executeQuery(
  'CREATE (p:Place {location: $loc})',
  { loc: londonWgs84 },
  { database: 'neo4j' }
)

// Distance — same SRID only (different SRIDs return null)
const { records } = await driver.executeQuery(
  'RETURN point.distance($p1, $p2) AS distance',
  { p1: new types.Point(7203, 1, 1), p2: new types.Point(7203, 10, 10) },
  { database: 'neo4j' }
)
const distance = records[0].get('distance')   // number (float)

// isPoint() guard — needed in toNative() helper
neo4j.isPoint(pt)   // true
```

SRID table: `4326` = WGS-84 2D, `4979` = WGS-84 3D, `7203` = Cartesian 2D, `9157` = Cartesian 3D.

---

## `toNative()` Conversion Helper

Converts all driver types to plain JS for REST APIs. Call on `.properties` or pass the full Node/Relationship with the explicit handler shown.

```javascript
import { isInt, isDate, isDateTime, isTime, isLocalDateTime,
         isLocalTime, isDuration, isPoint,
         isNode, isRelationship } from 'neo4j-driver'

function toNative(value) {
  if (value === null || value === undefined) return value
  if (Array.isArray(value))       return value.map(toNative)
  if (isInt(value))               return value.inSafeRange() ? value.toNumber() : value.toString()
  if (isDate(value) || isDateTime(value) || isTime(value) ||
      isLocalDateTime(value) || isLocalTime(value) || isDuration(value))
                                  return value.toString()
  if (isPoint(value))             return { x: toNative(value.x), y: toNative(value.y),
                                           z: toNative(value.z), srid: toNative(value.srid) }
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

// Usage
const props = toNative(record.get('p').properties)   // { name: 'Alice', age: 30 }
JSON.stringify(props)                                 // ✅
```
