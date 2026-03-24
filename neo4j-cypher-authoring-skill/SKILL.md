---
name: neo4j-cypher-authoring-skill
description: Generates, optimizes, and validates Cypher 25 queries for Neo4j 2025.x
  and 2026.x. Use when writing new Cypher queries, optimizing slow queries, graph
  pattern matching, vector or fulltext search, subqueries, batch writes, or building
  queries for autonomous agents. Covers MATCH, MERGE, CREATE, WITH, RETURN, CALL,
  UNWIND, FOREACH, LOAD CSV, SEARCH, expressions, functions, indexes, and subqueries.
  Not for driver migration or database administration.
allowed-tools: WebFetch
compatibility: Neo4j >= 2025.01; Cypher 25
---

## When NOT to Use This Skill

- **Driver code** → use `neo4j-migration-skill`
- **DB administration** (CREATE DATABASE, ALTER USER, roles, privileges, SHOW SERVERS) → use `neo4j-cli-tools-skill`
- **Cypher 4.x / 5.x migration** → use `neo4j-cypher-skill`
- **GQL-only clauses**: never emit `LET`, `FINISH`, `FILTER`, `NEXT`, `INSERT` — use `WITH`, `RETURN`, `WHERE`, `CREATE`

---

## Autonomous Operation Protocol

Non-negotiable defaults — apply before writing any query:

1. **CYPHER 25 always** — first token of every query
2. **Schema first** — inspect schema before writing any `MATCH` clause; if schema is provided in the prompt, use it directly
3. **Version** — resolve target DB version in order: (1) `database.neo4j_version` from injected schema context; (2) `CYPHER 25 CALL dbms.components() YIELD name, version RETURN version` if absent (note: Aura reports an internal version — treat Aura as always-latest); (3) assume conservative defaults if unknown. Cross-reference `references/version-matrix.md` before using any version-gated feature (SEARCH, GRAPH TYPE, `+`/`*` shorthands). When applying a conservative fallback, add an inline comment: `// version unknown — using {1,} instead of +`
4. **Output mode** — check invocation context for `interactive` (literals) or `programmatic` (parameters); default to `interactive`; always return both (see Output Mode section)
5. **Schema fidelity** — after generating Cypher, validate every label, rel-type, and property against the schema before returning (see MUST VALIDATE section)
6. **MERGE safety** — every `MERGE` must have `ON CREATE SET` and `ON MATCH SET`
7. **Validate** — `EXPLAIN` every query; `PROFILE` when performance matters
8. **Recover** — handle 0-result queries, TypeErrors, timeouts autonomously
9. **READ/WRITE/ADMIN first** — categorize, then load only the relevant L3 folder
10. **MATCH mode keyword position** — `REPEATABLE ELEMENTS` and `DIFFERENT RELATIONSHIPS` go **immediately after `MATCH`**, never at the end of the pattern:
    - `MATCH REPEATABLE ELEMENTS (a)(()-[:R]->()){2}(b)` ✓
    - `MATCH (a)(()-[:R]->()){2}(b) REPEATABLE ELEMENTS` ✗ **SYNTAX ERROR**
11. **Comments use `//` only** — `--` (SQL-style) is **not valid Cypher** and will cause a parse error. Always use `// comment text` for inline or line comments.
12. **`CYPHER 25` prefix is a single-query prefix** — never repeat it after `UNION`, `UNION ALL`, or within a subquery. One `CYPHER 25` per query, at the very top.
13. **SHOW commands cannot be combined with UNION** — `SHOW PROCEDURES ... UNION ALL SHOW FUNCTIONS ...` is a syntax error. Use two separate queries when you need results from multiple SHOW commands.
14. **Map-property access in MATCH is invalid** — you cannot use `p.peer` or any property-access expression directly as a node in a MATCH pattern. Unpack the map first:
    - `UNWIND peers AS p WITH p.peer AS peer MATCH (peer)-[...]` ✓
    - `MATCH (p.peer)-[...]` ✗ **SYNTAX ERROR**
