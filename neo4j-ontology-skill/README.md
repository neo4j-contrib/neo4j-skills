# neo4j-ontology-skill

Authors and validates **Neo4j Ontology Graph Specification** documents in YAML and JSON: defining nodes and relationships, properties with Neo4jType tokens, constraints (key/unique/must_exist), labels, endpoint cardinality, and extensions. Every document is validated against the live-resolved spec schema via the bundled `scripts/validate.py`.

## Topics covered

**Format structure** — required root fields (`schema`, `id`, `version`), `nodes`/`relationships` maps keyed by local ids, label shorthand vs full `labels` object

**Property types** — Neo4jType tokens exactly (`STRING`, `INTEGER`, `FLOAT`, `BOOLEAN`, temporal tokens with spaces like `ZONED DATETIME`, `POINT`, `UUID`), `LIST<…>`, `VECTOR<…>` with `dimension` on the property

**Constraints** — property flags (`key`, `unique`, `must_exist` — snake_case) and object form (`type` ∈ EXISTS/KEY/PROPERTY_TYPE/UNIQUE) for composite/named constraints

**Endpoint cardinality** — `count` exact or `min_count`/`max_count` ranged on relationship `from`/`to`

**Extensions** — fixed `extensions` shape per element (node `indexes`/`display`/`custom`, relationship `indexes`/`custom`, root `tables`/`mappings`/`custom`), free-form data under `custom` only

**Validation workflow** — `uv run scripts/validate.py <document>` with exit-code semantics and mandatory re-validation

**Both YAML and JSON** — equivalent documents in either syntax, YAML default

## Not covered

- Cypher, or loading/applying an ontology into a database → `neo4j-cypher-skill`
- Generic graph data modeling advice (node vs property vs label, anti-patterns, supernodes) → `neo4j-modeling-skill`

## Schema resolution

`scripts/validate.py` resolves the schema live from published sources, in order: `--schema <path-or-url>` (explicit, no fallback) → the document's own `schema` field when it is a URL → the ONT-31 published URLs (`https://neo4j.com/docs/ontology-graph-spec/<version>/schema.json`, immutable per version; `.../current/schema.json`, moving alias) → transitional fallback `https://raw.githubusercontent.com/neo4j/ontology-graph-spec/main/ontology-graph-spec.schema.json` while publication is pending (pre-release).

A document's `schema` field names the published versioned URL of the version being authored — older versions validate against their published schema.

## Reference files

Loaded on demand — not bundled into the main skill context:

| File | Contents |
|---|---|
| [`SKILL.md`](SKILL.md) | Operational playbook: authoring workflow, core facts, minimal example, checklist |
| [`references/format-reference.md`](references/format-reference.md) | Full field reference, data-type grammar, constraint objects, extension shapes, gotchas, YAML+JSON examples |
| [`scripts/validate.py`](scripts/validate.py) | PEP 723 validator (runs via `uv`); fetches the schema live and validates a document against it |

## Install

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-ontology-skill
```
