---
name: neo4j-mcp-skill
description: Use when installing, configuring, or troubleshooting the official Neo4j MCP server
  (neo4j/mcp) — connecting Claude Code, Claude Desktop, Cursor, Windsurf, VS Code,
  Kiro, or other MCP-compatible editors to a Neo4j database via stdio or HTTP
  transport. Covers the four MCP tools (get-schema, read-cypher, write-cypher,
  list-gds-procedures), read-only mode, and multi-database configuration.
  Does NOT cover writing Cypher queries via those tools — use neo4j-cypher-skill.
  Does NOT cover agent memory — use neo4j-agent-memory-skill.
  Does NOT cover Aura instance provisioning — use neo4j-aura-provisioning-skill.
allowed-tools: Bash, WebFetch
version: 1.0.3
---

# Neo4j MCP Skill

Installs and configures the [official Neo4j MCP server](https://github.com/neo4j/mcp) so AI agents can connect to Neo4j via any MCP-compatible client.

## When to Use

- Connecting Claude Code, Claude Desktop, Cursor, Windsurf, VS Code, Kiro, or another editor to Neo4j via MCP
- Installing the server (`neo4j-mcp` binary or `neo4j-mcp-server` from PyPI) and writing the correct config for a specific editor
- Switching between stdio and HTTP transport
- Enabling or disabling write access (`NEO4J_MCP_READ_ONLY`)
- Troubleshooting "MCP server not found" or connection errors

## When NOT to Use

- **Writing or optimizing Cypher queries** → use `neo4j-cypher-skill`
- **Provisioning a new Neo4j Aura instance** → use `neo4j-aura-provisioning-skill`
- **Agent long-term memory** → use `neo4j-agent-memory-skill`
- **neo4j-admin / cypher-shell / aura-cli** → use `neo4j-cli-tools-skill`

---

## Version: server 2.0.0 (2026-10-28) breaking changes

- Only `NEO4J_MCP_*` env vars (`NEO4J_MCP_URI`, `NEO4J_MCP_USERNAME`, `NEO4J_MCP_PASSWORD`, `NEO4J_MCP_DATABASE`, `NEO4J_MCP_READ_ONLY`, ...) and unprefixed flags (`--uri`, `--username`, `--read-only`, ...). Old `NEO4J_*` names and `--neo4j-*` flags removed — v1.x configs fail.
- STDIO: `NEO4J_MCP_DATABASE` required (no longer defaults to `neo4j`).
- HTTP: endpoint `/db/{database}/mcp`; URI and credentials per request; `NEO4J_MCP_HTTP_ALLOWED_URIS` required.
- Check version: `neo4j-mcp -v`. On v1.x, upgrade rather than mixing old names. [CHANGELOG](https://github.com/neo4j/mcp/blob/main/CHANGELOG.md)

---

## Available MCP Tools

| Tool | Type | What it does |
|---|---|---|
| `get-schema` | read | Returns labels, relationship types, property keys, and indexes |
| `read-cypher` | read | Executes read-only Cypher (`MATCH`, `RETURN`, `SHOW`) |
| `write-cypher` | write | Executes write Cypher (`MERGE`, `CREATE`, `SET`, `DELETE`) — not exposed when `NEO4J_MCP_READ_ONLY=true` |
| `list-gds-procedures` | read | Lists available Graph Data Science procedures; omitted from the tool list when GDS is not installed |

---

## Installation

### Step 1 — Install and find the absolute path

```bash
# Option A: PyPI — command name is neo4j-mcp-server
pip install neo4j-mcp-server        # or run without install: uvx neo4j-mcp-server

# Option B: Homebrew or release binary — command name is neo4j-mcp
brew install neo4j-mcp
# or download from https://github.com/neo4j/mcp/releases (neo4j-mcp_<OS>_<arch>.tar.gz / .zip)

# Option C: Docker
docker pull neo4j/mcp
```

**Get the absolute path — you will need this in Step 3.** Use the name that matches the install method:
```bash
which neo4j-mcp-server   # PyPI, e.g. /Users/you/project/.venv/bin/neo4j-mcp-server
which neo4j-mcp          # Homebrew/binary, e.g. /usr/local/bin/neo4j-mcp

neo4j-mcp -v             # binary: prints version; expect 2.x
```

> **Why absolute path matters**: editors (Claude Code, Cursor, Claude Desktop) spawn the MCP server as a subprocess using their own restricted PATH — not your shell's PATH. On macOS, GUI apps do not inherit `.zshrc` or `.zprofile`. Using a bare command name will silently fail; using the absolute path always works. Always use the output of `which` in the `command` field below (`/full/path/to/neo4j-mcp` in the examples — substitute `neo4j-mcp-server` for PyPI installs).

### Step 2 — Prepare credentials

```bash
# .env (gitignored)
NEO4J_MCP_URI=neo4j+s://<instance>.databases.neo4j.io   # Aura
# or bolt://localhost:7687                               # local
NEO4J_MCP_USERNAME=neo4j
NEO4J_MCP_PASSWORD=<password>
NEO4J_MCP_DATABASE=neo4j
```

Verify connectivity before configuring the editor:
```bash
source .env
cypher-shell -a "$NEO4J_MCP_URI" -u "$NEO4J_MCP_USERNAME" -p "$NEO4J_MCP_PASSWORD" -d "$NEO4J_MCP_DATABASE" \
  "RETURN 'connected' AS status"
# If cypher-shell not available: python3 -c "
# from neo4j import GraphDatabase, __version__
# d = GraphDatabase.driver('$NEO4J_MCP_URI', auth=('$NEO4J_MCP_USERNAME','$NEO4J_MCP_PASSWORD'))
# d.verify_connectivity(); print('connected'); d.close()"
```

### Step 3 — Configure your editor

Pick the config block for your editor. All use STDIO transport (the MCP server runs as a subprocess of the editor).

**Claude Code** — project `.mcp.json` (repo root, under `mcpServers`) or `claude mcp add` (local/user scope, stored in `~/.claude.json`). Never `~/.claude/settings.json` — Claude Code ignores MCP servers there. If `.mcp.json` exists, merge the `neo4j` block into `mcpServers` — do not replace the file. Gitignore `.mcp.json` if it holds a password.

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "/full/path/to/neo4j-mcp",
      "env": {
        "NEO4J_MCP_URI": "neo4j+s://<host>",
        "NEO4J_MCP_USERNAME": "neo4j",
        "NEO4J_MCP_PASSWORD": "<password>",
        "NEO4J_MCP_DATABASE": "neo4j",
        "NEO4J_MCP_READ_ONLY": "true"
      }
    }
  }
}
```

CLI alternative (sets command and env; at least one option such as `--transport stdio` must sit between `--env` and the name):
```bash
claude mcp add --env NEO4J_MCP_URI=neo4j+s://<host> --env NEO4J_MCP_USERNAME=neo4j \
  --env NEO4J_MCP_PASSWORD=<password> --env NEO4J_MCP_DATABASE=neo4j --env NEO4J_MCP_READ_ONLY=true \
  --transport stdio neo4j -- /full/path/to/neo4j-mcp
