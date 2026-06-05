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

Apply in order before generating any Cypher when schema file is present:

**1. Entity verification** — all node labels, relationship types, and properties must exist in schema. No guessing.

**2. Synonym mapping**
- Unambiguous close match → resolve silently, note, continue:
  `ℹ️ Resolved 'Minifigure' → 'Minifig'. Proceeding.`
- Ambiguous → suggest and halt:
  `⚠️ 'Fig' not found. Did you mean: Minifig, figNum?`
- No match → halt with validation matrix:

```
Schema Validation Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Requested Entity    | Status
─────────────────── | ──────
Node: Character     | ❌ NOT FOUND
Node: Movie         | ❌ NOT FOUND
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Halting. No Cypher generated.
```

**3. Property type enforcement** — check declared type for every filter value. Mismatch → halt:
```
Filter                  | Schema Type | Supplied | Status
────────────────────── | ─────────── | ──────── | ──────
Set.pieces = 'unknown' | INTEGER     | STRING   | ❌ MISMATCH
Halting. Set.pieces expects INTEGER.
```

**4. Relationship direction** — read `direction` field. `out` = `(a)-[:REL]->(b)`. `in` = `(b)-[:REL]->(a)`. Wrong direction → correct silently, note:
```
HAS_SET | Schema: Theme──→Set | Prompt: Set──→Theme | ↩ Corrected
```

**5. Generate** — all checks pass → Cypher 25 with `$param` syntax, returned fields restricted to schema-declared properties only.

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

### Blocked query
```
User: "Find all Character nodes linked to a Movie"

❌ Character NOT FOUND | ❌ Movie NOT FOUND
Halting. No Cypher generated.
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

### Type mismatch
```
User: "Find sets where pieces is 'unknown'"

Set.pieces = 'unknown' | INTEGER | STRING | ❌ MISMATCH
Halting. Set.pieces expects INTEGER.
```
