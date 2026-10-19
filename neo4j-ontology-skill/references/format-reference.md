# Format Reference — Neo4j Ontology Graph Specification v1

Deep reference for authoring ontology documents (YAML or JSON). Contract: `assets/ontology-graph-spec.schema.json` (JSON Schema draft 2020-12; `$id` `https://neo4j.com/ontology-graph-spec/1.0.0/schema.json`). Canonical examples: `assets/examples/` (`movies`, `org`, `foaf`).

## Gotchas

- Root key is plain `schema`, NOT `$schema` (ADR-0014). `$schema`/`$id` appear only at the top of the schema file itself — JSON Schema's own meta-keys.
- No `tools` field anywhere (ADR-0013). Removed from v1; never write it.
- VECTOR element types numeric only: `VECTOR<INTEGER>` or `VECTOR<FLOAT>` (ADR-0012). No other VECTOR arm exists.
- Map keys under `nodes`/`relationships` are local ids, NOT labels/types. Label lives in `label` / `labels.identifier`; relationship type lives in `type`. Endpoints reference the id. Label renames do not break references.
- `key: true` implies `unique` + `mustExist`.
- Constraint object `properties` references property names declared on the SAME element: a node's constraints name that node's properties; a relationship's constraints name that relationship's properties.
- Absent means none: empty maps and lists are omitted, never written empty. Never write `properties: {}`, `aliases: []`, `constraints: []`, `custom: []`.
- Property names non-empty (ADR-0010, schema-enforced via `propertyNames.minLength: 1`).
- Required root fields: `schema`, `id`, `version`. Root `additionalProperties: false` — unknown root fields rejected.
- The file at `https://github.com/neo4j/graph-spec/blob/main/ontology-graph-spec.schema.json` is the OLD 4.0.0-era schema (title `GraphModel`). Never author against it. The vendored asset (`assets/ontology-graph-spec.schema.json`) is the v1 contract.

## Top level

| field | type | required | notes |
|---|---|---|---|
| `schema` | string (uri) | yes | Spec link incl. version; doubles as document-type marker. Value: `https://neo4j.com/ontology-graph-spec/1.0.0/schema.json` |
| `id` | string | yes | Unique identifier of the ontology |
| `version` | integer ≥ 0 | yes | The ontology's own version. Identity metadata, not lifecycle |
| `name` | string | no | Human-readable name |
| `description` | string | no | Human-readable description |
| `nodes` | map id → `node` | no | Keys are local ids |
| `relationships` | map id → `relationshipEntry` | no | Keys are local ids |
| `extensions` | `extensionsMap` | no | Ontology-scope extensions |

## `node`

One entry per node type. Map key = local id (not the label).

| field | notes |
|---|---|
| `label` | Shorthand for `labels.identifier`; use when no implied/optional labels exist |
| `labels` | Full `labels` object; use when implied/optional labels exist |
| `properties` | Map property-name → `property`. Names non-empty |
| `constraints` | List of `constraint` objects — the nameable alternative to property flags |
| `aliases` | String list; alternative names for this node type |
| `reference` | Single informational URI pointing at an external definition (e.g. the original RDF resource) |
| `description` | Human-readable description |
| `extensions` | `extensionsMap` |

A node with neither `label` nor `labels` is meaningless (not schema-enforced — do not author one).

## `labels`

Full labels object: identifying label plus implied/optional labels.

| field | required | notes |
|---|---|---|
| `identifier` | yes | The identifying (main) label |
| `implied` | no | Labels entailed by the identifying label. Documented, never inferred |
| `optional` | no | Labels that may be present on instances but are not guaranteed |

## `property`

