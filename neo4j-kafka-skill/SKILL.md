---
name: neo4j-kafka-skill
description: Configure and operate the Neo4j Connector for Kafka (sink + source) and the
  native Neo4j CDC API. Covers Cypher/Pattern/CUD sink strategies, CDC-based and query-based
  source, exactly-once semantics, DLQ error handling, Confluent Cloud managed connector,
  schema registry (Avro/JSON), and native db.cdc.query cursor-loop patterns (Neo4j 5.13+
  Enterprise/Aura BC/VDC). Use when streaming Kafka events into Neo4j, streaming Neo4j
  changes to Kafka, or querying Neo4j change events without Kafka. Does NOT handle Cypher
  query authoring — use neo4j-cypher-skill. Does NOT handle bulk CSV/file import — use
  neo4j-import-skill. Does NOT handle GDS algorithms — use neo4j-gds-skill.
allowed-tools: Bash WebFetch
version: 1.0.0
---

# Neo4j Kafka Skill

## When to Use

- Writing Kafka events into Neo4j (sink connector — Cypher, Pattern, CDC, CUD strategies)
- Streaming Neo4j changes to Kafka topics (source connector — CDC or query-based)
- Querying Neo4j change events natively without Kafka (`db.cdc.query`)
- Configuring Confluent Cloud managed Neo4j sink connector
- Setting up schema registry (Avro/JSON Schema) for typed Kafka messages
- Enabling exactly-once semantics or dead-letter queue on sink

## When NOT to Use

- **Cypher query authoring** → `neo4j-cypher-skill`
- **Bulk CSV/JSON file import** → `neo4j-import-skill`
- **GDS algorithms** → `neo4j-gds-skill`
- **Live app write patterns** → `neo4j-cypher-skill`

---

## Decision Table — Which connector strategy?

| Use case | Strategy |
|---|---|
| Custom transformation of Kafka payload → graph | Sink: **Cypher** |
| Mirror another Neo4j CDC source | Sink: **CDC** (schema or source-id sub-strategy) |
| Map Kafka JSON fields to graph nodes/rels with no code | Sink: **Pattern** |
| Consume pre-formatted CUD JSON messages | Sink: **CUD** |
| Stream all Neo4j changes to Kafka (real-time) | Source: **CDC** (Neo4j 5.13+ EE/Aura BC/VDC) |
| Stream specific query results on a schedule | Source: **Query** |
| Consume CDC events in-process, no Kafka | **Native CDC API** (`db.cdc.query`) |

---

## Prerequisites

