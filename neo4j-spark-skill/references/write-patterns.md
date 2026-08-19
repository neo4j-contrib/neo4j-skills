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
| `node.keys.skip.nulls` | `false` | Skip rows with null in any `node.keys` column. |
| `batch.size` | `5000` | Rows per UNWIND batch; each batch commits in its own transaction. Aggressive: 20000. |
| `transaction.retries` | `3` | Retry budget per task (not per batch). |
| `transaction.retry.timeout` | `0` | Wait in ms before retry. |
| `schema.optimization.node.keys` | `NONE` | `UNIQUE` — uniqueness constraint; `KEY` — node key constraint. Rejected with `query` mode — use `script.N`. |
| `schema.optimization.relationship.keys` | `NONE` | `UNIQUE` / `KEY` constraints on `relationship.keys` properties. |
| `schema.optimization` | — | Comma-separated `TYPE`, `EXISTS` — property type and existence constraints from the DataFrame schema. |
| `type.conversion` | `default` | `legacy` — pre-5.4.0 handling of timestamps, intervals, byte arrays. |

## Relationship Write Options

| Option | Default | Description |
|--------|---------|-------------|
| `relationship` | — | Relationship type (no colon): `BOUGHT`, `ACTED_IN` |
| `relationship.save.strategy` | `keys` (6.0; `native` on 5.x) | `native`: expects `rel.*`, `source.*`, `target.*` column prefixes. `keys`: explicit mapping via sub-options. |
| `relationship.keys` | — | Properties treated as relationship keys. |
| `relationship.keys.skip.nulls` | `false` | Skip rows with null in any `relationship.keys` column. |
| `relationship.properties` | — | Comma-separated `df_col` or `df_col:rel_prop` pairs for relationship properties. |
| `relationship.source.labels` | — | Source node label(s): `:Customer` |
| `relationship.source.save.mode` | `Match` | `Match`, `Append`, `Overwrite` |
| `relationship.source.node.keys` | — | Required when save.mode=Match or Overwrite. `df_col:node_prop` mapping. |
| `relationship.source.node.properties` | — | Additional source node properties to write. |
| `relationship.target.labels` | — | Target node label(s): `:Product` |
| `relationship.target.save.mode` | `Match` | `Match`, `Append`, `Overwrite` |
| `relationship.target.node.keys` | — | Required when save.mode=Match or Overwrite. `df_col:node_prop` mapping. |
| `relationship.target.node.properties` | — | Additional target node properties to write. |
| `relationship.source.node.keys.skip.nulls` / `relationship.target.node.keys.skip.nulls` | `false` | Skip rows with null in the matching key columns. |

## Setup and Cypher Options [6.0]

| Option | Default | Description |
|--------|---------|-------------|
| `script` | — | Single Cypher statement run once before writes. Mutually exclusive with `script.N`. |
| `script.N` | — | `script.1`, `script.2`, … run in numbered order before writes. Replaces `;`-separated statements. |
| `index.await.timeout` | `300` | Seconds passed to `db.awaitIndexes` after scripts, before writes. `0` disables. |
| `cypher.version` | `5` | Cypher language version — `5` or `25`. |
| `cypher.tuning.<param>` | — | Adds `CYPHER <param>=<value>` preamble, e.g. `cypher.tuning.runtime=parallel`. |
| `db.transaction.metadata.<key>` | — | Transaction metadata map entry; dot-separated keys nest. Visible in `query.log`. |
| `db.transaction.timeout` | driver default | Transaction timeout in ms. |

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
- [ ] `coalesce(1)` before relationship write
- [ ] `node.properties` limits payload to needed columns
- [ ] `batch.size` validated against Neo4j heap
- [ ] `Overwrite` on nodes: constraint prevents duplicates under concurrency
