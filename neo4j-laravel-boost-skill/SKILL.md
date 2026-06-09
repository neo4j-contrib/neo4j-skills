---
name: neo4j-laravel-boost-skill
description: Install and configure neo4j/laravel-boost — Laravel integration for the official
  Neo4j MCP server. Covers composer install, php artisan neo4j-boost:setup, STDIO and HTTP
  transport modes, Cursor MCP config (.cursor/mcp.json), neo4j-boost:start-neo4j Docker
  helper, container:graph DI export, driver transport (in-process Bolt), neo4j-boost:doctor
  diagnostics, and single-server Boost MCP setup. Use when adding Neo4j MCP tools to a
  Laravel 12/13 application via Laravel Boost, or configuring Cursor to connect to Neo4j
  through php artisan boost:mcp.
  Does NOT handle raw PHP driver code — use neo4j-driver-php-skill.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT handle standalone MCP server setup (without Laravel) — use neo4j-mcp-skill.
version: 1.0.0
allowed-tools: Bash WebFetch
---

## When to Use
- Adding Neo4j MCP tools to a Laravel 12 or 13 application
- Running `neo4j-boost:setup` to install/configure the MCP binary
- Configuring Cursor MCP with `php artisan boost:mcp` (single-server pattern)
- Starting local Neo4j via `neo4j-boost:start-neo4j`
- Exporting Laravel container bindings to Neo4j (`container:graph`)
- Choosing between STDIO, HTTP, or driver transport
- Diagnosing Neo4j MCP issues with `neo4j-boost:doctor`

## When NOT to Use
- **Raw PHP driver code (ClientBuilder, transactions)** → `neo4j-driver-php-skill`
- **Writing/optimizing Cypher** → `neo4j-cypher-skill`
- **Standalone MCP server (no Laravel)** → `neo4j-mcp-skill`
- **Provisioning Aura instances** → `neo4j-aura-provisioning-skill`

---

## Requirements

| Requirement | Version |
|---|---|
| PHP | ^8.2 |
| Laravel | ^12.0 or ^13.0 |
| Laravel Boost | ^2.0 |
| Laravel MCP | ^0.5.1 |

`laudis/neo4j-php-client ^3.4` pulled automatically.

---

## Step 1 — Install packages

```bash
composer require laravel/boost laravel/mcp neo4j/laravel-boost
```

If `composer require` fails with dependency errors → verify PHP 8.2+ and Laravel 12/13. **Stop and report.**

---

## Step 2 — Run interactive setup

```bash
php artisan neo4j-boost:setup
```

Setup does:
1. Downloads/verifies `neo4j-mcp` binary for current platform
2. Validates STDIO requirements
3. Writes `.cursor/mcp.json` for Cursor integration

Non-interactive (CI / Composer hook):
```bash
php artisan neo4j-boost:setup --no-interaction
```

Optional — auto-run after `composer update`:
```json
{
  "scripts": {
    "post-update-cmd": [
      "@php artisan neo4j-boost:setup --no-interaction"
    ]
  }
}
```

---

## Step 3 — Configure .env

```env
NEO4J_TRANSPORT_MODE=stdio
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

Verify `.env` is in `.gitignore`. Never hardcode credentials.

---

## Step 4 — Start local Neo4j (STDIO mode)

```bash
php artisan neo4j-boost:start-neo4j
```

Starts Docker container on:
- `bolt://localhost:7687`
- `http://localhost:7474`

APOC enabled by default (required for `get-schema`).

Recreate with fresh data:
```bash
php artisan neo4j-boost:start-neo4j --recreate
```

---

## Step 5 — Configure Cursor MCP

Auto-generate `.cursor/mcp.json`:
```bash
php artisan neo4j-boost:cursor-config
```

Merges with existing servers in `.cursor/mcp.json`. Result:

