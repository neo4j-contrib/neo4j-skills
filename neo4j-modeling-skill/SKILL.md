---
name: neo4j-modeling-skill
description: Design, review, and refactor Neo4j graph data models. Use when choosing node
  labels vs relationship types vs properties, migrating relational/document schemas to
  graph, detecting anti-patterns (generic labels, supernodes, missing constraints),
  designing intermediate nodes for n-ary relationships, enforcing schema with constraints
  and indexes, or assessing an existing model against graph modeling best practices.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT handle Spring Data Neo4j entity mapping — use neo4j-spring-data-skill.
  Does NOT handle GraphQL type definitions — use neo4j-graphql-skill.
  Does NOT handle data import — use neo4j-import-skill.
version: 1.0.0
allowed-tools: WebFetch Bash
---

## When to Use

- Designing graph model from scratch (domain → nodes, rels, props)
- Reviewing existing model for anti-patterns
- Deciding node vs property vs relationship vs label
- Migrating relational or document schema to graph
- Designing intermediate nodes for n-ary or complex relationships
- Detecting and mitigating supernode / high-fanout problems
- Choosing and creating constraints + indexes for a model

## When NOT to Use

- **Writing or optimizing Cypher** → `neo4j-cypher-skill`
- **Spring Data Neo4j (@Node, @Relationship)** → `neo4j-spring-data-skill`
- **GraphQL type definitions** → `neo4j-graphql-skill`
- **Importing data (LOAD CSV, APOC import)** → `neo4j-import-skill`

---

## Inspect Before Designing

On existing database, run first — never propose changes without current state:

```cypher
CALL db.schema.visualization() YIELD nodes, relationships RETURN nodes, relationships;
SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties RETURN name, type, labelsOrTypes, properties;
SHOW INDEXES YIELD name, type, labelsOrTypes, state WHERE state = 'ONLINE' RETURN name, type, labelsOrTypes;
```

If APOC available:
```cypher
CALL apoc.meta.schema() YIELD value RETURN value;
```

MCP tool map:

| Operation | Tool |
|---|---|
| Inspect schema | `get-schema` |
| `SHOW CONSTRAINTS`, `SHOW INDEXES` | `read-cypher` |
| `CREATE CONSTRAINT ... IF NOT EXISTS` | `write-cypher` (show + confirm first) |

---

## Defaults — Apply to Every Model

1. Use-case first — list 5+ queries the model must answer before designing
2. Nodes = entities (nouns) with identity; rels = connections (verbs) with direction
3. Labels PascalCase; rel types SCREAMING_SNAKE_CASE; properties camelCase
4. Every node type used in MERGE has a uniqueness constraint on its key property
5. No generic labels (`:Entity`, `:Node`, `:Thing`); no generic rel types (`:RELATED_TO`, `:HAS`)
6. Rel direction encodes semantic meaning — not arbitrary
7. Inspect schema before proposing any change on an existing database
8. All constraint/index DDL uses `IF NOT EXISTS` — safe to rerun

---

## Key Patterns

### Node vs Relationship vs Property — Decision Table

| Question | Answer | Model as |
|---|---|---|
| Is it a thing with identity, queried as entry point? | Yes | Node |
| Is it a connection between two things with direction? | Yes | Relationship |
| Does the connection have its own properties or multiple targets? | Yes | Intermediate node |
| Is it a scalar always returned with its parent, never filtered alone? | Yes | Property on parent |
| Is it a category used for type-based filtering or path traversal? | Yes | Label (not a property) |
| Does the same attribute value repeat across many nodes (low cardinality)? | Yes | Label, not a property node |
| Is it a fact connecting >2 entities? | Yes | Intermediate node |

### Property vs Label — Decision Table

