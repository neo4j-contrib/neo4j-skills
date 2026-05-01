# Neo4j Agent Skills

Skills for building, querying, and managing Neo4j graph databases.

## Connection

Configure via environment variables or agent plugin settings:

| Variable | Description |
|---|---|
| `NEO4J_URI` | Bolt URI — `neo4j+s://<dbid>.databases.neo4j.io` (Aura) or `neo4j://localhost:7687` (local) |
| `NEO4J_USERNAME` | Database username (default: `neo4j`) |
| `NEO4J_PASSWORD` | Database password |
| `NEO4J_DATABASE` | Target database (default: `neo4j`) |

## Skills

| Skill | Activate when... |
|---|---|
| `neo4j-cypher-skill` | Writing, optimizing, or debugging Cypher queries |
| `neo4j-modeling-skill` | Designing or reviewing graph data models |
| `neo4j-vector-index-skill` | Creating vector indexes, running similarity search |
| `neo4j-graphrag-skill` | Building GraphRAG pipelines with `neo4j-graphrag` |
| `neo4j-import-skill` | Loading structured data (CSV, JSON) into Neo4j |
| `neo4j-document-import-skill` | Extracting knowledge graphs from documents/PDFs |
| `neo4j-gds-skill` | Running graph algorithms (PageRank, Louvain, etc.) |
| `neo4j-aura-graph-analytics-skill` | Graph algorithms on Neo4j Aura |
| `neo4j-aura-provisioning-skill` | Creating/managing Aura instances via CLI or API |
| `neo4j-aura-agent-skill` | Creating and managing Aura Agents (GraphRAG) backed by an AuraDB instance |
| `neo4j-migration-skill` | Upgrading drivers or Cypher from 4.x/5.x to 2025.x |
| `neo4j-graphql-skill` | Building GraphQL APIs backed by Neo4j |
| `neo4j-spring-data-skill` | Spring Boot + Neo4j (SDN, @Node, @Relationship) |
| `neo4j-driver-python-skill` | Python driver (`neo4j` package) |
| `neo4j-driver-javascript-skill` | JavaScript/TypeScript driver |
| `neo4j-driver-java-skill` | Java driver |
| `neo4j-driver-dotnet-skill` | .NET/C# driver |
| `neo4j-driver-go-skill` | Go driver |
| `neo4j-cli-tools-skill` | DB admin: `neo4j-admin`, `cypher-shell`, Aura CLI |
| `neo4j-getting-started-skill` | Zero-to-app: provision → model → load → query |
| `neo4j-mcp-skill` | Neo4j MCP server setup and usage |
| `neo4j-agent-memory-skill` | Persistent agent memory backed by Neo4j |

## Quick start

```bash
# Aura (cloud)
NEO4J_URI=neo4j+s://<dbid>.databases.neo4j.io
NEO4J_USERNAME=neo4j or <dbid>
NEO4J_PASSWORD=<your-password>
NEO4J_DATABASE=neo4j or <dbid>

# Local (Docker)
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```
