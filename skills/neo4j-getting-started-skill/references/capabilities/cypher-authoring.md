# Capability — cypher-authoring
# Guidelines for generating correct Cypher 25 queries.
# For deep Cypher authoring, load neo4j-cypher-authoring-skill if available.

## When to use neo4j-cypher-authoring-skill

If `neo4j-cypher-authoring-skill` is available, defer all Cypher generation to it — it has comprehensive Cypher 25 rules, QPE handling, and a schema-first protocol that produces higher-quality queries.

To check:
```bash
ls ../neo4j-cypher-authoring-skill/SKILL.md 2>/dev/null && echo "Available" || echo "Not found"
```

If available: `--append-system-prompt ../neo4j-cypher-authoring-skill/SKILL.md`

## Minimum rules for Cypher generated in this skill

### Mandatory

- Every query starts with `CYPHER 25`
- Always specify node labels — never `MATCH (n)` without a label except for counts
- Always add `LIMIT` to read queries
- Use `$param` placeholders for user-supplied values
- Labels and property names are case-sensitive — match schema exactly
- Use `MERGE` not `CREATE` for idempotent writes
- `IS NULL` / `IS NOT NULL` — never `= null`

### MERGE safety

```cypher
// Nodes: always specify the primary key in the MERGE pattern
MERGE (p:Person {id: $id})
SET p.name = $name, p.updatedAt = datetime();

// Relationships: always MATCH both endpoints first, then MERGE the relationship
MATCH (a:Person {id: $fromId})
MATCH (b:Person {id: $toId})
MERGE (a)-[:FOLLOWS]->(b)
```

### Write batching

```cypher
CYPHER 25
UNWIND $batch AS row
CALL (row) {
  MERGE (n:Label {id: row.id})
  SET n.name = row.name
} IN TRANSACTIONS OF 500 ROWS;
```

### Schema-first protocol

Before writing any MATCH clause:
1. Confirm node labels exist in schema
2. Confirm relationship types exist in schema  
3. Confirm property names are spelled correctly
4. Check whether indexes exist for the lookup property

### GDS / APOC guard

Only generate GDS or APOC queries after confirming availability:
```bash
cypher-shell ... "CALL gds.version() YIELD version" 2>/dev/null || echo "GDS not available"
```

Aura Free has no GDS. Local Docker default image has no GDS unless plugin flag is set.

### Vector / fulltext search

**Vector** (confirmed index exists):
```cypher
CYPHER 25
MATCH (node)
  SEARCH node IN (
    VECTOR INDEX index_name
    FOR $embedding
    LIMIT $topK
  ) SCORE AS score
RETURN node.text AS text, score ORDER BY score DESC;
```

**Fulltext**:
```cypher
CYPHER 25
CALL db.index.fulltext.queryNodes('index_name', $searchTerm)
YIELD node, score
RETURN node.name AS name, score ORDER BY score DESC LIMIT 20;
```

## Pattern anti-patterns — always apply these rewrites

### Existence checks — use EXISTS subquery, not pattern predicate

```cypher
// ✗ Wrong — legacy pattern predicate, deprecated in CYPHER 25
WHERE NOT (me)-[:FOLLOWS]->(other)
WHERE (a)-[:KNOWS]->(b)

// ✓ Correct — EXISTS subquery
WHERE NOT exists { (me)-[:FOLLOWS]->(other) }
WHERE exists { (a)-[:KNOWS]->(b) }
```

### Inline count — use COUNT subquery, not OPTIONAL MATCH + count(DISTINCT)

```cypher
// ✗ Wrong — verbose and slower
OPTIONAL MATCH (p)<-[:FOLLOWS]-(follower)
RETURN p.name, count(DISTINCT follower) AS followers

// ✓ Correct — inline count subquery
RETURN p.name, count { (p)<-[:FOLLOWS]-() } AS followers
```

### Property access — defer to the final RETURN, aggregate on nodes

Access properties only after filtering and sorting on the minimal node set.
Accessing properties in a `WITH` that feeds `ORDER BY` or aggregation forces
property reads on more rows than necessary.