15. **`collect(x ORDER BY y)` is NOT valid Cypher** — the built-in `collect()` aggregation does not accept inline `ORDER BY`. Use either:
    - A preceding `ORDER BY y` clause before `... collect(x)` ✓
    - A COLLECT subquery: `COLLECT { MATCH (a)-[]->(b) RETURN b.name ORDER BY b.name }` ✓
16. **`ORDER BY expr AS alias` is ILLEGAL in Cypher** — `AS` is not allowed in ORDER BY items. Write `ORDER BY b.average_rating DESC`, never `ORDER BY b.average_rating AS average_rating DESC`.
17. **SQL window functions do not exist in Cypher** — `rank() OVER (PARTITION BY ...)`, `ROW_NUMBER() OVER (...)`, `DENSE_RANK() OVER (...)` are SQL syntax and will cause a syntax error. For "rank within group" use: `WITH cat, collect({supplier:s, value:v}) AS ranked UNWIND range(0, size(ranked)-1) AS idx RETURN cat, ranked[idx].supplier, idx+1 AS rank`.

---

## Cypher 25 Pragma + Schema-First Protocol

Every query begins with `CYPHER 25` (enables QPEs, SEARCH, CALL scope clauses, type predicates).

**If schema context is provided in the prompt** (labels, properties, indexes, constraints, vector dimensions) — use it directly. Do NOT run inspection queries; the user may lack read access, schema queries cannot be mixed with data queries in the same transaction, and the agent may never see results from a separate query turn.

**If no schema context is provided** — run these inspection queries before any `MATCH` clause:

```cypher
CYPHER 25 CALL db.schema.visualization() YIELD nodes, relationships RETURN nodes, relationships;
CYPHER 25 SHOW INDEXES YIELD name, type, labelsOrTypes, properties, options, state WHERE state = 'ONLINE' RETURN name, type, labelsOrTypes, properties, options;
CYPHER 25 SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties RETURN name, type, labelsOrTypes, properties;
// Detect APOC:
CYPHER 25 SHOW PROCEDURES WHERE name = 'apoc.meta.schema' YIELD name RETURN count(name) > 0 AS apocAvailable;
// If APOC: CYPHER 25 CALL apoc.meta.schema() YIELD value RETURN value;
// Else:    CYPHER 25 CALL db.schema.nodeTypeProperties() YIELD nodeLabels, propertyName, propertyTypes, mandatory RETURN nodeLabels, propertyName, propertyTypes, mandatory;
```

**Vector index dimensions**: always read from the provided schema context (the `dimensions` field on the index or property). Never introspect `options.vector.dimensions` at runtime — this requires a separate schema query the agent may not be able to execute. If dimensions are absent from the provided schema, state the assumption explicitly in a comment.

---

## Output Mode: Literals vs Parameters

**Always return both formats** as a YAML block. Default mode: `interactive` (literal values). `programmatic` mode uses `$param` for plan caching.

```yaml
query_literals: |
  CYPHER 25
  MATCH (n:Organization {name: 'Apple'}) RETURN n.name LIMIT 10
query_parametrized: |
  CYPHER 25
  MATCH (n:Organization {name: $name}) RETURN n.name LIMIT 10
parameters:
  name: "Apple"
```

