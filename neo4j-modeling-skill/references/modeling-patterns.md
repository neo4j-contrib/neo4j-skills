# Modeling Patterns Reference

Use this reference when a modeling task needs a specific pattern beyond the main skill checklist.

## Time-Series Data

Use event nodes for individual observations, and connect them to stable domain entities:

```cypher
(:Sensor)-[:RECORDED]->(:Reading {timestamp, value})
```

Avoid encoding timestamps into labels or relationship types. Add range indexes on timestamp properties used for filtering.

## Versioned Entities

Keep a stable identity node and attach immutable version nodes:

```cypher
(:Product {id})-[:HAS_VERSION]->(:ProductVersion {version, validFrom, validTo})
```

Use one current-version relationship or a validity interval when queries need the active version.

## Multi-Tenancy

Use an explicit tenant node when tenant ownership is part of most queries:

```cypher
(:Tenant {id})-[:OWNS]->(:Account)
```

Add tenant-scoped uniqueness constraints where identifiers are only unique inside a tenant.

## Ordered Sequences

Use `:NEXT` relationships when order is intrinsic and traversal is common:

```cypher
(:Step)-[:NEXT]->(:Step)
```

Use numeric position properties when random access, sorting, or reordering is more important than traversal.

## Access Control

Model permissions as relationships when they are graph-shaped:

```cypher
(:User)-[:MEMBER_OF]->(:Group)-[:CAN_READ]->(:Resource)
```

Keep the authorization query explicit and bounded. Avoid broad variable-length traversals unless the maximum depth is justified.
