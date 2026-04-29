---
name: neo4j-spark-skill
description: Use when reading from or writing to Neo4j with Apache Spark or Databricks using the
  Neo4j Connector for Apache Spark (org.neo4j:neo4j-connector-apache-spark). Covers SparkSession
  setup, DataFrame reads via labels/Cypher/relationship scan, DataFrame writes with SaveMode,
  node.keys for MERGE, relationship write mapping, partition and batch tuning, PySpark and Scala
  examples, Databricks cluster config, Databricks secrets for credentials, Delta Lake to Neo4j
  pipelines. Does NOT handle Cypher authoring — use neo4j-cypher-skill. Does NOT handle the Python
  bolt driver — use neo4j-driver-python-skill. Does NOT handle GDS algorithms — use neo4j-gds-skill.
version: 1.0.0
allowed-tools: Bash WebFetch
---

# Neo4j Connector for Apache Spark

## When to Use

- Reading Neo4j nodes/relationships into Spark DataFrames
- Writing Spark DataFrames to Neo4j as nodes or relationships
- Databricks notebooks connecting to Neo4j
- Delta Lake → Neo4j ingestion pipelines
- Partitioned parallel reads from large Neo4j graphs

## When NOT to Use

- **Python bolt driver / execute_query** → `neo4j-driver-python-skill`
- **Cypher query writing** → `neo4j-cypher-skill`
- **GDS graph algorithms** → `neo4j-gds-skill`
- **Spring Boot + Neo4j** → `neo4j-spring-data-skill`

---

## Version Matrix

| Connector | Spark | Scala | Databricks Runtime | Neo4j |
|-----------|-------|-------|--------------------|-------|
| 5.4.x | 3.3, 3.4, 3.5 | 2.12, 2.13 | 12.2, 13.3, 14.3 LTS | 4.4, 5.x, 2025.x |

Maven artifact (Scala 2.12, Spark 3):
```
org.neo4j:neo4j-connector-apache-spark_2.12:5.4.2_for_spark_3
```

Scala 2.13 variant:
```
org.neo4j:neo4j-connector-apache-spark_2.13:5.4.2_for_spark_3
```

---

## Setup

### Standalone Spark (PySpark)

```python
from pyspark.sql import SparkSession

spark = (SparkSession.builder
    .appName("neo4j-app")
    .config("spark.jars.packages",
            "org.neo4j:neo4j-connector-apache-spark_2.12:5.4.2_for_spark_3")
    .config("neo4j.url", "neo4j+s://xxxx.databases.neo4j.io")
    .config("neo4j.authentication.type", "basic")
    .config("neo4j.authentication.basic.username", "neo4j")
    .config("neo4j.authentication.basic.password", "password")
    .getOrCreate())
```

### Standalone Spark (Scala)

```scala
val spark = SparkSession.builder
  .appName("neo4j-app")
  .config("spark.jars.packages",
    "org.neo4j:neo4j-connector-apache-spark_2.12:5.4.2_for_spark_3")
  .config("neo4j.url", "neo4j+s://xxxx.databases.neo4j.io")
  .config("neo4j.authentication.type", "basic")
  .config("neo4j.authentication.basic.username", "neo4j")
  .config("neo4j.authentication.basic.password", "password")
  .getOrCreate()
```

### Databricks — Cluster Installation

1. Cluster → **Libraries** → **Install New** → **Maven**
2. Search: `org.neo4j:neo4j-connector-apache-spark_2.12` — match Scala version to runtime
3. Cluster → **Advanced Options** → **Spark** tab — add config:
   ```
   neo4j.url neo4j+s://xxxx.databases.neo4j.io
   neo4j.authentication.type basic
   neo4j.authentication.basic.username {{secrets/neo4j/username}}
   neo4j.authentication.basic.password {{secrets/neo4j/password}}
   ```
4. Use **Single user** access mode (Unity Catalog shared mode not supported)

### Databricks — Secrets (preferred over plaintext)

```python
# Store credentials once:
# databricks secrets create-scope --scope neo4j
# databricks secrets put --scope neo4j --key url
# databricks secrets put --scope neo4j --key username
# databricks secrets put --scope neo4j --key password

neo4j_url  = dbutils.secrets.get(scope="neo4j", key="url")
neo4j_user = dbutils.secrets.get(scope="neo4j", key="username")
neo4j_pass = dbutils.secrets.get(scope="neo4j", key="password")

spark.conf.set("neo4j.url", neo4j_url)
spark.conf.set("neo4j.authentication.type", "basic")
spark.conf.set("neo4j.authentication.basic.username", neo4j_user)
spark.conf.set("neo4j.authentication.basic.password", neo4j_pass)
```