```json
{
  "mcpServers": {
    "laravel-boost": {
      "command": "php",
      "args": ["artisan", "boost:mcp"],
      "env": {
        "APP_ENV": "local"
      }
    }
  }
}
```

> `APP_ENV=local` required — Laravel Boost only registers commands when `APP_ENV=local` or `APP_DEBUG=true`. Without it: `"There are no commands defined in the 'boost' namespace"`.

**After config change**: reload Cursor or open MCP settings for pickup.

---

## Step 6 — Verify

```bash
php artisan neo4j-boost:doctor
```

Diagnoses transport, binary, password, and readiness. If doctor passes → MCP ready.

End-to-end STDIO test:
```bash
php artisan neo4j-boost:test-stdio --tool=get-schema
```

---

## Transport Modes

| Mode | `NEO4J_MCP_TRANSPORT` | How it works | Binary needed |
|---|---|---|---|
| STDIO (default) | `stdio` | Runs `neo4j-mcp` binary as subprocess | Yes |
| HTTP | `http` | Connects to remote/Docker MCP server | No |
| Driver | `driver` | In-process Bolt via `laudis/neo4j-php-client` | No |

### STDIO (default)

Default. Binary auto-installed by `neo4j-boost:setup`. Subprocess receives `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`.

### HTTP

```env
NEO4J_MCP_TRANSPORT=http
NEO4J_MCP_URL=http://localhost:8080/mcp
```

Start MCP server separately:
```bash
docker run --rm -p 8080:8080 \
  -e NEO4J_URI=bolt://host.docker.internal:7687 \
  -e NEO4J_TRANSPORT_MODE=http \
  docker.io/mcp/neo4j:latest
```

### Driver (in-process Bolt)

No binary, no separate server. Uses `laudis/neo4j-php-client` directly:

```env
NEO4J_MCP_TRANSPORT=driver
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

`get-schema` uses `apoc.meta.schema` when APOC installed; falls back to `db.labels`/`db.relationshipTypes` without APOC.

---

## Available MCP Tools

Single `php artisan boost:mcp` exposes **both** Laravel Boost tools and Neo4j tools:

| Tool | Type | Description |
|---|---|---|
| `get-schema` | read | Labels, relationship types, property keys, indexes |
| `read-cypher` | read | Read-only Cypher (MATCH, RETURN, SHOW) |
| `write-cypher` | write | Write Cypher (MERGE, CREATE, SET, DELETE) |
| `list-gds-procedures` | read | GDS procedures (requires GDS plugin) |
| `get-class-dependency-graph` | read | Laravel DI dependency graph (requires `container:graph` export) |

Boost tools (search-docs, browser-logs, database, etc.) also available from the same server.

---

## Container Graph — DI Export to Neo4j

Export Laravel container bindings as a graph:

```bash
php artisan container:graph               # export
php artisan container:graph --dry-run     # preview only
php artisan container:graph --print-cypher # show Cypher
```

Uses `NEO4J_URI` + `NEO4J_USER`/`NEO4J_USERNAME` + `NEO4J_PASSWORD`. Falls back to `NEO4J_DEFAULT_CONNECTION_DSN` when `NEO4J_URI` is empty.

### Graph model

```
(:Interface:Abstract)-[:BINDS_TO {shared}]->(:Class:Abstract)
(:Class:Abstract)-[:DEPENDS_ON]->(:Class:Abstract|:Interface:Abstract|:UnresolvedDependency:Abstract)
```

Query after export:
```cypher
MATCH p = (a:Abstract)-[:BINDS_TO|DEPENDS_ON*1..6]-(n)
RETURN p LIMIT 200;
```

Idempotent — `MERGE`-based, safe to re-run.

### get-class-dependency-graph tool

After running `container:graph`, use the MCP tool:
```json
{
  "class": "App\\Services\\FooService",
  "direction": "outbound",
  "depth": 4,
  "page": 1,
  "per_page": 100
}
```

Returns `dependencies`, `dependents`, `binding`, pagination metadata.

---

## GDS (Optional)

`list-gds-procedures` requires GDS plugin. Without it: that tool errors; others still work.

Docker with GDS + APOC:
```yaml
neo4j:
  image: neo4j:5-community
  environment:
    NEO4J_AUTH: neo4j/your-password
    NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
    NEO4J_dbms_security_procedures_unrestricted: 'apoc.*,gds.*'
    NEO4J_dbms_security_procedures_allowlist: 'apoc.*,gds.*'
  ports:
    - "7474:7474"
    - "7687:7687"