```cypher
// ✗ Wrong — property access before aggregation, sorts/limits on property values
MATCH (me:Person {id: $id})-[:FOLLOWS]->(f)-[:FOLLOWS]->(fof)
WHERE NOT exists { (me)-[:FOLLOWS]->(fof) } AND me <> fof
RETURN fof.name AS recommendation, fof.bio AS bio,
       count(DISTINCT f) AS mutualFriends
ORDER BY mutualFriends DESC LIMIT 10

// ✓ Correct — aggregate on nodes, sort/limit, then access properties in final RETURN
MATCH (me:Person {id: $id})-[:FOLLOWS]->(f)-[:FOLLOWS]->(fof)
WHERE NOT exists { (me)-[:FOLLOWS]->(fof) } AND me <> fof
WITH fof, count(DISTINCT f) AS mutualFriends
ORDER BY mutualFriends DESC LIMIT 10
RETURN fof.name AS recommendation, fof.bio AS bio, mutualFriends
```

Apply whenever ORDER BY or LIMIT precedes property access: use `WITH node, aggregation ORDER BY ... LIMIT` then `RETURN node.prop`.

## Common pitfalls (validated against Neo4j 2026.x / CYPHER 25)

| Wrong | Correct | Note |
|-------|---------|------|
| `-- comment` | `// comment` | Cypher uses `//`, not SQL `--` |
| `OPTIONS { indexConfig: { 'vector.dimensions': 1536 } }` | `OPTIONS { indexConfig: { \`vector.dimensions\`: 1536 } }` | Map keys in OPTIONS must be backtick identifiers, not strings |
| `(a)-[:REL*0..5]->(b)` | `(a) (()-[:REL]->()){0,5} (b)` | Use quantified path patterns (QPP) in CYPHER 25, not `*min..max` |
| `CALL db.index.vector.queryNodes('idx', k, $vec) YIELD node, score` | `MATCH (node) SEARCH node IN (VECTOR INDEX idx FOR $vec LIMIT k) SCORE AS score` | New `SEARCH` clause (Neo4j 2026.01+); procedure still works but is deprecated |
| `driver.execute_query("CALL (row) { ... } IN TRANSACTIONS OF N ROWS")` | `session.run("CALL (row) { ... } IN TRANSACTIONS OF N ROWS")` | `CALL {} IN TRANSACTIONS` requires an auto-commit (implicit) transaction — `execute_query` uses a managed transaction and will fail |
| `CALL { MATCH (n) DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS` | `MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 1000 ROWS` | Pass binding variable `(n)` into subquery so each node is its own batch row; outer CALL {} with inner MATCH doesn't batch at all — runs one giant tx |
| `CALL { UNWIND $batch AS row MERGE ... } IN TRANSACTIONS OF 500 ROWS` | `UNWIND $batch AS row CALL (row) { MERGE ... } IN TRANSACTIONS OF 500 ROWS` | Always wrong: `IN TRANSACTIONS OF N ROWS` batches on rows flowing *into* the subquery from outside. With UNWIND inside, the whole list runs in one transaction — batching has no effect. Move UNWIND outside and import the variable via `CALL (row) { ... }` |
| `WHERE NOT (a)-[:REL]->(b)` | `WHERE NOT exists { (a)-[:REL]->(b) }` | Pattern predicates are deprecated in CYPHER 25 — use EXISTS subquery |
| `WHERE (a)-[:REL]->(b)` | `WHERE exists { (a)-[:REL]->(b) }` | Same — positive pattern check also needs EXISTS subquery |
| `OPTIONAL MATCH (n)<-[:REL]-(m) RETURN count(DISTINCT m)` | `RETURN count { (n)<-[:REL]-() }` | Use inline COUNT subquery instead of OPTIONAL MATCH + count(DISTINCT) |
| `RETURN n.name, count(x) ORDER BY count(x)` | `WITH n, count(x) AS cnt ORDER BY cnt LIMIT k RETURN n.name, cnt` | Access properties after aggregation + sort/limit, not before — avoids reading properties on rows that will be discarded |
