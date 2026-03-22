> Source: git@github.com:neo4j/docs-cypher.git@238ab12a — hand-authored from Neo4j 2026.02 release notes
> Generated: 2026-03-22T00:00:00Z
> See: version-matrix.md for availability; https://neo4j.com/docs/cypher-manual/25/administration/graph-types/

> **PREVIEW — Enterprise Edition only, Neo4j 2026.02+**
> GRAPH TYPE DDL is a Preview feature. Not for production use. Syntax may change before GA.
> Only available in Enterprise Edition. Community Edition does not support GRAPH TYPE.

# GRAPH TYPE DDL

GRAPH TYPE DDL adds optional schema constraints to a graph database. Only explicitly declared
element types (node types and relationship types) are subject to constraint enforcement. All
other nodes and relationships remain unconstrained (open-model semantics).

## Key Concepts

- **Element type**: A typed, schema-constrained node or relationship. Uses `::` annotation syntax.
- **Open-model semantics**: Nodes and relationships NOT covered by a declared element type are unconstrained — they can have any labels and properties. GRAPH TYPE constraints only apply to declared types.
- **Mandatory property**: A property declared in an element type that must be present and non-null.
- **Property type validation**: Properties declared with a type (e.g., `STRING`, `INTEGER`) are validated on write.

## SHOW GRAPH TYPES

```cypher
CYPHER 25
SHOW GRAPH TYPES
```

List all declared graph types in the current database.

```cypher
CYPHER 25
SHOW GRAPH TYPES YIELD *
```

List all graph types with full column output.

## ALTER CURRENT GRAPH TYPE SET (declare element types)

Declare a node element type with mandatory typed properties:

```cypher
CYPHER 25
ALTER CURRENT GRAPH TYPE SET
  (::Person {
    name :: STRING NOT NULL,
    age  :: INTEGER
  })
```

Declare a relationship element type (requires source and target node types):

```cypher
CYPHER 25
ALTER CURRENT GRAPH TYPE SET
  [::KNOWS {
    since :: DATE
  }]
```

> **Note**: `:: TYPE NOT NULL` marks the property as mandatory (must be present and non-null).
> A property declared without `NOT NULL` is optional but type-validated if present.

## EXTEND GRAPH TYPE (add element types to existing schema)

```cypher
CYPHER 25
EXTEND GRAPH TYPE WITH
  (::Company {
    name     :: STRING NOT NULL,
    founded  :: INTEGER
  }),
  [::EMPLOYS {
    startDate :: DATE NOT NULL
  }]
```

`EXTEND GRAPH TYPE WITH` adds new element types without replacing existing ones.
Use this to incrementally evolve the schema.

## DROP GRAPH TYPE ELEMENTS

Remove specific element types from the graph type:

```cypher
CYPHER 25
DROP GRAPH TYPE ELEMENTS (::Person), [::KNOWS]
```

> **Caution**: Dropping an element type removes its schema constraints but does not delete
> the underlying data. Existing nodes and relationships with those labels/types remain.

## ALTER ELEMENT TYPES (modify property declarations)

```cypher
CYPHER 25
ALTER ELEMENT TYPES (::Person)
  SET (age :: INTEGER NOT NULL)
```

Adds or modifies property declarations on an existing element type.

## Element Type Annotation Syntax

| Syntax | Meaning |
|---|---|
| `(::Label)` | Node element type for label `Label` |
| `[::REL_TYPE]` | Relationship element type for `REL_TYPE` |
| `prop :: STRING NOT NULL` | Mandatory STRING property |
| `prop :: INTEGER` | Optional INTEGER property (validated if present) |
| `prop :: DATE NOT NULL` | Mandatory DATE property |
| `prop :: FLOAT` | Optional FLOAT property |
| `prop :: BOOLEAN NOT NULL` | Mandatory BOOLEAN property |

## Write Query Interaction

Element type constraints are enforced on `CREATE` and `MERGE` operations:

```cypher
CYPHER 25
CREATE (p::Person {name: 'Alice', age: 30})
```

The `::` annotation in a `CREATE` or `MERGE` clause explicitly asserts the node matches a
declared element type, triggering type validation. Without `::` in the data clause, the node
is created as a regular node (no type validation, even if a matching element type exists).

## When to Use GRAPH TYPE DDL

- Enforcing data quality guarantees on high-value node/relationship types
- Preventing NULL values in key properties without a full CONSTRAINT
- Gradual schema adoption — declare types for critical entities only; leave others open
- Enterprise deployments requiring audit-traceable schema governance

## SKILL.md Routing

GRAPH TYPE clauses are SCHEMA operations — route to `references/schema/` alongside indexes and constraints.

> **Available: Neo4j 2026.02+ Enterprise Edition** — use `references/version-matrix.md` to check availability before generating GRAPH TYPE queries.
