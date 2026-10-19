# Format Reference — Neo4j Ontology Graph Spec

Contract: JSON Schema draft 2020-12, `$id` `https://neo4j.com/docs/ontology-graph-spec/1.0.0/schema.json` (schema title `GraphModel` — naming leftover, ignore). Schema resolved live from the published URL or the neo4j/ontology-graph-spec repo. Section names below are the schema's `$defs` names.

## Gotchas

- Required root fields: `schema`, `id`, `version`. Root `additionalProperties: false` — unknown root fields rejected. Every object in the schema is `additionalProperties: false`; the only free-form escape hatch is `custom`.
- `version` is a STRING (user-defined revision label), not an integer. YAML: quote it (`version: "1"`).
- Field names are snake_case: `must_exist` (NOT `mustExist`), `min_count`, `max_count`, `one_of`, `primary_keys`, `foreign_keys`, `from_node`, `to_node`, `match_label`, `depends_on`.
- `type` values come from the Neo4jType enum exactly — case-sensitive; temporal tokens contain a space (`ZONED DATETIME`); parameterized tokens use angle brackets (`VECTOR<FLOAT32>`, `LIST<STRING>`).
- `constraints` is a MAP id → constraint object, not a list. Object carries `type` (∈ EXISTS/KEY/PROPERTY_TYPE/UNIQUE) + `properties` (list of property ids declared on the SAME element).
- Property flags (`must_exist`, `unique`, `key`) are single-property shorthands, expanded into constraints when the model is internalised. `key` = unique + exists per Neo4j key-constraint semantics. Composites and nameable constraints need the object form.
- Map keys under `nodes`/`relationships` are local ids, NOT labels/types. Label lives in `label` / `labels.identifier`; relationship type lives in `type`. Endpoints reference node ids (`from.node` / `to.node`) — label renames never break references.
- Extensions sit under `extensions` with a fixed shape per element: node → `indexes`/`display`/`custom`; relationship → `indexes`/`custom`; root → `tables`/`mappings`/`custom`; labels/property/constraint/index → `custom` only. Unknown extension keys rejected.
- Index `options` is `null` or one of FULLTEXT/POINT/VECTOR option objects whose `type` const must match the index `type`. RANGE/TEXT/LOOKUP indexes: omit `options`.
- `dimension` (integer|null) accompanies VECTOR types, on `Property` and `TableColumn`.
- `Node` and `RelationshipTarget` require nothing per schema. A node with neither `label` nor `labels` is meaningless — always author one. Identify a relationship end by `node` (id) or `label`; cardinality via `count` (exact) or `min_count`/`max_count`; absent = unconstrained.
- Absent means none: omit empty maps/lists. Never write `properties: {}`, `aliases: []`, `custom: {}`.

## Top level

| field | type | required | notes |
|---|---|---|---|
| `schema` | string | yes | Spec schema URI used; include version, e.g. `https://neo4j.com/docs/ontology-graph-spec/1.0.0/schema.json`. Validator resolves the schema from it |
| `id` | string | yes | Unique model id, typically kebab-case of the name |
| `version` | string | yes | User-defined revision label of this document |
| `name` | string | no | Human-readable name |
| `description` | string | no | |
| `nodes` | map id → Node | no | Keys are local ids |
| `relationships` | map id → Relationship | no | Keys are local ids |
| `extensions` | GraphModelExtensions | no | Root extensions: tables/mappings/custom |

## `Node`

| field | type | notes |
|---|---|---|
| `label` | string\|null | Shorthand for the identifying label |
| `labels` | Labels | Full labels object; use when implied/optional labels exist |
| `properties` | map id → Property | |
| `constraints` | map id → NodeConstraint | Keyed objects, not a list |
| `extensions` | NodeExtensions | indexes/display/custom |
| `name` | string\|null | Human-readable; replaces id in the pretty form |
| `description` | string | |
| `aliases` | string[] | Alternative names |
| `reference` | string | URI of an external resource describing the node |

