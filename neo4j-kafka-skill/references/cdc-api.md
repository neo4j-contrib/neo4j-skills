# Neo4j Native CDC API — Patterns, Event Structure, Cursor Loop

Source: [neo4j.com/docs/cdc/current/](https://neo4j.com/docs/cdc/current/)

## Requirements

| Requirement | Detail |
|---|---|
| Neo4j version | 5.13+ |
| Edition | Enterprise Edition, AuraDB Business Critical, AuraDB VDC |
| Self-managed config | `db.cdc.enabled=true` in `neo4j.conf` |
| Aura | Enabled by default on BC/VDC tiers |

CDC is NOT available on Community Edition or AuraDB Free/Professional.

---

## Procedures

### `db.cdc.current()`

Returns cursor for the last committed transaction. Cursor is **exclusive** — does not include changes from that transaction.

```cypher
CALL db.cdc.current() YIELD id RETURN id AS cursor;
```

Use as starting point for "stream from now forward".

### `db.cdc.earliest()`

Returns cursor for the earliest available change in CDC buffer.

```cypher
CALL db.cdc.earliest() YIELD id RETURN id AS cursor;
```

Use to replay full CDC history.

### `db.cdc.query(from, selectors)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `from` | STRING | `""` (= current) | Starting cursor (exclusive) |
| `selectors` | LIST OF MAP | `[]` (= all) | Filter criteria |

Returns: `id`, `txId`, `seq`, `metadata`, `event`

---

## Selector Reference

Selectors are ANDed within one map, ORed across list items.

```cypher
// AND: node labeled Person AND operation is CREATE
[{select: 'n', labels: ['Person'], operation: 'c'}]

// OR: Person creates OR Organization updates
[
  {select: 'n', labels: ['Person'], operation: 'c'},
  {select: 'n', labels: ['Organization'], operation: 'u'}
]
```

| Field | Values | Scope | Description |
|---|---|---|---|
| `select` | `'e'` (all), `'n'` (nodes), `'r'` (rels) | both | Entity type filter |
| `operation` | `'c'` (create), `'u'` (update), `'d'` (delete) | both | Operation type |
| `labels` | `['Label1', 'Label2']` | nodes | Node must have ALL listed labels |
| `type` | `'REL_TYPE'` | rels | Relationship type |
| `elementId` | element ID string | both | Specific entity by ID |
| `key` | `{prop: value}` | both | Match by key property (requires key constraint) |
| `changesTo` | `['prop1', 'prop2']` | both | ALL listed properties must change (AND) |
| `authenticatedUser` | username string | both | Filter by auth user |
| `executingUser` | username string | both | Filter by executing user |
| `txMetadata` | `{key: value}` | both | Match transaction metadata annotation |

---

## Event Output Schema

### Node Event (eventType = 'n')

```json
{
  "id": "AAAAAAAAAAAA",
  "txId": 12345,
  "seq": 0,
  "metadata": {
    "executingUser": "neo4j",
    "authenticatedUser": "neo4j",
    "captureMode": "DIFF",
    "txStartTime": "2024-01-15T10:00:00.000Z",
    "txCommitTime": "2024-01-15T10:00:00.100Z",
    "txMetadata": {}
  },
  "event": {
    "elementId": "4:abc123:0",
    "eventType": "n",
    "operation": "c",
    "labels": ["Person", "Employee"],
    "keys": {"id": "user-001"},
    "state": {
      "before": null,
      "after": {
        "properties": {
          "id": "user-001",
          "name": "Alice",
          "age": 30
        }
      }
    }
  }
}
```

### Relationship Event (eventType = 'r')

```json
{
  "id": "BBBBBBBBBBBB",
  "txId": 12346,
  "seq": 0,
  "metadata": { "...": "..." },
  "event": {
    "elementId": "5:def456:0",
    "eventType": "r",
    "operation": "u",
    "type": "KNOWS",
    "keys": {},
    "start": {
      "elementId": "4:abc123:0",
      "labels": ["Person"],
      "keys": {"id": "user-001"}
    },
    "end": {
      "elementId": "4:abc123:1",
      "labels": ["Person"],
      "keys": {"id": "user-002"}
    },
    "state": {
      "before": {
        "properties": {"since": 2020}
      },
      "after": {
        "properties": {"since": 2020, "strength": 0.9}
      }
    }
  }
}
```

### State field presence by operation

| operation | `state.before` | `state.after` |
|---|---|---|
| `c` (create) | `null` | populated |
| `u` (update) | populated (changed props only in DIFF mode) | populated |
| `d` (delete) | populated | `null` |

`captureMode: DIFF` — `before` contains only changed properties.
`captureMode: FULL` — `before` contains all properties at time of change.

---

## Cursor Loop Patterns

### Python — continuous poll

```python
import time
from neo4j import GraphDatabase

driver = GraphDatabase.driver("neo4j+s://...", auth=("neo4j", "password"))

def get_current_cursor() -> str:
    records, _, _ = driver.execute_query(
        "CALL db.cdc.current() YIELD id RETURN id",
        database_="neo4j"
    )
    return records[0]["id"]

def poll_changes(cursor: str, selectors: list) -> tuple[list, str]:
    records, _, _ = driver.execute_query(
        "CALL db.cdc.query($cursor, $selectors) "
        "YIELD id, txId, seq, metadata, event "
        "RETURN id, txId, seq, metadata, event ORDER BY txId, seq",
        cursor=cursor, selectors=selectors,
        database_="neo4j"
    )
    events = [r.data() for r in records]
    next_cursor = events[-1]["id"] if events else cursor
    return events, next_cursor

# Bootstrap cursor
cursor = get_current_cursor()

selectors = [
    {"select": "n", "labels": ["Person"], "operation": "c"},
    {"select": "n", "labels": ["Person"], "operation": "u"}
]

while True:
    events, cursor = poll_changes(cursor, selectors)
    for e in events:
        op = e["event"]["operation"]
        if op == "c":
            print("CREATED:", e["event"]["state"]["after"]["properties"])
        elif op == "u":
            before = e["event"]["state"]["before"]["properties"]
            after = e["event"]["state"]["after"]["properties"]
            print("UPDATED:", before, "->", after)
    time.sleep(1)
```

### Java — cursor loop

```java
try (var driver = GraphDatabase.driver("neo4j+s://...", AuthTokens.basic("neo4j", "password"));
     var session = driver.session(SessionConfig.forDatabase("neo4j"))) {

    // Bootstrap
    var cursor = session.run("CALL db.cdc.current() YIELD id RETURN id")
                        .single().get("id").asString();

    var selectors = List.of(Map.of("select", "n", "labels", List.of("Person")));

    while (true) {
        var result = session.run(
            "CALL db.cdc.query($cursor, $selectors) " +
            "YIELD id, txId, seq, event RETURN id, txId, seq, event ORDER BY txId, seq",
            Map.of("cursor", cursor, "selectors", selectors)
        ).list();

        for (var record : result) {
            var event = record.get("event").asMap();
            System.out.println(record.get("id").asString() + ": " + event.get("operation"));
        }
        if (!result.isEmpty()) {
            cursor = result.get(result.size() - 1).get("id").asString();
        }
        Thread.sleep(1000);
    }
}
```

### Cypher — manual step-through (REPL / debug)

```cypher
// Step 1: Get start cursor
CALL db.cdc.current() YIELD id RETURN id;
// → "AAAAAAAAAGc="

// Step 2: Query changes (paste cursor from step 1)
CALL db.cdc.query("AAAAAAAAAGc=", [{select: 'n', labels: ['Person']}])
YIELD id, txId, seq, event
RETURN id, txId, seq,
       event.operation AS op,
       event.state.after.properties AS after
ORDER BY txId, seq;

// Step 3: Use last returned id as next cursor
```

---

## Transaction Metadata — Annotate for Filtering

Tag transactions to filter CDC events by source system:

```cypher
// Annotate transaction with metadata
CALL tx.setMetaData({source: 'crm', batchId: '2024-01-batch-001'})
MERGE (p:Person {id: $id}) SET p += $props
```

Then filter in CDC:
```cypher
CALL db.cdc.query($cursor, [
  {select: 'n', txMetadata: {source: 'crm'}}
]) YIELD id, event
RETURN id, event;
```

---

## Source Connector Config Reference

| Property | Type | Default | Description |
|---|---|---|---|
| `connector.class` | STRING | — | `org.neo4j.connectors.kafka.source.Neo4jConnector` |
| `neo4j.source-strategy` | STRING | — | `CDC` or `QUERY` |
| `neo4j.start-from` | STRING | `NOW` | `NOW` \| `EARLIEST` \| cursor string |
| `neo4j.cdc.poll-interval` | DURATION | `1s` | How often to check for new changes |
| `neo4j.cdc.poll-duration` | DURATION | `5s` | Max duration per poll call |
| `neo4j.cdc.topic.<T>.patterns.<N>.pattern` | STRING | — | Entity pattern for topic T, index N |
| `neo4j.cdc.topic.<T>.patterns.<N>.operation` | STRING | — | `CREATE` \| `UPDATE` \| `DELETE` |
| `neo4j.cdc.topic.<T>.patterns.<N>.changesTo` | STRING | — | Comma-separated property names |
| `neo4j.cdc.topic.<T>.key-strategy` | STRING | — | Key generation for Kafka message key |
| `neo4j.query` | STRING | — | Cypher with `$lastCheck` param (QUERY strategy) |
| `neo4j.query.streaming-property` | STRING | — | Return column used as cursor |
| `neo4j.query.topic` | STRING | — | Target Kafka topic (QUERY strategy) |
| `neo4j.query.polling-interval` | DURATION | `5s` | Poll frequency (QUERY strategy) |
| `neo4j.query.polling-duration` | DURATION | `10s` | Poll duration (QUERY strategy) |
