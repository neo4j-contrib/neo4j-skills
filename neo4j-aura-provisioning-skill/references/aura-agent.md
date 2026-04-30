# Aura Agent (No-Code AI Agent)

No/low-code platform in the Aura Console for building AI agents that query AuraDB with natural language.

## When to Use

Use Aura Agent for: retrieval assistants over graph data without app code, natural language queries from the console, prototyping agent behavior.

Use LangChain/LangGraph/etc. for: custom orchestration, multi-agent coordination, production deployment outside Aura console.

## Prerequisites

In organization settings, both must be enabled:
- **Generative AI assistance**
- **Aura Agent**

**Tool authentication** must be enabled for the project (default ON for orgs created after May 2025; enable manually for older orgs).

## How It Works

Agent loop: interpret user input → plan tools → execute tools (read-only graph queries) → generate response.

## Tool Types

| Tool | Description | Use when |
|---|---|---|
| **Cypher Template** | Parameterized Cypher — agent extracts params from question | Known, repeatable query patterns |
| **Similarity Search** | Vector search using a vector index + embeddings | Semantic similarity ("products similar to X") |
| **Text2Cypher** | LLM generates Cypher at runtime from natural language | Ad-hoc questions not covered by templates |

All tools are **read-only**. Agent cannot write to the database.

Similarity Search requires: vector index on AuraDB instance + embeddings stored on nodes.

## MCP Endpoint

Agents can be exposed as MCP servers for use with external clients (Cursor, Claude Desktop, etc.):

1. Select agent → `...` menu → Configure
2. Under Access, select **External**
3. Enable **MCP server** toggle → click "Update agent"
4. Copy MCP endpoint: `...` menu → "Copy MCP server endpoint"

MCP config for Cursor (`~/.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "my-aura-agent": {
      "url": "<your-mcp-url>",
      "transport": "http"
    }
  }
}
```

Authentication: OAuth2 via Aura console. First connection prompts browser login → "Continue with Neo4j Aura" → Accept.

Restart client after adding MCP endpoint (Cursor, Claude Desktop, etc.).

For Claude Desktop and other clients: see https://neo4j.com/docs/aura/aura-agent/
