> Source: manual — neo4j-cypher-authoring-skill v2026.02.0  generated: 2026-03-23

# APOC (Awesome Procedures on Cypher) — Core Reference

> **Availability**:
> - `apoc-core`: bundled with Neo4j 5+ and **always on in Aura**. Covers `apoc.map.*`, `apoc.coll.*`, `apoc.text.*`, `apoc.date.*`, `apoc.temporal.*`, `apoc.path.*`, and most utility functions.
> - `apoc-extended`: optional plugin (NOT in Aura). Adds `apoc.load.*`, `apoc.export.*`, and advanced procedures.
> - **Only use `apoc.*` when the injected schema context `capabilities` list includes `"apoc"` (or `"apoc-extended"`)**. Do NOT emit APOC calls if capabilities is absent.

---

## 1. Map Utilities (`apoc.map.*`)

```cypher
// Build a map from two lists of keys and values
CYPHER 25
WITH apoc.map.fromLists(['a', 'b', 'c'], [1, 2, 3]) AS m
RETURN m  // {a: 1, b: 2, c: 3}

// Merge two maps (right wins on key conflict)
CYPHER 25
RETURN apoc.map.merge({x: 1}, {x: 2, y: 3}) AS merged  // {x: 2, y: 3}

// Set/remove a key from a map
CYPHER 25
RETURN apoc.map.setKey({a: 1, b: 2}, 'a', 99) AS updated         // {a: 99, b: 2}
RETURN apoc.map.removeKey({a: 1, b: 2}, 'b') AS cleaned          // {a: 1}

// Convert list of [key, value] pairs to a map
CYPHER 25
RETURN apoc.map.fromPairs([['x', 10], ['y', 20]]) AS m            // {x: 10, y: 20}
```

---

## 2. Collection Utilities (`apoc.coll.*`)

```cypher
// Set operations
CYPHER 25
RETURN apoc.coll.intersection([1,2,3,4], [2,4,6]) AS inter       // [2, 4]
RETURN apoc.coll.union([1,2,3], [2,3,4]) AS u                    // [1, 2, 3, 4]
RETURN apoc.coll.subtract([1,2,3,4], [2,4]) AS diff              // [1, 3]

// Deduplicate
CYPHER 25
RETURN apoc.coll.toSet([1, 1, 2, 3, 2]) AS unique               // [1, 2, 3]

// Sort (supports list of primitives)
CYPHER 25
RETURN apoc.coll.sort([3, 1, 4, 1, 5]) AS sorted                // [1, 1, 3, 4, 5]

// Flatten nested list
CYPHER 25
RETURN apoc.coll.flatten([[1, 2], [3, [4, 5]]]) AS flat         // [1, 2, 3, 4, 5]

// Zip two lists into pairs
CYPHER 25
RETURN apoc.coll.zip(['a','b'], [1,2]) AS pairs                  // [['a',1],['b',2]]

// Partition list into sublists of size N
CYPHER 25
RETURN apoc.coll.partition([1,2,3,4,5], 2) AS chunks            // [[1,2],[3,4],[5]]

// Average of a numeric list
CYPHER 25
RETURN apoc.coll.avg([10.0, 20.0, 30.0]) AS avg                 // 20.0
```

---

## 3. String Utilities (`apoc.text.*`)

```cypher
// Slug/clean text (camelCase → 'camel case')
CYPHER 25
RETURN apoc.text.camelCase('hello world') AS cc                  // 'helloWorld'
RETURN apoc.text.snakeCase('HelloWorld') AS sc                   // 'hello_world'

// Levenshtein edit distance (0 = identical; higher = more different)
CYPHER 25
RETURN apoc.text.distance('kitten', 'sitting') AS dist          // 3

// Jaro-Winkler similarity (0–1; 1 = identical) — fuzzy name matching
CYPHER 25
RETURN apoc.text.jaroWinklerDistance('John', 'Jon') AS sim      // e.g. 0.933

// Phone-level similarity with Soundex/Double Metaphone
CYPHER 25
RETURN apoc.text.doubleMetaphone('Smith') AS dm                  // 'SM0'

// Clean whitespace / normalize
CYPHER 25
RETURN apoc.text.clean('  Hello   World  ') AS cleaned           // 'Hello World'

// Replace all occurrences (regex-aware)
CYPHER 25
RETURN apoc.text.regexGroups('2026-03-23', '(\\d{4})-(\\d{2})-(\\d{2})') AS parts
// [['2026-03-23', '2026', '03', '23']]
```

---

## 4. Date & Temporal Utilities (`apoc.date.*` / `apoc.temporal.*`)

