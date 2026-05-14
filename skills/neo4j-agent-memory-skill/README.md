# neo4j-agent-memory-skill

Skill for building graph-native agent memory backed by Neo4j using the `neo4j-agent-memory` Python package and the hosted Neo4j Agent Memory Service (NAMS) at memory.neo4jlabs.com.

**Covers:**
- `MemoryClient` / `MemorySettings` — core API for storing and retrieving memories
- Short-term memory — conversation history stored as `:Message` nodes
- Long-term memory — structured knowledge using the POLE+O entity model (Person, Object, Location, Event + Organisation)
- Reasoning traces — storing agent thought chains for auditability and re-use
- NAMS hosted service — API key setup (`nams_` prefix), endpoints, rate limits
- Memory MCP server — exposing memory as MCP tools for any MCP-compatible agent
- Framework integrations: LangChain, PydanticAI, CrewAI, AWS Strands, Google ADK, Microsoft Agent Framework, OpenAI Agents SDK, LlamaIndex
- Graph schema — memory graph structure, Cypher queries for inspection
- Comparing graph-native memory vs vector-only approaches

**Version / compatibility:**
- `neo4j-agent-memory` Python package (latest)
- Neo4j 5.x / 2025.x or NAMS hosted service

**Not covered:**
- General Neo4j vector search → `neo4j-vector-index-skill`
- GraphRAG pipelines → `neo4j-graphrag-skill`
- MCP server setup (general) → `neo4j-mcp-skill`

**Install:**
```bash
pip install neo4j-agent-memory
```

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-agent-memory-skill
```

Or paste this link into your coding assistant:
https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-agent-memory-skill