claude mcp get neo4j   # verify
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
        "NEO4J_MCP_URI": "neo4j+s://<host>",
        "NEO4J_MCP_USERNAME": "neo4j",
        "NEO4J_MCP_PASSWORD": "<password>",
        "NEO4J_MCP_DATABASE": "neo4j",
        "NEO4J_MCP_READ_ONLY": "true"
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
        "NEO4J_MCP_URI": "bolt://localhost:7687",
        "NEO4J_MCP_USERNAME": "neo4j",
        "NEO4J_MCP_PASSWORD": "password",
        "NEO4J_MCP_DATABASE": "neo4j",
        "NEO4J_MCP_READ_ONLY": "true"
      }
    }
  }
}
```

**Cursor** — global: `~/.cursor/mcp.json` / project: `.cursor/mcp.json` (same structure as Claude Code, uses `mcpServers`).

**Windsurf** — path depends on version; check the editor's current MCP docs. Current docs (Devin Desktop): user `~/.config/devin/mcp_config.json`, project `.devin/mcp_config.json`. Older Windsurf installs: `~/.codeium/windsurf/mcp_config.json`.

**Kiro** — global: `~/.kiro/settings/mcp.json` / project: `.kiro/settings/mcp.json`. Supports `${VARIABLE}` to pull from the shell environment exported before the editor launched:
```json
{
  "mcpServers": {
    "neo4j": {
      "command": "/full/path/to/neo4j-mcp",
      "env": {
        "NEO4J_MCP_URI": "${NEO4J_MCP_URI}",
        "NEO4J_MCP_USERNAME": "${NEO4J_MCP_USERNAME}",
        "NEO4J_MCP_PASSWORD": "${NEO4J_MCP_PASSWORD}",
        "NEO4J_MCP_DATABASE": "neo4j",
        "NEO4J_MCP_READ_ONLY": "true"
      }
    }
  }
}
```

**Cline** — `~/.vscode/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` (same structure as Claude Code, uses `mcpServers`). Or add via VS Code settings → Cline extension → MCP Servers panel.

**Antigravity** — global `~/.gemini/config/mcp_config.json`, workspace `.agents/mcp_config.json` (uses `mcpServers`). Remote servers: `serverUrl` (not `httpUrl`).

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

Credentials are per request only — the server refuses to start if `NEO4J_MCP_URI`/`USERNAME`/`PASSWORD`/`DATABASE` (or `--uri`/`--username`/`--password`/`--database`) are set in HTTP mode.

```bash
NEO4J_MCP_TRANSPORT_MODE=http \
NEO4J_MCP_HTTP_HOST=127.0.0.1 \
NEO4J_MCP_HTTP_PORT=8080 \
NEO4J_MCP_HTTP_ALLOWED_URIS=localhost:7687 \
neo4j-mcp
# NEO4J_MCP_HTTP_ALLOWED_URIS: comma-separated host[:port] clients may target (required in 2.0; e.g. *.databases.neo4j.io)
```

Each request: `POST /db/{database}/mcp` with headers `X-Neo4j-MCP-URI: <bolt URI>` (missing → 400) and `Authorization: Basic <base64(user:password)>` or `Bearer <token>` (missing → 401). Optional per-request narrowing: `X-Neo4j-MCP-ReadOnly: true`, `X-Neo4j-MCP-Tools: get-schema,read-cypher`.

Generate the Basic value:
```bash
echo -n "neo4j:<password>" | base64
```

Editor config for HTTP — keys differ per editor:

Claude Code / Cursor (`mcpServers`, `url`):
```json
{
  "mcpServers": {
    "neo4j-http": {
      "type": "http",
      "url": "http://127.0.0.1:8080/db/neo4j/mcp",
      "headers": {
        "X-Neo4j-MCP-URI": "bolt://localhost:7687",
        "Authorization": "Basic <base64>"
      }
    }
  }
}
```
Claude Code CLI: `claude mcp add --transport http neo4j-http http://127.0.0.1:8080/db/neo4j/mcp --header "X-Neo4j-MCP-URI: bolt://localhost:7687" --header "Authorization: Basic <base64>"`.

