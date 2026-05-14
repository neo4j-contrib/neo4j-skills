---
name: neo4j-snowflake-graph-analytics-skill
description: Run Neo4j Graph Analytics algorithms (PageRank, Louvain, WCC, Dijkstra, KNN,
  Node2Vec, FastRP, GraphSAGE) directly inside Snowflake without moving data. Use when
  running graph algorithms against Snowflake tables via the Neo4j Snowflake Native App
  ("GDS Snowflake", "graph algorithms in Snowflake", "Neo4j Graph Analytics").
  Covers installation, privilege setup, project-compute-write pattern, and SQL CALL syntax.
  Does NOT cover Cypher or Neo4j DBMS queries — use neo4j-cypher-skill.
  Does NOT cover Aura Graph Analytics — use neo4j-aura-graph-analytics-skill.
  Does NOT cover self-managed GDS — use neo4j-gds-skill.
version: 1.0.0
allowed-tools: Bash WebFetch
---

Snowflake Native App — graph algorithm power inside Snowflake. Data stays in Snowflake; project into a graph, run algorithms via SQL `CALL`, results written back to Snowflake tables.

**Docs:** https://neo4j.com/docs/snowflake-graph-analytics/current/

---

## When to Use
- Running graph algorithms / GDS in Snowflake
- Data in Snowflake tables
- On-demand / pipeline workloads — ephemeral sessions, pay per session-minute
- Full isolation from the live database during analytics

## When NOT to Use
- **Aura Pro with embedded GDS plugin** → `neo4j-gds-skill`
- **Aura Graph Analytics** → `neo4j-aura-graph-analytics-skill`
- **Self-managed Neo4j with embedded GDS plugin** → `neo4j-gds-skill`
- **Writing Cypher queries** → `neo4j-cypher-skill`

## Key Concepts

### Project → Compute → Write

Every algorithm run follows three steps:

1. **Project** — specify node/relationship tables; app builds in-memory graph
2. **Compute** — run algorithm with config parameters
3. **Write** — results written back to a Snowflake table

### Required Table Columns

| Table type | Required columns | Optional columns |
|---|---|---|
| Node table | `nodeId` (Number) | Any additional columns become node properties |
| Relationship table | `sourceNodeId` (Number), `targetNodeId` (Number) | Any additional columns become relationship properties |

If your tables use different column names, create a view aliasing to `nodeId`, `sourceNodeId`, `targetNodeId`.

### Graph Orientation

When projecting relationships, you can set `orientation`:
- `NATURAL` (default) — directed, source → target
- `UNDIRECTED` — treated as bidirectional
- `REVERSE` — direction flipped

---

## Installation

