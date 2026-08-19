# neo4j-spark-skill

Skill for reading and writing Neo4j data using the Neo4j Connector for Apache Spark, including Databricks, EMR, and standalone Spark environments.

**Covers:**
- SparkSession setup with Maven artifact `org.neo4j.connectors:spark` (6.x) or `org.neo4j:neo4j-connector-apache-spark` (5.x)
- DataFrame reads: label scan, Cypher query, relationship scan
- DataFrame writes: node CREATE/MERGE, relationship write with source/target mapping
- `node.keys` for Overwrite (MERGE) mode
- Partition and batch tuning (`partitions`, `batch.size`, `schema.flatten.limit`)
- Databricks cluster installation, secrets management, Unity Catalog notes
- Delta Lake → Neo4j ingestion pipeline pattern
- PySpark and Scala code examples

**Version / Compatibility:**
- Connector: `org.neo4j.connectors:spark:6.0.0-s_2.13` (Spark 4.0/4.1, Scala 2.13, Java 17+) or `5.5.0_for_spark_3` (Spark 3.4/3.5, Scala 2.12 or 2.13)
- Databricks Runtime: 17.3 LTS (6.0), 14.3–16.4 LTS (5.x)
- Neo4j: 4.4 (5.x connector), 5.x, 2025.x, 2026.x

**Not covered:**
- Cypher query authoring → `neo4j-cypher-skill`
- Neo4j Python bolt driver → `neo4j-driver-python-skill`
- GDS graph algorithms → `neo4j-gds-skill`
- Spring Boot + Neo4j → `neo4j-spring-data-skill`

**Install:**
```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-spark-skill
```

Or paste this link into your coding assistant:
https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-spark-skill