Wrap `query_literals` in a ` ```cypher ` block too for direct rendering in interactive mode.

---

## MUST VALIDATE: Schema Fidelity

**After generating any Cypher query, before returning, verify every schema element against the provided schema. This is mandatory when a schema context is present in the prompt.**

### Validation checklist

| Element | Check | Action on failure |
|---|---|---|
| Node label `(n:Label)` | Label exists in schema's Node Labels | Replace with correct label from schema |
| **Label-free node** `(n)` | **Never emit unless strictly required** | **Add the correct label from schema** |
| Relationship type `-[:TYPE]->` | Type exists in schema's Relationship Types | Replace with nearest match from schema |
| Property `n.propName` | `propName` listed for that label in Node Properties | Remove or replace with a valid property |
| Index name in procedure call | Index name exists in schema's Indexes | Use correct index name from schema |
| **MERGE pattern** | Single-node with key only; rel MERGE has pre-bound endpoints; both `ON CREATE SET` and `ON MATCH SET` present | Refactor per MERGE Safety rules |

**Label-free `MATCH (n)` is forbidden** except in two narrow cases: (1) re-referencing a variable already bound with a label earlier in the same query; (2) inside a QPE group variable where the label is implied by the path pattern. In every other case, always specify the label. A label-free MATCH causes an `AllNodesScan` and will scan the entire graph.

### Vocabulary discipline

Business questions use domain vocabulary that does **not** match schema labels:

| Business term | Do NOT use | MUST use (from schema) |
|---|---|---|
| "company", "companies", "firm" | `:Company` | Use the label from the provided schema (e.g., `:Organization`) |
| "movie", "film" | `:Film` | Use label from schema (e.g., `:Movie`) |
| "user", "customer" | `:Member` | Use label from schema |
| ownership, "owns" | `:OWNS` | Use rel type from schema (e.g., `:HAS_SUBSIDIARY`) |
| "sends money" | `:TRANSFERS` | Use rel type from schema (e.g., `:SENT`) |

**Rule**: Never infer label or relationship type names from the business question wording. Always look them up in the provided schema. If no schema is provided, run the Schema-First Protocol before writing any MATCH clause.

### QPE quantifier compatibility

| Database | `+`/`*` shorthands | `{m,n}` / `{1,}` / `{0,}` | `REPEATABLE ELEMENTS` |
|---|---|---|---|
| Local Neo4j 2026.02.x | ✓ supported | ✓ | ✓ bounded `{m,n}` only |
| All other / unknown | ✗ use `{1,}` / `{0,}` | ✓ | ✓ bounded `{m,n}` only |

**Default to `{1,}` / `{0,}`.** Use `+`/`*` only after confirming support. `REPEATABLE ELEMENTS` always requires bounded `{m,n}` — never `+`, `*`, or `{1,}`.

---

## Value Normalization and Domain Translation

**When schema provides `values:` (enum) or `sample:` data, map user language to stored values before writing any query.**

> **Output format is internal.** Never mention `$param` placeholders or YAML keys in user-facing comments or responses.

**Rules:**
1. **Schema enum match** — map "active customers" → `'ACTIVE'` from schema `values`; "The Matrix" → `'Matrix, The'` if samples show article-inversion. Comment: `-- Translated: user said "active" → 'ACTIVE' (stored enum value)`
2. **Range validation** — if user value is outside schema `min`/`max` by 10×, surface a ⚠ concern and ask before proceeding
3. **ID pattern normalization** — `"txn 234"` → `"TXN-00234"` when samples show `"TXN-00001"` format
4. **No schema values?** — apply common-sense transformation (trim, uppercase, expand abbreviations); only elicit when genuinely insufficient

---

## Core Pattern Cheat Sheet

### MERGE Safety

**Rules:**
1. **Key property only** — `MERGE` on constrained key property(ies) only; set other properties in `ON CREATE SET` / `ON MATCH SET`
2. **Pre-bind endpoints** — for relationship MERGE, `MATCH` or `MERGE` both nodes first; never MERGE a full path
3. **Both sub-clauses** — every MERGE must have `ON CREATE SET` and `ON MATCH SET`

```cypher
// DO:     CYPHER 25 MATCH (a:Person {id:$a}) MATCH (b:Person {id:$b}) MERGE (a)-[r:KNOWS]->(b) ON CREATE SET r.since=date() ON MATCH SET r.lastSeen=date();
// DON'T: MERGE (p:Person {id:$id, name:$name})             // multi-property = duplicates
// DON'T: MERGE (:Person {id:$a})-[:KNOWS]->(:Person {id:$b}) // unbound = ghost nodes
```

### Quantified Path Expressions (QPEs)

**ALWAYS prefer `{1,}` over `+` and `{0,}` over `*`** — `+`/`*` shorthands fail on some servers (e.g. demo.neo4jlabs.com). Use `+`/`*` only after confirming server support.

Quantifier goes **outside** the group: `(pattern){N,M}` ✓ — never `(pattern{N,M})` ✗

```cypher
// DO:     CYPHER 25 MATCH (root:Category) (()-[:HAS_SUBCATEGORY]->()){1,} (leaf:Category) RETURN root.name, leaf.name;
// DO:     CYPHER 25 MATCH (a:Account) (()-[:SHARED_IDENTIFIERS]-()){2,4} (b:Account) RETURN a, b;
// DON'T: (()-[:HAS_SUBCATEGORY]->(){1,})  // {1,} INSIDE group — SYNTAX ERROR
// DON'T: (a:Account)-[:SHARED_IDENTIFIERS]-{2,4}-(b:Account)  // bare quantifier — SYNTAX ERROR
```

**NEVER** `SHORTEST 1 (a)-[:REL]+` — use `SHORTEST 1 (a)(()-[:REL]->()){1,}(b)`. Every node inside a QPE group must be closed: `(()-[:REL]-()-[:REL2]-()){1,}` ✓ — never `(()-[:REL]-){1,}` (dangling edge) ✗.

**REPEATABLE ELEMENTS** and **DIFFERENT RELATIONSHIPS** are **MATCH-level modes** placed immediately after the `MATCH` keyword — NEVER at the end of the pattern and NEVER inside a QPE group:
```cypher
// DO:     MATCH REPEATABLE ELEMENTS (a:Customer)(()-[:SHARED_IDENTIFIERS]->()){3}(b:Customer)
// DO:     MATCH DIFFERENT RELATIONSHIPS (a)-[:REL*1..5]->(b)
// DON'T: MATCH (a:Customer)(()-[:SHARED_IDENTIFIERS]->()){3}(b:Customer) REPEATABLE ELEMENTS  // SYNTAX ERROR
// DON'T: MATCH (a:Customer)(()-[:SHARED_IDENTIFIERS]->() REPEATABLE ELEMENTS){3}(b:Customer)  // inside group — SYNTAX ERROR
```
`REPEATABLE ELEMENTS` always requires bounded `{m,n}` — never `+`, `*`, or `{1,}`.

**QPE groups must always start AND end with a node**: `((:A)-[:REL]->(:B)){1,3}` ✓ — never `((:A)-[:REL]->){1,3}` ✗ (dangling relationship at end).

### ORDER BY and NULL Sorting

Cypher does **not** support `NULLS LAST` / `NULLS FIRST` (SQL syntax — will cause a syntax error). Use plain `ORDER BY x DESC` or `ORDER BY x ASC`. NULLs sort last in ascending order and first in descending order by default — no modifier needed.

`ORDER BY` items must be **expressions only** — never append `AS alias` to a sort key. After an aggregating `RETURN`, use the **RETURN alias** (not the pre-aggregation variable):

```cypher
// DO:     ORDER BY n.publication_year DESC, n.rating DESC
// DO:     RETURN decade, count(*) AS cnt  ORDER BY decade    // reference RETURN alias after aggregation
// DON'T: ORDER BY n.publication_year DESC, n.rating AS rating DESC   // SYNTAX ERROR — AS not allowed in ORDER BY
// DON'T: ORDER BY decade_start   // decade_start was a pre-aggregation variable — use the RETURN alias 'decade'
// DON'T: ORDER BY n.score DESC NULLS LAST   // SYNTAX ERROR — not valid Cypher
```

### Conditional Counting

`count(variable WHERE condition)` is **NOT valid Cypher** — it is SQL syntax. Use one of these patterns:

```cypher
// DO: sum/CASE pattern
sum(CASE WHEN r.rating = 5 THEN 1 ELSE 0 END) AS five_star_count