## `Labels`

| field | type | notes |
|---|---|---|
| `identifier` | string\|null | The identifying (main) label |
| `implied` | string[] | Labels entailed by the identifier; documented, never inferred |
| `optional` | string[] | Labels that may be present but are not guaranteed |
| `extensions` | LabelsExtensions | `custom` only |

## `Property`

| field | type | notes |
|---|---|---|
| `type` | Neo4jType | Type token from the enum |
| `dimension` | integer\|null | VECTOR companion: element count |
| `must_exist` | boolean\|null | Shorthand existence constraint |
| `unique` | boolean\|null | Shorthand uniqueness constraint |
| `key` | boolean\|null | Shorthand key constraint |
| `extensions` | PropertyExtensions | `custom` only |
| `name` | string\|null | Human-readable name |
| `description` | string | |
| `reference` | string | URI of an external resource |
| `pattern` | string | Regex values are expected to match |
| `one_of` | string[] | Values the property is restricted to |

## Data types — `Neo4jType` enum

Exact tokens (39):

```
ANY  LIST<ANY>  BOOLEAN  LIST<BOOLEAN>  DATE  LIST<DATE>  DURATION  LIST<DURATION>
FLOAT  LIST<FLOAT>  FLOAT32  LIST<FLOAT32>
INTEGER  LIST<INTEGER>  INTEGER8  LIST<INTEGER8>  INTEGER16  LIST<INTEGER16>  INTEGER32  LIST<INTEGER32>
STRING  LIST<STRING>  POINT  LIST<POINT>  UUID
LOCAL DATETIME  LIST<LOCAL DATETIME>  LOCAL TIME  LIST<LOCAL TIME>
ZONED DATETIME  LIST<ZONED DATETIME>  ZONED TIME  LIST<ZONED TIME>
VECTOR<FLOAT>  VECTOR<FLOAT32>  VECTOR<INTEGER>  VECTOR<INTEGER8>  VECTOR<INTEGER16>  VECTOR<INTEGER32>
```

- `UUID` and `VECTOR<...>` have no LIST arm. No nested lists, no unions.
- `ANY` opts out of type constraint.
- VECTOR element types: FLOAT/FLOAT32 or INTEGER8/16/32/INTEGER. Pair with `dimension` on the property.

## Constraints — `NodeConstraint` / `RelationshipConstraint`

`ConstraintType` enum: `EXISTS` | `KEY` | `PROPERTY_TYPE` | `UNIQUE`.

| field | required | notes |
|---|---|---|
| `type` | yes | ConstraintType token |
| `properties` | yes | Ids of properties declared on the SAME element |
| `label` | no | NodeConstraint only — label the constraint applies to |
| `name` | no | Human-readable name for tooling references |
| `extensions` | no | NodeConstraintExtensions / RelationshipConstraintExtensions — `custom` only |

## `Relationship`

| field | type | required | notes |
|---|---|---|---|
| `type` | string | yes | The relationship type; several ids may share one type across endpoint pairs |
| `from` | RelationshipTarget | yes | Start end |
| `to` | RelationshipTarget | yes | End end |
| `properties` | map id → Property | no | |
| `constraints` | map id → RelationshipConstraint | no | |
| `extensions` | RelationshipExtensions | no | indexes/custom |
| `name` | string\|null | no | |
| `description` | string | no | |
| `aliases` | string[] | no | |
| `reference` | string | no | |

## `RelationshipTarget`

| field | type | notes |
|---|---|---|
| `node` | string | Id of the node at this end (key from `nodes`) |
| `label` | string | Label of the node at this end |
| `count` | integer\|null | Exact relationships per node at this end |
| `min_count` | integer\|null | Minimum count |
| `max_count` | integer\|null | Maximum count |

Counts on `to` constrain relationships per from-instance; counts on `from` per to-instance.

## Extensions

