---
name: neo4j-kafka-skill
description: Configure and operate the Neo4j Connector for Kafka (sink + source) and the
  native Neo4j CDC API. Covers Cypher/Pattern/CUD sink strategies, CDC-based and query-based
  source, exactly-once semantics, DLQ error handling, Confluent Cloud managed connector,
  schema registry (Avro/JSON), and native db.cdc.query cursor-loop patterns (Neo4j 5.17+
  Enterprise/Aura BC/VDC). Use when streaming Kafka events into Neo4j, streaming Neo4j
  changes to Kafka, or querying Neo4j change events without Kafka. Does NOT handle Cypher
  query authoring — use neo4j-cypher-skill. Does NOT handle bulk CSV/file import — use
  neo4j-import-skill. Does NOT handle GDS algorithms — use neo4j-gds-skill.
allowed-tools: Bash WebFetch
version: 1.0.5
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

- Neo4j Connector for Kafka ≥ 5.5.2 (download versioned assets from [GitHub releases](https://github.com/neo4j/neo4j-kafka-connector/releases) or Confluent Hub; no unversioned "latest" archive) — 5.5.2 processes incoming messages per partition instead of per topic; 5.5.1 forces static labels in generated queries
- Kafka Connect ≥ 3.x or Confluent Platform ≥ 7.x (5.x connector)
- For CDC source: Neo4j 5.13+ Enterprise Edition, AuraDB Business Critical, or AuraDB VDC, with CDC enabled (off by default — see Native CDC API)
- For CDC sink strategies and query source: any Neo4j edition — CDC sink only reads CDC events from Kafka; target needs no CDC
- Java 11+ (5.x connector)

**Connector 6.0** (6.0.0 released 2026-10-15; docs `current` = 6.0): needs Kafka Connect 4.3.0+ (Confluent Platform/Cloud 8.3+) and Java 17+. Sink task fails to start when the EOS offset constraint is missing; `neo4j.eos-offset-auto-constraint=true` creates it. Check [6.0 release notes](https://github.com/neo4j/neo4j-kafka-connector/releases) before upgrading. Stay on 5.x (≥ 5.5.2) for older Connect/Java.

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

Requires: connector ≥ 5.3.0 (Cypher/Pattern/CDC strategies), connector ≥ 5.3.1 (CUD strategy), Kafka broker EOS support, and a NODE KEY constraint (Enterprise) or uniqueness constraint (Community).

Step 1 — Create constraint:
```cypher
CREATE CONSTRAINT kafka_offset_key IF NOT EXISTS
FOR (n:__KafkaOffset)
REQUIRE (n.strategy, n.topic, n.partition) IS NODE KEY;

// Community Edition: NODE KEY unsupported — use composite uniqueness
CREATE CONSTRAINT kafka_offset_key IF NOT EXISTS
FOR (n:__KafkaOffset)
REQUIRE (n.strategy, n.topic, n.partition) IS UNIQUE;
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

DLQ replication factor `3` (default) needs 3+ brokers. Single-broker dev cluster: set `"errors.deadletterqueue.topic.replication.factor": "1"`, else DLQ topic creation fails and first bad record fails the task.

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

`neo4j.start-from` options: `NOW` | `EARLIEST` | `USER_PROVIDED` (custom cursor in `neo4j.start-from.value`). Used only on first run; ignored once Kafka Connect has a stored offset.

Multiple patterns per topic — indexed 0, 1, 2...:
```json
{
  "neo4j.cdc.topic.all-changes.patterns.0.pattern": "(:Person)",
  "neo4j.cdc.topic.all-changes.patterns.1.pattern": "(:Organization)"
}
```

Cursor warning: after DB restore from backup, CDC cursors are invalidated. `neo4j.start-from` alone does not help (stored offset wins) — also set `neo4j.ignore-stored-offset=true`, or recreate connector under a new name.

### Query-Based Source (legacy / any edition)

```json
{
  "neo4j.source-strategy": "QUERY",
  "neo4j.query": "MATCH (p:Person) WHERE p.updatedAt > $lastCheck RETURN p.id AS id, p.name AS name, p.updatedAt AS updatedAt",
  "neo4j.query.streaming-property": "updatedAt",
  "neo4j.query.topic": "person-changes",
  "neo4j.query.poll-interval": "1s",
  "neo4j.query.poll-duration": "5s"
}
```

`$lastCheck` is auto-injected by connector. `neo4j.query.streaming-property` must be returned by the query and should be indexed.

---

## Native CDC API (no Kafka required)

Requires: Neo4j 5.17+ Enterprise, AuraDB BC, or AuraDB VDC (5.13-5.16 used `cdc.*` names; CDC GA since 5.23).

CDC is `OFF` by default everywhere. Enable per database first — no `neo4j.conf` setting exists.

Self-managed:
```cypher
// Mode: DIFF or FULL
ALTER DATABASE neo4j SET OPTION txLogEnrichment "DIFF";
// New database
CREATE DATABASE mydb IF NOT EXISTS OPTIONS {txLogEnrichment: "FULL"};
// Check
SHOW DATABASES YIELD name, options;
```
Aura: admin sets **Edit CDC Mode** (`OFF`/`DIFF`/`FULL`) in instance options. Aura resets CDC to `OFF` on new, cloned, paused/resumed and snapshot-restored instances.

Disabling then re-enabling CDC invalidates all earlier cursors.

Privileges: `db.cdc.query` needs admin, or:
```cypher
GRANT EXECUTE PROCEDURE db.cdc.query ON DBMS TO $role;
GRANT EXECUTE BOOSTED PROCEDURE db.cdc.query ON DBMS TO $role;
GRANT ACCESS ON DATABASE $database TO $role;
```
`db.cdc.current` / `db.cdc.earliest` need only database access and normal execute.

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
    keys:       MAP | LIST,    // node: {Label: [ {keyProp: v} ]}; rel: [ {keyProp: v} ]; empty without key constraints
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
| `Neo.DatabaseError.ChangeDataCapture.Disabled` / CDC not enabled | `txLogEnrichment` is `OFF` (default) / wrong tier | `ALTER DATABASE <db> SET OPTION txLogEnrichment "DIFF"` (Aura: Edit CDC Mode) or upgrade to EE/BC/VDC |
| `Invalid cursor` after DB restore | Backup invalidates cursors | Set `neo4j.start-from` to `NOW`/`EARLIEST` **and** `neo4j.ignore-stored-offset=true` (or recreate connector under new name) |
| `Cannot merge node using null` | Key property missing in message | Validate message schema; add null check in Cypher |
| Messages replayed after restart | No EOS configured | Add `neo4j.eos-offset-label` + NODE KEY constraint (Community: `IS UNIQUE`) |
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

- [ ] CDC availability confirmed (Neo4j 5.13+ EE / Aura BC / VDC) if using CDC source or `db.cdc.*` (5.17+)
- [ ] CDC enabled: `txLogEnrichment` `DIFF`/`FULL` (self-managed) or Edit CDC Mode (Aura) — off by default
- [ ] Uniqueness/NODE KEY constraints created before sink import (MERGE uses them)
- [ ] EOS constraint created if using `neo4j.eos-offset-label`
- [ ] Credentials via secrets provider — not hardcoded in config
- [ ] Cypher sink queries use MERGE (not CREATE) for idempotency
- [ ] `errors.tolerance=all` + DLQ configured for production sink
- [ ] Source: `neo4j.query.streaming-property` indexed
- [ ] Schema registry converters match on both source and sink sides
- [ ] After DB restore: CDC cursor reset (`neo4j.start-from` + `neo4j.ignore-stored-offset=true`)
- [ ] CDC cursor-loop: advance cursor only after successful processing
