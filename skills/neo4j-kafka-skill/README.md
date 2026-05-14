# neo4j-kafka-skill

## What it covers

Configure and operate the **Neo4j Connector for Kafka** (sink and source) and the **native Neo4j CDC API**.

| Component | Covered |
|---|---|
| Sink: Cypher strategy | ✅ |
| Sink: Pattern strategy | ✅ |
| Sink: CDC strategy (schema + source-id) | ✅ |
| Sink: CUD strategy | ✅ |
| Sink: Exactly-once semantics (EOS) | ✅ |
| Sink: Error handling / DLQ | ✅ |
| Source: CDC-based (Neo4j 5.13+) | ✅ |
| Source: Query-based (any edition) | ✅ |
| Native CDC API (`db.cdc.query`) | ✅ |
| Confluent Cloud managed connector | ✅ |
| Schema Registry (Avro / JSON Schema) | ✅ |
| CDC cursor-loop pattern (Python + Java) | ✅ |

## Not covered

- Cypher query authoring → [neo4j-cypher-skill](../neo4j-cypher-skill/)
- Bulk CSV/JSON file import → [neo4j-import-skill](../neo4j-import-skill/)
- GDS algorithms → [neo4j-gds-skill](../neo4j-gds-skill/)
- Legacy Neo4j Streams plugin (deprecated, use Connector for Kafka ≥ 5.0)

## Install

```bash
# Self-managed Kafka Connect — download JAR from Confluent Hub or neo4j.com
confluent-hub install neo4j/kafka-connect-neo4j:latest

# Or download directly
curl -L https://github.com/neo4j/neo4j-kafka-connector/releases/latest/download/neo4j-kafka-connector.zip \
     -o neo4j-kafka-connector.zip
```

Confluent Cloud: Neo4j Sink is available as a fully managed connector — no JAR install required. Select from the Confluent Cloud connector catalog.

## References

- `references/sink-config.md` — complete sink connector property reference
- `references/cdc-api.md` — CDC procedure details, event schema, cursor-loop examples
- [Neo4j Connector for Kafka docs](https://neo4j.com/docs/kafka/current/)
- [Neo4j CDC docs](https://neo4j.com/docs/cdc/current/)
