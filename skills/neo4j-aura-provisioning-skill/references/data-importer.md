# Aura Data Importer (GUI Import Tool)

Data Importer is built into the Aura console. Access: instance → **Import** in left sidebar.
No Cypher required — visual drag-and-drop CSV-to-graph mapping.

## Workflow

1. **Add data source** — click "New data source" → CSV or TSV → upload file
2. **Create node labels** — click "Add node label" → set label name → "Map from table" → select columns
3. **Set unique identifier** — click key icon next to ID property → auto-creates unique constraint + index
4. **Create relationships** — hover edge of source node → drag to target node → set type → map From/To ID columns
5. **Add relationship properties** — select relationship → "Map from table" → select extra columns
6. **Run import** — click "Run import" → enter DB credentials if prompted → wait for summary
7. **Save model** — name the model → "Save" (reusable for future imports)

## Key Behaviors

- Setting a unique identifier **automatically creates a constraint and index** — enables MERGE semantics on re-import
- Type mismatch: if Data Importer can't convert a value (e.g. text in Integer column), import continues but that node won't have the property — check counts
- Single CSV file can source both nodes AND relationships (denormalized data): map same file to node label and relationship; set From/To ID columns
- Models saved at project level; reusable across instances
- Download model + data: `...` menu → "Download model (with data)"; restore via "Open model (with data)"
- Clear existing model: `...` menu → "Clear all"

## Common Mistakes

| Mistake | Consequence | Fix |
|---|---|---|
| No unique identifier set | Duplicates on re-import; can't create relationships | Always set key icon before importing |
| Keeping FK columns as node properties | Graph has no relationships | Map FK columns to relationship definitions |
| Wrong data type | Properties silently missing | Check column types; verify node counts post-import |
| Nodes before constraints | Constraint creation fails on existing duplicates | Unique ID in Data Importer creates constraint first automatically |

## Verify After Import

```cypher
// Node counts by label
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY cnt DESC

// Relationship counts
MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS cnt ORDER BY cnt DESC

// Sample data
MATCH (n:Movie) RETURN n LIMIT 5
```

## Data Importer vs LOAD CSV

Use Data Importer when: GUI workflow preferred, one-time or occasional import, CSV files available.
Use LOAD CSV (Cypher) when: complex transformations, batched large imports, CI/CD pipelines, incremental sync.
Use `neo4j-import-skill` for bulk `neo4j-admin import` (offline, fastest for millions of rows).
