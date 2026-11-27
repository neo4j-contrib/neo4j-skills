# neo4j-mcp Reference

Applies to neo4j-mcp **2.0.0+** (2026-10-28). 2.0.0 removed all `NEO4J_*` env vars (e.g. `NEO4J_URI`) and `--neo4j-*` flags: only `NEO4J_MCP_*` env vars and unprefixed flags (`--uri`) work. See [CHANGELOG](https://github.com/neo4j/mcp/blob/main/CHANGELOG.md) and [configuration](https://neo4j.com/docs/mcp/current/configuration/).

## Installation

```bash
brew install neo4j-mcp            # Homebrew → command: neo4j-mcp
pip install neo4j-mcp-server      # PyPI → command: neo4j-mcp-server (not neo4j-mcp)

# Release archive from https://github.com/neo4j/mcp/releases
# Assets: neo4j-mcp_Darwin_arm64.tar.gz, neo4j-mcp_Darwin_x86_64.tar.gz,
#         neo4j-mcp_Linux_x86_64.tar.gz, neo4j-mcp_Linux_arm64.tar.gz, neo4j-mcp_Windows_x86_64.zip
curl -fL https://github.com/neo4j/mcp/releases/latest/download/neo4j-mcp_Darwin_arm64.tar.gz | tar xz
chmod +x neo4j-mcp
sudo mv neo4j-mcp /usr/local/bin/

# Verify installation
neo4j-mcp -v
```

Requires: APOC plugin (incl. `meta` component), network access to Neo4j.

## Configuration Options

### Connection Settings (STDIO only — required; must NOT be set in HTTP mode)

**Neo4j URI**:
```bash
neo4j-mcp --uri bolt://localhost:7687
# or
export NEO4J_MCP_URI=bolt://localhost:7687
neo4j-mcp
```

**Username**:
```bash
neo4j-mcp --username neo4j
# or
export NEO4J_MCP_USERNAME=neo4j
neo4j-mcp
```

**Password**:
```bash
neo4j-mcp --password password
# or
export NEO4J_MCP_PASSWORD=password
neo4j-mcp
```

**Database Name** (required in STDIO; no default since 2.0.0; must NOT be set in HTTP mode):
```bash
neo4j-mcp --database mydb
# or
export NEO4J_MCP_DATABASE=mydb
neo4j-mcp
```

### Operational Settings (Optional)

**Read-Only Mode**:
```bash
neo4j-mcp --read-only true
# or
export NEO4J_MCP_READ_ONLY=true  # default: false
neo4j-mcp
```

Disables write tools when enabled.

**Telemetry**:
```bash
neo4j-mcp --telemetry false
# or
export NEO4J_MCP_TELEMETRY=false  # default: true
neo4j-mcp
```

**Schema Sample Size**:
```bash
neo4j-mcp --schema-sample-size 200
# or
export NEO4J_MCP_SCHEMA_SAMPLE_SIZE=200  # default: 100
neo4j-mcp
```

Number of nodes to sample for schema inference.

### Transport Modes

**STDIO Mode** (default):
```bash
neo4j-mcp --transport-mode stdio
# or
export NEO4J_MCP_TRANSPORT_MODE=stdio
neo4j-mcp
```

Used for direct integration with AI agents.

**HTTP Mode**:
```bash
# No URI/username/password/database: clients send them per request
neo4j-mcp --transport-mode http \
  --http-port 8080 \
  --http-allowed-uris "localhost:7687"
# or
export NEO4J_MCP_TRANSPORT_MODE=http
export NEO4J_MCP_HTTP_PORT=8080
export NEO4J_MCP_HTTP_ALLOWED_URIS="localhost:7687"
neo4j-mcp
```

Used for remote access via HTTP. Endpoint: `POST /db/{databaseName}/mcp`. Each request sends `X-Neo4j-MCP-URI: bolt://...` and `Authorization: Basic <base64 user:pass>` (or `Bearer <token>`). Server refuses to start if `NEO4J_MCP_URI`/`USERNAME`/`PASSWORD`/`DATABASE` are set, or if `NEO4J_MCP_HTTP_ALLOWED_URIS` (comma-separated `host[:port]`, `*.` wildcard) is missing. See [HTTP mode](https://neo4j.com/docs/mcp/current/http-mode/).

### HTTP-Specific Settings

**Port Configuration**:
```bash
neo4j-mcp --http-port 8443
# or
export NEO4J_MCP_HTTP_PORT=8443  # default: 443 (TLS) or 80 (no TLS)
```

**Host Binding**:
```bash
neo4j-mcp --http-host 127.0.0.1
# or
export NEO4J_MCP_HTTP_HOST=127.0.0.1  # default: 127.0.0.1
```

**CORS Origins**:
```bash
neo4j-mcp --http-allowed-origins "https://example.com,https://app.example.com"
# or
export NEO4J_MCP_HTTP_ALLOWED_ORIGINS="https://example.com,https://app.example.com"
```

**TLS/HTTPS**:
```bash
neo4j-mcp --http-tls-enabled true \
  --http-tls-cert-file /path/to/cert.pem \
  --http-tls-key-file /path/to/key.pem
# or
export NEO4J_MCP_HTTP_TLS_ENABLED=true
export NEO4J_MCP_HTTP_TLS_CERT_FILE=/path/to/cert.pem
export NEO4J_MCP_HTTP_TLS_KEY_FILE=/path/to/key.pem
```

**Authentication Header**:
```bash
neo4j-mcp --http-auth-header-name X-API-Key
# or
export NEO4J_MCP_HTTP_AUTH_HEADER_NAME=X-API-Key  # default: Authorization
```

## Environment Variables Reference

### Required (STDIO only)
- `NEO4J_MCP_URI` - Database connection URI
- `NEO4J_MCP_USERNAME` - Database username
- `NEO4J_MCP_PASSWORD` - Database password
- `NEO4J_MCP_DATABASE` - Database name (no default since 2.0.0)

### Optional
- `NEO4J_MCP_READ_ONLY` - Enable read-only mode (default: `false`)
- `NEO4J_MCP_TELEMETRY` - Enable telemetry (default: `true`)
- `NEO4J_MCP_SCHEMA_SAMPLE_SIZE` - Schema sampling size (default: `100`)
- `NEO4J_MCP_TRANSPORT_MODE` - Transport mode: `stdio` or `http` (default: `stdio`)
- `NEO4J_MCP_TOOLS` - Comma-separated tools to advertise (default: all four)
- `NEO4J_MCP_REQUEST_TIMEOUT` - Request timeout (default: `3m`, max `30m`)

### HTTP Transport (when `NEO4J_MCP_TRANSPORT_MODE=http`)
- `NEO4J_MCP_HTTP_ALLOWED_URIS` - Required. Hosts clients may target via `X-Neo4j-MCP-URI`
- `NEO4J_MCP_HTTP_PORT` - HTTP server port (default: `443` with TLS, `80` without)
- `NEO4J_MCP_HTTP_HOST` - HTTP server host (default: `127.0.0.1`)
- `NEO4J_MCP_HTTP_ALLOWED_ORIGINS` - CORS origins (comma-separated)
- `NEO4J_MCP_HTTP_TLS_ENABLED` - Enable TLS (default: `false`)
- `NEO4J_MCP_HTTP_TLS_CERT_FILE` - TLS certificate file path
- `NEO4J_MCP_HTTP_TLS_KEY_FILE` - TLS private key file path
- `NEO4J_MCP_HTTP_AUTH_HEADER_NAME` - Auth header name (default: `Authorization`)

### Removed in 2.0.0
- All unprefixed `NEO4J_*` names (`NEO4J_URI`, `NEO4J_TRANSPORT_MODE`, ...) and `NEO4J_MCP_TRANSPORT` — use the `NEO4J_MCP_*` names above

## Common Use Cases

### Local Development with Claude Desktop

**Configuration for Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "neo4j-mcp",
      "env": {
        "NEO4J_MCP_URI": "bolt://localhost:7687",
        "NEO4J_MCP_USERNAME": "neo4j",
        "NEO4J_MCP_PASSWORD": "password",
        "NEO4J_MCP_DATABASE": "neo4j"
      }
    }
  }
}
```

### Read-Only Access

```bash
NEO4J_MCP_URI=bolt://localhost:7687 \
NEO4J_MCP_USERNAME=neo4j \
NEO4J_MCP_PASSWORD=password \
NEO4J_MCP_DATABASE=neo4j \
NEO4J_MCP_READ_ONLY=true \
neo4j-mcp
```

**Use Case**: Provide safe access to production databases for AI analysis.

### Neo4j Aura Integration

```bash
NEO4J_MCP_URI=neo4j+s://xxxxx.databases.neo4j.io \
NEO4J_MCP_USERNAME=neo4j \
NEO4J_MCP_PASSWORD=your-aura-password \
NEO4J_MCP_DATABASE=neo4j \
neo4j-mcp
```

### HTTP Server Mode

```bash
# No credentials on the server: each request carries X-Neo4j-MCP-URI + Authorization
NEO4J_MCP_TRANSPORT_MODE=http \
NEO4J_MCP_HTTP_ALLOWED_URIS="localhost:7687" \
NEO4J_MCP_HTTP_PORT=8080 \
neo4j-mcp

