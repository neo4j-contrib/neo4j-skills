# Stage 3 — model
# Design or discover the graph data model for the use-case.

## Autonomous mode check — do this FIRST

Before anything else, check `progress.md` for `MODE=autonomous`.

**If `MODE=autonomous`**: design the model without any review pause. Do not show a "does this look right?" message. Do not wait for confirmation at any point. Auto-approve your design and proceed immediately through all steps M4→M5→completion.

**If `MODE=hitl`**: Step M3 (model review) is active — show the draft and wait for user approval.

## Path selection

```
DATA_SOURCE=demo        → use the demo dataset's pre-built schema (see domain-patterns.md)
                          skip to load stage directly
DB_TARGET=existing      → introspect existing schema (Path D below)
DATA_SOURCE=csv         → inspect CSV headers first, derive model (Path B)
DATA_SOURCE=documents   → use KG/RAG model template from domain-patterns.md
otherwise               → greenfield modeling (Path C)
```

## Path A — Demo dataset schema

Look up the schema in `${CLAUDE_SKILL_DIR}/references/domain-patterns.md` for the chosen demo.
Write `schema.json` from that template. Write `schema.cypher` with DDL.
Proceed to `load`.

## Path B — CSV-first modeling

Inspect headers and sample rows before designing anything:
```bash
for f in ./data/*.csv; do
  echo "=== $f ==="
  head -4 "$f"
  echo
done
```

Derive model from structure:
- Each entity-centric file → candidate node label (look for `_id` columns as primary key)
- Foreign key column in one file referencing another → relationship
- Normalize names: `customer_id` column → `Customer` node with `id` property
- Numeric columns → properties; date columns → datetime properties

## Path C — Greenfield modeling

Use `${CLAUDE_SKILL_DIR}/references/domain-patterns.md` as starting templates. Adapt for the user's specific use-case.

Principles:
- 3–6 node labels (more for advanced users)
- 3–8 relationship types with clear direction and semantics
- One natural primary key per node (enables MERGE safety)
- 2–5 properties per node with realistic types
- At least one property suitable for fulltext search (e.g. `name`, `title`, `description`)

## Path D — Existing DB introspection

```bash
# Via neo4j-mcp get-schema tool (preferred)
# OR via cypher-shell:
source .env
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
  "CALL db.schema.visualization() YIELD nodes, relationships RETURN nodes, relationships"
```

Write discovered schema to `schema.json`. Skip to `query` stage.

## Step M3 — Model review (HITL only)

**AUTONOMOUS MODE (all context provided upfront): SKIP THIS STEP ENTIRELY. Do not show the model for review. Do not ask "does this look right?". Proceed directly to Step M4.**

HITL only — show the proposed model and wait for approval:
```
Here's the graph model I'm proposing for <USE_CASE>:

Nodes:
  - <Label> {<primaryKey>, <prop1>, <prop2>}
  ...

Relationships:
  - (<LabelA>)-[:<REL_TYPE>]->(<LabelB>)
  ...

Does this look right? Anything to add, rename, or remove?
(Reply "ok" to proceed, or describe changes.)
```

## Step M4 — Write schema/schema.json

```bash
mkdir -p schema
```

```json
{
  "nodes": [
    {"label": "Person", "primaryKey": "id", "properties": ["id","name","email","createdAt"]}
  ],
  "relationships": [
    {"type": "FOLLOWS", "from": "Person", "to": "Person", "properties": []}
  ]
}
```

Write to `schema/schema.json`.

## Step M5 — Write schema/schema.cypher (DDL)

Write to `schema/schema.cypher`.

**Constraints before indexes. Constraints before data.**

```cypher
CYPHER 25
// Uniqueness constraints — required for fast MERGE
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE;

// Lookup indexes for common query patterns
CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name);
```

For vector/graphrag use-cases, add the vector index here too:
```cypher
CYPHER 25
CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
  FOR (c:Chunk) ON (c.embedding)
  OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' } };
```

## On Completion — write to progress.md

```markdown
### 3-model
status: done
labels=<comma-separated node labels>
relationships=<comma-separated relationship types>
constraints=<number applied>
files=schema/schema.json,schema/schema.cypher
sample_id=<a real primary-key value from the data, e.g. "p1" — used for query params>
```

## Completion condition

- `schema/schema.json` written with at least 2 nodes and 1 relationship
- `schema/schema.cypher` written with at least 1 uniqueness constraint
- HITL: user approved; Autonomous: auto-approved (no pause)
