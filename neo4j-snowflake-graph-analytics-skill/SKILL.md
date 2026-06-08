---
name: neo4j-snowflake-graph-analytics-skill
description: Run Neo4j Graph Analytics algorithms (PageRank, Louvain, WCC, Dijkstra, KNN,
  Node2Vec, FastRP, GraphSAGE) directly inside Snowflake without moving data. Use when
  running graph algorithms against Snowflake tables via the Neo4j Snowflake Native App
  ("GDS Snowflake", "graph algorithms in Snowflake", "Neo4j Graph Analytics").
  Covers the explore → prepare projection views → project-compute-write flow,
  the strict view/column type rules the graph engine requires, and exact SQL CALL syntax.
  Does NOT cover Cypher or Neo4j DBMS queries — use neo4j-cypher-skill.
  Does NOT cover Aura Graph Analytics — use neo4j-aura-graph-analytics-skill.
  Does NOT cover self-managed GDS — use neo4j-gds-skill.
version: 1.1.0
allowed-tools: Bash WebFetch
---

Snowflake Native App — graph algorithm power inside Snowflake. Data stays in Snowflake; project into a graph, run algorithms via SQL `CALL`, results written back to Snowflake tables.

**Docs:** https://neo4j.com/docs/snowflake-graph-analytics/current/

---

## When to Use
- Running graph algorithms / GDS in Snowflake
- Data already lives in Snowflake tables
- On-demand / pipeline workloads — ephemeral sessions, pay per session-minute
- Full isolation from the live database during analytics

## When NOT to Use
- **Aura Pro with embedded GDS plugin** → `neo4j-gds-skill`
- **Aura Graph Analytics** → `neo4j-aura-graph-analytics-skill`
- **Self-managed Neo4j with embedded GDS plugin** → `neo4j-gds-skill`
- **Writing Cypher queries** → `neo4j-cypher-skill`

---

## The End-to-End Flow

This is the flow that works. Don't jump straight to a `CALL` — most failures come from skipping the data-preparation step.

1. **Explore** the source data — inspect table DDLs to learn columns and types.
2. **Prepare projection views** — create node/relationship views that expose the required key columns and cast every property to a supported type (see the strict rules below). This is the step that matters most.
3. **Project → Compute → Write** — run the algorithm with a single `CALL`, assembling the `project`, `compute`, and `write` config.
4. **Inspect & look up names** — join numeric results back to the source table to get human-readable labels.

---

## Step 1 — Explore the Source Data

Look at the table definitions before designing the graph:

```sql
SELECT GET_DDL('TABLE', 'MY_DATABASE.MY_SCHEMA.MY_TABLE');
-- or inspect columns/types:
SELECT COLUMN_NAME, DATA_TYPE
FROM MY_DATABASE.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'MY_SCHEMA' AND TABLE_NAME = 'MY_TABLE';
```

Decide which tables are **nodes** and which represent **relationships** (edges) between them.

---

## Step 2 — Prepare Projection Views (the important part)

The graph engine is strict about column names and types. **Snowflake views inherit the source column type by default**, so you MUST add explicit `CAST`s — never `SELECT col` without one for a property column.

Create views that reshape your tables into the node/relationship format:

```sql
CREATE OR REPLACE VIEW MY_DATABASE.MY_SCHEMA.MY_NODES_VW AS
SELECT ... FROM MY_DATABASE.MY_SCHEMA.MY_TABLE;
```

### Node views

- **Key column:** expose the primary key as `NODEID`. It must be `BIGINT` or `STRING`. Always alias **and** cast explicitly:
  `SOURCE_COL::BIGINT AS NODEID` or `SOURCE_COL::STRING AS NODEID`.
- **Allowed node property types (exactly):** `BIGINT`, `DOUBLE`, `ARRAY`, `VECTOR(FLOAT, n)`. Anything else must be cast to one of these or dropped.
- **Composite keys:** concatenate parts with `'++'`.
- **Naming:** `<table>_NODES_VW`.

### Source-type → view-type casting rules

Apply these when projecting columns from your tables (keep the original column name unless renaming):

