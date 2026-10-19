# neo4j-ontology-skill

Authors and validates **Neo4j Ontology Graph Specification v1** documents in YAML and JSON: defining nodes and relationships, properties with type tokens, constraints (key/unique/mustExist), labels, endpoint cardinality, and extensions. Every document is validated against the vendored spec schema via the bundled `scripts/validate.py`.

## Topics covered

**Format structure** — required root fields (`schema`, `id`, `version`), `nodes`/`relationships` maps keyed by local ids, label shorthand vs full `labels` object

**Property types** — `SCALAR` tokens (`STRING`, `INTEGER`, `FLOAT`, `BOOLEAN`, temporal types, `POINT`, `BYTES`), `LIST<…>`, `VECTOR<INTEGER|FLOAT>` with `dimension`

**Constraints** — property flags (`key`, `unique`, `mustExist`) and object form for composite/named constraints

**Endpoint cardinality** — `count` exact or `min_count`/`max_count` ranged on relationship `from`/`to`

**Extensions** — named first-party keys (`neo4j:index`, `ui:display`, `importer:table`, `importer:mapping`) plus the custom-extension envelope

**Validation workflow** — `uv run scripts/validate.py <document>` with exit-code semantics and mandatory re-validation

**Both YAML and JSON** — equivalent documents in either syntax, YAML default

## Not covered

- Cypher, or loading/applying an ontology into a database → `neo4j-cypher-skill`
- Generic graph data modeling advice (node vs property vs label, anti-patterns, supernodes) → `neo4j-modeling-skill`

## Spec status

The v1 schema is vendored from `neo4j/graph-spec`, branch `ontology-graph-spec` (PR #118) — a **pre-release draft**, not yet merged. The pinned commit and refresh command live in [`assets/PROVENANCE.md`](assets/PROVENANCE.md).

## Reference files

| File | Contents |
|---|---|
| [`SKILL.md`](SKILL.md) | Operational playbook: authoring workflow, core facts, minimal example, checklist |
| [`references/format-reference.md`](references/format-reference.md) | Full field reference, data-type grammar, constraint objects, extension envelope, gotchas |
| [`scripts/validate.py`](scripts/validate.py) | PEP 723 validator (runs via `uv`); validates a document against the vendored schema |
| [`assets/`](assets/) | Vendored JSON Schema, canonical spec examples, provenance record |

## Install

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-ontology-skill
```