// DO: COUNT subquery (Cypher 25)
COUNT { MATCH (r:Review)-[:WRITTEN_FOR]->(b) WHERE r.rating = 5 } AS five_star_count

// DON'T: count(r WHERE r.rating = 5)   // SYNTAX ERROR — not valid Cypher
```

### Variable Scope After WITH

`WITH` projects a new scope. Any variable NOT listed in the `WITH` clause is out of scope afterwards. Use `count(*)` when the entity variable is no longer in scope:

```cypher
WITH b.category AS cat, b.rating AS rating   // 'b' is dropped from scope here
RETURN cat, avg(rating) AS avg_rating,
       count(*) AS book_count                // correct — 'b' is out of scope
// DON'T: count(b) AS book_count            // SYNTAX ERROR — 'b' not defined after the WITH above
```

### Subquery Body Format Rules

`EXISTS {}` and `COUNT {}` accept **either** a bare pattern (with optional `WHERE`) or a full `MATCH ... RETURN` statement:
```cypher
EXISTS { (a)-[:R]->(b) }                    // bare pattern ✓
EXISTS { MATCH (a)-[:R]->(b) WHERE a.x > 0 } // full statement ✓
COUNT  { (a)-[:R]->(b) WHERE a.x > 0 }      // bare with WHERE ✓
```

`COLLECT {}` requires a **full `MATCH ... RETURN x` statement** — bare pattern is a syntax error:
```cypher
COLLECT { MATCH (a)-[:R]->(b) RETURN b.name }  // ✓ (RETURN exactly one column)
COLLECT { (a)-[:R]->(b) }                      // SYNTAX ERROR ✗
```

### WITH Cardinality Reset

`WITH` closes the row stream; use it to filter aggregated results before further traversal: `MATCH (p:Person)-[:ACTED_IN]->(m:Movie) WITH p, count(m) AS mc WHERE mc > 5 MATCH (p)-[:KNOWS]->(f:Person) RETURN p.name, f.name;`

### CASE WHEN Conditional

```cypher
CYPHER 25
MATCH (n:Event)
RETURN n.name,
  CASE WHEN n.type = 'A' THEN 'Alpha'
       WHEN n.type = 'B' THEN 'Beta'
  ELSE 'Other' END AS category;