```

For GDS algorithms → delegate to `neo4j-gds-skill`.

---

## Configuration Reference

Publish config (optional):
```bash
php artisan vendor:publish --tag=neo4j-boost-config
```

Full reference → [references/configuration.md](references/configuration.md)

---

## Artisan Commands

| Command | Description |
|---|---|
| `neo4j-boost:setup` | Interactive STDIO-first setup (binary, env checks, Cursor config) |
| `neo4j-boost:install-mcp` | Download/install the official `neo4j-mcp` binary |
| `neo4j-boost:start-neo4j` | Start local Neo4j Docker for STDIO mode |
| `neo4j-boost:doctor` | Diagnose transport, binary, password, and readiness |
| `neo4j-boost:test-stdio` | Verbose end-to-end STDIO handshake/tool test |
| `neo4j-boost:cursor-config` | Create/update `.cursor/mcp.json` for the MCP server |
| `container:graph` | Export Laravel container bindings to Neo4j graph |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Could not open input file: artisan" | Cursor not running from Laravel app dir | Open **Laravel app folder** as workspace, not package dir |
| "Unexpected token … is not valid JSON" or "no commands in 'boost' namespace" | `APP_ENV` not `local` | Add `"env": {"APP_ENV": "local"}` to `.cursor/mcp.json` server entry |
| "Neo4j password is required for STDIO mode" | `NEO4J_PASSWORD` not set | Set in `.env`; run `php artisan config:clear` |
| STDIO test fails with APOC/meta error | Neo4j missing APOC plugin | `php artisan neo4j-boost:start-neo4j --recreate` |
| HTTP 404: "only handles requests to /mcp" | Cursor sends GET; MCP expects POST | Use Boost STDIO (`php artisan boost:mcp`); don't point Cursor at MCP HTTP URL directly |
| `container:graph` connects to wrong host in Docker | `NEO4J_URI` points to `localhost` inside container | Set `NEO4J_URI` to container network host, or use `NEO4J_DEFAULT_CONNECTION_DSN` |
| GDS errors ("Unknown function 'gds.version'") | GDS plugin not installed | Install GDS; other tools work without it |

---

## References

- [references/configuration.md](references/configuration.md) — full config/neo4j-boost.php reference, env vars, transport details
- [Neo4j Boost GitHub](https://github.com/neo4j-php/neo4j-boost)
- [Official Neo4j MCP Server](https://github.com/neo4j/mcp)
- [Laravel Boost](https://github.com/laravel/boost)

---

## Checklist
- [ ] `composer require laravel/boost laravel/mcp neo4j/laravel-boost` — all three installed
- [ ] `php artisan neo4j-boost:setup` run successfully
- [ ] `.env` has `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`; `.env` in `.gitignore`
- [ ] Transport mode chosen: `stdio` (default), `http`, or `driver`
- [ ] Local Neo4j running (`neo4j-boost:start-neo4j`) or remote URI configured
- [ ] `.cursor/mcp.json` has `"env": {"APP_ENV": "local"}` in server entry
- [ ] Cursor workspace is the Laravel app folder (not the package dir)
- [ ] `php artisan neo4j-boost:doctor` passes
- [ ] Smoke test: `read-cypher: RETURN 'connected' AS status` returns result
- [ ] `container:graph` run if using `get-class-dependency-graph` tool