| Source type | Action |
|---|---|
| Whole-number numerics (`INT`, `INTEGER`, `BIGINT`, `SMALLINT`, `TINYINT`, `BYTEINT`, `NUMBER(p,0)`) | `CAST(col AS BIGINT) AS col` |
| Fractional numerics (`FLOAT`, `DOUBLE`, `REAL`, `DECIMAL(p,s>0)`, `NUMBER(p,s>0)`) | `CAST(col AS DOUBLE) AS col` |
| `ARRAY` of numbers | keep as `ARRAY` (except GraphSAGE — see below). Not allowed on relationship views. |
| `VECTOR(FLOAT, n)` | keep as-is. Not allowed on relationship views. |
| `BOOLEAN` | **drop by default**. Opt-in only: `IFF(col, 1, 0)::BIGINT AS col` |
| `DATE`, `TIME`, `TIMESTAMP*` | **drop by default**. Opt-in only: `DATE_PART('EPOCH_SECOND', col)::BIGINT AS col` (tell the user the unit) |
| `VARCHAR`, `CHAR`, `TEXT`, `STRING` | **drop** — can't be a graph property. To read results by name, join output back to the source table on the key (see Step 4) |
| `VARIANT`, `OBJECT`, `GEOGRAPHY`, `GEOMETRY`, `BINARY` | **drop** — not supported as graph properties |

**Lowest-common-denominator policy:** by default include only safe columns (numeric → BIGINT/DOUBLE, ARRAY, VECTOR). Booleans and time-like columns require explicit opt-in. When you drop columns, briefly tell the user which and why, so they can ask for them back.

### Relationship views

- **Key columns:** expose `SOURCENODEID` and `TARGETNODEID`, cast with the same rules as `NODEID`
  (`SOURCE_COL::BIGINT AS SOURCENODEID`, etc.). Every value must match an existing `NODEID` in a node view.
- **Allowed relationship property types (narrower):** `BIGINT`, `DOUBLE`, `INT` only. **No `ARRAY`, no `VECTOR`.** (The docs describe relationship properties as `FLOAT`; the engine accepts these whole/fractional numeric casts and treats them as weights — keep them numeric.)
- **Naming:** `<table>_RELATIONSHIPS_VW`.

Example node + relationship views:

```sql
CREATE OR REPLACE VIEW MY_DATABASE.MY_SCHEMA.USER_NODES_VW AS
SELECT user_id::BIGINT AS NODEID,
       CAST(age AS BIGINT)        AS age,
       CAST(balance AS DOUBLE)    AS balance
FROM MY_DATABASE.MY_SCHEMA.USERS;

CREATE OR REPLACE VIEW MY_DATABASE.MY_SCHEMA.TRANSFERS_RELATIONSHIPS_VW AS
SELECT from_user::BIGINT AS SOURCENODEID,
       to_user::BIGINT   AS TARGETNODEID,
       CAST(amount AS DOUBLE) AS amount
FROM MY_DATABASE.MY_SCHEMA.TRANSFERS;
```

> The required logical column names are `nodeId` / `sourceNodeId` / `targetNodeId` — Snowflake folds unquoted identifiers to uppercase, so `NODEID` etc. match. Casting explicitly is what matters.

---

## Step 3 — Project → Compute → Write

Every run is a single `CALL` whose first argument is the compute pool and second is a JSON config with three parts. Note JSON uses **single quotes** in Snowflake SQL.

> **App name:** `Neo4j_Graph_Analytics` is only the *default* installation name. If the app was installed under a different name, replace it everywhere — in the procedure call (`<APP>.graph.<algo>`), the `USE DATABASE <APP>` statement, and the privilege grants below. Check with `SHOW APPLICATIONS;`.

```sql
USE ROLE MY_CONSUMER_ROLE;

CALL Neo4j_Graph_Analytics.graph.wcc('CPU_X64_XS', {
    'defaultTablePrefix': 'MY_DATABASE.MY_SCHEMA',
    'project': {
        'nodeTables': ['USER_NODES_VW'],
        'relationshipTables': {
            'TRANSFERS_RELATIONSHIPS_VW': {
                'sourceTable': 'USER_NODES_VW',
                'targetTable': 'USER_NODES_VW',
                'orientation': 'NATURAL'
            }
        }
    },
    'compute': { 'consecutiveIds': true },
    'write': [{
        'nodeLabel': 'USER_NODES_VW',
        'outputTable': 'result_wcc_user_communities'
    }]
});

SELECT * FROM MY_DATABASE.MY_SCHEMA.result_wcc_user_communities;
```

### Config parts

- **`defaultTablePrefix`** — set to the database + schema where your views and output tables live (`DB.SCHEMA`); lets you reference them by short name.
- **`project`** — `nodeTables` (array; each maps to a label) and `relationshipTables` (map; each key maps to a type, with `sourceTable`/`targetTable`/`orientation`).
- **`compute`** — algorithm parameters. Omit any parameter whose value would be null.
- **`write`** — a **list** of write targets. `nodeLabel` (or `sourceLabel`/`targetLabel`) is the **table/view name** of the nodes being written. For relationship results use `relationshipType`.

