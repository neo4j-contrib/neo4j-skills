> Source: git@github.com:neo4j/docs-cypher.git@238ab12a
> Files: subqueries/call-subquery.adoc, subqueries/count.adoc, subqueries/collect.adoc, subqueries/existential.adoc
> Curated: 2026-03-20

# Cypher 25 — Read Subqueries Reference

Covers: `CALL` subqueries (read), `COUNT {}`, `COLLECT {}`, `EXISTS {}`.
For bulk-write subqueries (`CALL IN TRANSACTIONS`), see `write/cypher25-call-in-transactions.md`.

## Subquery forms at a glance

| Form | Used in | Returns | Outer vars auto-imported? | Body format |
|---|---|---|---|---|
| `CALL (vars) { ... }` | Standalone clause | Multiple columns, multiple rows | No — must declare in `()` | Full Cypher statement |
| `COUNT { ... }` | Expression (WHERE, RETURN, etc.) | INTEGER | Yes | Pattern **or** full statement |
| `COLLECT { MATCH ... RETURN x }` | Expression | LIST | Yes | **Full statement only** (MATCH + RETURN required) |
| `EXISTS { ... }` | Predicate expression | BOOLEAN | Yes | Pattern **or** full statement |

**Critical format rule:**
- `EXISTS {}` and `COUNT {}` accept **both** a bare pattern `(a)-[:R]->(b)` (with optional `WHERE`) **and** a full Cypher statement with `MATCH ... RETURN`.
- `COLLECT {}` accepts **only** the full statement form — `COLLECT { MATCH ... RETURN x }`. A bare pattern inside `COLLECT {}` is a syntax error.

```cypher
-- EXISTS: both forms valid
EXISTS { (person)-[:HAS_DOG]->(:Dog) }                          -- bare pattern ✓
EXISTS { MATCH (person)-[:HAS_DOG]->(d:Dog) WHERE d.age > 2 }  -- full statement ✓

-- COUNT: both forms valid
COUNT { (person)-[:HAS_DOG]->() }                              -- bare pattern ✓
COUNT { MATCH (person)-[:HAS_DOG]->(d:Dog) WHERE d.age > 2 }   -- full statement ✓

-- COLLECT: full statement ONLY
COLLECT { MATCH (person)-[:HAS_DOG]->(d:Dog) RETURN d.name }   -- ✓
COLLECT { (person)-[:HAS_DOG]->(d:Dog) }                       -- SYNTAX ERROR ✗
```

`COUNT {}` vs `count()`: `COUNT { pattern }` counts **rows** from a subquery; `count(expr)` is an aggregating function over the current row stream — not interchangeable.

---

## CALL subqueries

### Scope (variable import) — Cypher 25

Variables from the outer scope **must be explicitly imported** via a scope clause:

```cypher
MATCH (t:Team)
CALL (t) {
  MATCH (p:Player)-[:PLAYS_FOR]->(t)
  RETURN collect(p) AS players
}
RETURN t, players
```

Scope clause variants:
- `CALL (x, y)` — import specific variables
- `CALL (*)` — import all outer variables
- `CALL ()` — import nothing (isolated subquery)

**Rules:**
- Imported vars are globally visible inside the subquery; a subsequent `WITH` cannot delist them.
- Variable names cannot be aliased in the scope clause (`CALL (x AS y)` is invalid).
- Subquery cannot return a name already used in outer scope — rename it.
- `CALL` subqueries **without** a scope clause are **deprecated**.

### Deprecated importing WITH (do not use)

```cypher
-- DEPRECATED
CALL {
  WITH x        -- importing WITH, must be first clause
  MATCH (n:Label {id: x})
  RETURN n
}
```

Restrictions: cannot follow `WITH` with `DISTINCT`, `ORDER BY`, `WHERE`, `SKIP`, `LIMIT`.

### Execution semantics

- Executes **once per incoming row**; each execution can observe changes from previous executions.
- Variables returned by the subquery are added to the outer row.
- Memory benefit: intermediate data structures released after each row's execution.

### OPTIONAL CALL

```cypher
MATCH (p:Player)
OPTIONAL CALL (p) {
  MATCH (p)-[:PLAYS_FOR]->(t:Team)
  RETURN t
}
RETURN p, t  -- t is null if no team found
```

Behaves like `OPTIONAL MATCH` — null-pads missing rows instead of dropping them.

---

## COUNT subquery

```cypher
-- In WHERE
MATCH (person:Person)
WHERE COUNT { (person)-[:HAS_DOG]->(:Dog) } > 1
RETURN person.name

-- With WHERE inside subquery
MATCH (person:Person)
WHERE COUNT {
  (person)-[:HAS_DOG]->(dog:Dog)
  WHERE person.name = dog.name
} = 1
RETURN person.name

-- In RETURN
MATCH (p:Person)
RETURN p.name, COUNT { (p)-[:HAS_DOG]->() } AS dogCount
```

- Outer-scope variables **automatically in scope** — no import needed.
- Returns `INTEGER` — use in numeric comparisons or as a RETURN expression.
- **Pattern form** (simple): `COUNT { (a)-[:R]->(b) }` or `COUNT { (a)-[:R]->(b) WHERE cond }` — no MATCH, no RETURN.
- **Full statement form**: `COUNT { MATCH (a)-[:R]->(b) WHERE ... RETURN a }` — RETURN is optional in this form.

---

## COLLECT subquery

```cypher
-- In WHERE (membership test)
MATCH (person:Person)
WHERE 'Ozzy' IN COLLECT { MATCH (person)-[:HAS_DOG]->(d:Dog) RETURN d.name }
RETURN person.name

-- In SET / RETURN
MATCH (person:Person)
SET person.dogNames = COLLECT { MATCH (person)-[:HAS_DOG]->(d:Dog) RETURN d.name }

-- With WHERE inside
MATCH (person:Person)
RETURN person.name, COLLECT {
  MATCH (person)-[r:HAS_DOG]->(d:Dog)
  WHERE r.since > 2017
  RETURN d.name
} AS recentDogs
```

- **Full statement only**: `COLLECT { MATCH ... RETURN x }` — `MATCH` and `RETURN` are both mandatory.
- `RETURN` must return **exactly one column** — `RETURN x` not `RETURN x, y`.
- Bare pattern form (`COLLECT { (a)-[:R]->(b) }`) is **not valid** — syntax error.
- Outer-scope variables automatically in scope.
- Returns `LIST` — use anywhere a list is expected.

---

## EXISTS subquery

```cypher
MATCH (person:Person)
WHERE EXISTS {
  MATCH (person)-[:HAS_DOG]->(dog:Dog)
  WHERE person.name = dog.name
}
RETURN person.name
```

- Outer-scope variables automatically in scope.
- Returns `BOOLEAN` — use only as a predicate.
- **Pattern form**: `EXISTS { (a)-[:R]->(b) }` or `EXISTS { (a)-[:R]->(b) WHERE cond }` — no MATCH needed.
- **Full statement form**: `EXISTS { MATCH (a)-[:R]->(b) WHERE ... }` — RETURN clause is omitted (the subquery just needs to match something).
- Short-circuits on first match (efficient).
- `NOT EXISTS { ... }` follows the same rules — both pattern and full statement forms are valid.

---

## Scope summary

| Subquery | Outer vars | Import syntax |
|---|---|---|
| `CALL` | Not auto-imported | `CALL (x, y)` required |
| `COUNT { }` | Auto-imported | None |
| `COLLECT { }` | Auto-imported | None |
| `EXISTS { }` | Auto-imported | None |