---

## Key Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `neo4j.url` | Bolt/Neo4j URI | — (required) |
| `neo4j.authentication.type` | `none`, `basic`, `kerberos`, `bearer` | `basic` |
| `neo4j.authentication.basic.username` | Username | driver default |
| `neo4j.authentication.basic.password` | Password | driver default |
| `neo4j.authentication.bearer.token` | Bearer token | — |
| `neo4j.database` | Target database | driver default |
| `neo4j.access.mode` | `read` or `write` | `read` |
| `neo4j.encryption.enabled` | TLS (ignored with `+s`/`+ssc` URI) | `false` |

---

## Reading from Neo4j

Three mutually exclusive read modes — use exactly one per `.read()` call.

### Label scan (nodes)

```python
# PySpark
df = (spark.read.format("org.neo4j.spark.DataSource")
    .option("labels", ":Person")
    .load())
df.printSchema()
df.show()
```

```scala
// Scala
val df = spark.read
  .format("org.neo4j.spark.DataSource")
  .option("labels", ":Person")
  .load()
```

Multi-label filter (AND): `.option("labels", ":Person:Employee")`

Result includes `<id>` (internal Neo4j id) and `<labels>` columns.

### Cypher query read

```python
df = (spark.read.format("org.neo4j.spark.DataSource")
    .option("query", "MATCH (p:Person)-[:ACTED_IN]->(m:Movie) RETURN p.name AS actor, m.title AS movie, m.year AS year")
    .load())
```

Use explicit RETURN aliases — they become DataFrame column names. No `SKIP`/`LIMIT` in query (connector handles pagination).

### Relationship scan

```python
df = (spark.read.format("org.neo4j.spark.DataSource")
    .option("relationship", "BOUGHT")
    .option("relationship.source.labels", ":Customer")
    .option("relationship.target.labels", ":Product")
    .load())
```

Result columns: `<rel.id>`, `<rel.type>`, `<source.*>`, `<target.*>`, plus relationship properties.

### Read partition tuning

```python
df = (spark.read.format("org.neo4j.spark.DataSource")
    .option("labels", ":Transaction")
    .option("partitions", "10")        # parallel partitions (default: 1)
    .option("batch.size", "5000")      # rows per partition batch (default: 5000)
    .option("schema.flatten.limit", "100")  # rows sampled for schema inference
    .load())
```

Full read options reference: [references/read-patterns.md](references/read-patterns.md)

---

## Writing to Neo4j

### SaveMode

| SaveMode | Cypher | Requires |
|----------|--------|----------|
| `Append` | `CREATE` | nothing extra |
| `Overwrite` | `MERGE` | `node.keys` (nodes) or `*.node.keys` (rels) |
| `ErrorIfExists` | `CREATE` + error if exists | — |

Always create uniqueness constraints on `node.keys` properties before writing in `Overwrite` mode.

### Write nodes — Append (CREATE)

```python
from pyspark.sql import Row

people = spark.createDataFrame([
    {"name": "Alice", "age": 30},
    {"name": "Bob",   "age": 25},
])

(people.write.format("org.neo4j.spark.DataSource")
    .mode("Append")
    .option("labels", ":Person")
    .save())
```

### Write nodes — Overwrite (MERGE)

```python
(people.write.format("org.neo4j.spark.DataSource")
    .mode("Overwrite")
    .option("labels", ":Person")
    .option("node.keys", "name")       # comma-separated; df_col:node_prop if names differ
    .save())
```

`node.keys` with rename: `.option("node.keys", "df_col:node_property,id:personId")`

### Write nodes — Scala

```scala
import org.apache.spark.sql.SaveMode

peopleDF.write
  .format("org.neo4j.spark.DataSource")
  .mode(SaveMode.Overwrite)
  .option("labels", ":Person")
  .option("node.keys", "name")
  .save()
```

### Write relationships

Use `coalesce(1)` before relationship writes to avoid deadlocks.

```python
rel_df = spark.createDataFrame([
    {"cust_id": "C1", "prod_id": "P1", "qty": 3},
    {"cust_id": "C2", "prod_id": "P2", "qty": 1},
])

(rel_df.coalesce(1)
    .write.format("org.neo4j.spark.DataSource")
    .mode("Append")
    .option("relationship", "BOUGHT")
    .option("relationship.save.strategy", "keys")
    .option("relationship.source.labels", ":Customer")
    .option("relationship.source.save.mode", "Match")          # require existing nodes
    .option("relationship.source.node.keys", "cust_id:id")
    .option("relationship.target.labels", ":Product")
    .option("relationship.target.save.mode", "Match")
    .option("relationship.target.node.keys", "prod_id:id")
    .option("relationship.properties", "qty:quantity")
    .save())
```

