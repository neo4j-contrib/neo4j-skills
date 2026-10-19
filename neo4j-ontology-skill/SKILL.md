---
name: neo4j-ontology-skill
description: Author and validate Neo4j Ontology Graph Specification v1 (ontology graph spec)
  documents. Use when writing or editing an ontology, defining nodes and relationships with
  properties, data types, constraints (key/unique/mustExist), labels, and endpoint cardinality,
  in YAML or JSON, or validating an ontology document against the spec schema. Does NOT handle
  Cypher or loading an ontology into a database — use neo4j-cypher-skill. Does NOT cover
  generic graph data modeling advice — use neo4j-modeling-skill.
compatibility: uv required to run scripts/validate.py (PEP 723 inline deps)
version: 1.0.0
---

## When to Use

- Authoring an ontology document (Neo4j Ontology Graph Specification v1) from a domain description
- Editing existing ontology YAML/JSON: nodes, relationships, properties, types, constraints, cardinality, extensions
- Validating an ontology document against the spec schema

## When NOT to Use

- **Cypher queries, or loading/applying an ontology into a database** → `neo4j-cypher-skill` (ontology Cypher procedures do not exist yet — later work there)
- **Generic graph modeling advice (node vs property vs label, anti-patterns, supernodes)** → `neo4j-modeling-skill`

---

## Authoring Workflow

### Step 1 — Gather domain intent

Identify what is being modeled: entity types (nodes), connections (relationships + direction), properties per element, identifying keys, mandatory fields, cardinality. If the domain or required shape is unclear, ask the user what is being modeled and which questions the ontology must answer. Do NOT guess a domain.

### Step 2 — Draft the document

YAML or JSON per user preference; default YAML (more readable). Apply the Core Facts below. Load [references/format-reference.md](references/format-reference.md) when anything beyond the minimal example is needed (full `labels` object, constraint objects, extensions, full data-type grammar).

### Step 3 — Validate

```bash
# From the skill directory:
uv run scripts/validate.py <document.{yaml,yml,json}>
# From the repo root:
uv run neo4j-ontology-skill/scripts/validate.py <document.{yaml,yml,json}>
```

Exit 0 = valid · exit 1 = schema violations (one line per field path) · exit 2 = parse/read error. PEP 723 script — `uv` resolves deps (jsonschema, pyyaml) itself.

### Step 4 — Fix and re-validate

Fix every reported error; re-run Step 3. Repeat until exit 0. Validation is MANDATORY — never present an ontology as done with a non-zero exit.

---

## Core Facts

- Required root fields: `schema`, `id` (unique ontology id string), `version` (integer ≥ 0). Root rejects unknown fields (`additionalProperties: false`).
- `schema` value exactly `https://neo4j.com/ontology-graph-spec/1.0.0/schema.json`. Root key is plain `schema`, NOT `$schema`.
- `nodes` / `relationships` are maps keyed by LOCAL IDS, not labels/types. Label lives in `label` or `labels.identifier`; relationship type lives in `type`. Endpoints reference node ids — label renames never break references.
- `label: X` is shorthand for `labels: {identifier: X}`. Use the full `labels` object only when `implied` or `optional` labels exist.
- Type tokens: `ANY`, `LIST<ANY>`, `SCALAR` (`STRING | INTEGER | FLOAT | BOOLEAN | DATE | TIME | LOCALTIME | DATETIME | LOCALDATETIME | DURATION | POINT | BYTES`), `LIST<SCALAR>`, `VECTOR<INTEGER>`, `VECTOR<FLOAT>`. VECTOR numeric only; `dimension` (integer ≥ 1) sits on the property. No unions, no nested lists, no lists of vectors.
- Constraints — two forms:
  - Flags on a property: `key: true`, `unique: true`, `mustExist: true`. `key` implies `unique` + `mustExist`.
  - Object form in the element's `constraints` list: `{constraint_type: key|unique|mustExist, properties: [p1, ...], name: optional}` — required for composites (≥ 2 properties) and for nameable constraints. `properties` must name properties declared on the SAME element.
- Endpoint cardinality: `count` exact, or `min_count`/`max_count` ranged; absent = unconstrained (0..*).
- Extensions: named first-party keys (`neo4j:index`, `ui:display`, `importer:table`, `importer:mapping`) sit directly on an `extensions` map; custom extensions ride the fixed envelope as a list under `custom` (`{type, schema?, name?, definition?}`). Payloads never validated by the spec schema. An extension lives on the element it describes (root, node, relationship, property).
- Absent means none — never write empty maps/lists (`properties: {}`, `aliases: []`, `constraints: []`, `custom: []`); omit them.
- No `tools` field anywhere (removed from v1).
- The file at `github.com/neo4j/graph-spec/blob/main/ontology-graph-spec.schema.json` is the OLD 4.0.0-era schema — never author against it. The v1 contract is the vendored [assets/ontology-graph-spec.schema.json](assets/ontology-graph-spec.schema.json).

## Minimal Example

`library.ontology.yaml` — 2 nodes, 1 relationship:

```yaml
schema: "https://neo4j.com/ontology-graph-spec/1.0.0/schema.json"
id: 9c2f1a4e-6b3d-4e8f-a1c5-7d2b9e4f6a08
version: 1
name: library
nodes:
  Author:
    label: Author
    properties:
      id: { type: STRING, key: true }
      name: { type: STRING, mustExist: true }
  Book:
    label: Book
    properties:
      isbn: { type: STRING, key: true }
relationships:
  WROTE:
    type: WROTE
    from: { node: Author, max_count: 1 }
    to: { node: Book }
```

Full worked examples: `assets/examples/` (`movies.ontology.json`, `foaf.ontology.json`, `org.ontology.json`).

---

## References

Load on demand:

- [references/format-reference.md](references/format-reference.md) — full field reference: every node/relationship/property/endpoint field, `labels` object, constraint objects, extension envelope, data-type grammar, gotchas, YAML+JSON examples
- [assets/ontology-graph-spec.schema.json](assets/ontology-graph-spec.schema.json) — vendored JSON Schema contract (draft 2020-12)
- `assets/examples/` — canonical spec examples

## Spec Status

Pre-release: the spec lives on neo4j/graph-spec PR #118 (branch `ontology-graph-spec`), not yet merged. Assets vendored at a pinned commit — pinned SHA and refresh command in `assets/PROVENANCE.md`. Ontology Cypher procedures do not exist yet; applying an ontology to a database is out of scope here.

---

## Checklist

- [ ] Root fields `schema`, `id`, `version` present; `schema` = exact v1 URL under plain `schema` key
- [ ] No unknown root fields; no `$schema`; no `tools` field
- [ ] `nodes`/`relationships` keyed by local ids; relationship `from`/`to` reference node ids
- [ ] Every node has `label` or `labels.identifier`
- [ ] Type tokens from the grammar; VECTOR element types numeric only; `dimension` on the property
- [ ] Flags only for single-property constraints; object form for composites/named; constraint `properties` exist on the same element
- [ ] No empty maps/lists written
- [ ] `uv run scripts/validate.py <file>` exits 0 (every reported error fixed and re-validated)