```

**Note**: Use `CASE WHEN ... THEN ... ELSE ... END`. The standalone `WHEN ... THEN ... END` form (without `CASE`) is not yet supported in Neo4j 2026.x.

### CALL IN TRANSACTIONS

```cypher
// CORRECT: CYPHER 25 MATCH (c:Customer) CALL (c) { SET c.flag = 'done' } IN TRANSACTIONS OF 100 ROWS RETURN count(c);
```
**NEVER write** `CALL (x) IN TRANSACTIONS { }` — `IN TRANSACTIONS` comes AFTER the `{ }` block.

**CALL IN TRANSACTIONS is for write batching only** — never use it for read queries; it requires an implicit (auto-commit) transaction and will fail with `TransactionStartFailed` if the driver uses an explicit transaction.

---

### APOC Library (apoc.*)

> **Capability gate** — only use `apoc.*` procedures and functions when the schema context `capabilities` list includes `"apoc"`. **Aura always has apoc-core** (bundled); local/cloud Neo4j requires the plugin to be installed. `apoc-extended` (load/export procedures) is NOT available in Aura.

**When APOC is available**: Load `read/cypher25-apoc.md` for procedure signatures and examples. Key categories:
- `apoc.map.*` — build/merge/transform maps; `apoc.coll.*` — set ops, flatten, zip, partition
- `apoc.text.*` — fuzzy matching (`jaroWinklerDistance`), Soundex, regex groups, camelCase/snakeCase
- `apoc.date.*` — parse/format non-ISO date strings via epoch ms; `apoc.temporal.*` — truncate/format Neo4j temporal values
- `apoc.path.*` — configurable BFS/DFS traversal with label/rel filters (`apoc.path.expand`, `subgraphNodes`)
- `apoc.load.*` / `apoc.export.*` — CSV/JSON load-import/export (requires `"apoc-extended"` in capabilities; NOT in Aura)

**When APOC is NOT listed**: prefer native Cypher — `collect()`, `size()`, `[x IN list WHERE ...]`, `duration.between()`, `SHORTEST`. Do NOT emit any `apoc.*` call.

---

### Graph Data Science (GDS) Library

> **GDS is NOT available by default** — only use GDS procedures (`gds.*`) when the schema context explicitly states `gds: true` or lists GDS procedures. On demo databases and most cloud instances, GDS is not installed.

**When GDS is NOT available:** Use native Cypher equivalents:
- Betweenness / degree centrality → `count()` aggregation on relationships
- PageRank approximation → count in-neighbors weighted by their in-degree
- Community detection → not expressible in pure Cypher; use `COLLECT` for local neighborhoods
- Shortest path → `SHORTEST` keyword (Cypher 25) or `shortestPath()`

**When GDS IS available** (schema block has `gds: true`): Use `CALL gds.*` procedures normally with `YIELD`. Load `write/cypher25-gds.md` for graph projection, algorithm streaming, write-back patterns, and `gds.util.asNode()` usage.

> **NEVER assume stored GDS properties** — properties such as `louvainCommunity`, `pageRank`, `betweenness` do NOT exist on nodes unless schema context explicitly confirms a `.write` call was run. Always stream results via `.stream` procedures instead of filtering on assumed stored properties.

---

### Neo4j GenAI Plugin (`ai.*`)

> **Capability gate** — only use `ai.*` when the schema context `capabilities` list includes `"genai"`, **or** when the target is confirmed Aura (GenAI plugin is always-on in Aura; may be absent from capabilities list but still usable).

**Scalar similarity vs top-K retrieval** — critical distinction:

| Use case | Tool |
|---|---|
| Score similarity between **two known vectors** | `ai.similarity.cosine(vec1, vec2)` or `ai.similarity.euclidean(vec1, vec2)` — returns a single FLOAT |
| Find **top-K most similar nodes** to a query vector | `db.index.vector.queryNodes()` or SEARCH clause — queries the index |

**Never use `ai.similarity.*` for top-K ranking** — it has no index backing and forces a full scan.

**`ai.embedding.*`** (Aura-only): generates embeddings inline during the query via a configured provider (OpenAI, Azure OpenAI, Vertex AI, Bedrock). Not available on self-managed Neo4j even with the genai plugin installed.

Load `schema/cypher25-genai.md` for full signatures, provider map, and re-scoring patterns.

---

### SEARCH Clause (Vector — GA in Neo4j 2026.02.1+)

> **SEARCH is vector-only** — fulltext always uses `db.index.fulltext.queryNodes()`. **Version check**: SEARCH is available as Preview from ~2026.01 (including demo.neo4jlabs.com) and GA in 2026.02.1+. Use the procedure fallback (`db.index.vector.queryNodes()`) only for versions before 2026.01.

```cypher
// Vector 2026.02.1+ (SEARCH clause):
CYPHER 25
MATCH (c:Chunk)
SEARCH c IN (VECTOR INDEX news FOR $embedding LIMIT 10)
SCORE AS score
WHERE score > 0.8
RETURN c.text, score
ORDER BY score DESC

