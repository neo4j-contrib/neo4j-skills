# Neo4j Spark Connector — Read Options Reference

Full option reference for `.read.format("org.neo4j.spark.DataSource")`.

## Core Read Options (mutually exclusive — pick one)

| Option | Value | Description |
|--------|-------|-------------|
| `labels` | `:Label` or `:Label1:Label2` | Read nodes with given label(s). Multiple = AND. |
| `query` | Cypher string | Custom MATCH ... RETURN query. Aliases become column names. |
| `relationship` | `REL_TYPE` | Read relationships of given type. Requires source/target label options. |

## Label Read Sub-Options

| Option | Default | Description |
|--------|---------|-------------|
| `node.keys` | — | Comma-separated property names to include as match keys |

## Relationship Read Sub-Options

| Option | Required | Description |
|--------|----------|-------------|
| `relationship.source.labels` | Yes | Colon-prefixed labels of source node `:Label` |
| `relationship.target.labels` | Yes | Colon-prefixed labels of target node `:Label` |

## Query Read Sub-Options

| Option | Description |
|--------|-------------|
| `query.count` | Cypher count query for partition planning (e.g. `MATCH (n:Person) RETURN count(n)`). Avoids full count scan. |

## Partition and Performance Options

| Option | Default | Description |
|--------|---------|-------------|
| `partitions` | `1` | Number of Spark partitions. Connector uses SKIP/LIMIT internally. |
| `batch.size` | `5000` | Rows per partition batch. |
| `schema.flatten.limit` | `10` | Rows sampled for schema inference (no APOC). Increase for heterogeneous nodes. |

## Output Columns

**Label scan result columns:**
- `<id>` — internal Neo4j element ID
- `<labels>` — array of node labels
- One column per node property

**Relationship scan result columns:**
- `<rel.id>` — internal relationship ID
- `<rel.type>` — relationship type string
- `<source.id>`, `<source.labels>`, `source.<prop>` — source node fields
- `<target.id>`, `<target.labels>`, `target.<prop>` — target node fields
- Relationship property columns at top level

## Schema Inference Notes

- Without APOC: connector samples `schema.flatten.limit` rows to infer types
- With APOC installed: uses `apoc.meta.nodeTypeProperties` — more accurate
- Map/list properties: flattened into dot-notation columns (e.g. `address.city`)
- Use `query` mode with explicit RETURN types when schema inference is unreliable

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
    .option("batch.size", "10000")
    .option("query.count", "MATCH (n:Transaction) RETURN count(n)")
    .load())
```

### Relationship with properties

```python
df = (spark.read.format("org.neo4j.spark.DataSource")
    .option("relationship", "ACTED_IN")
    .option("relationship.source.labels", ":Person")
    .option("relationship.target.labels", ":Movie")
    .load())
# Columns: <rel.id>, <rel.type>, <source.id>, source.name, <target.id>, target.title, roles
```
