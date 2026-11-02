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

## Server version and env vars (neo4j-mcp 2.0+)

neo4j-mcp 2.0.0 (2026-10-28) accepts only `NEO4J_MCP_*` env vars (old `NEO4J_URI`, `NEO4J_USERNAME`, … are removed) and unprefixed flags (`--uri`, `--database`, …). STDIO mode requires `NEO4J_MCP_URI`, `NEO4J_MCP_USERNAME`, `NEO4J_MCP_PASSWORD` **and** `NEO4J_MCP_DATABASE` (no default). Defaults: read-only `false`, telemetry `true`. The server requires APOC (incl. `meta`) on the target DB — local Docker: add `-e NEO4J_PLUGINS='["apoc"]'`; Aura has APOC. Check `neo4j-mcp -v`. Docs: https://neo4j.com/docs/mcp/current/configuration/

## Claude Desktop

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Merge the `neo4j` entry into existing `mcpServers` — never overwrite the file.

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "<absolute-path-to-neo4j-mcp>",
      "env": {
        "NEO4J_MCP_URI": "<NEO4J_URI from .env>",
        "NEO4J_MCP_USERNAME": "<NEO4J_USERNAME from .env>",
        "NEO4J_MCP_PASSWORD": "<NEO4J_PASSWORD from .env>",
        "NEO4J_MCP_DATABASE": "neo4j"
      }
    }
  }
}
```

## Claude Code

Claude Code reads MCP servers from `claude mcp add` (local/user scope, stored in `~/.claude.json`) or project `.mcp.json`. **Not** from `.claude/settings.json` or `~/.claude/settings.json` — servers there never load.

Preferred — CLI (local scope: this project only, not checked in):
```bash
claude mcp add --env NEO4J_MCP_URI="<NEO4J_URI>" NEO4J_MCP_USERNAME=neo4j \
  NEO4J_MCP_PASSWORD="<NEO4J_PASSWORD>" NEO4J_MCP_DATABASE=neo4j \
  --transport stdio neo4j -- <absolute-path-to-neo4j-mcp>
claude mcp get neo4j   # verify
```

Alternative — project `.mcp.json` (merge into existing file; never overwrite). It holds the password → add `.mcp.json` to `.gitignore`; never commit it:
```json
{
  "mcpServers": {
    "neo4j": {
      "command": "<absolute-path-to-neo4j-mcp>",
      "env": {
        "NEO4J_MCP_URI": "<NEO4J_URI>",
        "NEO4J_MCP_USERNAME": "neo4j",
        "NEO4J_MCP_PASSWORD": "<NEO4J_PASSWORD>",
        "NEO4J_MCP_DATABASE": "neo4j"
      }
    }
  }
}
```
`.mcp.json` servers need one-time approval: run `claude` in the project and accept.

## Read-only mode (recommended for production / shared DBs)

Default is read-write. Add to env:
```json
"NEO4J_MCP_READ_ONLY": "true"
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
