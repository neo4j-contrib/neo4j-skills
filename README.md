# Neo4j Agent Skills

Agent skills for [Neo4j](https://neo4j.com) — Cypher queries, graph modeling, drivers, imports, GraphRAG, GDS, vector indexes, and Aura provisioning.

Browse and install at **[skills.sh/neo4j-contrib/neo4j-skills](https://skills.sh/neo4j-contrib/neo4j-skills)**.

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills
```

## Configuration

Set these before or during installation:

| Variable | Description |
|---|---|
| `NEO4J_URI` | `neo4j+s://<dbid>.databases.neo4j.io` (Aura) or `neo4j://localhost:7687` (local) |
| `NEO4J_USERNAME` | Database username (default: `neo4j`) |
| `NEO4J_PASSWORD` | Database password |
| `NEO4J_DATABASE` | Target database (default: `neo4j`) |

## Installation

### Gemini CLI

```bash
gemini extensions install https://github.com/neo4j-contrib/neo4j-skills
```

Enter your env vars when prompted. Then run `gemini` and use `/extensions list` to verify.

### Claude Code

```
/plugin marketplace add https://github.com/neo4j-contrib/neo4j-skills.git
/plugin install neo4j-skills@neo4j-skills-marketplace
```

Use `/plugin list` to verify, or `/reload-plugins` after installation.

### Codex

```bash
git clone https://github.com/neo4j-contrib/neo4j-skills.git
mkdir -p ~/.codex/plugins
cp -R neo4j-skills ~/.codex/plugins/neo4j-skills
```

Add to `~/.agents/plugins/marketplace.json`:

```json
{
  "name": "neo4j-marketplace",
  "interface": { "displayName": "Neo4j Skills" },
  "plugins": [
    {
      "name": "neo4j-skills",
      "source": { "source": "local", "path": "./plugins/neo4j-skills" },
      "policy": { "installation": "AVAILABLE" },
      "category": "Database"
    }
  ]
}
```

## Available Skills

### Querying & Modeling

| Skill | Description |
|---|---|
| [`neo4j-cypher-skill`](./neo4j-cypher-skill) | Write, optimize, and debug Cypher queries. Covers CYPHER 25 syntax, query planning, indexes, and common patterns. |
| [`neo4j-modeling-skill`](./neo4j-modeling-skill) | Design and review graph data models. Covers node/relationship patterns, property choices, and relational-to-graph migration. |
| [`neo4j-getting-started-skill`](./neo4j-getting-started-skill) | Zero-to-app walkthrough: provision → model → load → query. Use for first-time setup on Aura or Docker. |

### Importing Data

| Skill | Description |
|---|---|
| [`neo4j-import-skill`](./neo4j-import-skill) | Load structured data (CSV, JSON) via `LOAD CSV`, `neo4j-admin import`, and the Data Importer GUI. |
| [`neo4j-document-import-skill`](./neo4j-document-import-skill) | Extract knowledge graphs from unstructured documents and PDFs using `SimpleKGPipeline`. |
| [`neo4j-migration-skill`](./neo4j-migration-skill) | Upgrade drivers and Cypher from 4.x/5.x to 2025.x. Covers API changes, deprecated functions, and Cypher 25 syntax. |

### AI & Search

| Skill | Description |
|---|---|
| [`neo4j-vector-index-skill`](./neo4j-vector-index-skill) | Create and query vector indexes for semantic similarity search. Covers index creation, embedding ingestion, and `genai.vector.encode()`. |
| [`neo4j-graphrag-skill`](./neo4j-graphrag-skill) | Build GraphRAG retrieval pipelines with `neo4j-graphrag`. Covers retriever selection (`VectorCypherRetriever`, `HybridCypherRetriever`), `retrieval_query` patterns, and LangChain/LlamaIndex integration. |
| [`neo4j-agent-memory-skill`](./neo4j-agent-memory-skill) | Graph-native agent memory: short-term (conversations), long-term (POLE+O entity model), and reasoning traces. Covers `neo4j-agent-memory`, NAMS, MCP, LangChain, CrewAI, ADK. |
| [`neo4j-mcp-skill`](./neo4j-mcp-skill) | Set up and use the Neo4j MCP server for tool-based agent access to the database. |

### Graph Data Science

| Skill | Description |
|---|---|
| [`neo4j-gds-skill`](./neo4j-gds-skill) | Run graph algorithms (PageRank, Louvain, node embeddings) on self-managed Neo4j using GDS. |
| [`neo4j-aura-graph-analytics-skill`](./neo4j-aura-graph-analytics-skill) | Run GDS-compatible graph algorithms on Neo4j Aura via the Graph Analytics API. |

### Drivers

| Skill | Description |
|---|---|
| [`neo4j-driver-python-skill`](./neo4j-driver-python-skill) | Python driver: `execute_query`, sessions, transactions, async, UNWIND batching, data types. |
| [`neo4j-driver-javascript-skill`](./neo4j-driver-javascript-skill) | JavaScript/TypeScript driver v6: `executeQuery`, managed transactions, RxJS, data types. |
| [`neo4j-driver-java-skill`](./neo4j-driver-java-skill) | Java driver: `ExecutableQuery`, managed/explicit transactions, object mapping, reactive. |
| [`neo4j-driver-dotnet-skill`](./neo4j-driver-dotnet-skill) | .NET/C# driver: `ExecuteReadAsync`/`ExecuteWriteAsync`, DI registration, `IResultCursor`. |
| [`neo4j-driver-go-skill`](./neo4j-driver-go-skill) | Go driver v6: `ExecuteQuery`, generic helpers, spatial types, connection configuration. |

### Frameworks & Platforms

| Skill | Description |
|---|---|
| [`neo4j-graphql-skill`](./neo4j-graphql-skill) | Build GraphQL APIs backed by Neo4j using `@neo4j/graphql`. Covers type definitions, `@relationship`, `@cypher`, and filtering. |
| [`neo4j-spring-data-skill`](./neo4j-spring-data-skill) | Spring Boot + Neo4j with Spring Data Neo4j: `@Node`, `@Relationship`, repositories, projections. |
| [`neo4j-cli-tools-skill`](./neo4j-cli-tools-skill) | DB admin via `neo4j-admin`, `cypher-shell`, and `aura-cli`. Covers backups, imports, user management, and Aura provisioning. |
| [`neo4j-aura-provisioning-skill`](./neo4j-aura-provisioning-skill) | Create and manage Neo4j Aura instances via the Aura CLI and REST API. Covers async polling, credential handling, and tier selection. |

## What are Agent Skills?

Agent Skills are a standardized format for domain-specific AI agent knowledge. Each skill bundles step-by-step instructions, on-demand reference docs, and executable scripts — loaded progressively to keep context lean. See [agentskills.io/specification](https://agentskills.io/specification).

## Contributing

Pull requests welcome — new skills or improvements to existing ones.

## License

MIT — see the [LICENSE](LICENSE) file for details.
