---
name: neo4j-modeling-skill
description: Design, review, refactor, and visually model Neo4j property graph schemas. Use when choosing node labels vs relationship types vs properties, migrating relational or document schemas to graph, detecting anti-patterns (generic labels, supernodes, missing constraints), designing intermediate nodes for n-ary relationships, enforcing schema with constraints and indexes, assessing an existing model, or creating interactive visual schema diagrams. Also triggers for "design a graph schema", "visualise", "arrows.app", "reference model", "interactive schema editor", or any Neo4j use case. Does NOT handle Cypher query authoring — use neo4j-cypher-skill. Does NOT handle Spring Data Neo4j entity mapping — use neo4j-spring-data-skill. Does NOT handle GraphQL type definitions — use neo4j-graphql-skill. Does NOT handle data import — use neo4j-import-skill. Does NOT trigger for graph charts (bar/line/pie), mathematical graphs, or visualising query results.
version: 1.1.0
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
- Creating interactive visual schema diagrams
- Loading from 32 pre-built reference models or user-uploaded arrows.app JSON

## When NOT to Use

- **Writing or optimizing Cypher** → `neo4j-cypher-skill`
- **Spring Data Neo4j (@Node, @Relationship)** → `neo4j-spring-data-skill`
- **GraphQL type definitions** → `neo4j-graphql-skill`
- **Importing data (LOAD CSV, APOC import)** → `neo4j-import-skill`
- **Graph charts (bar/line/pie), mathematical graphs, query result visualisation** — out of scope

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
5. Add property type constraints (`REQUIRE n.prop IS :: STRING`) where type is known
6. No generic labels (`:Entity`, `:Node`, `:Thing`); no generic rel types (`:RELATED_TO`, `:HAS`)
7. Security labels (row-level access control) start with common prefix (e.g. `Sec`)
8. Rel direction encodes semantic meaning — not arbitrary
9. Inspect schema before proposing any change on an existing database
10. All constraint/index DDL uses `IF NOT EXISTS`
11. **On Neo4j 2026.02+ (Enterprise/Aura):** consider `ALTER CURRENT GRAPH TYPE SET { … }` — see `neo4j-cypher-skill/references/graph-type.md`. PREVIEW — syntax may change before GA.

---

## Key Patterns

### Node vs Relationship vs Property — Decision Table

| Question | Answer | Model as |
|---|---|---|
| Is it a thing with identity, queried as entry point? | Yes | Node |
| Is a connection between two things with direction? | Yes | Relationship |
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
| Audit/history columns | Intermediate versioning node | See references/modeling-patterns.md |

---

### Supernode Detection and Mitigation

**Detect:**
```cypher
MATCH (n)
RETURN labels(n) AS labels, elementId(n) AS id, count{ (n)--() } AS degree
ORDER BY degree DESC LIMIT 10;
```

Node with degree >> median for its label = supernode candidate. Any node with >100K relationships degrades traversal queries that pass through it.

**Mitigation strategies (in priority order):**

| Strategy | When to use | Implementation |
|---|---|---|
| **Query direction** | Directional asymmetry exists | Query from low-degree side; exploit direction |
| **Relationship type split** | Supernode serves multiple roles | `:FOLLOWS` + `:FAN` instead of single `:RELATED_TO` |
| **Label segregation** | Supernode conflates entity types | `:Celebrity` vs `:User` → query only relevant subtype |
| **Bucket pattern** | Time-series or high-volume event nodes | See references/modeling-patterns.md |
| **Avoid modeling** | Low-cardinality categoricals | Use label instead of node (`:Active` not `(:Status {name:"Active"})`) |
| **Join hint** | Query tuning last resort | `USING JOIN ON n` in Cypher |

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
| `id` as property name | `id(n)` is deprecated (use `elementId(n)`); bare `id` is fine but domain-qualified names (`personId`, `movieId`) are clearer | Prefer `personId`, `movieId`, `tmdbId` |
| All dates as strings | No range queries; no temporal operators | Use Neo4j `date()` or `datetime()` type |

---

## Schema Enforcement

See [references/schema-enforcement.md](references/schema-enforcement.md) for full constraint/index DDL examples, vector index setup, and embedding property modeling rules.

---

## Visual Modeling

When the user wants to create, visualise, or edit a graph schema interactively, run the injector script to produce an interactive React artifact.

### The Injector Script

`scripts/inject.py` lives in this skill's folder. Resolve the absolute path from where this SKILL.md was loaded — do NOT hardcode `/mnt/skills/...`:

```bash
SCRIPT=$(find /mnt /opt ~/.claude /skills /workspace 2>/dev/null \
  -name inject.py -path '*/neo4j-modeling-skill/*' | head -1)
python3 "$SCRIPT" <input> [output.jsx]
```

The script auto-detects `<input>`:

| Input type | Example |
|---|---|
| Reference model ID | `inject.py claims-fraud` |
| File path | `inject.py /path/to/schema.json` |
| Stdin | `cat schema.json | inject.py` |
| List catalog | `inject.py --list` |

Accepted wrapping formats (auto-unwrapped): bare `{nodes, relationships}`, arrows.app `{graph: {...}}`, reference model `{initialGraph: {...}}`.

Default output: `/mnt/user-data/outputs/graph-schema-editor.jsx` when that directory exists; otherwise the current working directory. Pass a `.jsx` path as the second argument to override.

### Outputs

Each injection writes **three sibling files** with matching basename:

