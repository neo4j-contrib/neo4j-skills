# Neo4j Graph Analytics for Snowflake Skill

An [Agent Skill](https://agentskills.io/specification) that helps AI agents work with [Neo4j Graph Analytics for Snowflake](https://neo4j.com/docs/snowflake-graph-analytics/current/) — a Snowflake Native Application that brings graph algorithms directly into Snowflake via SQL procedures.

## What this skill covers

- Installing Neo4j Graph Analytics from the Snowflake Marketplace
- Setting up the required privileges and roles
- The end-to-end flow: **explore → prepare projection views → project-compute-write → inspect**
- The strict view/column type rules the graph engine requires (key columns, supported property types, casting)
- Exact SQL `CALL` syntax for all available graph algorithms
- Projection configuration (node tables, relationship tables, orientation)
- Looking up human-readable names by joining results back to source tables
- Chaining algorithms together
- Troubleshooting common errors

## Use this skill when

- Writing SQL to run graph algorithms on Snowflake tables
- Preparing source tables into graph-ready projection views
- Setting up Neo4j Graph Analytics for the first time
- Choosing the right algorithm for a business problem (fraud detection, recommendations, entity resolution, etc.)
- Configuring compute pool sizes for jobs
- Troubleshooting privilege, projection, or column-type errors

## Installation

### Cortex Code Desktop

This skill is built for [Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-desktop/skills). Add it from GitHub:

1. Open **Agent Settings** → **Skills**.
2. In the **GitHub Skills** section, click **`+`** (_Add from GitHub_).
3. Enter the skill's path in this repo:
   ```
   https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-snowflake-graph-analytics-skill
   ```
4. Click **Add**.

You can also add it as a **Local** skill (point _Add Local Skill_ at a folder containing this skill directory, saved to `~/.snowflake/cortex/skills.json`) or from a **Snowflake Stage** (`@DATABASE.SCHEMA.STAGE/...`).

Once added, Cortex Code invokes the skill automatically when your prompt matches its description, or you can trigger it explicitly by typing `/` in the chat and selecting it. Skills are folders with a `SKILL.md` (plus optional `references/`), which is exactly this directory's layout.

### Cortex Code CLI

Use the [`/skill add`](https://docs.snowflake.com/en/user-guide/cortex-code/extensibility) command (or the `cortex skill add` equivalent) — from a Git repo, a local folder, or a Snowflake stage:

Alternatively, drop the skill folder into a skills directory the CLI scans — project scope `.cortex/skills/` (or `.claude/skills/`) or user scope `~/.snowflake/cortex/skills/`.

Verify with `/skill list`. Invoke automatically by matching prompt, or explicitly with `$neo4j-snowflake-graph-analytics-skill` in the conversation.

### Other agents

This skill also ships in the [**neo4j-skills**](https://github.com/neo4j-contrib/neo4j-skills) bundle for other agents. Quickest, cross-agent:

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills
```

- **Claude Code** — `/plugin marketplace add https://github.com/neo4j-contrib/neo4j-skills.git` then `/plugin install neo4j-skills@neo4j-skills-marketplace`
- **Gemini CLI** — `gemini extensions install https://github.com/neo4j-contrib/neo4j-skills`

See the [root README](../README.md#installation) for full per-agent instructions.

> Note: this installs the **agent skill** (guidance for the AI). The Neo4j Graph Analytics **Snowflake Native App** itself is installed separately from the Snowflake Marketplace — see `SKILL.md` for that setup.

## Available algorithms

Procedure = `Neo4j_Graph_Analytics.graph.<name>`.

| Category | Algorithms (procedure name) |
|---|---|
| Community Detection | WCC (`wcc`), Louvain (`louvain`), Leiden (`leiden`), Label Propagation (`label_propagation`), K-Means (`kmeans`), Triangle Count (`triangle_count`) |
| Centrality | PageRank (`page_rank`), Article Rank (`article_rank`), Betweenness (`betweenness`), Degree (`degree`) |
| Pathfinding | Dijkstra (`dijkstra`, `dijkstra_single_source`), Delta-Stepping (`delta_stepping`), BFS (`bfs`), Yen's (`yens`), Max Flow (`max_flow`, `max_flow_min_cost`), FastPath (`fastpath`) |
| Similarity | Node Similarity (`node_similarity`, `node_similarity_filtered`), KNN (`knn`, `knn_filtered`) |
| Node Embeddings | FastRP (`fast_rp`), Node2Vec (`node2vec`), HashGNN (`hashgnn`) |
| Graph ML (GraphSAGE) | Node classification (`gs_nc_train`, `gs_nc_predict`), Unsupervised embeddings (`gs_unsup_train`, `gs_unsup_predict`) |

## Quick example

```sql
CALL Neo4j_Graph_Analytics.graph.wcc('CPU_X64_XS', {
    'defaultTablePrefix': 'MY_DB.MY_SCHEMA',
    'project': {
        'nodeTables': ['NODES_VW'],
        'relationshipTables': {
            'RELATIONSHIPS_VW': {
                'sourceTable': 'NODES_VW',
                'targetTable': 'NODES_VW',
                'orientation': 'NATURAL'
            }
        }
    },
    'compute': { 'consecutiveIds': true },
    'write': [{
        'nodeLabel': 'NODES_VW',
        'outputTable': 'result_wcc_components'
    }]
});
```

> Don't call an algorithm against raw tables blindly — first create projection views that expose `NODEID` / `SOURCENODEID` / `TARGETNODEID` and cast every property to a supported type. See `SKILL.md` for the full rules.

## Resources

- [Neo4j Graph Analytics for Snowflake documentation](https://neo4j.com/docs/snowflake-graph-analytics/current/)
- [Snowflake Marketplace listing](https://app.snowflake.com/marketplace/listing/GZTDZH40CN/neo4j-neo4j-graph-analytics)
- [Example: Basket analysis on TPC-H data](https://github.com/neo4j-product-examples/snowflake-graph-analytics/tree/main/basket-analysis)