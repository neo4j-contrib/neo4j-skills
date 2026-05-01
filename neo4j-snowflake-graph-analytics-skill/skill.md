---
name: neo4j-snowflake-graph-analytics-skill
description: >
  Use this skill when working with Neo4j Graph Analytics for Snowflake.
  Triggers on any mention of "Neo4j Graph Analytics", "Snowflake graph",
  "graph algorithms in Snowflake", "GDS Snowflake", or requests to run
  graph algorithms (PageRank, Louvain, WCC, Dijkstra, KNN, Node2Vec, etc.)
  against Snowflake tables. Covers installation, privilege setup, the
  project-compute-write pattern, SQL procedure syntax, and all available
  algorithms. Do NOT use for standard Neo4j DBMS or Cypher queries against
  a Neo4j database — use the neo4j-cypher-skill for those.
version: 1.0.0
allowed-tools: Bash WebFetch
---

# Neo4j Graph Analytics for Snowflake

Neo4j Graph Analytics is a **Snowflake Native Application** that brings graph
algorithm power directly into Snowflake. Data stays in Snowflake — you project
it into a graph, run algorithms via SQL `CALL` procedures, and results are
written back to Snowflake tables.

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

### The Project → Compute → Write Pattern

Every algorithm run follows three steps:

1. **Project** — specify which Snowflake tables are nodes and which are
   relationships (edges). The app reads them and builds an in-memory graph.
2. **Compute** — run the algorithm with its configuration parameters.
3. **Write** — results are written back to a Snowflake table you specify.

### Required Table Columns

| Table type | Required columns | Optional columns |
|---|---|---|
| Node table | `nodeId` (Number) | Any additional columns become node properties |
| Relationship table | `sourceNodeId` (Number), `targetNodeId` (Number) | Any additional columns become relationship properties |

If your existing tables use different column names, **create a view** on top of
them that aliases to `nodeId`, `sourceNodeId`, `targetNodeId`.

### Graph Orientation

When projecting relationships you can set `orientation`:
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

> Replace `MY_DATABASE`, `MY_SCHEMA`, `MY_CONSUMER_ROLE`, and `MY_DB_ROLE`
> with your actual names throughout.

---

## Running an Algorithm — Full Example

```sql
-- Optional: set default database to avoid fully-qualified names
USE DATABASE Neo4j_Graph_Analytics;
USE ROLE MY_CONSUMER_ROLE;

-- Call WCC (Weakly Connected Components)
CALL Neo4j_Graph_Analytics.graph.wcc('CPU_X64_XS', {
    'project': {
        'nodeTables': ['MY_DATABASE.MY_SCHEMA.NODES'],
        'relationshipTables': {
            'MY_DATABASE.MY_SCHEMA.RELATIONSHIPS': {
                'sourceTable': 'MY_DATABASE.MY_SCHEMA.NODES',
                'targetTable': 'MY_DATABASE.MY_SCHEMA.NODES',
                'orientation': 'NATURAL'
            }
        }
    },
    'compute': { 'consecutiveIds': true },
    'write': [{
        'nodeLabel': 'NODES',
        'outputTable': 'MY_DATABASE.MY_SCHEMA.NODES_COMPONENTS'
    }]
});

-- Inspect results
SELECT * FROM MY_DATABASE.MY_SCHEMA.NODES_COMPONENTS;
```

The first argument to `CALL` is the **compute pool size**. Common values:
- `CPU_X64_XS` — smallest, suitable for development and small graphs
- `CPU_X64_S`, `CPU_X64_M`, `CPU_X64_L` — progressively larger
- `HIGHMEM_X64_S`, `HIGHMEM_X64_M`, `HIGHMEM_X64_L` - for when you need larger graphs but dont always require more CPU
- `GPU_NV_S`, `GPU_NV_XS`, `GPU_GCP_NV_L4_1_24G` - for algorithms that are compute intensive e.g. GraphSAGE and are capable of running on the python runtime
- Note, not all regions offer all compute pools especially GPU types
- See [Estimating Jobs](https://neo4j.com/docs/snowflake-graph-analytics/current/jobs/estimation/) to choose the right size
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

- Multiple node tables are supported — each maps to a different node label.
- Multiple relationship tables are supported — each maps to a different relationship type.
- Node and relationship properties (extra columns) are automatically available
  to algorithms that use them (e.g. weighted shortest path uses a `weight` column).

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

- `nodeLabel` must match the node table name (without schema prefix).
- `outputTable` will be **created or overwritten**.
- `nodeProperty` (optional) — specify which computed property to write if the
  algorithm produces multiple properties.

For algorithms that produce **relationship** results (KNN, Node Similarity):

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

Because results are written to tables, you can feed one algorithm's output into
the next. Grant `FUTURE TABLES` permissions (as shown in the setup above) so
the app can read tables it just created.

```sql
-- Step 1: Run FastRP to generate embeddings
CALL Neo4j_Graph_Analytics.graph.fastrp('CPU_X64_XS', { ... });

-- Step 2: Run KNN on the embedding output
CALL Neo4j_Graph_Analytics.graph.knn('CPU_X64_XS', { ... });
```

### Using Views Instead of Renaming Columns

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