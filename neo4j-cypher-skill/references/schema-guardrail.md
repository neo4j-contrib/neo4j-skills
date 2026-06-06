# Schema Guardrail Reference

File-based schema validation for Cypher generation. Prevents hallucinated labels, properties, and relationship types when no live database connection is available.

---

## Schema File

Name the file after your database: `<db-name>-schema.json` (e.g. `movies-schema.json`, `supply-chain-schema.json`). Place anywhere in the project — root, `config/`, `data/`, etc.

### Generate from existing database (requires APOC)
```bash
pip install neo4j python-dotenv
```
Store credentials in `.env` (verify `.env` is in `.gitignore`):
```
NEO4J_URI=neo4j+s://<instance>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```
```bash
python scripts/generate_schema.py <db-name>
```

### Build from CSV or description (agent-driven, no DB needed)
Tell the agent what data you have. Agent runs the script and fills in labels, properties, relationships automatically:
```bash
python scripts/define_schema.py
```

### Convert from Neo4j standard JSON / graphrag format
```bash
python scripts/import_neo4j_schema.py path/to/input-schema.json
```
Auto-detects: `neo4j-graphrag-python` SchemaBuilder, `graph-schema-introspector`, `graph-schema-json-js-utils`, `mcp-neo4j-data-modeling`.

---

## Schema Format (APOC meta.schema)

```json
{
  "schema_retrieved_at": "2026-06-06T10:00:00+00:00",
  "value": {
    "Theme": {
      "type": "node",
      "properties": {
        "name":     { "type": "STRING" },
        "theme_id": { "type": "INTEGER" }
      },
      "relationships": {
        "HAS_SET": { "direction": "out", "labels": ["Set"], "properties": {} }
      }
    },
    "Set": {
      "type": "node",
      "properties": {
        "name":         { "type": "STRING" },
        "id":           { "type": "STRING" },
        "year":         { "type": "INTEGER" },
        "pieces":       { "type": "INTEGER" }
      },
      "relationships": {
        "HAS_SET":     { "direction": "in",  "labels": ["Theme"], "properties": {} },
        "HAS_MINIFIG": { "direction": "out", "labels": ["Minifig"],
                         "properties": { "quantity": { "type": "INTEGER" } } }
      }
    },
    "Minifig": {
      "type": "node",
      "properties": {
        "name":      { "type": "STRING" },
        "fig_num":   { "type": "STRING" },
        "num_parts": { "type": "INTEGER" }
      }
    },
    "HAS_MINIFIG": {
      "type": "relationship",
      "properties": { "quantity": { "type": "INTEGER" } }
    }
  }
}
```

---

## Validation Rules

Apply in order before generating any Cypher when schema file is present.

**Guiding principle**: reason about the most likely intent before asking the user. Ask only when genuinely unable to resolve — never silently generate wrong Cypher, but avoid stopping when a safe interpretation exists.

**1. Entity verification** — all node labels, relationship types, and properties must exist in schema. If not found: attempt synonym resolution (rule 2) and look for structurally similar entities before asking.

**2. Synonym mapping**
- Unambiguous close match → resolve silently, note, continue:
  `ℹ️ Resolved 'Minifigure' → 'Minifig'. Proceeding.`
- Ambiguous → pick the most likely match given query context, note the choice, continue:
  `ℹ️ 'Fig' is ambiguous (Minifig, figNum). Interpreted as 'Minifig' based on context. Correct if wrong.`
- No match after reasoning → surface candidates and ask; only if no candidates exist, report and ask:
  `⚠️ 'Character' not found in schema and no close match. Did you mean one of: [list schema nodes]?`

**3. Property type enforcement** — check declared type for every filter value. Valid types: `STRING` `INTEGER` `FLOAT` `BOOLEAN` `DATE` `DATETIME` `LOCAL_DATETIME` `TIME` `LOCAL_TIME` `DURATION` `POINT` `LIST` `LIST<STRING>` `LIST<INTEGER>` etc.

On mismatch: reason about intent first.
- String against INTEGER with value like `'unknown'` / `'n/a'` → likely a null/existence check; rewrite as `WHERE n.prop IS NULL` and note.
- Clearly wrong literal (e.g. string UUID passed as INTEGER) → propose correction and ask to confirm before proceeding.

**4. Relationship direction** — read `direction` field. `out` = `(a)-[:REL]->(b)`. `in` = `(b)-[:REL]->(a)`. Wrong direction → correct silently, note:
```
HAS_SET | Schema: Theme──→Set | Prompt: Set──→Theme | ↩ Corrected
```

**5. Generate** — Cypher 25 with `$param` syntax; returned fields restricted to schema-declared properties only.

---

## Examples

### Valid query
```
User: "List minifigures in the Cloud City set"

✅ Set | ✅ Minifig | ✅ HAS_MINIFIG (Set→Minifig)

CYPHER 25
MATCH (s:Set {id: $setId})-[:HAS_MINIFIG]->(m:Minifig)
RETURN m.name AS minifigName, m.fig_num AS figNum, m.num_parts AS numParts
ORDER BY m.name
// Parameters: { setId: "10123-1" }
```

### Entity not found — agent reasons and asks
```
User: "Find all Character nodes linked to a Movie"

❌ Character NOT FOUND | ❌ Movie NOT FOUND
Schema nodes: Theme, Set, Minifig

⚠️ Neither 'Character' nor 'Movie' exists in this schema.
Closest nodes are: Theme, Set, Minifig.
Did you mean something like Set linked to Minifig, or are you querying a different database?
```

### Synonym resolved
```
User: "Find all Minifigures in a set"

ℹ️ Resolved 'Minifigure' → 'Minifig'. Proceeding.

CYPHER 25
MATCH (s:Set {id: $setId})-[:HAS_MINIFIG]->(m:Minifig)
RETURN m.name AS minifigName, m.fig_num AS figNum
// Parameters: { setId: $setId }
```

### Type mismatch — agent reasons about intent
```
User: "Find sets where pieces is 'unknown'"

Set.pieces declared INTEGER, value 'unknown' is a STRING.
Interpreting as null/missing-value check.

ℹ️ Rewritten: WHERE s.pieces IS NULL. Correct if you meant something else.

CYPHER 25
MATCH (s:Set) WHERE s.pieces IS NULL RETURN s.name, s.id
```

---

## Commit or ignore?

The schema file captures the DB structure at a point in time. Choose based on your project:

**Commit** (`git add *-schema.json`) when:
- Schema is stable and shared across the team
- You want reproducible Cypher generation in CI or without a live DB

**Ignore** (add `*-schema.json` to `.gitignore`) when:
- Schema contains sensitive label/property names
- DB is actively evolving and a stale committed file would cause confusion

Either way, `schema_retrieved_at` tells any reader when the snapshot was taken.