### Orientation

Set `orientation` per relationship table in `relationshipTables`:

- `NATURAL` (default) — directed, source → target (as stored in the table).
- `UNDIRECTED` — treated as bidirectional (each relationship is included in both directions).
- `REVERSE` — direction flipped, target → source.

Choose based on the algorithm:
- **`UNDIRECTED`** — community detection that treats edges symmetrically: WCC, Louvain, Leiden, Label Propagation. **Triangle Count requires `UNDIRECTED`.**
- **`NATURAL`** — directed-flow and ranking: PageRank, Article Rank, Dijkstra and the other pathfinding algorithms, Max Flow. **Node Similarity** expects a *bipartite* graph (two disjoint node sets) projected `NATURAL`; use `REVERSE` to compare the other node set instead.
- **KNN ignores relationships entirely** — similarity comes from node properties, so orientation has no effect on it (and K-Means likewise uses only node properties).

### Compute pools (first `CALL` argument)

| Pool | Use |
|---|---|
| `CPU_X64_XS` | Default — dev / small graphs |
| `CPU_X64_S/M/L` | Progressively larger |
| `HIGHMEM_X64_S/M/L` | Large graphs, lower CPU need |
| `GPU_NV_XS`, `GPU_NV_S`, `GPU_GCP_NV_L4_1_24G` | GraphSAGE / GPU work (availability varies by region) |

