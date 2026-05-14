# neo4j-spark-skill

Skill for reading and writing Neo4j data using the Neo4j Connector for Apache Spark, including Databricks, EMR, and standalone Spark environments.

**Covers:**
- SparkSession setup with Maven artifact `org.neo4j:neo4j-connector-apache-spark`
- DataFrame reads: label scan, Cypher query, relationship scan
- DataFrame writes: node CREATE/MERGE, relationship write with source/target mapping
- `node.keys` for Overwrite (MERGE) mode
- Partition and batch tuning (`partitions`, `batch.size`, `schema.flatten.limit`)
- Databricks cluster installation, secrets management, Unity Catalog notes
- Delta Lake → Neo4j ingestion pipeline pattern
- PySpark and Scala code examples

**Version / Compatibility:**
- Connector: `5.4.2_for_spark_3` (Scala 2.12 or 2.13)
- Spark: 3.3, 3.4, 3.5
- Databricks Runtime: 12.2, 13.3, 14.3 LTS
- Neo4j: 4.4, 5.x, 2025.x

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