# Client request
curl -X POST http://127.0.0.1:8080/db/neo4j/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'X-Neo4j-MCP-URI: bolt://localhost:7687' \
  -H "Authorization: Basic $(echo -n 'neo4j:password' | base64)" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

**Use Case**: Remote access from web applications or multiple clients. Bind `0.0.0.0` (`NEO4J_MCP_HTTP_HOST`) only behind TLS and a firewall.

### Secure HTTP with TLS

```bash
NEO4J_MCP_TRANSPORT_MODE=http \
NEO4J_MCP_HTTP_ALLOWED_URIS="localhost:7687" \
NEO4J_MCP_HTTP_PORT=8443 \
NEO4J_MCP_HTTP_TLS_ENABLED=true \
NEO4J_MCP_HTTP_TLS_CERT_FILE=/path/to/cert.pem \
NEO4J_MCP_HTTP_TLS_KEY_FILE=/path/to/key.pem \
neo4j-mcp
```

### Docker Deployment

```bash
docker run -d \
  --name neo4j-mcp \
  -e NEO4J_MCP_TRANSPORT_MODE=http \
  -e NEO4J_MCP_HTTP_ALLOWED_URIS="neo4j:7687" \
  -e NEO4J_MCP_HTTP_PORT=8080 \
  -e NEO4J_MCP_HTTP_HOST=0.0.0.0 \
  -p 8080:8080 \
  neo4j/mcp:latest
```

