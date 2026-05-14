---
name: neo4j-mcp-skill
description: >
  Use when installing, configuring, or troubleshooting the official Neo4j MCP server
  (neo4j/mcp): connecting Claude Code, Claude Desktop, Cursor, Windsurf, VS Code,
  Kiro, or other MCP-compatible editors to a Neo4j database via stdio or HTTP
  transport. Covers the four MCP tools (get-schema, read-cypher, write-cypher,
  list-gds-procedures), read-only mode, and multi-database configuration.
  Does NOT cover writing Cypher queries via those tools — use neo4j-cypher-skill.
  Does NOT cover agent memory — use neo4j-agent-memory-skill.
  Does NOT cover Aura instance provisioning — use neo4j-aura-provisioning-skill.
allowed-tools: Bash, WebFetch
---

# Neo4j MCP Skill

Installs and configures the [official Neo4j MCP server](https://github.com/neo4j/mcp) so AI agents can connect to Neo4j via any MCP-compatible client.

## When to Use

- Connecting Claude Code, Claude Desktop, Cursor, Windsurf, VS Code, Kiro, or another editor to Neo4j via MCP
- Installing `neo4j-mcp-server` and writing the correct config for a specific editor
- Switching between stdio and HTTP transport
- Enabling or disabling write access (`NEO4J_READ_ONLY`)
- Troubleshooting "MCP server not found" or connection errors

## When NOT to Use

- **Writing or optimizing Cypher queries** → use `neo4j-cypher-skill`
- **Provisioning a new Neo4j Aura instance** → use `neo4j-aura-provisioning-skill`
- **Agent long-term memory** → use `neo4j-agent-memory-skill`
- **neo4j-admin / cypher-shell / aura-cli** → use `neo4j-cli-tools-skill`

---

## Available MCP Tools

| Tool | Type | What it does |
|---|---|---|
| `get-schema` | read | Returns labels, relationship types, property keys, and indexes |
| `read-cypher` | read | Executes read-only Cypher (`MATCH`, `RETURN`, `SHOW`) |
| `write-cypher` | write | Executes write Cypher (`MERGE`, `CREATE`, `SET`, `DELETE`) — disabled when `NEO4J_READ_ONLY=true` |
| `list-gds-procedures` | read | Lists available Graph Data Science procedures (requires GDS plugin) |

---

## Installation

### Step 1 — Install and find the absolute path

```bash
# Option A: pip (recommended)
pip install neo4j-mcp-server

# Option B: Download binary
# https://github.com/neo4j/mcp/releases -- macOS, Linux, Windows binaries

# Option C: Docker
docker pull neo4j/mcp
```

**Get the absolute path — you will need this in Step 3:**
```bash
which neo4j-mcp          # e.g. /usr/local/bin/neo4j-mcp
                         # or:  /Users/you/project/.venv/bin/neo4j-mcp  (if installed in venv)

neo4j-mcp --version      # confirm it runs
```

> **Why absolute path matters**: editors (Claude Code, Cursor, Claude Desktop) spawn the MCP server as a subprocess using their own restricted PATH — not your shell's PATH. On macOS, GUI apps do not inherit `.zshrc` or `.zprofile`. Using `neo4j-mcp` as the command will silently fail; using `/full/path/to/neo4j-mcp` always works. Always use the output of `which neo4j-mcp` in the `command` field below.

### Step 2 — Prepare credentials

```bash
# .env (gitignored)
NEO4J_URI=neo4j+s://<instance>.databases.neo4j.io   # Aura
# or bolt://localhost:7687                           # local
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password>
NEO4J_DATABASE=neo4j
```

Verify connectivity before configuring the editor:
```bash
source .env
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
  "RETURN 'connected' AS status"
# If cypher-shell not available: python3 -c "
# from neo4j import GraphDatabase, __version__
# d = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USERNAME','$NEO4J_PASSWORD'))
# d.verify_connectivity(); print('connected'); d.close()"
```

### Step 3 — Configure your editor

Pick the config block for your editor. All use STDIO transport (the MCP server runs as a subprocess of the editor).

**Claude Code** — add to `~/.claude/settings.json`. If the file already exists, merge the `neo4j` block into the existing `mcpServers` object — do not replace the whole file.

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "/full/path/to/neo4j-mcp",
      "env": {
        "NEO4J_URI": "neo4j+s://<host>",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "<password>",
        "NEO4J_DATABASE": "neo4j",
        "NEO4J_READ_ONLY": "true"
      }
    }
  }
}
```

CLI alternative (sets command only — you still need to add env vars to the file):
```bash
claude mcp add neo4j /full/path/to/neo4j-mcp
```

**Claude Desktop**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "/full/path/to/neo4j-mcp",
      "env": {
        "NEO4J_URI": "neo4j+s://<host>",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "<password>",
        "NEO4J_DATABASE": "neo4j",
        "NEO4J_READ_ONLY": "true"
      }
    }
  }
}
```