VS Code (`.vscode/mcp.json`): same entry under `servers` instead of `mcpServers`.

Antigravity: same entry under `mcpServers`, with `serverUrl` in place of `url` and `type`.

Windsurf, Kiro, Cline, Claude Desktop: check the editor's docs for remote-server keys; Claude Desktop JSON config has no direct remote entry — use STDIO there.

> **Security**: bind to `127.0.0.1`, not `0.0.0.0`. Only change to a broader interface if you need remote access and have TLS + auth in front of it.

---

## Environment Variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `NEO4J_MCP_URI` | STDIO: yes | — | `neo4j+s://` for Aura; `bolt://` for local. HTTP: unset (per-request header) |
| `NEO4J_MCP_USERNAME` | STDIO: yes | — | HTTP: unset |
| `NEO4J_MCP_PASSWORD` | STDIO: yes | — | HTTP: unset |
| `NEO4J_MCP_DATABASE` | STDIO: yes | none (2.0) | HTTP: unset (database in URL path) |
| `NEO4J_MCP_READ_ONLY` | no | `false` | Set `true` to hide `write-cypher` (safe default for exploration) |
| `NEO4J_MCP_TELEMETRY` | no | `true` | Set `false` to opt out |
| `NEO4J_MCP_TOOLS` | no | all four | Comma-separated tool allowlist |