// Vector <2026.02 (procedure fallback):
CYPHER 25
CALL db.index.vector.queryNodes('news', 5, $embedding)
YIELD node AS c, score
WHERE score > 0.8
RETURN c.text, score

// Fulltext (all versions — SEARCH clause never covers fulltext):
CYPHER 25
CALL db.index.fulltext.queryNodes('entity', $query)
YIELD node, score
RETURN node.name, score
ORDER BY score DESC
LIMIT 20
```

**SEARCH syntax rules:**
- Variable name only — NOT `SEARCH (n)`, must be `SEARCH n`
- `IN (VECTOR INDEX index_name FOR $embedding LIMIT N)` — limit is required inside parens
- `SCORE AS varname` — bind the similarity score after the closing paren
- `WHERE score > 0.8` comes after `SCORE AS`, before `RETURN`
- Only for node vector indexes — relationship vector indexes still require the procedure

---

## Deprecated Syntax → Cypher 25 Preferred

| Deprecated / Invalid | Cypher 25 |
|---|---|
| `[:REL*1..5]` | `-[:REL]-{1,5}` |
| `[:REL*]` | `-[:REL]*` |
| `shortestPath((a)-[*]->(b))` | `SHORTEST 1 (a)(()-[]->()){1,}(b)` |
| `allShortestPaths((a)-[*]->(b))` | `ALL SHORTEST (a)(()-[]->()){1,}(b)` |
| `CALL { WITH x ... }` | `CALL (x) { ... }` |
| `id(n)` | `elementId(n)` |
| `collect()[..N]` | `COLLECT { MATCH ... RETURN ... LIMIT N }` |
| `-- SQL comment` | `// Cypher comment` |
| `ACYCLIC / TRAIL / WALK` path modes | Not supported in Neo4j 2026.x — omit; use `WHERE` guards |
| `ORDER BY x DESC NULLS LAST` | `ORDER BY x DESC` — `NULLS LAST`/`FIRST` is SQL, not valid Cypher |
| `ORDER BY n.prop AS alias DESC` | `ORDER BY n.prop DESC` — `AS` is **not** allowed inside `ORDER BY` items |
| `MATCH (a)(p){n}(b) REPEATABLE ELEMENTS` | `MATCH REPEATABLE ELEMENTS (a)(p){n}(b)` — mode goes after MATCH |
| `COLLECT { (a)-[:R]->(b) }` | `COLLECT { MATCH (a)-[:R]->(b) RETURN x }` — COLLECT requires full MATCH+RETURN; bare pattern is syntax error |
| `UNWIND range(0, min(2, size(lst)-1))` | `UNWIND range(0, CASE WHEN size(lst) < 3 THEN size(lst)-1 ELSE 2 END)` — `min()` is an **aggregation function**, not a scalar; use `CASE WHEN` for scalar minimum |
| `rank() OVER (PARTITION BY x ORDER BY y)` | Not valid Cypher — use `WITH cat, collect({v:v, s:s}) AS ranked UNWIND range(0, size(ranked)-1) AS idx` for ranking within groups |

