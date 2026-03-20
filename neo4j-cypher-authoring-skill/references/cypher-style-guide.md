> Source: git@github.com:neo4j/docs-cypher.git@238ab12a
> Generated: 2026-03-20
> Files: styleguide.adoc, syntax/naming.adoc, syntax/keywords.adoc

# Cypher Style Guide

## Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Node labels | PascalCase (no separators) | `:Person`, `:VehicleOwner` |
| Relationship types | SCREAMING_SNAKE_CASE | `:OWNS_VEHICLE`, `:KNOWS` |
| Properties | camelCase (lower first) | `firstName`, `createdAt` |
| Variables | camelCase (lower first) | `person`, `relType` |
| Parameters | camelCase (lower first) | `$userId`, `$pageSize` |
| Functions | camelCase + parentheses | `toString()`, `count()` |

**Rules:**
- Names are **case-sensitive**: `:Person` ≠ `:person` ≠ `:PERSON`
- Names must start with an alphabetic character (no leading digits or symbols)
- Names must not contain symbols except `_`; use backticks only when unavoidable
- Max identifier length: 16,383 characters

**Backtick usage (avoid when possible):**
```cypher
// Avoid — requires backticks
MATCH (`odd-label` {`my prop`: 42})

// Prefer — clean identifiers
MATCH (n:CleanLabel {myProp: 42})
```

---

## Casing Rules

| Token type | Case | Example |
|---|---|---|
| Clauses / operators / keywords | UPPERCASE | `MATCH`, `WHERE`, `RETURN`, `AND`, `OR`, `NOT`, `IN`, `STARTS WITH`, `CONTAINS`, `IS NULL` |
| Functions | camelCase | `count()`, `toInteger()`, `toLower()`, `elementId()` |
| Boolean literals | lowercase | `true`, `false` |
| Null literal | lowercase | `null` |
| String literals | single-quoted | `'Alice'`, `"Alice's"` (double when string contains `'`) |

```cypher
// Bad
match (p:Person) where p.name starts with 'Ma' return p.name, Count(p)

// Good
MATCH (p:Person)
WHERE p.name STARTS WITH 'Ma'
RETURN p.name, count(p)
```

```cypher
// Bad: wrong literal casing
WITH NULL AS n, TRUE AS b
// Good
WITH null AS n, true AS b
```

---

## Indentation and Line Breaks

- **One clause per line** — never inline multiple clauses
- **Indent 2 spaces** for `ON CREATE SET` / `ON MATCH SET` under `MERGE`
- `ON CREATE` before `ON MATCH` when both present
- **80-character soft limit** — break long `WHERE` conditions at `AND`/`OR`
- `ORDER BY` and `LIMIT` each on their own line
- Break after arrows when patterns wrap, not before

```cypher
// Bad
MERGE (n) ON CREATE SET n.prop = 0
MERGE (a:A)-[:T]->(b:B) ON MATCH SET b.name = 'you' ON CREATE SET a.name = 'me'

// Good
MERGE (n)
  ON CREATE SET n.prop = 0
MERGE (a:A)-[:T]->(b:B)
  ON CREATE SET a.name = 'me'
  ON MATCH SET b.name = 'you'
```

```cypher
// Long WHERE — break at AND
MATCH (n)
WHERE
  n.prop <> 'a' AND
  n.prop <> 'b' AND
  n.prop <> 'c'
RETURN n
ORDER BY n.prop
LIMIT 10
```

**Subqueries:**
```cypher
// Full CALL/EXISTS subquery — open brace same line, indent body 2 spaces, close brace own line
MATCH (a:A)
WHERE EXISTS {
  MATCH (a)-->(b:B)
  WHERE b.prop = 'yellow'
}
RETURN a.foo

// Simplified (pattern-only) subquery — keep on one line, pad with spaces
WHERE EXISTS { (a)-->(b:B) }
```

**CASE expression — always break:**
```cypher
RETURN
  CASE
    WHEN n.age >= 18 THEN 'Adult'
    ELSE 'Minor'
  END AS ageGroup
```

---

## Spacing Rules

| Context | Rule | Example |
|---|---|---|
| Operators | Wrap with spaces | `n.age > 18`, `a <> b` |
| Pattern arrows | No spaces | `(a)-->(b)`, `(a)-[:REL]->(b)` |
| Label predicates | No spaces | `(p:Person:Owner)` |
| Property map in pattern | Space after `:` label, before `{` | `(p:Person {name: 'Alice'})` |
| Literal map `{}` | `{key: value, key2: val2}` | No space before `:`, one after; one after `,` |
| Function calls | No padding inside `()` | `split('a', 'i')` not `split( 'a', 'i' )` |
| Simple subquery `{}` | Pad with spaces | `EXISTS { (a)-->(b) }` |
| After comma | One space | `RETURN a, b, c` |
| No semicolon at end | Omit `;` | `RETURN 1` |

---

## Pattern Authoring

- **Anonymous** nodes/relationships when variable is unused: `(:Person)-[:KNOWS]->(c:Company)`
- **Chain** patterns instead of repeating variables: `(a)-->(b)-->(c)` not `(a)-->(b), (b)-->(c)`
- Put **named** nodes before anonymous nodes
- Start with the **anchor** (most constrained) node; prefer left-to-right direction
- Break long patterns **after** arrows: `(...)->(\n      ...)`

---

## String Quoting

- Use **single quotes** `'value'` by default
- Use **double quotes** `"value"` when string contains a single quote: `"Cypher's easy"`
- When string has both, use the form requiring fewest escapes; tie → single quotes
- Avoid backtick-quoted identifiers in queries that serve unsanitized user input (injection risk)
