# AGA Full Workflow Examples

## AuraDB — PageRank + FastRP → Write Back

```python
from graphdatascience.session import (
    AuraAPICredentials, GdsSessions, DbmsConnectionInfo,
    SessionMemory, AlgorithmCategory
)
from datetime import timedelta
import os

# 1. Auth
sessions = GdsSessions(api_credentials=AuraAPICredentials.from_env())

# 2. Size
memory = sessions.estimate(
    node_count=500_000,
    relationship_count=2_000_000,
    algorithm_categories=[AlgorithmCategory.CENTRALITY, AlgorithmCategory.NODE_EMBEDDING],
)

# 3. Session
gds = sessions.get_or_create(
    session_name="prod-analysis",
    memory=memory,
    db_connection=DbmsConnectionInfo.from_env(),
    ttl=timedelta(hours=4),
)
gds.verify_connectivity()

# 4. Project
G, _ = gds.graph.project(
    "social",
    """
    CALL () {
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[r:KNOWS]->(p2:Person)
        RETURN p AS source, r AS rel, p2 AS target,
               p {.score} AS sourceNodeProperties,
               p2 {.score} AS targetNodeProperties
    }
    RETURN gds.graph.project.remote(source, target, {
        sourceNodeLabels: labels(source),
        targetNodeLabels: labels(target),
        sourceNodeProperties: sourceNodeProperties,
        targetNodeProperties: targetNodeProperties,
        relationshipType: type(rel)
    })
    """,
)

# 5. Analyse
gds.pageRank.mutate(G, mutateProperty="pagerank")
gds.fastRP.mutate(G, embeddingDimension=128, mutateProperty="embedding",
                  featureProperties=["pagerank"], randomSeed=42)

# 6. Write back
gds.graph.nodeProperties.write(G, ["pagerank", "embedding"])

# 7. Cleanup
sessions.delete(session_name="prod-analysis")
```

## Standalone — Pandas DataFrame → Community Detection

```python
import pandas as pd
from graphdatascience.session import AuraAPICredentials, GdsSessions, SessionMemory, CloudLocation
from datetime import timedelta

sessions = GdsSessions(api_credentials=AuraAPICredentials.from_env())

gds = sessions.get_or_create(
    session_name="csv-analysis",
    memory=SessionMemory.m_4GB,
    ttl=timedelta(hours=1),
    cloud_location=CloudLocation("gcp", "europe-west1"),
)

nodes = pd.read_csv("nodes.csv")   # required: nodeId (int), labels (str)
edges = pd.read_csv("edges.csv")   # required: sourceNodeId, targetNodeId, relationshipType

G = gds.graph.construct("my-graph", nodes, edges)

gds.louvain.mutate(G, mutateProperty="community")

result = gds.graph.nodeProperties.stream(G, ["community"], separate_property_columns=True)
output = result.merge(nodes[["nodeId", "name"]], how="left")
print(output.sort_values("community"))

gds.delete()
```

## Multiple Node/Relationship DataFrames

```python
G = gds.graph.construct("multi-graph", [nodes1, nodes2], [rels1, rels2])
```

## Spark Integration

```python
pip install "graphdatascience>=1.18" pyspark

arrow_client = gds.arrow_client()
# Use arrow_client with mapInArrow for large Spark DataFrames
```

See [Spark Tutorial Notebook](https://github.com/neo4j/graph-data-science-client/blob/main/examples/graph-analytics-serverless-spark.ipynb).