```cypher
// Parse a non-ISO date string → epoch milliseconds
CYPHER 25
RETURN apoc.date.parse('23/03/2026', 'ms', 'dd/MM/yyyy') AS epochMs

// Format epoch ms → readable string
CYPHER 25
RETURN apoc.date.format(1711152000000, 'ms', 'dd/MM/yyyy') AS formatted

// Add duration to epoch timestamp
CYPHER 25
RETURN apoc.date.add(1711152000000, 'ms', 7, 'd') AS sevenDaysLater

// Truncate Cypher temporal value to specific unit (Neo4j temporal-aware)
CYPHER 25
RETURN apoc.temporal.truncate(datetime('2026-03-23T14:35:00'), 'day') AS truncated
// datetime('2026-03-23T00:00:00')

// Format Cypher temporal value as custom string
CYPHER 25
WITH datetime('2026-03-23T14:35:00') AS dt
RETURN apoc.temporal.format(dt, 'yyyy-MM-dd HH:mm') AS formatted
```

---

## 5. Path / Graph Traversal (`apoc.path.*`)

> `apoc.path.*` procedures are useful when a full QPE traversal is too broad and you need breadth-first / depth-first with callback predicates. Only available with `apoc-core`.

```cypher
// Expand from a start node with relationship filter
CYPHER 25
MATCH (start:Organization {name: 'Apple'})
CALL apoc.path.expand(start, 'HAS_SUBSIDIARY>', null, 1, 5)
YIELD path
RETURN [n IN nodes(path) | n.name] AS chain, length(path) AS depth;

// Subgraph reachable within max hops, returning nodes only
CYPHER 25
MATCH (start:Person {id: $id})
CALL apoc.path.subgraphNodes(start, {
  relationshipFilter: 'KNOWS',
  maxLevel: 3,
  labelFilter: 'Person'
})
YIELD node
RETURN node.name;

// Breadth-first span from multiple starting nodes
CYPHER 25
MATCH (a:Account) WHERE a.fraudFlag = 'True'
WITH collect(a) AS seeds
CALL apoc.path.expandConfig(seeds[0], {
  relationshipFilter: 'SHARED_IDENTIFIERS',
  minLevel: 1, maxLevel: 4,
  uniqueness: 'NODE_GLOBAL'
})
YIELD path
RETURN path;
```

**Relationship filter syntax**: `'REL_TYPE>'` = outgoing, `'<REL_TYPE'` = incoming, `'REL_TYPE'` = either. Combine types with `|`: `'KNOWS|WORKS_AT>'`.

---

## 6. Load & Export (apoc-extended only)

> These procedures require `apoc-extended` in `capabilities`. NOT available in Aura.

```cypher
// Load CSV from URL (line by line)
CYPHER 25
CALL apoc.load.csv('https://example.com/data.csv', {header: true, sep: ','})
YIELD map
MERGE (p:Product {id: map.id})
ON CREATE SET p.name = map.name, p.price = toFloat(map.price);

// Load JSON from URL
CYPHER 25
CALL apoc.load.json('https://api.example.com/items')
YIELD value
UNWIND value.items AS item
MERGE (n:Item {id: item.id}) ON CREATE SET n += item;

// Export graph to JSON (writes to import dir)
CYPHER 25
CALL apoc.export.json.all('export.json', {batchSize: 1000})
YIELD file, source, format, nodes, relationships, time;
```

---

## 7. Availability Check

```cypher
// Check if APOC core is installed
CYPHER 25
SHOW PROCEDURES WHERE name = 'apoc.meta.schema'
YIELD name RETURN count(name) > 0 AS apocAvailable;

// Check if apoc-extended is available
CYPHER 25
SHOW PROCEDURES WHERE name = 'apoc.load.csv'
YIELD name RETURN count(name) > 0 AS apocExtendedAvailable;
```

---

## Key Rules

- **Capability gate**: only use `apoc.*` when `"apoc"` appears in `capabilities` in the schema context. Aura always provides apoc-core; local/cloud Neo4j depends on installation.
- **`apoc-extended` gate**: `apoc.load.*` and `apoc.export.*` require `"apoc-extended"` in capabilities — not available in Aura.
- **Prefer native Cypher** when an equivalent exists: `collect()`, `size()`, `[x IN list WHERE ...]`, `duration.between()`. APOC is for operations that Cypher cannot express natively.
- **apoc.path.expand** relationship filter direction markers (`>`, `<`) are string tokens, not Cypher arrows.
- **apoc.date.parse/format** operates on epoch milliseconds (`'ms'`) or seconds (`'s'`) — not on Neo4j `date()`/`datetime()` types. Use `apoc.temporal.*` for Neo4j temporal values.