- **`.jsx`** — interactive React editor (renders in claude.ai artifacts)
- **`.json`** — arrows.app-compatible schema (paste into https://arrows.app)
- **`.svg`** — static dark-theme rendering for non-artifact environments

### Minimal Schema Shape

Each **node** needs only `caption`. Supply `properties` when you have them. Everything else is auto-filled.

| Field | Required? | Default when omitted |
|---|---|---|
| `caption` | yes | — |
| `properties` | no | `{}` |
| `id` | no | `n0`, `n1`, … |
| `position` | no | Circular auto-layout centred on viewport |
| `labels` | no | `[caption]` |
| `style.color` | no | Cycled through 10-colour palette |
| `style.radius` | no | `55` |

Each **relationship** needs `type`, and either `from`/`to` (caption lookup) or `fromId`/`toId` (explicit ids — required when two nodes share a caption).

| Field | Required? | Notes |
|---|---|---|
| `type` | yes | UPPER_SNAKE_CASE, e.g. `ACTED_IN` |
| `from` or `fromId` | yes | Caption lookup OR explicit id |
| `to` or `toId` | yes | Caption lookup OR explicit id |
| `properties` | no | `{}` |
| `id` | no | `r0`, `r1`, … |

### Custom Domain — Stdin Pattern

```bash
cat <<'EOF' | python3 inject.py
{
  "nodes": [
    { "caption": "Customer", "properties": { "customerId": "string", "name": "string" } },
    { "caption": "Order",    "properties": { "orderId": "string", "total": "float" } },
    { "caption": "Product",  "properties": { "sku": "string", "price": "float" } }
  ],
  "relationships": [
    { "type": "PLACED",   "from": "Customer", "to": "Order" },
    { "type": "CONTAINS", "from": "Order",    "to": "Product", "properties": { "quantity": "integer" } }
  ]
}
EOF
```

### Multi-Label Nodes

Neo4j supports multiple labels per node. Supply a `labels` array with more than one entry:

```json
{
  "nodes": [
    { "caption": "Account", "labels": ["Account", "Internal"], "properties": { "accountNumber": "string" } },
    { "caption": "Account", "labels": ["Account", "External"], "properties": { "accountNumber": "string" } }
  ],
  "relationships": [
    { "type": "TRANSFERRED_TO", "fromId": "n0", "toId": "n1" }
  ]
}
```

Invariants: `caption` is always the first element of `labels`; duplicates and empties are dropped. Relationship endpoints cannot resolve by caption when two nodes share one — use explicit `fromId`/`toId`.

### Reference Models

32 pre-built models across Financial Services, Insurance, Healthcare & Life Sciences, Manufacturing, Cybersecurity, and Industry Agnostic. Run `inject.py --list` for the live catalog. See [references/reference-models.md](references/reference-models.md) for the full catalog with keyword mapping.

When a reference model is injected, the script surfaces its name and source URL — share these with the user.

### Presenting Results

**In claude.ai (artifacts render):** Call `present_files` on the `.jsx` first. Mention `.json` and `.svg` as companion files. Brief orientation:

- Double-click canvas (or "Add Node") to add nodes
- Drag from a node's edge to another node to create a relationship
- Click any element to edit in sidebar — primary label, additional labels, properties, colour, radius
- Scroll wheel zooms; drag canvas to pan
- Export → "Copy JSON" gives arrows.app-compatible JSON

**In CLI / API (no artifact rendering):** Lead with `.svg` for visual preview, `.json` as portable artifact. User can paste JSON into https://arrows.app for visual editing, then export back and re-feed to the injector.

### Editing in arrows.app

The exported `.json` is byte-compatible with https://arrows.app:

1. Open https://arrows.app and click *Use Storage > Local*
2. Paste contents of `.json`
3. Edit visually with arrows.app's full toolset
4. Use *Export* → *JSON* to get updated schema
5. Paste JSON back in chat — injector handles both formats interchangeably

### Saving User Edits

The `.jsx` artifact runs in a sandbox — it cannot write to disk. Round-trip:

1. User clicks **Export → Copy JSON** in the editor
2. User pastes it in chat ("here's my updated schema" or "save my changes")
3. **Re-run the injector against the pasted JSON:**

```bash
cat <<'EOF' | python3 inject.py
{ "style": {...}, "nodes": [...], "relationships": [...] }
EOF
```

This refreshes `.jsx`, `.json`, and `.svg` so all three stay in sync.

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
- [ ] Visual artifact presented when user wants to see/edit schema interactively
- [ ] Reference model source URL shared when loading a pre-built model

---

## References

Load on demand:
- [references/schema-enforcement.md](references/schema-enforcement.md) — constraint/index DDL, vector/embedding modeling
- [references/modeling-patterns.md](references/modeling-patterns.md) — time-series, versioning, multi-tenancy, linked list, access control patterns
- [references/reference-models.md](references/reference-models.md) — full catalog of 32 pre-built industry reference models
- [Neo4j Data Modeling Guide](https://neo4j.com/docs/getting-started/data-modeling/guide-data-modeling/)
- [Neo4j Modeling Tips](https://neo4j.com/docs/getting-started/data-modeling/modeling-tips/)
- [GraphAcademy: Graph Data Modeling Fundamentals](https://graphacademy.neo4j.com/courses/modeling-fundamentals/)
- [Super Nodes — All About Super Nodes (David Allen)](https://medium.com/neo4j/graph-modeling-all-about-super-nodes-d6ad7e11015b)