| Use label when | Use property when |
|---|---|
| Values are few, fixed, used as traversal filters (`WHERE n:Active`) | Values are many, dynamic, or unique per node |
| You traverse by type (`MATCH (n:VIPCustomer)`) | You filter by value (`WHERE n.tier = 'vip'`) |
| Category drives index selection | Fine-grained value drives range scans |
| Example: `:Active`, `:Verified`, `:Premium` | Example: `status`, `score`, `email` |

Rule: adding a label is cheap; scanning all `:Label` nodes is fast. Never model high-cardinality values as labels.

---

### Intermediate Node Pattern

Use when a relationship needs its own properties, connects >2 entities, or is independently queryable.

**Before (relationship with property — limited):**
```
(Person)-[:ACTED_IN {role: "Neo"}]->(Movie)
// Cannot query roles independent of movies
```

**After (intermediate node — queryable, extensible):**
```
(Person)-[:PLAYED]->(Role {name: "Neo"})-[:IN]->(Movie)
// MATCH (r:Role) WHERE r.name STARTS WITH 'Neo' RETURN r
```

**Employment overlap example:**
```cypher
// Find colleagues who overlapped at same company
MATCH (p1:Person)-[:WORKED_AT]->(e1:Employment)-[:AT]->(c:Company)<-[:AT]-(e2:Employment)<-[:WORKED_AT]-(p2:Person)
WHERE p1 <> p2
  AND e1.startDate <= e2.endDate AND e2.startDate <= e1.endDate
RETURN p1.name, p2.name, c.name
```

Promote relationship to intermediate node when:
- Relationship has >2 properties
- Relationship is the subject of another query
- Multiple entities share the same connection context
- You need to connect >2 entities in one fact

---

### Relational → Graph Migration Table

| Relational construct | Graph equivalent | Notes |
|---|---|---|
| Table row | Node | One label per table (add more as needed) |
| Column (scalar) | Node property | |
| Primary key | Uniqueness constraint property | Use `tmdbId`, not `id` (too generic) |
| Foreign key | Relationship | Direction: from dependent → referenced |
| Many-to-many junction table | Intermediate node | Especially if junction has own columns |
| Junction table (no own columns) | Direct relationship | Simpler; upgrade to intermediate node later |
| NULL FK (optional relation) | Absent relationship | No node created; absence is the signal |
| Polymorphic FK (Rails-style) | Multiple labels or relationship types | Split into type-specific rels |
| Self-referential FK | Same-label relationship | `:Employee {managerId}` → `(e)-[:REPORTS_TO]->(m)` |
| Audit/history columns | Intermediate versioning node | See References for versioning pattern |

---

### Supernode Detection and Mitigation

**Detect:**
```cypher
// Find top-10 highest-degree nodes
MATCH (n)
RETURN labels(n) AS labels, elementId(n) AS id, count{ (n)--() } AS degree
ORDER BY degree DESC LIMIT 10
```

Node with degree >> median for its label = supernode candidate. Any node with >100K relationships will degrade traversal queries that pass through it.

**Causes:**
- Domain supernodes: airports, celebrities, popular hashtags — unavoidable
- Modeling supernodes: gender, country, status modeled as nodes with millions of edges — avoidable

**Mitigation strategies (in priority order):**

| Strategy | When to use | Implementation |
|---|---|---|
| **Query direction** | Directional asymmetry exists | Query from low-degree side; exploit direction |
| **Relationship type split** | Supernode serves multiple roles | `:FOLLOWS` + `:FAN` instead of single `:RELATED_TO` |
| **Label segregation** | Supernode conflates entity types | `:Celebrity` vs `:User` → query only relevant subtype |
| **Bucket pattern** | Time-series or high-volume event nodes | See below |
| **Avoid modeling** | Low-cardinality categoricals | Use label instead of node (`:Active` not `(:Status {name:"Active"})`) |
| **Join hint** | Query tuning last resort | `USING JOIN ON n` in Cypher |