`relationship.source.save.mode` / `relationship.target.save.mode`:
- `Match` — find existing nodes (fail if missing)
- `Append` — always CREATE new nodes
- `Overwrite` — MERGE nodes

Full write options reference: [references/write-patterns.md](references/write-patterns.md)

---

## Databricks — Delta Lake → Neo4j Pipeline

```python
# Read from Delta table (Unity Catalog or DBFS)
delta_df = spark.read.format("delta").table("catalog.schema.customers")

# Optional: filter/transform in Spark before writing
filtered = delta_df.filter("active = true").select("customer_id", "name", "region")

# Write to Neo4j
(filtered.write.format("org.neo4j.spark.DataSource")
    .mode("Overwrite")
    .option("labels", ":Customer")
    .option("node.keys", "customer_id")
    .option("batch.size", "20000")
    .save())
```

Pipeline pattern for relationships — load both node sets first, then write edges:

```python
# Step 1: ensure nodes exist
customers_df.write.format("org.neo4j.spark.DataSource").mode("Overwrite") \
    .option("labels", ":Customer").option("node.keys", "customer_id").save()

products_df.write.format("org.neo4j.spark.DataSource").mode("Overwrite") \
    .option("labels", ":Product").option("node.keys", "product_id").save()

# Step 2: write relationships (single partition)
orders_df.coalesce(1).write.format("org.neo4j.spark.DataSource").mode("Append") \
    .option("relationship", "ORDERED") \
    .option("relationship.save.strategy", "keys") \
    .option("relationship.source.labels", ":Customer") \
    .option("relationship.source.save.mode", "Match") \
    .option("relationship.source.node.keys", "customer_id:customer_id") \
    .option("relationship.target.labels", ":Product") \
    .option("relationship.target.save.mode", "Match") \
    .option("relationship.target.node.keys", "product_id:product_id") \
    .save()
```

---

## Write Performance Tuning

| Scenario | Recommendation |
|----------|---------------|
| Node writes (no lock contention) | `repartition(N)` where N ≤ Neo4j CPU cores |
| Relationship writes (lock risk) | `coalesce(1)` — single partition |
| Large datasets | `batch.size` 10000–20000 (adjust to heap) |
| MERGE-heavy loads | Add uniqueness constraint on `node.keys` properties first |

```python
# Aggressive batch — monitor Neo4j heap; OOM risk above 50k
(big_df.repartition(8)
    .write.format("org.neo4j.spark.DataSource")
    .mode("Overwrite")
    .option("labels", ":Event")
    .option("node.keys", "event_id")
    .option("batch.size", "20000")
    .save())
```

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ClassNotFoundException: org.neo4j.spark.DataSource` | JAR not on classpath | Add `spark.jars.packages` or attach library |
| Deadlock on relationship write | Multiple partitions locking nodes | `coalesce(1)` before write |
| Duplicate nodes on Overwrite | No uniqueness constraint on keys | `CREATE CONSTRAINT ON (n:Label) ASSERT n.prop IS UNIQUE` |
| OOM on Neo4j side | `batch.size` too large | Reduce to 5000–10000; check heap |
| Schema all `string` columns | No APOC, schema not sampled | Set `schema.flatten.limit` higher; or use `query` mode with explicit types |
| `Access mode is read` error on write | Session opened in read mode | Remove `neo4j.access.mode` or set to `write` |
| Databricks Shared cluster fails | Unity Catalog shared mode unsupported | Switch to Single User access mode |

---

## Checklist

- [ ] Connector JAR version matches Spark version suffix (`_for_spark_3`)
- [ ] Scala version in artifact matches cluster runtime (2.12 vs 2.13)
- [ ] Credentials in Databricks secrets or env vars — not hardcoded
- [ ] `node.keys` set when using `Overwrite` mode
- [ ] Uniqueness constraint created on `node.keys` properties before MERGE writes
- [ ] `coalesce(1)` applied before relationship writes
- [ ] `batch.size` sized to Neo4j heap (start 5000, tune up)
- [ ] Delta Lake → Neo4j: nodes written before relationships
- [ ] `query` mode: no `SKIP`/`LIMIT` in Cypher (connector paginates internally)
- [ ] Databricks: Single User access mode (not Shared)