Prefer `CPU_X64_XS` unless the user asks otherwise or GraphSAGE makes a GPU pool appropriate. See [Estimating Jobs](https://neo4j.com/docs/snowflake-graph-analytics/current/jobs/estimation/).

### Result table naming

Name output tables `result_<algotag>_<short_description>`, underscores only, no spaces/special chars (e.g. `result_louvain_customer_segments`). When writing multiple node labels, use a distinct table per label.

---

## Step 4 — Inspect & Look Up Names

What the algorithm produces depends on its type — check the algorithm's **write** config:

- **Node-property results** (centrality, community detection, k-means, embeddings, FastPath) — a table keyed by `NODEID`.
- **Relationship results** (Node Similarity, KNN, Dijkstra & other pathfinding, Max Flow) — a table keyed by `SOURCENODEID` / `TARGETNODEID`. BFS and other heterogeneous writes also add `SOURCELABEL` / `TARGETLABEL`, with the node IDs stored as strings.
- **A model** (GraphSAGE training) — no output table; it writes to the model catalog. Use the model later for prediction, which then produces a node-property table.

VARCHAR labels were dropped during projection, so join the result back to the **source table** on the key column(s) to get readable names. For node-property results, join on `NODEID`:

```sql
SELECT u.name, u.country, r.score
FROM MY_DATABASE.MY_SCHEMA.result_page_rank_influence r
JOIN MY_DATABASE.MY_SCHEMA.USERS u
  ON r.NODEID = u.user_id
ORDER BY r.score DESC
LIMIT 10;
```

For relationship results, join the source table twice — once on `SOURCENODEID` and once on `TARGETNODEID`.

---
 
## Available Algorithms

Procedure = `Neo4j_Graph_Analytics.graph.<name>`. Names below are exact.

For complete algorithm compute/write parameter reference, see [references/algorithms.md](references/algorithms.md).

### Community Detection
| Algorithm | Procedure | Use case |
|---|---|---|
| Weakly Connected Components | `wcc` | Find disconnected subgraphs |
| Louvain | `louvain` | Community detection (modularity) |
| Leiden | `leiden` | Community detection, more stable than Louvain |
| Label Propagation | `label_propagation` | Fast community detection by label spreading |
| K-Means | `kmeans` | Cluster nodes by node properties |
| Triangle Count | `triangle_count` | Local clustering / dense subgraphs |

### Centrality
| Algorithm | Procedure | Use case |
|---|---|---|
| PageRank | `page_rank` | Rank nodes by influence |
| Article Rank | `article_rank` | PageRank variant, discounts high-degree neighbours |
| Betweenness | `betweenness` | Find bridge nodes |
| Degree | `degree` | Count direct connections |

### Pathfinding
| Algorithm | Procedure | Use case |
|---|---|---|
| Dijkstra Source-Target | `dijkstra` | Shortest path(s) from source to target(s) or pairs |
| Dijkstra Single-Source | `dijkstra_single_source` | Shortest paths from one node to all others |
| Delta-Stepping SSSP | `delta_stepping` | Parallel single-source shortest paths |
| Breadth First Search | `bfs` | BFS traversal from a source |
| Yen's K-Shortest Paths | `yens` | Top-K shortest loopless paths |
| Max Flow | `max_flow` | Maximum flow with capacities |
| Min-Cost Max Flow | `max_flow_min_cost` | Max flow minimising total cost |
| FastPath | `fastpath` | Fast approximate shortest paths |

### Similarity
| Algorithm | Procedure | Use case |
|---|---|---|
| Node Similarity | `node_similarity` | Similar nodes by shared neighbours |
| Filtered Node Similarity | `node_similarity_filtered` | Node similarity with source/target filters |
| KNN | `knn` | K most similar nodes |
| Filtered KNN | `knn_filtered` | KNN with source/target filters |

### Node Embeddings
| Algorithm | Procedure | Use case |
|---|---|---|
| FastRP | `fast_rp` | Fast node embeddings |
| Node2Vec | `node2vec` | Random-walk node embeddings |
| HashGNN | `hashgnn` | GNN-inspired embeddings without training |

### GraphSAGE (Graph ML)
| Algorithm | Procedure | Use case |
|---|---|---|
| Node Classification — train | `gs_nc_train` | Train supervised node-label model |
| Node Classification — predict | `gs_nc_predict` | Predict labels with a trained model |
| Unsupervised embeddings — train | `gs_unsup_train` | Train unsupervised embedding model |
| Unsupervised embeddings — predict | `gs_unsup_predict` | Infer embeddings with a trained model |

### Model catalog (GraphSAGE)
`show_models`, `model_exists`, `drop_model`.

---

## Algorithm-Specific Notes

### GraphSAGE
- Projected node tables used by GraphSAGE must **not** contain `ARRAY` property columns — use `VECTOR(FLOAT, n)` for multi-valued numeric features. (`ARRAY` is fine for non-GraphSAGE algorithms.)
- Feature columns must be **non-NULL and finite** — filter, impute, or exclude nullable feature columns in the view. For `gs_nc_train`, the `targetProperty` is a label (not a feature) and may be NULL.
- Before running, list the node properties GraphSAGE will use per node table: all non-`NODEID` columns; for `gs_nc_train` exclude the `targetProperty`.
- Training (`gs_nc_train`, `gs_unsup_train`) can be slow and may use a GPU pool (`GPU_NV_S`). Show the exact `CALL` and get explicit confirmation before running training.

### Dijkstra Source-Target (`dijkstra`)
Provide one of:
- single pair: `sourceNode` + `sourceNodeTable`, `targetNode` + `targetNodeTable`;
- one source, many targets: `sourceNode` + `sourceNodeTable`, `targetNodes` (list) + `targetNodesTable`;
- many pairs: `sourceTargetNodePairsTable` (table with `SOURCENODEID`/`TARGETNODEID` columns) + `sourceNodeTable` + `targetNodeTable`.

### General
- Never use `NODEID` itself as an algorithm property.
- Omit any config parameter whose value is null.

---

## Installation

1. Install **Neo4j Graph Analytics** from the [Snowflake Marketplace](https://app.snowflake.com/marketplace/listing/GZTDZH40CN/neo4j-neo4j-graph-analytics) (default app name `Neo4j_Graph_Analytics`).
2. **Enable Event sharing** when prompted.
3. **Data Products → Apps → Neo4j Graph Analytics → Privileges → Grant**: grant `CREATE COMPUTE POOL` and `CREATE WAREHOUSE`, then click **Activate**.

---

## Privilege Setup (run once per database/schema)

```sql
USE ROLE ACCOUNTADMIN;

-- Consumer role for app users
CREATE ROLE IF NOT EXISTS MY_CONSUMER_ROLE;
GRANT APPLICATION ROLE Neo4j_Graph_Analytics.app_user TO ROLE MY_CONSUMER_ROLE;
SET MY_USER = (SELECT CURRENT_USER());
GRANT ROLE MY_CONSUMER_ROLE TO USER IDENTIFIER($MY_USER);

-- Database role granting the app access to your data
USE DATABASE MY_DATABASE;
CREATE DATABASE ROLE IF NOT EXISTS MY_DB_ROLE;
GRANT USAGE ON DATABASE MY_DATABASE TO DATABASE ROLE MY_DB_ROLE;
GRANT USAGE ON SCHEMA MY_DATABASE.MY_SCHEMA TO DATABASE ROLE MY_DB_ROLE;
GRANT SELECT ON ALL TABLES  IN SCHEMA MY_DATABASE.MY_SCHEMA TO DATABASE ROLE MY_DB_ROLE;
GRANT SELECT ON ALL VIEWS   IN SCHEMA MY_DATABASE.MY_SCHEMA TO DATABASE ROLE MY_DB_ROLE;
-- FUTURE grants let the app read tables/views it creates (needed for chaining)
GRANT SELECT ON FUTURE TABLES IN SCHEMA MY_DATABASE.MY_SCHEMA TO DATABASE ROLE MY_DB_ROLE;
GRANT SELECT ON FUTURE VIEWS  IN SCHEMA MY_DATABASE.MY_SCHEMA TO DATABASE ROLE MY_DB_ROLE;
GRANT CREATE TABLE ON SCHEMA MY_DATABASE.MY_SCHEMA TO DATABASE ROLE MY_DB_ROLE;
GRANT DATABASE ROLE MY_DB_ROLE TO APPLICATION Neo4j_Graph_Analytics;

-- Let the consumer role read output tables
GRANT USAGE ON DATABASE MY_DATABASE TO ROLE MY_CONSUMER_ROLE;
GRANT USAGE ON SCHEMA MY_DATABASE.MY_SCHEMA TO ROLE MY_CONSUMER_ROLE;
GRANT SELECT ON FUTURE TABLES IN SCHEMA MY_DATABASE.MY_SCHEMA TO ROLE MY_CONSUMER_ROLE;

USE ROLE MY_CONSUMER_ROLE;   -- run algorithms as the consumer role
```

> Replace `MY_DATABASE`, `MY_SCHEMA`, `MY_CONSUMER_ROLE`, `MY_DB_ROLE` with your names throughout.

---

## Common Patterns

### Chaining algorithms
Because results write to tables (and the `FUTURE TABLES` grant lets the app read what it creates), feed one algorithm's output into the next:

```sql
-- 1. Embeddings
CALL Neo4j_Graph_Analytics.graph.fast_rp('CPU_X64_XS', { ... });
-- 2. KNN over the embedding output table (projected as a node view)
CALL Neo4j_Graph_Analytics.graph.knn('CPU_X64_XS', { ... });
```

### Convert categorical data to numeric
The graph engine can't use VARCHAR as a property. Map categories to numbers in the view (e.g. `CASE` / a lookup join). To read results by their original label, join the output table back to the source table on the key.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Insufficient privileges` | App needs `SELECT` on your tables/views and `CREATE TABLE` on the schema (see Privilege Setup) |
| `Column nodeId not found` | View is missing/mis-cast the key — expose `NODEID` (and `SOURCENODEID`/`TARGETNODEID`) with explicit casts |
| Type / projection error on a property | A property column wasn't cast to a supported type — apply the casting rules; relationship props must be `BIGINT`/`DOUBLE`/`INT` |
| GraphSAGE fails on features | Remove `ARRAY` feature columns (use `VECTOR`), and ensure features are non-NULL/finite |
| `Compute pool not available` | Pool may still be starting; wait a minute and retry |
| Algorithm returns no results | Check node/relationship views aren't empty and that every `SOURCENODEID`/`TARGETNODEID` matches a `NODEID` |

Full guide: https://neo4j.com/docs/snowflake-graph-analytics/current/troubleshooting/

---

## Further Reading

- [Getting Started](https://neo4j.com/docs/snowflake-graph-analytics/current/getting-started/)
- [Running Jobs](https://neo4j.com/docs/snowflake-graph-analytics/current/jobs/) · [Scaling Out](https://neo4j.com/docs/snowflake-graph-analytics/current/jobs/scale-out/) · [Estimating Jobs](https://neo4j.com/docs/snowflake-graph-analytics/current/jobs/estimation/)
- [All Algorithms](https://neo4j.com/docs/snowflake-graph-analytics/current/algorithms/)
- [Administration](https://neo4j.com/docs/snowflake-graph-analytics/current/administration/)
- [Integration with Cortex Agent](https://neo4j.com/docs/snowflake-graph-analytics/current/agents/)
- [Basket Analysis Example on TPC-H Data](https://github.com/neo4j-product-examples/snowflake-graph-analytics/tree/main/basket-analysis)

---

## Checklist

- [ ] App installed; privileges granted on the database/schema
- [ ] Views expose `NODEID` / `SOURCENODEID` / `TARGETNODEID`, every property explicitly cast
- [ ] `orientation` matches the algorithm
- [ ] Single `CALL` ran without error; output table populated
- [ ] Results joined back to source table for readable labels
