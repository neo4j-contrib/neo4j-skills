# neo4j-mcp Reference

Official Neo4j MCP server for AI agents (Claude, Cursor, etc.) to query Neo4j.

## Installation

```bash
# macOS/Linux
curl -L https://github.com/neo4j/mcp/releases/latest/download/neo4j-mcp-<platform> -o neo4j-mcp
chmod +x neo4j-mcp
sudo mv neo4j-mcp /usr/local/bin/
neo4j-mcp --version
```

**Requirements**: any Neo4j deployment; APOC plugin for full functionality.

## Configuration Options

### Connection (required)

```bash
neo4j-mcp --neo4j-uri bolt://localhost:7687
neo4j-mcp --neo4j-username neo4j
neo4j-mcp --neo4j-password password
neo4j-mcp --neo4j-database mydb   # optional, default: neo4j
```

All accept env vars: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`

### Operational (optional)

```bash
neo4j-mcp --neo4j-read-only true          # disable write tools; env: NEO4J_READ_ONLY
neo4j-mcp --neo4j-telemetry false         # env: NEO4J_TELEMETRY (default: true)
neo4j-mcp --neo4j-schema-sample-size 200  # nodes to sample for schema inference; default: 100
```

### Transport Modes

**STDIO** (default — for desktop AI agent integration):
```bash
neo4j-mcp --neo4j-transport-mode stdio
```

**HTTP** (for remote/multi-client access):
```bash
neo4j-mcp --neo4j-transport-mode http \
  --neo4j-http-port 8080 \
  --neo4j-http-host 0.0.0.0
```

### HTTP-Specific Settings

```bash
neo4j-mcp --neo4j-http-port 8443                      # env: NEO4J_MCP_HTTP_PORT
neo4j-mcp --neo4j-http-host 127.0.0.1                 # env: NEO4J_MCP_HTTP_HOST (default)
neo4j-mcp --neo4j-http-allowed-origins "https://example.com"  # env: NEO4J_MCP_HTTP_ALLOWED_ORIGINS
neo4j-mcp --neo4j-http-tls-enabled true \
  --neo4j-http-tls-cert-file /path/to/cert.pem \
  --neo4j-http-tls-key-file /path/to/key.pem
neo4j-mcp --neo4j-http-auth-header-name X-API-Key     # env: NEO4J_HTTP_AUTH_HEADER_NAME (default: Authorization)
```

## Environment Variables Reference

### Required
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`

### Optional
- `NEO4J_DATABASE` (default: `neo4j`)
- `NEO4J_READ_ONLY` (default: `false`)
- `NEO4J_TELEMETRY` (default: `true`)
- `NEO4J_SCHEMA_SAMPLE_SIZE` (default: `100`)
- `NEO4J_TRANSPORT_MODE` — `stdio` or `http` (default: `stdio`)

### HTTP Transport
- `NEO4J_MCP_HTTP_PORT` (default: `443` with TLS, `80` without)
- `NEO4J_MCP_HTTP_HOST` (default: `127.0.0.1`)
- `NEO4J_MCP_HTTP_ALLOWED_ORIGINS`
- `NEO4J_MCP_HTTP_TLS_ENABLED`, `NEO4J_MCP_HTTP_TLS_CERT_FILE`, `NEO4J_MCP_HTTP_TLS_KEY_FILE`
- `NEO4J_HTTP_AUTH_HEADER_NAME` (default: `Authorization`)

**Deprecated**: `NEO4J_MCP_TRANSPORT` → use `NEO4J_TRANSPORT_MODE`

## Common Configurations

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "neo4j": {
      "command": "neo4j-mcp",
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password",
        "NEO4J_DATABASE": "neo4j"
      }
    }
  }
}
```

**Claude Code** (`.claude/mcp_servers.json`):
```json
{
  "neo4j": {
    "command": "/usr/local/bin/neo4j-mcp",
    "env": {
      "NEO4J_URI": "bolt://localhost:7687",
      "NEO4J_USERNAME": "neo4j",
      "NEO4J_PASSWORD": "password"
    }
  }
}
```

**Aura**:
```bash
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io \
NEO4J_USERNAME=neo4j NEO4J_PASSWORD=your-aura-password neo4j-mcp
```

**HTTP server mode**:
```bash
NEO4J_URI=bolt://localhost:7687 NEO4J_USERNAME=neo4j NEO4J_PASSWORD=password \
NEO4J_TRANSPORT_MODE=http NEO4J_MCP_HTTP_PORT=8080 NEO4J_MCP_HTTP_HOST=0.0.0.0 neo4j-mcp
```

**Docker**:
```bash
docker run -d --name neo4j-mcp \
  -e NEO4J_URI=bolt://neo4j:7687 \
  -e NEO4J_USERNAME=neo4j -e NEO4J_PASSWORD=password \
  -e NEO4J_TRANSPORT_MODE=http -e NEO4J_MCP_HTTP_PORT=8080 \
  -e NEO4J_MCP_HTTP_HOST=0.0.0.0 \
  -p 8080:8080 neo4j/mcp:latest
```

**Systemd service**:
```ini
[Unit]
Description=Neo4j MCP Server
After=network.target neo4j.service

[Service]
Type=simple
User=neo4j
Environment="NEO4J_URI=bolt://localhost:7687"
Environment="NEO4J_USERNAME=neo4j"
Environment="NEO4J_PASSWORD=password"
ExecStart=/usr/local/bin/neo4j-mcp
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Best Practices

- Use read-only mode for production analysis
- Never hardcode credentials — use environment variables
- Enable TLS for HTTP transport in production
- Restrict CORS origins to trusted domains
- Adjust schema sample size to balance accuracy vs performance

## Troubleshooting

**Connection refused**: verify Neo4j is running, URI correct, firewall allows connection, credentials valid.

**APOC not available**: add `dbms.security.procedures.unrestricted=apoc.*` to `neo4j.conf`; download APOC jar to plugins; restart.

**Port already in use (HTTP mode)**: use a different port: `--neo4j-http-port 8081`

**TLS certificate errors**: verify cert path, cert matches key, cert not expired, readable permissions.

**Capture logs**: `neo4j-mcp 2>&1 | tee neo4j-mcp.log`

## Resources

- [Neo4j MCP Documentation](https://neo4j.com/docs/mcp/current/)
- [GitHub Repository](https://github.com/neo4j/mcp)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