**VS Code** — `.vscode/mcp.json` (note: uses `servers`, not `mcpServers` — different from all other editors):
```json
{
  "servers": {
    "neo4j": {
      "type": "stdio",
      "command": "/full/path/to/neo4j-mcp",
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password",
        "NEO4J_DATABASE": "neo4j",
        "NEO4J_READ_ONLY": "true"
      }
    }
  }
}
```

**Cursor** — global: `~/.cursor/mcp.json` / project: `.cursor/mcp.json` (same structure as Claude Code, uses `mcpServers`).

**Windsurf** — global: `~/.codeium/windsurf/mcp_config.json` / project: `.windsurf/mcp_config.json` (same structure as Claude Code, uses `mcpServers`).

**Kiro** — global: `~/.kiro/settings/mcp.json` / project: `.kiro/settings/mcp.json`. Supports `${VARIABLE}` to pull from the shell environment exported before the editor launched:
```json
{
  "mcpServers": {
    "neo4j": {
      "command": "/full/path/to/neo4j-mcp",
      "env": {
        "NEO4J_URI": "${NEO4J_URI}",
        "NEO4J_USERNAME": "${NEO4J_USERNAME}",
        "NEO4J_PASSWORD": "${NEO4J_PASSWORD}",
        "NEO4J_DATABASE": "neo4j",
        "NEO4J_READ_ONLY": "true"
      }
    }
  }
}
```

**Cline** — `~/.vscode/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` (same structure as Claude Code, uses `mcpServers`). Or add via VS Code settings → Cline extension → MCP Servers panel.

**Antigravity** — `mcp_config.json` at project root (same structure as Claude Code, uses `mcpServers`).

### Step 4 — Restart the editor

After editing the config file, restart the editor (or reload the MCP server if the editor supports hot-reload). Verify the server appears in the editor's MCP panel or tool list.

### Step 5 — Smoke test

Run `get-schema` via the agent or directly via MCP. **Do not use "does it return labels?" as the test** — an empty database returns no labels and looks identical to a broken connection.

Use this instead — it succeeds even on an empty DB:
```
read-cypher: RETURN 'connected' AS status
```
Expected: `{ "status": "connected" }`. Any result confirms the server is alive and the credentials are valid.

If the database has data, also run:
```
get-schema
```
and confirm it returns the node labels and relationship types you expect.

---

## HTTP Transport

HTTP transport runs the MCP server as a persistent network service — useful for shared servers, containers, or multiple clients.

```bash
# With credentials baked in (simpler — server authenticates all clients as the same user)
neo4j-mcp \
  --neo4j-transport-mode http \
  --neo4j-http-host 127.0.0.1 \
  --neo4j-http-port 8080 \
  --neo4j-uri bolt://localhost:7687 \
  --neo4j-username neo4j \
  --neo4j-password <password> \
  --neo4j-database neo4j
```

Editor config for HTTP (no credentials in config — server holds them):
```json
{
  "mcpServers": {
    "neo4j-http": {
      "type": "http",
      "url": "http://127.0.0.1:8080/mcp"
    }
  }
}
```