**Bucket pattern (time-series / high-volume):**
```cypher
// Instead of: (:User)-[:VIEWED]->(:Page) (millions of rels per user)
// Bucket by hour:
(u:User)-[:VIEWED_IN]->(b:ViewBucket {userId: u.id, hour: '2025-04-28T14'})-[:VIEWED]->(p:Page)

// Query last hour's views without traversing full history:
MATCH (u:User {id: $uid})-[:VIEWED_IN]->(b:ViewBucket {hour: $hour})-[:VIEWED]->(p)
RETURN p.url
```

---

### Naming Conventions

| Element | Convention | Good | Bad |
|---|---|---|---|
| Node label | PascalCase, singular noun | `:Person`, `:BlogPost` | `:person`, `:blog_posts`, `:Entity` |
| Relationship type | SCREAMING_SNAKE_CASE, verb phrase | `:ACTED_IN`, `:WORKS_FOR` | `:actedin`, `:relatedTo`, `:HAS` |
| Property key | camelCase | `firstName`, `createdAt` | `FirstName`, `first_name` |
| Constraint name | snake_case descriptive | `person_id_unique` | `constraint1` |
| Index name | snake_case descriptive | `person_name_idx` | `index2` |

---

### Schema Enforcement — What to Create for Each Element

Run all DDL with `IF NOT EXISTS`. Apply before importing data.

```cypher
// 1. Uniqueness constraint — every node type used in MERGE
CREATE CONSTRAINT person_id_unique IF NOT EXISTS
  FOR (p:Person) REQUIRE p.id IS UNIQUE;

// 2. Existence constraint (Enterprise) — mandatory properties
CREATE CONSTRAINT person_name_exists IF NOT EXISTS
  FOR (p:Person) REQUIRE p.name IS NOT NULL;

// 3. Property type constraint (Enterprise) — enforce data type
CREATE CONSTRAINT person_born_integer IF NOT EXISTS
  FOR (p:Person) REQUIRE p.born IS :: INTEGER;

// 4. Key constraint (Enterprise) — unique + exists in one
CREATE CONSTRAINT movie_tmdbid_key IF NOT EXISTS
  FOR (m:Movie) REQUIRE m.tmdbId IS NODE KEY;

// 5. Range index — equality and range filters on properties
CREATE INDEX person_name_idx IF NOT EXISTS
  FOR (p:Person) ON (p.name);

// 6. Fulltext index — CONTAINS, STARTS WITH, free text search
CREATE FULLTEXT INDEX person_fulltext IF NOT EXISTS
  FOR (n:Person) ON EACH [n.name, n.bio];

// 7. Vector index — embedding similarity search
CREATE VECTOR INDEX chunk_embedding_idx IF NOT EXISTS
  FOR (c:Chunk) ON (c.embedding)
  OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' } };

// 8. Relationship index — filter on rel properties
CREATE INDEX acted_in_year_idx IF NOT EXISTS
  FOR ()-[r:ACTED_IN]-() ON (r.year);
```

After creating indexes, poll until ONLINE:
```cypher
SHOW INDEXES YIELD name, state WHERE state <> 'ONLINE' RETURN name, state;
```
Do NOT use an index until state = `ONLINE`.

---

### Vector / Embedding Property Modeling

Store embeddings on dedicated `:Chunk` nodes, never on business nodes:

```
(:Document)-[:HAS_CHUNK]->(c:Chunk {text: "...", embedding: [...]})
```

Rules:
- Chunk node: `text` (source text), `embedding` (float array), `chunkIndex` (int)
- Parent document: metadata only (title, url, createdAt)
- Vector index on `c.embedding` only
- Chunk size 200–500 tokens with 20% overlap is production default [field]
- Do NOT put embedding on `:Document` — makes the node too large and pollutes traversal

---

### Anti-Patterns Table