Fixed `extensions` shape per element; every extensions object is `additionalProperties: false`. `custom` is a free-form object (`additionalProperties: {}`) for arbitrary owner data, present on every extensions object (and directly on NodeIndex, RelationshipIndex, NodeDisplay, Table, TableColumn, ForeignKey, ForeignKeyReference).

### Node — `NodeExtensions`

| field | type | notes |
|---|---|---|
| `indexes` | map id → NodeIndex | Database indexes on this node |
| `display` | null \| NodeDisplay | Visual placement |
| `custom` | object | Free-form |

`NodeIndex` — required: `type`, `labels`, `properties`:

| field | notes |
|---|---|
| `type` | IndexType token |
| `labels` | Labels covered |
| `properties` | Property ids covered |
| `options` | null \| IndexOption; must match `type` |
| `name` | Human-readable name |
| `custom` | Free-form |

`IndexType` enum: `FULLTEXT` | `POINT` | `RANGE` | `TEXT` | `VECTOR` | `LOOKUP`.

`IndexOption` — oneOf three shapes; `type` const must equal the index `type`; each requires only `type`:

- FULLTEXT: `fulltext.default_analyzer` (string), `fulltext.analyzer` (string|null), `fulltext.eventually_consistent` (boolean), `fulltext.eventually_consistent_apply_parallelism` (integer), `fulltext.eventually_consistent_refresh_interval` (string), `fulltext.eventually_consistent_refresh_parallelism` (integer), `fulltext.eventually_consistent_index_update_queue_max_length` (integer)
- POINT: `spatial.cartesian.min`/`.max`, `spatial.cartesian-3d.min`/`.max`, `spatial.wgs-84.min`/`.max`, `spatial.wgs-84-3d.min`/`.max` (number arrays)
- VECTOR: `vector.dimensions` (integer|null), `vector.similarity_function` (string, e.g. cosine/euclidean), `vector.default_search_expansion_factor` (number|null), `vector.quantization.enabled` (boolean), `vector.quantization.type` (string), `vector.hnsw.m` (integer), `vector.hnsw.ef_construction` (integer)

`NodeDisplay` — required: `x`, `y`:

| field | type | notes |
|---|---|---|
| `x` | number | Horizontal position |
| `y` | number | Vertical position |
| `colour` | string\|null | Hex string, e.g. `#FF8800` |
| `custom` | object | Free-form |

### Relationship — `RelationshipExtensions`

| field | type | notes |
|---|---|---|
| `indexes` | map id → RelationshipIndex | Indexes on this relationship |
| `custom` | object | Free-form |

`RelationshipIndex` — required: `type`, `properties`. Fields: `type` (IndexType), `properties` (property ids), `options` (null | IndexOption), `name`, `custom`. No `labels` field — relationship indexes key on the type.

### Root — `GraphModelExtensions` (import)

| field | type | notes |
|---|---|---|
| `tables` | map id → Table | Data source table schemas |
| `mappings` | map id → Mapping[] | Mapping sets from tables to nodes/relationships |
| `custom` | object | Free-form |

`Table` — required: `source`:

| field | notes |
|---|---|
| `source` | Where the table's data comes from |
| `columns` | TableColumn list in source order |
| `primary_keys` | Column names forming the primary key |
| `foreign_keys` | map id → ForeignKey |
| `custom` | Free-form |

`TableColumn` — nothing required. Fields: `name` (unique within table), `type` (source data type), `size` (integer), `suggested` (Neo4jType suggested for values), `supported` (Neo4jType list convertible by the import tool), `dimension` (integer|null, for vectors), `custom`.

`ForeignKey` — required: `columns`, `references`. `columns`: column names in this table. `references`: ForeignKeyReference. Plus `custom`.

`ForeignKeyReference` — required: `table` (referenced table id). Optional: `columns` (referenced column names), `custom`.

### Mappings — `Mapping` = oneOf NODE | QUERY | RELATIONSHIP

Discriminator: `type` const. Common optional: `id` (mapping id, so siblings can reference it), `depends_on` (id of a mapping that must import first).

