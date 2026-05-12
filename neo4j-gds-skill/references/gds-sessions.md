# Aura Graph Analytics GDS Sessions

Use Python client first. Use Cypher API only when user explicitly wants AuraDB-side Cypher operations or cannot use Aura API credentials.

## Session Types

| Type | Source | Projection | Write-back |
|---|---|---|---|
| Attached | AuraDB | Remote projection from AuraDB | Built in |
| Self-managed | Self-managed Neo4j DBMS | Remote projection from Neo4j URI | Built in |
| Standalone | Non-Neo4j data | `gds.graph.construct` | Stream and persist manually |

Prefer Attached sessions for AuraDB GDS workloads. They avoid installing GDS plugin in the database and allocate ephemeral compute for analytics.

## Create Attached Session

```python
import os
from datetime import timedelta
from graphdatascience.session import AuraAPICredentials, DbmsConnectionInfo, GdsSessions, SessionMemory

sessions = GdsSessions(
    api_credentials=AuraAPICredentials(
        os.environ["CLIENT_ID"],
        os.environ["CLIENT_SECRET"],
        os.environ.get("PROJECT_ID"),
    )
)

gds = sessions.get_or_create(
    session_name="product-recs",
    memory=SessionMemory.m_8GB,
    ttl=timedelta(hours=2),
    db_connection=DbmsConnectionInfo(
        aura_instance_id=os.environ["AURA_INSTANCEID"],
        database=os.environ["NEO4J_DATABASE"]
        username=os.environ["NEO4J_USERNAME"],
        password=os.environ["NEO4J_PASSWORD"],
    ),
)
gds.verify_connectivity()
```

If user belongs to multiple Aura projects, provide `PROJECT_ID`.
Do not print `CLIENT_SECRET` or database password.

## Estimate Session Size

```python
from graphdatascience.session import AlgorithmCategory

memory = sessions.estimate(
    node_count=1_000_000,
    relationship_count=5_000_000,
    algorithm_categories=[
        AlgorithmCategory.CENTRALITY,
        AlgorithmCategory.NODE_EMBEDDING,
    ],
    node_label_count=1,
    node_property_count=2,
    relationship_property_count=1,
)
```

Use estimate before `get_or_create` when graph size is known. Pick the next supported memory size if estimate falls between sizes.

## Remote Projection

```python
G, result = gds.v2.graph.project(
    graph_name="product-graph",
    query="""
    CYPHER runtime=parallel
    MATCH (source:Product)-[r:BOUGHT_TOGETHER]->(target:Product)
    RETURN gds.graph.project.remote(source, target, {
      sourceNodeLabels: labels(source),
      targetNodeLabels: labels(target),
      sourceNodeProperties: source { .price },
      targetNodeProperties: target { .price },
      relationshipType: type(r),
      relationshipProperties: r { .weight }
    })
    """,
    undirected_relationship_types=["BOUGHT_TOGETHER"],
    concurrency=8,
    batch_size=25_000,
)
```

Rules:
- Use `gds.graph.project.remote(...)` inside query.
- Pass `graph_name` to `gds.graph.project(...)`; do not put graph name in remote function.
- Use `undirected_relationship_types=[...]` parameter for remote projection orientation.
- Native projection and legacy Cypher projection are not supported in Aura Graph Analytics.
- Standalone sessions cannot use remote projection; use `gds.graph.construct`.
- only specify nodeLabels, relationshipType and properties if actually needed later by any algorithms
- prefer using the gds.v2 endpoints if available

## Run Algorithms

```python
gds.v2.page_rank.mutate(G, mutate_property="pagerank")
gds.fastRP.mutate(
    G,
    featureProperties=["pagerank"],
    embeddingDimension=128,
    randomSeed=42,
    mutateProperty="embedding",
)
df = gds.graph.nodeProperties.stream(
    G,
    db_node_properties=["name"],
    node_properties=["pagerank", "embedding"],
gds.v2.fast_rp.mutate(
    G,
    feature_properties=["pagerank"],
    embedding_dimension=128,
    random_seed=42,
    mutate_property="embedding",
)
df = gds.v2.graph.node_properties.stream(
    G,
    db_node_properties=["name"],
    node_properties=["pagerank", "embedding"],
```

Algorithm calls use same Python-client shape as plugin calls after projection.

Limitations:
- Check the gds.v2 result for availability of endpoints
- Check current API reference before using alpha/beta procedures.

## Remote Write-back

Attached and self-managed sessions:

```python
gds.v2.graph.node_properties.write(G, "embedding")

gds.v2.wcc.write(
    G,
    write_property="componentId",
    arrow_configuration={"batchSize": 25_000},
)

Standalone sessions: stream results and persist through target-system client.

Before write-back:
- Run `stream` or `stats` first when available.
- Confirm target property/relationship does not overwrite needed data.
- Tune `concurrency` and `arrowConfiguration.batchSize` for large writes.
- Ask for user confirmation before writing back to the database. 

## Query Source Database

```python
gds.run_cypher("MATCH (n:Product) RETURN count(n) AS products")
```

`gds.run_cypher(...)` runs on source Neo4j DB, not inside GDS Session. Use it for source validation and reading write-back results.

## Delete Session

```python
G.drop()
gds.delete()

# or:
sessions.delete(session_name="product-recs")
```

Default idle TTL: 1 hour. Maximum lifetime: 7 days. Expired sessions cannot run workloads. Delete sessions when done to stop cost.

## Cypher API Notes

Use only for AuraDB plans that support Aura Graph Analytics Cypher API.

```cypher
CYPHER runtime=parallel
MATCH (source)
OPTIONAL MATCH (source)-->(target)
RETURN gds.graph.project(
  'g',
  source,
  target,
  {},
  { memory: '2GB' }
)
```

Existing explicit session:

```cypher
CYPHER runtime=parallel
MATCH (source)
OPTIONAL MATCH (source)-->(target)
RETURN gds.graph.project(
  'g',
  source,
  target,
  {},
  { sessionId: '00000000-11111111' }
)
```

Session management:

```cypher
CALL gds.session.getOrCreate('test-session', '2GB', duration({minutes: 30}))
YIELD id, name, status
RETURN id, name, status

CALL gds.session.list()
YIELD id, name, status, memory
RETURN id, name, status, memory
```

Implicit Cypher API sessions are deleted when all projected graphs in the session are dropped.

## Checklist

- [ ] Session type selected: Attached / Self-managed / Standalone
- [ ] Aura API credentials read from env; values never printed
- [ ] Session memory estimated or chosen intentionally
- [ ] `gds.verify_connectivity()` passed
- [ ] Remote projection uses `gds.graph.project.remote(...)`
- [ ] Algorithm limitation checked for alpha/beta/model-publish operations
- [ ] Write-back path selected: built-in or manual stream/persist
- [ ] Graph dropped and session deleted