| field | notes |
|---|---|
| `type` | `propertyType` token |
| `dimension` | VECTOR companion: element count, integer ≥ 1. Absent = unconstrained |
| `mustExist` | boolean; shorthand single-property mustExist constraint |
| `unique` | boolean; shorthand single-property unique constraint |
| `key` | boolean; shorthand single-property key constraint (implies `unique` + `mustExist`) |
| `one_of` | Allowed values list (JSON Schema's word). Default value support |
| `pattern` | Regex the value must match |
| `aliases` | String list |
| `reference` | Single informational URI, as on `node` |
| `description` | |
| `extensions` | `extensionsMap` |

Flags are the single-property shorthand of the object form: `mustExist: true` on property `p` ≡ `{ constraint_type: mustExist, properties: [p] }`; likewise `unique`, `key`. Object form carries what shorthand cannot: composites (`properties` list > 1 entry) and names tooling can reference.

## `propertyType` — data types

Type token grammar (schema `pattern`, exact):

```
ANY
LIST<ANY>
SCALAR           — STRING | INTEGER | FLOAT | BOOLEAN | DATE | TIME | LOCALTIME | DATETIME | LOCALDATETIME | DURATION | POINT | BYTES
LIST<SCALAR>
VECTOR<INTEGER>
VECTOR<FLOAT>
```

- Element types always scalars: no nested lists, no lists of vectors.
- VECTOR numeric only (ADR-0012); companion `dimension` lives on the property.
- No union types in v1: a property is a single type token or `ANY`.
- `ANY` opts the property out of type constraints (mixed value types).

## `constraint`

Object form; alternative to the property flags. Nameable so tooling can reference individual constraints.

| field | required | notes |
|---|---|---|
| `constraint_type` | yes | `key` \| `unique` \| `mustExist` (`key` = unique + mustExist) |
| `properties` | yes | List of ≥ 1 property names declared on the same element |
| `name` | no | Optional name for tooling references |

## `relationshipEntry`

Map key = local id. One-to-one id-to-type in the common case; several keys may share one `type` across different endpoint pairs (graph-type enforcement keys on the type alone and cannot distinguish pairs).

| field | required | notes |
|---|---|---|
| `type` | yes | The relationship type |
| `from` | yes | Start `endpoint` |
| `to` | yes | End `endpoint` |
| `properties` | no | Map property-name → `property`, as on `node` |
| `constraints` | no | List of `constraint` objects, as on `node` |
| `aliases` | no | String list |
| `reference` | no | Single informational URI |
| `description` | no | |
| `extensions` | no | `extensionsMap` |

## `endpoint`

Endpoint cardinality: `count` is the exact form, `min_count`/`max_count` the ranged form; absent means unconstrained (0..*). Counts on `to` constrain relationships per from-instance; counts on `from` constrain per to-instance.

| field | required | notes |
|---|---|---|
| `node` | yes | A node id from the `nodes` map |
| `count` | no | Exact relationship count per endpoint instance, integer ≥ 0 |
| `min_count` | no | Minimum count, integer ≥ 0 |
| `max_count` | no | Maximum count, integer ≥ 1 |

## Extensions — `extensionsMap` and `extension`

Named first-party keys on any `extensions` map: `neo4j:index`, `ui:display`, `importer:table`, `importer:mapping`. Payload shape owner-defined, shipped in the spec SDK, NEVER validated by the spec schema (`additionalProperties: true`). A named key's payload may be one object or a list of objects (owner's choice).

Custom extensions ride the fixed envelope under the reserved `custom` key — a list of `extension` objects:

| field | required | notes |
|---|---|---|
| `type` | yes | Custom extension type token (owner-namespaced, e.g. `governance:pii`) |
| `schema` | no | The extension type's own schema URI, owner-managed; never the ontology spec schema |
| `name` | no | Optional (a per-node display has no natural name) |
| `definition` | no | Free-form payload; never validated by this spec |

Unknown extra envelope fields (e.g. `description`) are carried untouched. Envelope always validates.

Placement rule: an extension lives on the element it describes (root, node, relationship, property all accept `extensions`). Describes several elements or none (tables, mappings) → top level.

## Examples

YAML (`library.ontology.yaml`):

```yaml
schema: "https://neo4j.com/ontology-graph-spec/1.0.0/schema.json"
id: 9c2f1a4e-6b3d-4e8f-a1c5-7d2b9e4f6a08
version: 1
name: library
description: Library domain ontology
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
      title: { type: STRING, mustExist: true }
relationships:
  WROTE:
    type: WROTE
    from: { node: Author, max_count: 1 }
    to: { node: Book }
```

JSON (`library.ontology.json`) — same document:

```json
{
  "schema": "https://neo4j.com/ontology-graph-spec/1.0.0/schema.json",
  "id": "9c2f1a4e-6b3d-4e8f-a1c5-7d2b9e4f6a08",
  "version": 1,
  "name": "library",
  "description": "Library domain ontology",
  "nodes": {
    "Author": {
      "label": "Author",
      "properties": {
        "id": { "type": "STRING", "key": true },
        "name": { "type": "STRING", "mustExist": true }
      }
    },
    "Book": {
      "label": "Book",
      "properties": {
        "isbn": { "type": "STRING", "key": true },
        "title": { "type": "STRING", "mustExist": true }
      }
    }
  },
  "relationships": {
    "WROTE": {
      "type": "WROTE",
      "from": { "node": "Author", "max_count": 1 },
      "to": { "node": "Book" }
    }
  }
}
```

Both validated against the vendored schema. YAML parses to the identical document (`yaml.safe_load`).

## Validate before delivering

Run from skill root (`neo4j-ontology-skill/`):

```bash
# JSON document
uv run --with jsonschema python3 -c "import json,jsonschema; s=json.load(open('assets/ontology-graph-spec.schema.json')); d=json.load(open('DOC.json')); jsonschema.validate(d,s); print('valid')"

# YAML document
uv run --with jsonschema --with pyyaml python3 -c "import json,yaml,jsonschema; s=json.load(open('assets/ontology-graph-spec.schema.json')); d=yaml.safe_load(open('DOC.yaml')); jsonschema.validate(d,s); print('valid')"
```

If validation fails: read the error path, fix the document, re-run. Never deliver an invalid document.