## MCP Capabilities

### Tools

Four tools only — no MCP resources or prompts are registered:

| Tool | Read-only | Purpose |
|---|---|---|
| `get-schema` | Yes | Labels, relationship types, property keys |
| `read-cypher` | Yes | Run read Cypher; rejects writes, schema/admin and PROFILE |
| `write-cypher` | No | Run write Cypher; hidden when read-only mode is on |
| `list-gds-procedures` | Yes | List GDS procedures; omitted from `tools/list` when GDS is not installed |

Restrict with `NEO4J_MCP_TOOLS` / `--tools 'get-schema,read-cypher'`. See [Tools](https://neo4j.com/docs/mcp/current/tools/).

## Integration Examples

### Claude Code Integration

Claude Code reads MCP servers from project `.mcp.json` (or `~/.claude.json` via `claude mcp add`) — not `settings.json` or `.claude/mcp_servers.json`. Add with the CLI:

```bash
claude mcp add --transport stdio neo4j \
  --env NEO4J_MCP_URI=bolt://localhost:7687 \
  --env NEO4J_MCP_USERNAME=neo4j \
  --env NEO4J_MCP_PASSWORD=password \
  --env NEO4J_MCP_DATABASE=neo4j \
  -- /usr/local/bin/neo4j-mcp
```

Or project `.mcp.json` (gitignore it if it holds a password):

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "/usr/local/bin/neo4j-mcp",
      "env": {
        "NEO4J_MCP_URI": "bolt://localhost:7687",
        "NEO4J_MCP_USERNAME": "neo4j",
        "NEO4J_MCP_PASSWORD": "password",
        "NEO4J_MCP_DATABASE": "neo4j"
      }
    }
  }
}
```

### Python Script Integration

```python
import subprocess
import json