---

## FOREACH vs UNWIND

| Use | When |
|---|---|
| `FOREACH (x IN list \| clause)` | Side-effect only — no RETURN value needed |
| `UNWIND list AS x` | Need to inspect, filter, or return list items |

`FOREACH` cannot be followed by `RETURN`. When in doubt, use `UNWIND`.

**`WHERE` after `UNWIND` is invalid** — `WHERE` requires a preceding `WITH` or `MATCH`:
```cypher
// DON'T: UNWIND list AS x WHERE x > 5 RETURN x       // SyntaxError
// DO:    UNWIND list AS x WITH x WHERE x > 5 RETURN x
// ALSO DO: UNWIND list AS x MATCH (n) WHERE n.val = x RETURN n
```

---

## USE Clause (Multi-Database)

```cypher
CYPHER 25 USE myDatabase MATCH (n:Person) RETURN n.name LIMIT 5;
```

`USE` before query body. Omit when the driver connection already targets the correct database.

---

## Query Construction Decision Tree

**Step 1 — Categorize:**

| Category | Clauses | L3 Folder |
|---|---|---|
| **READ** | MATCH, OPTIONAL MATCH, CALL subquery, WITH, RETURN, COUNT{}/COLLECT{}/EXISTS{}, SEARCH | `references/read/` |
| **WRITE** | CREATE, MERGE, SET, REMOVE, DELETE, DETACH DELETE, CALL IN TRANSACTIONS, FOREACH, LOAD CSV | `references/write/` |
| **SCHEMA** | CREATE/DROP INDEX, CREATE/DROP CONSTRAINT, SHOW INDEXES, SHOW CONSTRAINTS, SHOW PROCEDURES, GRAPH TYPE DDL (ALTER CURRENT GRAPH TYPE, EXTEND GRAPH TYPE, SHOW GRAPH TYPES, DROP GRAPH TYPE ELEMENTS) | `references/schema/` |
| **ADMIN** | CREATE/DROP DATABASE, ALTER USER, roles/privileges, SHOW TRANSACTIONS, SHOW SERVERS | `references/admin/` |

**Step 2 — Load only the relevant L3 file(s):**