`NODE` — required: `type`, `node`, `table`, `properties`:

| field | notes |
|---|---|
| `type` | const `NODE` |
| `node` | Id of the node mapped |
| `table` | Id of the source table |
| `properties` | map property-id → PropertyMapping |
| `mode` | MappingMode |
| `match_label` | string\|null — label used to match existing nodes |
| `key` | Property ids identifying a node |

`QUERY` — required: `type`, `table`, `query`. `query`: the query string run against the table.

`RELATIONSHIP` — required: `type`, `relationship`, `table`, `from_node`, `to_node`:

| field | notes |
|---|---|
| `relationship` | Id of the relationship mapped |
| `from_node` / `to_node` | TargetMapping — how each end node is matched |
| `properties` | map property-id → PropertyMapping |
| `mode`, `key`, `match_label` | As on NODE |

`PropertyMapping` — required: `column` (source column name). Sole field.

`MappingMode` enum: `MERGE` | `CREATE`.

`TargetMapping` — nothing required. Fields: `label` (node label), `properties` (map property-id → PropertyMapping used to match the node).

## Publication and schema resolution (ONT-31)

- Versioned URL: `https://neo4j.com/docs/ontology-graph-spec/<version>/schema.json` — immutable per version; `1.0.0` is the current spec version. Set the document's `schema` field to the versioned URL it conforms to.
- Moving alias: `https://neo4j.com/docs/ontology-graph-spec/current/schema.json` → newest stable.
- Pre-live fallback: while the published URLs are not live, `scripts/validate.py` falls back to `https://raw.githubusercontent.com/neo4j/ontology-graph-spec/main/ontology-graph-spec.schema.json` (tracks main — moving).

## Validation

One tool: `scripts/validate.py` (PEP 723 — `uv` resolves jsonschema + pyyaml itself). Works from any cwd.

```bash
uv run neo4j-ontology-skill/scripts/validate.py <document.{yaml,yml,json}>
uv run neo4j-ontology-skill/scripts/validate.py <document> --schema <path-or-url>
```

Schema resolution order: `--schema` (path or URL; explicit = no fallback) → document's own `schema` field when a URL → published `current` alias → repo raw fallback. Exit codes: 0 valid · 1 schema violations (all printed with field paths) · 2 document/schema parse or fetch failure. `format` keywords are annotations only (no format checker). On exit 1: fix every reported path, re-run, never deliver non-zero.

## Examples

YAML (`library.ontology.yaml`):

```yaml
schema: "https://neo4j.com/docs/ontology-graph-spec/1.0.0/schema.json"
id: library
version: "1"
name: Library
description: Library domain ontology
nodes:
  author:
    label: Author
    properties:
      id: { type: STRING, key: true }
      name: { type: STRING, must_exist: true }
  book:
    label: Book
    properties:
      isbn: { type: STRING, key: true }
      title: { type: STRING, must_exist: true }
relationships:
  wrote:
    type: WROTE
    from: { node: author, max_count: 1 }
    to: { node: book }
```

JSON (`library.ontology.json`) — same document:

```json
{
  "schema": "https://neo4j.com/docs/ontology-graph-spec/1.0.0/schema.json",
  "id": "library",
  "version": "1",
  "name": "Library",
  "description": "Library domain ontology",
  "nodes": {
    "author": {
      "label": "Author",
      "properties": {
        "id": { "type": "STRING", "key": true },
        "name": { "type": "STRING", "must_exist": true }
      }
    },
    "book": {
      "label": "Book",
      "properties": {
        "isbn": { "type": "STRING", "key": true },
        "title": { "type": "STRING", "must_exist": true }
      }
    }
  },
  "relationships": {
    "wrote": {
      "type": "WROTE",
      "from": { "node": "author", "max_count": 1 },
      "to": { "node": "book" }
    }
  }
}
```

Both validate exit 0 against the live-resolved schema via `scripts/validate.py`. YAML parses to the identical document (`yaml.safe_load`).