Full list (HTTP/TLS, timeouts, logging): [configuration reference](https://neo4j.com/docs/mcp/current/configuration/).

**When to set `NEO4J_MCP_READ_ONLY=false`** (or remove the variable): any use case that needs to write data — imports, MERGE, schema changes, GDS write-back. Without write access, the agent will see only three tools (`get-schema`, `read-cypher`, `list-gds-procedures`) and `write-cypher` calls will fail.

---

## APOC Requirement

The MCP server requires APOC (incl. `apoc.meta.schema`) — without it the server fails its requirement check at the MCP `initialize` handshake ("please ensure the APOC plugin is installed..."). On **Aura**, APOC is included automatically. On **self-managed Neo4j**, install the APOC plugin and allow it:

```
# neo4j.conf
dbms.security.procedures.unrestricted=apoc.*
```

Without the `unrestricted` line, `get-schema` returns an error ("apoc.meta.schema is unavailable because it is sandboxed"), not partial results.

Verify before configuring the editor (`apoc.version()` passing does not prove the meta procedures exist):
```bash
cypher-shell -a "$NEO4J_MCP_URI" -u "$NEO4J_MCP_USERNAME" -p "$NEO4J_MCP_PASSWORD" -d "$NEO4J_MCP_DATABASE" \
  "CALL apoc.meta.schema() YIELD value RETURN 'ok' AS apoc_meta"
# 'ok' → OK; "Unknown procedure"/no such procedure → install APOC (core); 52N34 "restricted" → add dbms.security.procedures.unrestricted=apoc.*
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Server not listed in editor | Config file path wrong, JSON malformed, or editor not restarted | Validate JSON (`python3 -m json.tool <config-file>`); confirm correct file for your editor; restart editor |
| `neo4j-mcp: command not found` | Editor PATH doesn't include the binary location, or PyPI install (command is `neo4j-mcp-server`) | Use absolute path in `command`: run `which neo4j-mcp` (binary/Homebrew) or `which neo4j-mcp-server` (PyPI) and paste the result |
| Server starts then immediately exits | Python not found (pip install) or wrong binary for OS (binary install) | Run the command manually in terminal to see the error: `/full/path/neo4j-mcp -v` |
| `AuthenticationException` | Wrong credentials | Verify URI + credentials with `cypher-shell` or driver before editing config |
| `write-cypher` tool missing | `NEO4J_MCP_READ_ONLY=true` | Remove or set to `false` if writes are needed |
| `ServiceUnavailable` | DB not reachable from editor process | Check firewall, VPN, or whether Aura instance is paused |
| `list-gds-procedures` missing from tool list | GDS not installed or Aura Free | GDS requires Aura Professional/Enterprise or self-managed with plugin |

---

## Checklist

- [ ] Server 2.x (`neo4j-mcp -v`); config uses only `NEO4J_MCP_*` names
- [ ] `which neo4j-mcp` (or `which neo4j-mcp-server` for PyPI) run and absolute path noted — this goes in `command`
- [ ] Connectivity verified (`RETURN 'connected'`) before editing editor config
- [ ] Credentials not committed to git; `.env` in `.gitignore`
- [ ] `NEO4J_MCP_READ_ONLY` set intentionally — `true` for exploration, `false`/absent for write use cases
- [ ] `NEO4J_MCP_DATABASE` set (required in STDIO)
- [ ] Correct config file used for the target editor (Claude Code: `.mcp.json` or `claude mcp add`; VS Code uses `servers`; others `mcpServers`)
- [ ] Config is valid JSON (validate with `python3 -m json.tool <file>` before saving)
- [ ] Editor restarted after config change
- [ ] Smoke test passed: `read-cypher: RETURN 'connected' AS status` returns a result
- [ ] APOC meta works on self-managed: `CALL apoc.meta.schema()` succeeds

---

## References

- [MCP Server Docs](https://neo4j.com/docs/mcp/)
- [MCP GitHub](https://github.com/neo4j/mcp)
- [All Neo4j MCP Servers](https://neo4j.com/developer/genai-ecosystem/model-context-protocol-mcp/)
- [GraphAcademy: Developing with Neo4j MCP Tools](https://graphacademy.neo4j.com/courses/genai-mcp-neo4j-tools/)
