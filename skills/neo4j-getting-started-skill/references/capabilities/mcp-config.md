# Capability — mcp-config
# Configure the official neo4j-mcp server for different agent environments.
# Reference this from the `build` stage when APP_TYPE=mcp or integration is requested.

## Binary location

```bash
# Check candidates in priority order
NEO4J_MCP_BIN=$(which neo4j-mcp 2>/dev/null \
  || ls $HOME/bin/neo4j-mcp 2>/dev/null \
  || ls ./neo4j-mcp 2>/dev/null \
  || echo "NOT_FOUND")
echo "neo4j-mcp: $NEO4J_MCP_BIN"
```

Use that absolute path in all config files below.

## Claude Desktop

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "<absolute-path-to-neo4j-mcp>",
      "env": {
        "NEO4J_URI": "<NEO4J_URI from .env>",
        "NEO4J_USERNAME": "<NEO4J_USERNAME from .env>",
        "NEO4J_PASSWORD": "<NEO4J_PASSWORD from .env>",
        "NEO4J_DATABASE": "neo4j"
      }
    }
  }
}
```

## Claude Code

Project-level (`.claude/settings.json` — checked in, safe since no secrets if using env vars):
```json
{
  "mcpServers": {
    "neo4j": {
      "command": "./neo4j-mcp",
      "env": {
        "NEO4J_URI": "<NEO4J_URI>",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "<NEO4J_PASSWORD>",
        "NEO4J_DATABASE": "neo4j"
      }
    }
  }
}
```

User-level (`~/.claude/settings.json` — applies to all projects):
```json
{
  "mcpServers": {
    "neo4j-<project-name>": {
      "command": "<absolute-path-to-neo4j-mcp>",
      "env": {
        "NEO4J_URI": "<URI>",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "<PASSWORD>",
        "NEO4J_DATABASE": "neo4j"
      }
    }
  }
}
```

## Read-only mode (recommended for production / shared DBs)

Add to env:
```json
"NEO4J_READ_ONLY": "true"
```

This disables the `write-cypher` tool entirely.

## Available MCP tools after restart

| Tool | Description |
|------|-------------|
| `get-schema` | Introspect node labels, relationship types, property keys |
| `read-cypher` | Execute read-only Cypher |
| `write-cypher` | Execute write Cypher (disabled in read-only mode) |
| `list-gds-procedures` | List GDS procedures (only if GDS installed) |

## Verify config is working

After restart, ask: "What node labels are in my Neo4j database?" — should use `get-schema` automatically.