1. Go to the [Snowflake Marketplace](https://app.snowflake.com/marketplace/listing/GZTDZH40CN/neo4j-neo4j-graph-analytics)
2. Install **Neo4j Graph Analytics** (default app name: `Neo4j_Graph_Analytics`)
3. During install, **enable Event sharing** when prompted
4. After install, go to **Data Products → Apps → Neo4j Graph Analytics → Privileges → Grant**
5. Grant `CREATE COMPUTE POOL` and `CREATE WAREHOUSE` privileges, then click **Activate**

---

## Privilege Setup (run once per database/schema)

```sql
-- Step 1: Use ACCOUNTADMIN to set up roles and grants
USE ROLE ACCOUNTADMIN;

-- Create a consumer role for users of the application
CREATE ROLE IF NOT EXISTS MY_CONSUMER_ROLE;
GRANT APPLICATION ROLE Neo4j_Graph_Analytics.app_user TO ROLE MY_CONSUMER_ROLE;
SET MY_USER = (SELECT CURRENT_USER());
GRANT ROLE MY_CONSUMER_ROLE TO USER IDENTIFIER($MY_USER);

-- Step 2: Create a database role and grant it to the app
USE DATABASE MY_DATABASE;
CREATE DATABASE ROLE IF NOT EXISTS MY_DB_ROLE;
GRANT USAGE ON DATABASE MY_DATABASE TO DATABASE ROLE MY_DB_ROLE;
GRANT USAGE ON SCHEMA MY_DATABASE.MY_SCHEMA TO DATABASE ROLE MY_DB_ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA MY_DATABASE.MY_SCHEMA TO DATABASE ROLE MY_DB_ROLE;
GRANT SELECT ON ALL VIEWS IN SCHEMA MY_DATABASE.MY_SCHEMA TO DATABASE ROLE MY_DB_ROLE;
GRANT SELECT ON FUTURE TABLES IN SCHEMA MY_DATABASE.MY_SCHEMA TO DATABASE ROLE MY_DB_ROLE;
GRANT SELECT ON FUTURE VIEWS IN SCHEMA MY_DATABASE.MY_SCHEMA TO DATABASE ROLE MY_DB_ROLE;
GRANT CREATE TABLE ON SCHEMA MY_DATABASE.MY_SCHEMA TO DATABASE ROLE MY_DB_ROLE;
GRANT DATABASE ROLE MY_DB_ROLE TO APPLICATION Neo4j_Graph_Analytics;

-- Step 3: Grant the consumer role access to output tables
GRANT USAGE ON DATABASE MY_DATABASE TO ROLE MY_CONSUMER_ROLE;
GRANT USAGE ON SCHEMA MY_DATABASE.MY_SCHEMA TO ROLE MY_CONSUMER_ROLE;
GRANT SELECT ON FUTURE TABLES IN SCHEMA MY_DATABASE.MY_SCHEMA TO ROLE MY_CONSUMER_ROLE;

-- Step 4: Switch to the consumer role to run algorithms
USE ROLE MY_CONSUMER_ROLE;
```

> Replace `P2P`, `PUBLIC`, `GRAPH_USER_ROLE`, and `GRAPH_DB_ROLE`
> with your actual names throughout.

---

## Running an Algorithm — Full Example

```sql
-- Optional: set default database to avoid fully-qualified names
USE DATABASE Neo4j_Graph_Analytics;
USE ROLE GRAPH_USER_ROLE;

-- Call WCC (Weakly Connected Components)
CALL Neo4j_Graph_Analytics.graph.wcc('CPU_X64_XS', {
    'defaultTablePrefix': 'P2P.PUBLIC',
    'project': {
        'nodeTables': ['USER_VW'],
        'relationshipTables': {
            'AGG_TRANSACTIONS_VW': {
                'sourceTable': 'P2P.PUBLIC.USER_VW',
                'targetTable': 'P2P.PUBLIC.USER_VW',
                'orientation': 'NATURAL'
            }
        }
    },
    'compute': { 'consecutiveIds': true },
    'write': [{
        'nodeLabel': 'NODES',
        'outputTable': 'USER_COMPONENTS'
    }]
});

-- Inspect results
SELECT * FROM P2P.PUBLIC.USER_COMPONENTS;
```

First argument is the compute pool size:

| Pool | Use |
|---|---|
| `CPU_X64_XS` | Dev / small graphs |
| `CPU_X64_S/M/L` | Progressively larger |
| `HIGHMEM_X64_S/M/L` | Large graphs, lower CPU need |
| `GPU_NV_S/XS`, `GPU_GCP_NV_L4_1_24G` | Compute-intensive (GraphSAGE); GPU not available in all regions |

See [Estimating Jobs](https://neo4j.com/docs/snowflake-graph-analytics/current/jobs/estimation/) to choose size.
---

## Available Algorithms

### Community Detection
| Algorithm | Procedure | Use case |
|---|---|---|
| Weakly Connected Components | `graph.wcc` | Find disconnected subgraphs |
| Louvain | `graph.louvain` | Community detection, modularity optimisation |
| Leiden | `graph.leiden` | Improved community detection (more stable than Louvain) |
| K-Means Clustering | `graph.kmeans` | Cluster nodes by node properties |
| Triangle Count | `graph.triangle_count` | Measure local clustering / detect dense subgraphs |

### Centrality
| Algorithm | Procedure | Use case |
|---|---|---|
| PageRank | `graph.pagerank` | Rank nodes by influence |
| Article Rank | `graph.article_rank` | PageRank variant, discounts high-degree neighbours |
| Betweenness Centrality | `graph.betweenness` | Find bridge nodes in a network |
| Degree Centrality | `graph.degree` | Count direct connections per node |

### Pathfinding
| Algorithm | Procedure | Use case |
|---|---|---|
| Dijkstra Source-Target | `graph.dijkstra_source_target` | Shortest path between two nodes |
| Dijkstra Single-Source | `graph.dijkstra_single_source` | Shortest paths from one node to all others |
| Delta-Stepping SSSP | `graph.delta_stepping` | Faster parallel shortest paths |
| Breadth First Search | `graph.bfs` | BFS traversal from a source node |
| Yen's K-Shortest Paths | `graph.yens` | Top-K shortest paths between two nodes |
| Max Flow | `graph.max_flow` | Maximum flow through a network |
| FastPath | `graph.fastpath` | Fast approximate shortest paths |

### Similarity
| Algorithm | Procedure | Use case |
|---|---|---|
| Node Similarity | `graph.node_similarity` | Find similar nodes based on shared neighbours |
| Filtered Node Similarity | `graph.filtered_node_similarity` | Node similarity with source/target filters |
| K-Nearest Neighbors | `graph.knn` | Find K most similar nodes |
| Filtered KNN | `graph.filtered_knn` | KNN with source/target filters |

### Node Embeddings / ML
| Algorithm | Procedure | Use case |
|---|---|---|
| Fast Random Projection (FastRP) | `graph.fastrp` | Fast node embeddings |
| Node2Vec | `graph.node2vec` | Random-walk-based node embeddings |
| HashGNN | `graph.hashgnn` | GNN-inspired embeddings without training |
| GraphSAGE (train) | `graph.graphsage_train` | Train inductive node embeddings |
| GraphSAGE (predict) | `graph.graphsage_predict` | Predict with a trained GraphSAGE model |
| Node Classification (train) | `graph.node_classification_train` | Supervised node label prediction |
| Node Classification (predict) | `graph.node_classification_predict` | Apply trained node classifier |

---

## Projection Configuration Reference

```json
{
  "project": {
    "nodeTables": [
      "DB.SCHEMA.TABLE_A",
      "DB.SCHEMA.TABLE_B"
    ],
    "relationshipTables": {
      "DB.SCHEMA.REL_TABLE": {
        "sourceTable": "DB.SCHEMA.TABLE_A",
        "targetTable": "DB.SCHEMA.TABLE_B",
        "orientation": "NATURAL"
      }
    }
  }
}
```
- `defaultTablePrefix` — use when all tables are in the same schema
- Multiple node/relationship tables supported — each maps to a different label/type
- Extra columns become node/relationship properties (e.g. `weight` column for weighted paths)


---

## Write Configuration Reference

```json
{
  "write": [
    {
      "nodeLabel": "TABLE_A",
      "outputTable": "DB.SCHEMA.OUTPUT_TABLE",
      "nodeProperty": "score"
    }
  ]
}
```

- `nodeLabel` — node table name without schema prefix
- `outputTable` — created or overwritten
- `nodeProperty` (optional) — which computed property to write if algorithm produces multiple

For relationship results (KNN, Node Similarity):

```json
{
  "write": [
    {
      "relationshipType": "SIMILAR",
      "outputTable": "DB.SCHEMA.SIMILARITY_OUTPUT"
    }
  ]
}
```

---

## Common Patterns

### Chaining Algorithms

Results write to tables — feed one algorithm's output into the next. `FUTURE TABLES` grant (done in setup) lets the app read tables it just created.

```sql
-- Step 1: Run FastRP to generate embeddings
CALL Neo4j_Graph_Analytics.graph.fastrp('CPU_X64_XS', { ... });

-- Step 2: Run KNN on the embedding output
CALL Neo4j_Graph_Analytics.graph.knn('CPU_X64_XS', { ... });
```

### Using Views Instead of Renaming Columns

Create views with required column names and supported data types. Convert categorical data to numerical scores.
```sql
CREATE VIEW MY_SCHEMA.NODES_VIEW AS
  SELECT user_id AS nodeId, name, age
  FROM MY_SCHEMA.USERS;

CREATE VIEW MY_SCHEMA.RELS_VIEW AS
  SELECT from_user AS sourceNodeId, to_user AS targetNodeId, weight
  FROM MY_SCHEMA.CONNECTIONS;
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Insufficient privileges` | Check the app has `SELECT` on your tables and `CREATE TABLE` on the schema |
| `Column nodeId not found` | Your table is missing the required column — create a view that aliases it |
| `Compute pool not available` | The pool may still be starting up; wait a minute and retry |
| Algorithm returns no results | Check your node/relationship tables are not empty and projections are correct |

Full troubleshooting guide: https://neo4j.com/docs/snowflake-graph-analytics/current/troubleshooting/

---

## Further Reading

- [Running Jobs](https://neo4j.com/docs/snowflake-graph-analytics/current/jobs/)
- [Scaling Out Jobs](https://neo4j.com/docs/snowflake-graph-analytics/current/jobs/scale-out/)
- [Estimating Jobs](https://neo4j.com/docs/snowflake-graph-analytics/current/jobs/estimation/)
- [All Algorithms](https://neo4j.com/docs/snowflake-graph-analytics/current/algorithms/)
- [Administration](https://neo4j.com/docs/snowflake-graph-analytics/current/administration/)
- [Integration with Cortex Agent](https://neo4j.com/docs/snowflake-graph-analytics/current/agents/)
- [Basket Analysis Example on TPC-H Data](https://github.com/neo4j-product-examples/snowflake-graph-analytics/tree/main/basket-analysis)
