# Cypher-to-PHP Type Mapping

## Full Type Table

| Cypher | PHP |
|---|---|
| `null` | `null` |
| `string` | `string` |
| `integer` | `int` |
| `float` | `float` |
| `boolean` | `bool` |
| `Map` | `\Laudis\Neo4j\Types\CypherMap` |
| `List` | `\Laudis\Neo4j\Types\CypherList` |
| `Point` | `\Laudis\Neo4j\Contracts\PointInterface` |
| `Date` | `\Laudis\Neo4j\Types\Date` |
| `Time` | `\Laudis\Neo4j\Types\Time` |
| `LocalTime` | `\Laudis\Neo4j\Types\LocalTime` |
| `DateTime` | `\Laudis\Neo4j\Types\DateTime` |
| `DateTimeZoneId` | `\Laudis\Neo4j\Types\DateTimeZoneId` |
| `LocalDateTime` | `\Laudis\Neo4j\Types\LocalDateTime` |
| `Duration` | `\Laudis\Neo4j\Types\Duration` |
| `Node` | `\Laudis\Neo4j\Types\Node` |
| `Relationship` | `\Laudis\Neo4j\Types\Relationship` |
| `Path` | `\Laudis\Neo4j\Types\Path` |
| `Vector` | `\Laudis\Neo4j\Types\Vector` |

`Vector` — receive from server only; not supported as a query parameter.

## PHP-to-Cypher Parameter Conversion

| PHP | Cypher |
|---|---|
| `null` | `null` |
| `string` | `string` |
| `int` | `integer` |
| `float` | `float` |
| `bool` | `boolean` |
| Indexed/empty `array` | `List` |
| Associative `array` | `Map` |
| `\DateTimeInterface` | `DateTimeZoneId` |

Empty `[]` is ambiguous — use `ParameterHelper`:

```php
use Laudis\Neo4j\ParameterHelper;

ParameterHelper::asList([])  // → empty Cypher List
ParameterHelper::asMap([])   // → empty Cypher Map
```

## Point Subtypes

| Class | SRID | Use |
|---|---|---|
| `CartesianPoint` | 7203 | 2D Cartesian |
| `Cartesian3DPoint` | 9157 | 3D Cartesian |
| `WGS84Point` | 4326 | 2D geographic (lat/lon) |
| `WGS843DPoint` | 4979 | 3D geographic |

```php
$point = $row->get('location');  // PointInterface

if ($point instanceof \Laudis\Neo4j\Types\WGS84Point) {
    $point->getX();  // longitude
    $point->getY();  // latitude
}
```

## Temporal Types

**No calendar-field getters** — `getYear()`, `getMonth()`, `getDay()`, `getHour()`, `getMinute()`, `getSecond()`, `getTimezone()` do not exist. Use `toDateTime()` or epoch accessors:

```php
$dt = $row->get('created');     // Laudis\Neo4j\Types\DateTime

$php = $dt->toDateTime();       // \DateTimeImmutable (recommended)

$dt->getSeconds();              // epoch seconds
$dt->getNanoseconds();
$dt->getTimeZoneOffsetSeconds();
```

`DateTimeZoneId`, `LocalDateTime`, `Date`, `Time`, `LocalTime` — all have `toDateTime()` or raw accessors; none have year/month/day/hour/minute/second getters.

Pass `\DateTimeInterface` as a parameter — mapped to `DateTimeZoneId`:

```php
$client->run('CREATE (e:Event {at: $ts})', ['ts' => new \DateTime('2024-06-01 12:00:00')]);
```

## Node and Relationship Access

```php
// Node
$node      = $row->get('p');                     // Laudis\Neo4j\Types\Node
$intId     = $node->getId();                     // integer (legacy)
$elementId = $node->getElementId();              // string element ID (Neo4j 5+)
$labels    = $node->getLabels();                 // CypherList<string>
$name      = $node->getProperty('name');
$all       = $node->getProperties()->toArray();  // PHP array

// Relationship
$rel        = $row->get('r');                    // Laudis\Neo4j\Types\Relationship
$type       = $rel->getType();                   // e.g. 'KNOWS'
$startIntId = $rel->getStartNodeId();            // integer (legacy)
$endIntId   = $rel->getEndNodeId();              // integer (legacy)
$startEId   = $rel->getStartNodeElementId();     // string element ID
$endEId     = $rel->getEndNodeElementId();       // string element ID
$since      = $rel->getProperty('since');

// Path
$path  = $row->get('p');                         // Laudis\Neo4j\Types\Path
$nodes = $path->getNodes();                      // CypherList<Node>
$rels  = $path->getRelationships();              // CypherList<Relationship>
```