| Query type | Load |
|---|---|
| Variable-length paths, QPEs, match modes | `read/cypher25-patterns.md` |
| Aggregation, list, string, temporal, spatial, vector functions | `read/cypher25-functions.md` |
| CALL subquery, COUNT{}, COLLECT{}, EXISTS{} | `read/cypher25-subqueries.md` |
| Type errors, null propagation, casting, type predicates | `read/cypher25-types-and-nulls.md` |
| Runtime hints (`CYPHER runtime=parallel`), parallel execution, PROFILE pipeline analysis | `read/cypher25-runtime.md` |
| Batch writes, CALL IN TRANSACTIONS | `write/cypher25-call-in-transactions.md` |
| GDS algorithms (`gds.*`) — only when `gds: true` in schema | `write/cypher25-gds.md` |
| APOC procedures/functions (`apoc.*`) — only when `capabilities` includes `"apoc"` | `read/cypher25-apoc.md` |
| GenAI similarity / embedding (`ai.*`) — only when `capabilities` includes `"genai"` or target is Aura | `schema/cypher25-genai.md` |
| Index creation, SEARCH, fulltext, vector, hints | `schema/cypher25-indexes.md` |
| GRAPH TYPE DDL (Enterprise Preview — 2026.02+) | `schema/cypher25-graph-types.md` |
| Naming, casing, formatting (all categories) | `cypher-style-guide.md` |

Do **not** load all files — select only what the current query type requires.

---

## EXPLAIN / PROFILE Validation Loop

`CYPHER 25 EXPLAIN <query>` — red flags: `AllNodesScan` (missing index or label-free MATCH), `CartesianProduct` (missing join predicate), `NodeByLabelScan` (no property filter index).

`CYPHER 25 PROFILE <query>` — check: `dbHits` (warn: > expected; fail: > expected × 10), `rows` (fail if < min_results), `allocatedMemory` (warn: > 100 MB; fail: > expected × 5), `elapsedTimeMs` (guidance only). Rewrite until `dbHits` and `allocatedMemory` are within bounds.

**Parallel runtime** — when EXPLAIN shows large `AllNodesScan`, `NodeByLabelScan`, or high-fanout `Expand(All)` on analytics queries, prepend `CYPHER runtime=parallel` after `CYPHER 25`. Confirm with EXPLAIN that the header shows `Runtime PARALLEL` (not `PIPELINED`). See `read/cypher25-runtime.md` for applicable query types, version requirements, and pipeline analysis.

---

## Failure Recovery Patterns

**0-Result Queries:** (1) verify params non-null and correctly typed; (2) remove `WHERE` predicates one at a time to isolate; (3) check label/rel-type spelling against schema; (4) EXPLAIN to confirm index used.
**TypeErrors:** prefer `toIntegerOrNull`/`toFloatOrNull` over base casting; guard with `IS NOT NULL` before coercion.
**No `least()`/`greatest()`** — these SQL functions do not exist in Cypher. Use `CASE WHEN a < b THEN a ELSE b END`.
**DateTime vs date() mismatch** — `DateTime >= date('2025-01-01')` returns 0 rows: use `.year` accessor (`t.date.year = 2025`) or `datetime()` literals for DateTime-typed properties.
**Timeouts:** EXPLAIN → fix AllNodesScan/CartesianProduct → add LIMIT → switch to `CALL IN TRANSACTIONS OF 1000 ROWS`.

---

## WebFetch Escalation

**WebFetch is always available for online agents.** Do not wait until L3 reference files are insufficient — fetch Neo4j docs pages proactively whenever a query involves syntax you are not fully certain about. L3 reference files are token-budget-truncated (≤ 2,000 tokens each); the full docs pages contain the complete picture. Use WebFetch as a **proactive, first-class** knowledge source.

| Trigger | URL / Path |
|---|---|
| **Version-gated features** (check first) | `references/version-matrix.md` (local) |
| Specific clause semantics | `https://neo4j.com/docs/cypher-manual/25/clauses/{clause}/` |
| Function signatures | `https://neo4j.com/docs/cypher-manual/25/functions/{type}/` |
| Path / QPE edge cases | `https://neo4j.com/docs/cypher-manual/25/patterns/` |
| Full syntax overview | `https://neo4j.com/docs/cypher-cheat-sheet/25/all/` |

High-priority pages: `merge/`, `with/`, `call-subquery/`, `search/`, `aggregating/`, `use/`