**Per-request auth** (omit `--neo4j-username`/`--neo4j-password` from the server command): each client request must include an `Authorization: Basic <base64(username:password)>` header. Generate the value with:
```bash
echo -n "neo4j:<password>" | base64
```
Then add to the editor config:
```json
{
  "headers": { "Authorization": "Basic bmVvNGo6cGFzc3dvcmQ=" }
}
```

> **Security**: bind to `127.0.0.1`, not `0.0.0.0`. Only change to a broader interface if you need remote access and have TLS + auth in front of it.

---

## Environment Variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `NEO4J_URI` | yes | — | `neo4j+s://` for Aura; `bolt://` for local |
| `NEO4J_USERNAME` | yes | — | |
| `NEO4J_PASSWORD` | yes | — | |
| `NEO4J_DATABASE` | no | server default | Specify explicitly to avoid routing to wrong DB |
| `NEO4J_READ_ONLY` | no | `false` | Set `true` to hide `write-cypher` (safe default for exploration) |

**When to set `NEO4J_READ_ONLY=false`** (or remove the variable): any use case that needs to write data — imports, MERGE, schema changes, GDS write-back. Without write access, the agent will see only three tools (`get-schema`, `read-cypher`, `list-gds-procedures`) and `write-cypher` calls will fail.

---

## APOC Requirement

The MCP server uses APOC for schema introspection (`get-schema`). On **Aura**, APOC is included automatically. On **self-managed Neo4j**, install the APOC plugin and whitelist it:

```
# neo4j.conf
dbms.security.procedures.unrestricted=apoc.*
```

Verify: `read-cypher: RETURN apoc.version() AS v` — if this fails, `get-schema` will return incomplete results.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Server not listed in editor | Config file path wrong, JSON malformed, or editor not restarted | Validate JSON (`python3 -m json.tool settings.json`); confirm correct file for your editor; restart editor |
| `neo4j-mcp: command not found` | Editor PATH doesn't include the binary location | Use absolute path in `command`: run `which neo4j-mcp` in terminal and paste the result |
| Server starts then immediately exits | Python not found (pip install) or wrong binary for OS (binary install) | Run the command manually in terminal to see the error: `/full/path/neo4j-mcp --version` |
| `AuthenticationException` | Wrong credentials | Verify URI + credentials with `cypher-shell` or driver before editing config |
| `write-cypher` tool missing | `NEO4J_READ_ONLY=true` | Remove or set to `false` if writes are needed |
| `ServiceUnavailable` | DB not reachable from editor process | Check firewall, VPN, or whether Aura instance is paused |
| `list-gds-procedures` returns empty | GDS not installed or Aura Free | GDS requires Aura Professional/Enterprise or self-managed with plugin |

---

## Checklist

- [ ] `which neo4j-mcp` run and absolute path noted — this goes in `command`, not `neo4j-mcp`
- [ ] Connectivity verified (`RETURN 'connected'`) before editing editor config
- [ ] Credentials not committed to git; `.env` in `.gitignore`
- [ ] `NEO4J_READ_ONLY` set intentionally — `true` for exploration, `false`/absent for write use cases
- [ ] `NEO4J_DATABASE` specified explicitly
- [ ] Correct config file used for the target editor (VS Code uses `servers`; all others use `mcpServers`)
- [ ] Config is valid JSON (validate with `python3 -m json.tool <file>` before saving)
- [ ] Editor restarted after config change
- [ ] Smoke test passed: `read-cypher: RETURN 'connected' AS status` returns a result
- [ ] APOC available on self-managed: `read-cypher: RETURN apoc.version()`

---

## References

- [MCP Server Docs](https://neo4j.com/docs/mcp/)
- [MCP GitHub](https://github.com/neo4j/mcp)
- [All Neo4j MCP Servers](https://neo4j.com/developer/genai-ecosystem/model-context-protocol-mcp/)
- [GraphAcademy: Developing with Neo4j MCP Tools](https://graphacademy.neo4j.com/courses/genai-mcp-neo4j-tools/)
