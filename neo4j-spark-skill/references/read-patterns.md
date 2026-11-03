# Neo4j Spark Connector — Read Options Reference

Full option reference for `.read.format("org.neo4j.spark.DataSource")`.

## Core Read Options (mutually exclusive — pick one)

| Option | Value | Description |
|--------|-------|-------------|
| `labels` | `:Label` or `:Label1:Label2` | Read nodes with given label(s). Multiple = AND. |
| `query` | Cypher string | Custom MATCH ... RETURN query. Aliases become column names. |
| `relationship` | `REL_TYPE` | Read relationships of given type. Requires source/target label options. |

## Relationship Read Sub-Options

| Option | Required | Description |
|--------|----------|-------------|
| `relationship.source.labels` | Yes | Colon-prefixed labels of source node `:Label` |
| `relationship.target.labels` | Yes | Colon-prefixed labels of target node `:Label` |

## Query Read Sub-Options

| Option | Description |
|--------|-------------|
| `query.count` | `query` reads only (ignored with a warning on `labels`/`relationship`). Count query returning a field named `count` (e.g. `MATCH (n:Person) RETURN count(n) AS count`) or a plain number. Used for partition planning. |

## Partition and Performance Options

| Option | Default | Description |
|--------|---------|-------------|
| `partitions` | `1` | Number of Spark partitions. Each partition reads a `SKIP`/`LIMIT` window in its own transaction — no shared snapshot. Partitioned `query` reads need a deterministic `ORDER BY`, else rows silently go missing. |
| `schema.flatten.limit` | `10` | Rows sampled for schema inference (no APOC). Increase for heterogeneous nodes. |

## Output Columns

**Label scan result columns:**
- `<elementId>` — STRING element ID (5.x: `<id>`, numeric internal id)
- `<labels>` — array of node labels
- One column per node property

**Relationship scan result columns:**
- `<rel.elementId>` — STRING relationship element ID (5.x: `<rel.id>`)
- `<rel.type>` — relationship type string
- `<source.elementId>` (5.x: `<source.id>`), `<source.labels>`, `source.<prop>` — source node fields
- `<target.elementId>` (5.x: `<target.id>`), `<target.labels>`, `target.<prop>` — target node fields
- Relationship properties as `rel.<prop>` columns

## Schema Inference Notes

- Without APOC: samples `schema.flatten.limit` rows to infer types
- With APOC: uses `apoc.meta.nodeTypeProperties` — more accurate
- Map/list properties: flattened into dot-notation columns (e.g. `address.city`)
- Use `query` mode with explicit RETURN types when inference is unreliable

## Examples

### Multi-label AND filter

```python
df = (spark.read.format("org.neo4j.spark.DataSource")
    .option("labels", ":Person:Employee")
    .load())
```

### Cypher with explicit column types

```python
df = (spark.read.format("org.neo4j.spark.DataSource")
    .option("query", """
        MATCH (p:Person)-[r:ACTED_IN]->(m:Movie)
        RETURN p.name AS name,
               toFloat(r.earnings) AS earnings,
               m.year AS year,
               m.title AS movie
    """)
    .load())
```

### Partitioned read for large node set

```python
df = (spark.read.format("org.neo4j.spark.DataSource")
    .option("labels", ":Transaction")
    .option("partitions", "20")
    .load())
```

### Partitioned query read

```python
df = (spark.read.format("org.neo4j.spark.DataSource")
    .option("query", "MATCH (n:Transaction) RETURN n.id AS id, n.amount AS amount ORDER BY n.id")
    .option("partitions", "20")
    .option("query.count", "MATCH (n:Transaction) RETURN count(n) AS count")
    .load())
```

### Relationship with properties

```python
df = (spark.read.format("org.neo4j.spark.DataSource")
    .option("relationship", "ACTED_IN")
    .option("relationship.source.labels", ":Person")
    .option("relationship.target.labels", ":Movie")
    .load())
# Columns (6.x): <rel.elementId>, <rel.type>, <source.elementId>, <source.labels>, source.name, <target.elementId>, <target.labels>, target.title, rel.roles
```