- Neo4j Connector for Kafka ≥ 5.0 (download from [neo4j.com/labs/kafka](https://neo4j.com/labs/kafka/) or Confluent Hub)
- Kafka Connect ≥ 3.x or Confluent Platform ≥ 7.x
- For CDC source/sink: Neo4j 5.13+ Enterprise Edition, AuraDB Business Critical, or AuraDB VDC
- For query source: any Neo4j edition
- Java 11+

---

## Core Connection Config (all connectors)

```json
{
  "neo4j.uri": "neo4j+s://your-instance.databases.neo4j.io:7687",
  "neo4j.authentication.type": "BASIC",
  "neo4j.authentication.basic.username": "neo4j",
  "neo4j.authentication.basic.password": "${file:/opt/secrets.properties:neo4j.password}",
  "neo4j.database": "neo4j"
}
```

Authentication types: `BASIC` | `BEARER` | `KERBEROS` | `CUSTOM` | `NONE`

Never hardcode passwords — use Kafka Connect secrets provider (`${file:...}` or `${env:...}`).

---

## Sink Connector

### Strategy 1 — Cypher

Connector auto-prepends `UNWIND $events AS __value` — write query using `__value`:

```json
{
  "connector.class": "org.neo4j.connectors.kafka.sink.Neo4jConnector",
  "topics": "person-creates,person-updates",
  "neo4j.uri": "neo4j+s://...",
  "neo4j.authentication.type": "BASIC",
  "neo4j.authentication.basic.username": "neo4j",
  "neo4j.authentication.basic.password": "secret",
  "neo4j.cypher.topic.person-creates":
    "MERGE (p:Person {id: __value.id}) SET p += __value.properties",
  "neo4j.cypher.topic.person-updates":
    "MATCH (p:Person {id: __value.id}) SET p += __value.properties",
  "neo4j.cypher.bind-value-as": "__value",
  "neo4j.cypher.bind-key-as": "__key",
  "neo4j.cypher.bind-header-as": "__header"
}
```

MERGE pattern — idempotent upsert:
```cypher
MERGE (p:Person {id: __value.id})
ON CREATE SET p.createdAt = datetime(), p += __value.properties
ON MATCH  SET p.updatedAt = datetime(), p += __value.properties
```

### Strategy 2 — Pattern

No Cypher needed — map message fields to graph via pattern syntax:

```json
{
  "neo4j.pattern.topic.users": "(:User{!userId, name, email})",
  "neo4j.pattern.topic.friendships":
    "(:User{!userId: from.userId})-[:KNOWS{since}]->(:User{!userId: to.userId})"
}
```

Pattern rules:
- `!prop` = key property (used for MERGE)
- `prop: field.path` = map from nested message field
- `*` = map all message fields
- `-prop` = exclude property (cannot mix with inclusions)

### Strategy 3 — CDC (mirror another Neo4j)

```json
{
  "neo4j.cdc.schema.topics": "neo4j-cdc-events"
}
```

Or with source-id tracking (stores elementId as property):
```json
{
  "neo4j.cdc.source-id.topics": "neo4j-cdc-events",
  "neo4j.cdc.source-id.label-name": "SourceEvent",
  "neo4j.cdc.source-id.property-name": "sourceId"
}
```

### Exactly-Once Semantics (EOS)

Requires: connector ≥ 5.3.0, Kafka broker EOS support, and a NODE KEY constraint.

Step 1 — Create constraint:
```cypher
CREATE CONSTRAINT kafka_offset_key IF NOT EXISTS
FOR (n:__KafkaOffset)
REQUIRE (n.strategy, n.topic, n.partition) IS NODE KEY;
```

Step 2 — Add to connector config:
```json
{
  "neo4j.eos-offset-label": "__KafkaOffset"
}
```

Without EOS: connector provides at-least-once — write idempotent Cypher (MERGE, not CREATE).

### Error Handling / DLQ

```json
{
  "errors.tolerance": "all",
  "errors.log.enable": "true",
  "errors.log.include.messages": "true",
  "errors.deadletterqueue.topic.name": "neo4j-dlq",
  "errors.deadletterqueue.context.headers.enable": "true",
  "errors.deadletterqueue.topic.replication.factor": "3"
}
```

`errors.tolerance=none` (default) — stops on first error. Use `all` + DLQ for production.

---

## Source Connector

### CDC-Based Source (recommended, Neo4j 5.13+)

```json
{
  "connector.class": "org.neo4j.connectors.kafka.source.Neo4jConnector",
  "neo4j.uri": "neo4j+s://...",
  "neo4j.authentication.type": "BASIC",
  "neo4j.authentication.basic.username": "neo4j",
  "neo4j.authentication.basic.password": "secret",
  "neo4j.source-strategy": "CDC",
  "neo4j.start-from": "NOW",
  "neo4j.cdc.poll-interval": "1s",
  "neo4j.cdc.poll-duration": "5s",
  "neo4j.cdc.topic.person-creates.patterns.0.pattern": "(:Person)",
  "neo4j.cdc.topic.person-creates.patterns.0.operation": "CREATE",
  "neo4j.cdc.topic.person-updates.patterns.0.pattern": "(:Person)",
  "neo4j.cdc.topic.person-updates.patterns.0.operation": "UPDATE",
  "neo4j.cdc.topic.person-deletes.patterns.0.pattern": "(:Person)",
  "neo4j.cdc.topic.person-deletes.patterns.0.operation": "DELETE"
}
```

`neo4j.start-from` options: `NOW` | `EARLIEST` | a specific cursor string

Multiple patterns per topic — indexed 0, 1, 2...:
```json
{
  "neo4j.cdc.topic.all-changes.patterns.0.pattern": "(:Person)",
  "neo4j.cdc.topic.all-changes.patterns.1.pattern": "(:Organization)"
}
```

Cursor warning: after DB restore from backup, CDC cursors are invalidated. Reconfigure `neo4j.start-from`.

### Query-Based Source (legacy / any edition)

```json
{
  "neo4j.source-strategy": "QUERY",
  "neo4j.query": "MATCH (p:Person) WHERE p.updatedAt > $lastCheck RETURN p.id AS id, p.name AS name, p.updatedAt AS updatedAt",
  "neo4j.query.streaming-property": "updatedAt",
  "neo4j.query.topic": "person-changes",
  "neo4j.query.polling-interval": "5s",
  "neo4j.query.polling-duration": "10s"
}
```

`$lastCheck` is auto-injected by connector. `neo4j.query.streaming-property` must be returned by the query and should be indexed.

---

## Native CDC API (no Kafka required)

Requires: Neo4j 5.13+ Enterprise, AuraDB BC, or AuraDB VDC.

Enable CDC first (self-managed — set in neo4j.conf):
```
db.cdc.enabled=true
```
On Aura: enabled by default on eligible tiers.

### Cursor Bootstrap

```cypher
// Get cursor for "right now" — start tracking from this point forward
CALL db.cdc.current() YIELD id RETURN id AS cursor;

// Get earliest available cursor (replay from history start)
CALL db.cdc.earliest() YIELD id RETURN id AS cursor;
```

Cursors are exclusive: `db.cdc.current()` does NOT include the transaction it points to.

### Query Changes

```cypher
// All changes since cursor
CALL db.cdc.query($cursor, []) YIELD id, txId, seq, metadata, event
RETURN id, txId, seq, metadata, event
ORDER BY txId, seq;
```

Filtered — nodes with label Person, CREATE only:
```cypher
CALL db.cdc.query($cursor, [
  {select: 'n', labels: ['Person'], operation: 'c'}
]) YIELD id, txId, seq, event
RETURN id, event.state.after.properties AS newProps
ORDER BY txId, seq;
```

Filtered — specific relationship type with property change tracking:
```cypher
CALL db.cdc.query($cursor, [
  {select: 'r', type: 'KNOWS', changesTo: ['since', 'strength']}
]) YIELD id, txId, seq, event
RETURN id, event.state.before AS before, event.state.after AS after;
```

### Selector Reference

| Field | Values | Applies to |
|---|---|---|
| `select` | `'e'` (all), `'n'` (nodes), `'r'` (rels) | both |
| `operation` | `'c'` (create), `'u'` (update), `'d'` (delete) | both |
| `labels` | `['Label1','Label2']` (node must have ALL) | nodes |
| `type` | `'REL_TYPE'` | relationships |
| `elementId` | specific element ID string | both |
| `key` | `{propName: value}` (requires key constraint) | both |
| `changesTo` | `['prop1','prop2']` (AND — all must change) | both |
| `authenticatedUser` | username string | both |
| `executingUser` | username string | both |
| `txMetadata` | `{key: value}` | both |

### Event Structure

```
{
  id:       STRING,           // cursor for this event (use as next $cursor)
  txId:     INTEGER,          // transaction ID
  seq:      INTEGER,          // ordering within transaction
  metadata: {
    executingUser:     STRING,
    authenticatedUser: STRING,
    captureMode:       STRING,  // "DIFF" or "FULL"
    txStartTime:       DATETIME,
    txCommitTime:      DATETIME,
    txMetadata:        MAP
  },
  event: {
    elementId:  STRING,
    eventType:  STRING,         // "n" or "r"
    operation:  STRING,         // "c", "u", "d"
    labels:     [STRING],       // nodes only
    type:       STRING,         // relationships only
    keys:       MAP,
    state: {
      before: { properties: MAP },  // null on CREATE
      after:  { properties: MAP }   // null on DELETE
    }
  }
}
```

### Cursor-Loop Pattern (Python)

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("neo4j+s://...", auth=("neo4j", "password"))

def poll_changes(cursor: str, selectors: list) -> tuple[list, str]:
    records, _, _ = driver.execute_query(
        "CALL db.cdc.query($cursor, $selectors) YIELD id, txId, seq, event "
        "RETURN id, txId, seq, event ORDER BY txId, seq",
        cursor=cursor, selectors=selectors,
        database_="neo4j"
    )
    events = [r.data() for r in records]
    # Advance cursor to last event id; keep current if no events
    next_cursor = events[-1]["id"] if events else cursor
    return events, next_cursor

# Bootstrap
with driver.session(database="neo4j") as s:
    cursor = s.run("CALL db.cdc.current() YIELD id RETURN id").single()["id"]

selectors = [{"select": "n", "labels": ["Person"]}]

import time
while True:
    events, cursor = poll_changes(cursor, selectors)
    for e in events:
        print(e["event"]["operation"], e["event"]["elementId"])
    time.sleep(1)
```

---

## Confluent Cloud Managed Connector

Confluent Cloud hosts the Neo4j Sink connector as a fully managed service (no JAR upload needed).

Config differences vs self-managed:
- No `connector.class` field — selected in UI/API
- Credentials via Confluent Cloud secret manager or direct JSON
- Private endpoints supported (AWS PrivateLink, Azure Private Link, GCP PSC)
- Managed upgrades — pin connector version explicitly if needed

Required Confluent Cloud fields:
```json
{
  "kafka.auth.mode": "KAFKA_API_KEY",
  "kafka.api.key": "...",
  "kafka.api.secret": "...",
  "input.data.format": "JSON",
  "neo4j.uri": "neo4j+s://...",
  "neo4j.authentication.type": "BASIC",
  "neo4j.authentication.basic.username": "neo4j",
  "neo4j.authentication.basic.password": "..."
}
```

One strategy per topic — cannot mix Cypher and Pattern on same topic.

---

## Schema Registry (Avro / JSON Schema)

Source connector always generates messages with schema support — must configure converters:

```json
{
  "key.converter": "io.confluent.connect.avro.AvroConverter",
  "key.converter.schema.registry.url": "https://your-schema-registry",
  "value.converter": "io.confluent.connect.avro.AvroConverter",
  "value.converter.schema.registry.url": "https://your-schema-registry"
}
```

For JSON Schema:
```json
{
  "value.converter": "io.confluent.connect.json.JsonSchemaConverter",
  "value.converter.schema.registry.url": "https://..."
}
```

Sink converter must match source — Avro sink cannot consume JSON schema source messages.

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `CDC is not enabled` | `db.cdc.enabled` not set / wrong tier | Enable in neo4j.conf or upgrade to EE/BC/VDC |
| `Invalid cursor` after DB restore | Backup invalidates cursors | Reset `neo4j.start-from` to `NOW` or `EARLIEST` |
| `Cannot merge node using null` | Key property missing in message | Validate message schema; add null check in Cypher |
| Messages replayed after restart | No EOS configured | Add `neo4j.eos-offset-label` + NODE KEY constraint |
| Connector stops on bad message | `errors.tolerance=none` (default) | Set `errors.tolerance=all` + DLQ topic |
| `SchemaException` on sink | Converter mismatch source/sink | Match key/value converters on both ends |
| Empty events from `db.cdc.query` | Cursor points to current | Use `db.cdc.earliest()` to replay; wait for new txns |

---

## References

- [Full connector config reference](references/sink-config.md) — all neo4j.* properties, defaults, types
- [CDC API patterns](references/cdc-api.md) — cursor loop, selector examples, event structure detail
- [Neo4j Connector for Kafka docs](https://neo4j.com/docs/kafka/current/)
- [CDC docs](https://neo4j.com/docs/cdc/current/)

---

## Checklist

- [ ] CDC availability confirmed (Neo4j 5.13+ EE / Aura BC / VDC) if using CDC source or sink
- [ ] Uniqueness/NODE KEY constraints created before sink import (MERGE uses them)
- [ ] EOS constraint created if using `neo4j.eos-offset-label`
- [ ] Credentials via secrets provider — not hardcoded in config
- [ ] Cypher sink queries use MERGE (not CREATE) for idempotency
- [ ] `errors.tolerance=all` + DLQ configured for production sink
- [ ] Source: `neo4j.query.streaming-property` indexed
- [ ] Schema registry converters match on both source and sink sides
- [ ] After DB restore: CDC cursor reconfigured (`neo4j.start-from`)
- [ ] CDC cursor-loop: advance cursor only after successful processing
