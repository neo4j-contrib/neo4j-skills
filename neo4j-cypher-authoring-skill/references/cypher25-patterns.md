> Source: git@github.com:neo4j/docs-cypher.git@238ab12a / git@github.com:neo4j/docs-cheat-sheet.git@e11fe2f2
> Generated: 2026-03-20T00:00:00Z
> Files: patterns/variable-length-patterns.adoc, patterns/shortest-paths.adoc, patterns/non-linear-patterns.adoc, patterns/match-modes.adoc, quantified-path-patterns.adoc, path-pattern-expressions.adoc

## Quantified Path Patterns (QPE)

Syntax: wrap a path segment in `()` and append a quantifier.

| Quantifier | Meaning |
| --- | --- |
| `{m,n}` | Between m and n repetitions (inclusive) |
| `{n}` | Exactly n repetitions |
| `{m,}` | At least m repetitions |
| `+` | One or more (shorthand for `{1,}`) |
| `*` | Zero or more (shorthand for `{0,}`) |

```cypher
// QPE — full form
MATCH (:A)-[(:X)-[:R]->(:Y)]{1,5}->(:B)

// QPE — quantified relationship (shorthand when only rel varies)
MATCH (a:Person)-[:KNOWS]-{1,3}(b:Person)

// Plus quantifier
MATCH SHORTEST 1 (src:Station)-[:LINK]-+(dst:Station)

// Star quantifier (use with care — may match zero hops)
MATCH (a)-[:FOLLOWS]-*(b)
```

**Predicates inside QPE** — use `WHERE` inside the parentheses to filter each hop:

```cypher
MATCH ((m:Person)-[:KNOWS]->(n:Person) WHERE m.born < n.born){1,5}
```

## Group Variables

Variables declared *inside* a QPE are **group variables** — bound to a list of all matched elements across repetitions:

```cypher
MATCH (start)-[(r:NEXT)]->{2,4}(end)
RETURN [x IN r | x.distance] AS legDistances  // r is a list
```

Variables declared *outside* the QPE are singleton variables.

## Shortest Paths

`SHORTEST` replaces the deprecated `shortestPath()` and `allShortestPaths()` functions.

| Keyword | Meaning |
| --- | --- |
| `SHORTEST 1` | One shortest path (non-deterministic if tie) |
| `SHORTEST k` | Up to k shortest paths |
| `ALL SHORTEST` | All paths tied for shortest length |
| `SHORTEST k GROUPS` | All paths tied for 1st, 2nd, … up to kth shortest |
| `ANY` | Same as `SHORTEST 1`; preferred when testing reachability |

```cypher
// Single shortest path
MATCH p = SHORTEST 1 (a:Station {name: 'X'})-[:LINK]-+(b:Station {name: 'Y'})
RETURN length(p) AS hops

// All shortest paths
MATCH p = ALL SHORTEST (a:Station)-[:LINK]-+(b:Station)

// Any (reachability test)
MATCH path = ANY (src)-[:KNOWS]-+(dst:Person {name: 'Alice'})

// Shortest k groups
MATCH p = SHORTEST 2 GROUPS (a)-[r]-+(b)
RETURN length(p), [x IN r | x.cost] AS costs
```

**Pre-filters** (inside the QPE) are applied at each hop; **post-filters** (WHERE after MATCH) are applied after full path expansion. Use pre-filters for performance.

## Match Modes

Specified after `MATCH` keyword. Default is `DIFFERENT RELATIONSHIPS`.

| Mode | Behavior |
| --- | --- |
| `DIFFERENT RELATIONSHIPS` | Each relationship may appear at most once in a match (default). Nodes may repeat. |
| `REPEATABLE ELEMENTS` | No restriction — nodes and relationships can repeat. Requires bounded quantifier. |

```cypher
// Explicit default (equivalent to omitting the keyword)
MATCH DIFFERENT RELATIONSHIPS p = (a)--{,5}(b)

// Allow relationship re-traversal — MUST use bounded quantifier
MATCH REPEATABLE ELEMENTS p = (a:Location {name: 'X'})-[:BRIDGE]-{7}(b)
```

> **Warning**: `REPEATABLE ELEMENTS` with unbounded quantifiers (`+`, `*`, `{1,}`) raises error 42N53.

`DIFFERENT RELATIONSHIPS` keyword available since Neo4j 2025.06 (Cypher 25 only); previously the default was implicit.

## Non-Linear Patterns

**Equijoin** — same variable in multiple patterns forces the matched element to be identical:

```cypher
// Both paths must share the same 'mid' node
MATCH (a)-[:KNOWS]->(mid), (mid)-[:LIKES]->(c)
```

**Graph patterns** — comma-separated path patterns:

```cypher
MATCH (a:Person)-[:WORKS_AT]->(co:Company),
      (co)-[:LOCATED_IN]->(city:City)
WHERE city.name = 'Berlin'
RETURN a.name, co.name
```

## Path Pattern Expressions

A path pattern used as a boolean predicate inside `WHERE` (similar to `EXISTS` subquery):

```cypher
// Assert path exists (path pattern expression)
MATCH (a:Person)
WHERE (a)-[:KNOWS]->(:Person {name: 'Alice'})
RETURN a.name

// With boolean operators
MATCH (a:Person)
WHERE (a)-[:KNOWS]->(:Person) AND NOT (a)-[:BLOCKS]->(:Person {name: 'Bob'})
RETURN a.name
```

## Deprecated Syntax

| Deprecated | Cypher 25 Replacement |
| --- | --- |
| `shortestPath((a)-[*]-(b))` | `SHORTEST 1 (a)--+(b)` |
| `allShortestPaths((a)-[*]-(b))` | `ALL SHORTEST (a)--+(b)` |
| `[:REL*]` variable-length rel | QPE: `(:A)-[:REL]-+(:B)` or `{m,n}` form |
