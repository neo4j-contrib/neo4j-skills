# Neo4j Spark Connector — Write Options Reference

Full option reference for `.write.format("org.neo4j.spark.DataSource")`.

## Save Modes

| Mode | Cypher | Requirements |
|------|--------|--------------|
| `Append` | `UNWIND ... CREATE` | None |
| `Overwrite` | `UNWIND ... MERGE` | `node.keys` or `*.node.keys` |
| `ErrorIfExists` | `CREATE` + error on conflict | — |

## Core Write Options (mutually exclusive — pick one)

| Option | Description |
|--------|-------------|
| `labels` | Write nodes. `:Label` or `:Label1:Label2`. |
| `relationship` | Write relationships with source and target nodes. |
| `query` | Custom Cypher with `CREATE`/`MERGE`. DataFrame row available as `event`. |

## Node Write Options

| Option | Default | Description |
|--------|---------|-------------|
| `labels` | — | Colon-prefixed label(s): `:Person` or `:Person:Employee` |
| `node.keys` | — | Required for Overwrite. Comma-separated `df_col` or `df_col:node_prop` pairs used in MERGE ON. |
| `node.properties` | all columns | Subset of DataFrame columns to write as node properties. |
| `batch.size` | `5000` | Rows per UNWIND batch. Aggressive: 20000. |
| `schema.optimization.node.keys` | `NONE` | `UNIQUE` — adds uniqueness constraint; `NODE_KEY` — adds node key constraint. |

## Relationship Write Options

| Option | Default | Description |
|--------|---------|-------------|
| `relationship` | — | Relationship type (no colon): `BOUGHT`, `ACTED_IN` |
| `relationship.save.strategy` | `native` | `native`: expects `rel.*`, `source.*`, `target.*` column prefixes. `keys`: explicit mapping via sub-options. |
| `relationship.properties` | — | Comma-separated `df_col` or `df_col:rel_prop` pairs for relationship properties. |
| `relationship.source.labels` | — | Source node label(s): `:Customer` |
| `relationship.source.save.mode` | `Match` | `Match`, `Append`, `Overwrite` |
| `relationship.source.node.keys` | — | Required when save.mode=Match or Overwrite. `df_col:node_prop` mapping. |
| `relationship.source.node.properties` | — | Additional source node properties to write. |
| `relationship.target.labels` | — | Target node label(s): `:Product` |
| `relationship.target.save.mode` | `Match` | `Match`, `Append`, `Overwrite` |
| `relationship.target.node.keys` | — | Required when save.mode=Match or Overwrite. `df_col:node_prop` mapping. |
| `relationship.target.node.properties` | — | Additional target node properties to write. |

## Node Keys Mapping Syntax

```
node.keys = "df_column"               # same name in graph property
node.keys = "df_column:graph_prop"    # rename
node.keys = "id,email"                # multiple keys (AND match in MERGE)
node.keys = "user_id:id,email:email"  # multiple with rename
```

## Property Column Mapping Syntax

Same syntax for `node.properties`, `relationship.properties`,
`relationship.source.node.properties`, `relationship.target.node.properties`:

```
"col1,col2"              # include these columns, use same names
"df_col:graph_prop"      # rename on write
"name,email:emailAddr"   # mix
```

## Query Write Mode

DataFrame row values available via `event.column_name`:

```python
write_query = """
    MERGE (p:Person {email: event.email})
    SET p.name = event.name, p.updatedAt = timestamp()
"""
(df.write.format("org.neo4j.spark.DataSource")
    .option("query", write_query)
    .mode("Overwrite")
    .save())
```

## Performance Options

| Option | Default | Recommended |
|--------|---------|-------------|
| `batch.size` | `5000` | `10000`–`20000` for throughput; tune to Neo4j heap |
| partitions (Spark) | DataFrame partitions | `repartition(N)` for nodes; `coalesce(1)` for rels |

## Relationship Node Save Modes

| Mode | Behavior | Use When |
|------|----------|----------|
| `Match` | MATCH existing node by keys | Nodes already exist |
| `Append` | CREATE new node | Always create (risk duplicates) |
| `Overwrite` | MERGE node by keys | Upsert nodes during rel write |

## Full Relationship Write Example (Scala)

```scala
import org.apache.spark.sql.SaveMode

relDF.coalesce(1)
  .write
  .format("org.neo4j.spark.DataSource")
  .mode(SaveMode.Append)
  .option("relationship", "BOUGHT")
  .option("relationship.save.strategy", "keys")
  .option("relationship.source.labels", ":Customer")
  .option("relationship.source.save.mode", "Match")
  .option("relationship.source.node.keys", "cust_id:customerId")
  .option("relationship.target.labels", ":Product")
  .option("relationship.target.save.mode", "Match")
  .option("relationship.target.node.keys", "prod_id:productId")
  .option("relationship.properties", "qty:quantity,ts:purchasedAt")
  .save()
```

## Pre-Write Checklist

- [ ] Uniqueness constraint on all `node.keys` / `*.node.keys` properties
- [ ] `coalesce(1)` before any relationship write
- [ ] `node.properties` reduces payload to only needed columns
- [ ] `batch.size` validated against Neo4j heap settings
- [ ] For `Overwrite` on nodes: constraint prevents duplicates under concurrency