def start_neo4j_mcp():
    env = {
        "NEO4J_MCP_URI": "bolt://localhost:7687",
        "NEO4J_MCP_USERNAME": "neo4j",
        "NEO4J_MCP_PASSWORD": "password",
        "NEO4J_MCP_DATABASE": "neo4j"
    }

    process = subprocess.Popen(
        ["neo4j-mcp"],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    return process

# Start MCP server
mcp_server = start_neo4j_mcp()
```

### Node.js Integration

```javascript
const { spawn } = require('child_process');

const neo4jMcp = spawn('neo4j-mcp', [], {
  env: {
    NEO4J_MCP_URI: 'bolt://localhost:7687',
    NEO4J_MCP_USERNAME: 'neo4j',
    NEO4J_MCP_PASSWORD: 'password',
    NEO4J_MCP_DATABASE: 'neo4j',
    NEO4J_MCP_TRANSPORT_MODE: 'stdio'
  }
});

neo4jMcp.stdout.on('data', (data) => {
  console.log(`MCP: ${data}`);
});
```

## Best Practices

### Security

1. **Use Read-Only Mode** for production analysis
2. **Secure Credentials**: Use environment variables, never hardcode
3. **Enable TLS** for HTTP transport in production
4. **Restrict CORS Origins** to trusted domains only
5. **Use Strong Passwords**: Follow Neo4j security best practices
6. **Network Isolation**: Run MCP server in secure network segments

### Performance

1. **Adjust Schema Sample Size**: Balance between accuracy and performance
2. **Connection Pooling**: Let the MCP server manage connections
3. **Monitor Resources**: Track memory and CPU usage

### Operational

1. **Enable Telemetry**: Help improve the MCP server (or disable for privacy)
2. **Log Management**: Capture stdout/stderr for debugging
3. **Health Checks**: Implement monitoring for MCP server availability
4. **Version Control**: Document neo4j-mcp version in deployments
5. **Test Connections**: Verify Neo4j connectivity before starting MCP

### Development

1. **Use STDIO Locally**: Simplest for desktop AI agent integration
2. **Use HTTP for Remote**: Better for web applications
3. **Test in Read-Only**: Develop queries safely before enabling writes
4. **Schema Exploration**: Start with schema inspection before complex queries

## Troubleshooting

### Connection Refused

```
Error: Unable to connect to Neo4j
```

**Check**:
1. Neo4j is running: `neo4j status`
2. URI is correct (protocol, host, port)
3. Firewall allows connection
4. Credentials are valid

### APOC Not Available

Server fails on MCP `initialize` with an error asking to ensure the APOC plugin is installed and includes the `meta` component.

**Solution**:
Install APOC plugin:
```bash
# For Neo4j installations
# Add to neo4j.conf:
dbms.security.procedures.unrestricted=apoc.*

# Download APOC jar to plugins directory
# Restart Neo4j
```

### Authentication Failed

```
Error: Authentication failed
```

**Solution**:
1. Verify credentials
2. Check user has appropriate permissions
3. Verify database name is correct

### Port Already in Use (HTTP mode)

```
Error: Address already in use
```

**Solution**:
```bash
# Use different port
neo4j-mcp --transport-mode http --http-port 8081 --http-allowed-uris "localhost:7687"
```

### TLS Certificate Errors

```
Error: Invalid TLS certificate
```

**Check**:
1. Certificate file path is correct
2. Certificate matches key file
3. Certificate is not expired
4. Certificate permissions are readable

## Monitoring and Logging

### Capture Logs

```bash
# Redirect to log file
neo4j-mcp 2>&1 | tee neo4j-mcp.log
```

### Systemd Service (Linux)

```ini
[Unit]
Description=Neo4j MCP Server
After=network.target neo4j.service

[Service]
Type=simple
User=neo4j
# HTTP mode: STDIO exits when stdin closes, so a service must run HTTP (no credentials here)
Environment="NEO4J_MCP_TRANSPORT_MODE=http"
Environment="NEO4J_MCP_HTTP_PORT=8080"
Environment="NEO4J_MCP_HTTP_ALLOWED_URIS=localhost:7687"
ExecStart=/usr/local/bin/neo4j-mcp
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

if curl -f http://localhost:8080/healthz > /dev/null 2>&1; then
    echo "neo4j-mcp is healthy"
    exit 0
else
    echo "neo4j-mcp is unhealthy"
    exit 1
fi
```

## Example AI Agent Interactions

### Schema Exploration

**User**: "What's in this database?"

**Agent via MCP**:
- Calls `get-schema` tool
- Returns: Labels, relationships, properties
- Presents summary to user

### Natural Language Query

**User**: "Show me all people over 30"

**Agent via MCP**:
- Converts to Cypher: `MATCH (p:Person) WHERE p.age > 30 RETURN p`
- Executes via `read-cypher` tool
- Formats results for user

### Data Analysis

**User**: "Find the most connected person"

**Agent via MCP**:
- Executes via `read-cypher`: `MATCH (p:Person)-[r]->() RETURN p.name, count(r) ORDER BY count(r) DESC LIMIT 1`
- Provides insights

## Additional Resources

- [Neo4j MCP Official Documentation](https://neo4j.com/docs/mcp/current/)
- [Neo4j MCP GitHub Repository](https://github.com/neo4j/mcp)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Neo4j Developer Guides - MCP](https://neo4j.com/developer/genai-ecosystem/model-context-protocol-mcp/)
- [Getting Started with MCP Servers Blog](https://neo4j.com/blog/developer/model-context-protocol/)
- [Neo4j APOC Documentation](https://neo4j.com/docs/apoc/current/)
