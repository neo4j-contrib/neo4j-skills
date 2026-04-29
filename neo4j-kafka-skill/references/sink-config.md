# Neo4j Kafka Sink Connector — Full Config Reference

Source: [neo4j.com/docs/kafka/current/](https://neo4j.com/docs/kafka/current/)

## Common / Connection Properties

| Property | Type | Default | Description |
|---|---|---|---|
| `connector.class` | STRING | — | `org.neo4j.connectors.kafka.sink.Neo4jConnector` |
| `topics` | STRING | — | Comma-separated list of Kafka topics to consume |
| `neo4j.uri` | STRING | — | Connection URI (`neo4j://`, `neo4j+s://`, `bolt://`, `bolt+s://`) |
| `neo4j.database` | STRING | `neo4j` | Target database name |
| `neo4j.authentication.type` | STRING | `BASIC` | `BASIC` \| `BEARER` \| `KERBEROS` \| `CUSTOM` \| `NONE` |
| `neo4j.authentication.basic.username` | STRING | — | Username (BASIC auth) |
| `neo4j.authentication.basic.password` | PASSWORD | — | Password (BASIC auth) |
| `neo4j.authentication.bearer.token` | PASSWORD | — | Bearer token |
| `neo4j.authentication.kerberos.ticket` | PASSWORD | — | Kerberos base64 ticket |
| `neo4j.connection-timeout` | DURATION | `30s` | Max time to establish connection |
| `neo4j.max-connection-pool-size` | INT | `100` | Connection pool max size |
| `neo4j.connection-acquisition-timeout` | DURATION | `60s` | Max wait for pool connection |
| `neo4j.batch-size` | INT | `1000` | Messages per write batch |
| `neo4j.batch-timeout` | DURATION | `0s` | Max wait to fill batch (0=no wait) |

## Cypher Strategy Properties

| Property | Type | Default | Description |
|---|---|---|---|
| `neo4j.cypher.topic.<TOPIC>` | STRING | — | Cypher query for named topic |
| `neo4j.cypher.bind-value-as` | STRING | `__value` | Variable name for message value |
| `neo4j.cypher.bind-key-as` | STRING | `""` | Variable name for message key (empty=disabled) |
| `neo4j.cypher.bind-header-as` | STRING | `""` | Variable name for message headers |
| `neo4j.cypher.bind-value-as-event` | BOOLEAN | `false` | Legacy compat flag (pre-5.1 behavior) |

Query is auto-wrapped: `UNWIND $events AS <bind-value-as>` — query body uses the bound variable.

## Pattern Strategy Properties

| Property | Type | Default | Description |
|---|---|---|---|
| `neo4j.pattern.topic.<TOPIC>` | STRING | — | Pattern expression for named topic |

Pattern syntax:
- Node: `(:Label{!keyProp, otherProp: field.path})`
- Relationship: `(:Label{!id})-[:TYPE{prop}]->(:Label{!id})`
- `!prop` = MERGE key; `*` = all fields; `-prop` = exclude; `prop: path` = map from nested field

## CDC Sink Strategy Properties

| Property | Type | Default | Description |
|---|---|---|---|
| `neo4j.cdc.schema.topics` | STRING | — | Topics for CDC schema sub-strategy |
| `neo4j.cdc.source-id.topics` | STRING | — | Topics for CDC source-id sub-strategy |
| `neo4j.cdc.source-id.label-name` | STRING | `SourceEvent` | Label added to merged nodes |
| `neo4j.cdc.source-id.property-name` | STRING | `sourceId` | Property storing source elementId |

## CUD Strategy Properties

| Property | Type | Default | Description |
|---|---|---|---|
| `neo4j.cud.topics` | STRING | — | Topics with CUD-formatted messages |

CUD message format: `{"op": "create"/"update"/"delete", "labels": [...], "properties": {...}, "ids": {...}}`

## Exactly-Once Semantics

| Property | Type | Default | Description |
|---|---|---|---|
| `neo4j.eos-offset-label` | STRING | — | Label for offset tracking node (enables EOS when set) |

Required constraint before enabling:
```cypher
CREATE CONSTRAINT kafka_offset_key IF NOT EXISTS
FOR (n:__KafkaOffset)
REQUIRE (n.strategy, n.topic, n.partition) IS NODE KEY;
```

Default (no EOS): at-least-once — ensure Cypher is idempotent.

## Error Handling

| Property | Type | Default | Description |
|---|---|---|---|
| `errors.tolerance` | STRING | `none` | `none` (stop on error) \| `all` (skip + continue) |
| `errors.log.enable` | BOOLEAN | `false` | Log error details |
| `errors.log.include.messages` | BOOLEAN | `false` | Include topic/partition/offset in logs |
| `errors.deadletterqueue.topic.name` | STRING | `""` | DLQ topic (empty = no DLQ) |
| `errors.deadletterqueue.context.headers.enable` | BOOLEAN | `false` | Add `__connect.errors.*` headers to DLQ |
| `errors.deadletterqueue.topic.replication.factor` | INT | `3` | DLQ topic replication (use `1` for single-node) |

## Schema / Converter Properties

Set on the connector config (not neo4j-specific — standard Kafka Connect):

```json
{
  "key.converter": "org.apache.kafka.connect.json.JsonConverter",
  "key.converter.schemas.enable": "false",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter",
  "value.converter.schemas.enable": "false"
}
```

For Avro with schema registry:
```json
{
  "value.converter": "io.confluent.connect.avro.AvroConverter",
  "value.converter.schema.registry.url": "https://schema-registry:8081"
}
```

## Complete Sink Example — Production Cypher with EOS + DLQ

```json
{
  "name": "neo4j-person-sink",
  "connector.class": "org.neo4j.connectors.kafka.sink.Neo4jConnector",
  "topics": "person-events",
  "neo4j.uri": "neo4j+s://instance.databases.neo4j.io:7687",
  "neo4j.authentication.type": "BASIC",
  "neo4j.authentication.basic.username": "neo4j",
  "neo4j.authentication.basic.password": "${file:/secrets/neo4j.properties:password}",
  "neo4j.database": "neo4j",
  "neo4j.batch-size": "1000",
  "neo4j.cypher.bind-value-as": "__value",
  "neo4j.cypher.topic.person-events":
    "MERGE (p:Person {id: __value.id}) SET p += __value",
  "neo4j.eos-offset-label": "__KafkaOffset",
  "errors.tolerance": "all",
  "errors.log.enable": "true",
  "errors.log.include.messages": "true",
  "errors.deadletterqueue.topic.name": "neo4j-person-dlq",
  "errors.deadletterqueue.context.headers.enable": "true",
  "errors.deadletterqueue.topic.replication.factor": "3",
  "key.converter": "org.apache.kafka.connect.json.JsonConverter",
  "key.converter.schemas.enable": "false",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter",
  "value.converter.schemas.enable": "false"
}
```