| Anti-pattern | Problem | Fix |
|---|---|---|
| Generic labels `:Entity`, `:Node` | No filtering benefit; all nodes scan | Use domain labels `:Person`, `:Product` |
| Generic rel types `:RELATED_TO`, `:HAS` | Can't filter by relationship type | Use semantic types `:PURCHASED`, `:AUTHORED` |
| Low-cardinality value as node | Supernode (`:Status {name:"active"}` → millions of edges) | Use label `:Active` instead |
| Property as label (`n.type = 'VIP'` + `:VIP` label both exist) | Inconsistency, duplication | Pick one; prefer label if used in traversal |
| Storing embeddings on business node | Node bloat, slow traversal | Dedicated `:Chunk` node |
| MERGE without uniqueness constraint | Duplicate nodes silently created | Add constraint before any MERGE |
| Missing relationship direction meaning | Arbitrary direction; confusing model | Direction = semantic flow of action |
| Junction table modeled as bare property | Loses history and extensibility | Intermediate node with its own properties |
| `id` as property name | Conflicts with driver internal `id(n)` | Use `personId`, `movieId`, `tmdbId` |
| All dates as strings | No range queries; no temporal operators | Use Neo4j `date()` or `datetime()` type |

---

## Output Format — Schema Assessment

When reviewing an existing model:

```
## Schema Assessment

### Compliant
- [constraint / pattern that is correct]

### Issues Found
#### [Title] — Severity: ERROR / WARNING / INFO
- **Current**: what the model does
- **Problem**: why it is an issue
- **Fix**: specific Cypher DDL or model change

## Recommended Schema
### Node Labels
- :Label {key: TYPE, prop: TYPE, ...}  → constraints: [list]

### Relationships
- (:LabelA)-[:TYPE {prop: TYPE}]->(:LabelB)

### Constraints to Create
[CREATE CONSTRAINT ... statements]

### Indexes to Create
[CREATE INDEX ... statements]
```

Severity semantics:

| Severity | Meaning | Action |
|---|---|---|
| `ERROR` | Model correctness failure (duplicates possible, data loss risk) | Stop; fix before proceeding |
| `WARNING` | Performance or extensibility risk | Report; ask user before proceeding |
| `INFO` | Style or convention deviation | Surface; continue |

---

## Provenance Labels

- `[official]` — stated directly in Neo4j docs
- `[derived]` — follows from documented behavior
- `[field]` — community heuristic; treat as default but validate

---

## Checklist

- [ ] Use cases (≥5 queries) defined before modeling
- [ ] Schema inspected on existing database before changes proposed
- [ ] Every MERGE-target node label has a uniqueness constraint
- [ ] No generic labels (`:Entity`, `:Node`, `:Thing`)
- [ ] No generic relationship types (`:RELATED_TO`, `:HAS`, `:CONNECTED_TO`)
- [ ] Relationship direction encodes semantic meaning
- [ ] N-ary or propertied relationships use intermediate nodes
- [ ] High-cardinality values stored as properties, not nodes
- [ ] Low-cardinality categoricals used as labels, not property nodes
- [ ] Embeddings on dedicated `:Chunk` nodes, not business nodes
- [ ] Supernode candidates identified and mitigated
- [ ] All DDL uses `IF NOT EXISTS`
- [ ] Indexes polled to ONLINE before use
- [ ] Assessment output follows the structured format above
- [ ] Every prohibition paired with a concrete fix

---

## References

Load on demand:
- [references/modeling-patterns.md](references/modeling-patterns.md) — time-series, versioning, multi-tenancy, linked list, access control patterns
- [Neo4j Data Modeling Guide](https://neo4j.com/docs/getting-started/data-modeling/guide-data-modeling/)
- [Neo4j Modeling Tips](https://neo4j.com/docs/getting-started/data-modeling/modeling-tips/)
- [GraphAcademy: Graph Data Modeling Fundamentals](https://graphacademy.neo4j.com/courses/modeling-fundamentals/)
- [Super Nodes — All About Super Nodes (David Allen)](https://medium.com/neo4j/graph-modeling-all-about-super-nodes-d6ad7e11015b)
