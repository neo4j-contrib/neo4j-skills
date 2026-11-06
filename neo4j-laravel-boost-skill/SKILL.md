---
name: neo4j-laravel-boost-skill
description: neo4j/laravel-boost — app knowledge graph and MCP server for Laravel: routes,
  middleware, events, jobs, scheduled tasks, policies, notifications, mailables, and container
  wiring exported to Neo4j. Answers architecture queries (what depends on X, impact of changing Y,
  classes built on route invocation), uncovers hidden dependencies (facades, app()/resolve(),
  helpers, new instantiation), and adds missing edges via contribute-graph-knowledge. Covers
  artisan neo4j-boost:setup, doctor, Cursor MCP config, and transport modes (in-process driver default,
  STDIO optional, HTTP optional).
  Does NOT handle raw PHP driver code — use neo4j-driver-php-skill.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT handle standalone MCP server setup — use neo4j-mcp-skill.
version: 1.0.0
allowed-tools: Bash
---

## When to Use
- Querying Laravel app wiring: classes instantiated by routes, jobs, events, tasks, policies, mailables
- Change impact analysis: dependents or dependencies of a class/interface
- Uncovering hidden dependencies: facades, `app()`/`resolve()`, global helpers, `new` instantiation
- Contributing missing graph edges detected during analysis
- Adding Neo4j MCP tools to Laravel 12 or 13 via Laravel Boost
- Configuring Cursor MCP with `php artisan boost:mcp`
- Diagnosing MCP configuration with `neo4j-boost:doctor`

## When NOT to Use
- **Raw PHP driver code (ClientBuilder, sessions)** → `neo4j-driver-php-skill`
- **Writing/optimizing Cypher** → `neo4j-cypher-skill`
- **Standalone MCP server without Laravel** → `neo4j-mcp-skill`
- **Provisioning Aura instances** → `neo4j-aura-provisioning-skill`

---

## Requirements

| Requirement | Version |
|---|---|
| PHP | ^8.2 |
| Laravel | ^12.0 or ^13.0 |
| Laravel Boost | ^2.0 |
| Laravel MCP | ^0.5.1 (dev dependency) |

`laudis/neo4j-php-client ^3.4` pulled automatically.

---

## Step 1 — Install

```bash
composer require neo4j/laravel-boost
```

Pulls `laravel/boost` and `laudis/neo4j-php-client`. Install `laravel/mcp` only if not present:

```bash
composer require laravel/mcp
```

If fails → verify PHP 8.2+ and Laravel 12/13. **Stop and report.**

---

## Step 2 — Run setup

```bash
php artisan neo4j-boost:setup
```

Defaults to **driver transport** (in-process Bolt — no binary required). Flags:

- `--install-mcp` — download `neo4j-mcp` binary for STDIO
- `--skip-mcp` — skip binary installation
- `--no-cursor-config` — skip `.cursor/mcp.json` generation

Non-interactive:
```bash
php artisan neo4j-boost:setup --no-interaction
```

Optional `composer.json` post-update hook:
```json
{
  "scripts": {
    "post-update-cmd": ["@php artisan neo4j-boost:setup --no-interaction"]
  }
}
```

---

## Step 3 — Configure .env

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

Aura connection (driver transport supports `neo4j+s://` directly):
```env
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-aura-password
```

Ensure `.env` in `.gitignore`. Never commit credentials.

---

## Step 4 — Start local Neo4j

```bash
php artisan neo4j-boost:start-neo4j
```

Runs Docker on `bolt://localhost:7687` and `http://localhost:7474`. APOC enabled.

Wipe and recreate:
```bash
php artisan neo4j-boost:start-neo4j --recreate
```

---

## Step 5 — Configure Cursor MCP

```bash
php artisan neo4j-boost:cursor-config
```

Generates/merges `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "laravel-boost": {
      "command": "php",
      "args": ["artisan", "boost:mcp"],
      "env": { "APP_ENV": "local" }
    }
  }
}
```

> `APP_ENV=local` required — Boost registers commands only when `APP_ENV=local` or `APP_DEBUG=true`.

If command fails → create `.cursor/mcp.json` manually with above content. Restart Cursor after edits.

---

## Step 6 — Verify

```bash
php artisan neo4j-boost:doctor
```

If fails → verify transport, re-run `neo4j-boost:setup`, check credentials in `.env`, re-run doctor. **Stop and report** if error persists.

Verbose STDIO handshake test:
```bash
php artisan neo4j-boost:test-stdio --tool=get-schema
```

---

## App Knowledge Graph (core feature)

Graph models routes, middleware, events, jobs, scheduled tasks, auth guards, providers, password brokers, policies, gate abilities, notifications, mailables, broadcast channels, container bindings. Captures **declared** (constructor injection) and **hidden** dependencies (facades, `app()`/`resolve()`, `cache()`, `auth()`, `config()`, `new ClassName()`).

### 1 — Export

```bash
php artisan container:graph            # write to Neo4j
php artisan container:graph --dry-run  # preview counts
php artisan container:graph --print-cypher
```

Capture hidden dependencies: set scan paths before running:
```env
NEO4J_CONTAINER_GRAPH_STATIC_SCAN_PATHS=/abs/path/to/app/Services
NEO4J_CONTAINER_GRAPH_STATIC_SCAN_PROVIDER_PATHS=/abs/path/to/app/Providers
```

Without scan paths → only constructor-injected dependencies exported. Idempotent (`MERGE`-based).

### 2 — Graph model

```
(:Route)-[:HANDLED_BY]->(:Abstract)-[:RESOLVES_TO {lifetime}]->(:Instance)
  -[:DEPENDS_ON {type,source,confidence,...}]->(:Dependency)-[:IDENTIFIED_AS]->(:Abstract)
(:Route)-[:USES_MIDDLEWARE {order,parameters}]->(:Middleware)-[:IDENTIFIED_AS]->(:Abstract)
(:Event|:Job|:ScheduledTask|:Notification|:Mailable|:BroadcastChannel)-[:HANDLED_BY]->(:Abstract)
(:Job|:Mailable)-[:USES_CONNECTION]->(:QueueConnection)
(:AuthGuard)-[:USES_PROVIDER]->(:AuthProvider)-[:USES_MODEL]->(:Abstract)
(:Policy)-[:FOR_MODEL]->(:Abstract)
(:Abstract)-[:BINDS_TO]->(:Abstract)
(:Instance)-[:CONTEXTUAL_BINDS {needs,reason}]->(:Abstract)
```

Key edge attributes:
- `DEPENDS_ON.type`: `constructor_injection`, `method_injection`, `global_helper`, `instantiation`
- `DEPENDS_ON.source`: `di`, `facade`, `global_helper`, `service_location`
- `RESOLVES_TO.lifetime`: `singleton`, `bind`

### 3 — Query

Single class: `get-class-dependency-graph`. Cross-cutting analysis: `read-cypher`:

```cypher
// Full dependency chain from route
MATCH (r:Route)-[:HANDLED_BY]->(:Abstract)-[:RESOLVES_TO]->(root:Instance)
OPTIONAL MATCH path = (root)-[:DEPENDS_ON|IDENTIFIED_AS|RESOLVES_TO*0..8]->(n)
RETURN r, root, path LIMIT 50;

// Inbound dependents on target service
MATCH (dep)-[:DEPENDS_ON]->(:Dependency)-[:IDENTIFIED_AS]->(:Abstract {fqcn: 'App\\Services\\PaymentGateway'})
RETURN dep LIMIT 50;
```

Always inspect `graph_completeness` in `get-class-dependency-graph` output before concluding zero dependents exist.

### 4 — Contribute missing edges

Use `contribute-graph-knowledge` when static analysis misses runtime wiring:

- `confidence: medium` or `low` → returns `confirmation_required` without writing. Prompt user for confirmation, then re-call with `confirmed: true`. Saved with `source: user`.
- `confidence: high` → written immediately with `source: agent`.
- Contributed `DEPENDS_ON` edges default to `type: service_location`.

Query templates and sample prompts → [`docs/PROMPTS.md`](https://github.com/neo4j-php/neo4j-boost/blob/main/docs/PROMPTS.md), [`docs/tutorials/container-graph.md`](https://github.com/neo4j-php/neo4j-boost/blob/main/docs/tutorials/container-graph.md).

---

## Transport Modes

| Mode | `NEO4J_MCP_TRANSPORT` | Mechanism | Binary |
|---|---|---|---|
| Driver **(default)** | `driver` | In-process Bolt via `laudis/neo4j-php-client` | No |
| STDIO | `stdio` | `neo4j-mcp` subprocess | Yes — `neo4j-boost:install-mcp` |
| HTTP | `http` | Remote/Docker MCP server | No |

### STDIO

```env
NEO4J_MCP_TRANSPORT=stdio
```

Download binary: `php artisan neo4j-boost:install-mcp`

### HTTP

```env
NEO4J_MCP_TRANSPORT=http
NEO4J_MCP_URL=http://localhost:8080/mcp
```

```bash
docker run --rm -p 8080:8080 \
  -e NEO4J_URI=bolt://host.docker.internal:7687 \
  -e NEO4J_USERNAME=neo4j \
  -e NEO4J_PASSWORD=your-password \
  -e NEO4J_TRANSPORT_MODE=http \
  neo4j/mcp:latest
```

---

## Available MCP Tools

`php artisan boost:mcp` exposes Neo4j tools and standard Laravel Boost tools:

| Tool | Type | Description |
|---|---|---|
| `get-schema` | read | Labels, relationship types, property keys, indexes |
| `read-cypher` | read | Read-only Cypher queries (MATCH, RETURN, SHOW) |
| `write-cypher` | write | Mutating Cypher queries (MERGE, CREATE, SET, DELETE) |
| `list-gds-procedures` | read | GDS procedures (requires GDS plugin) |
| `get-class-dependency-graph` | read | App knowledge graph for specified class |
| `contribute-graph-knowledge` | write | Add missing DEPENDS_ON or BINDS_TO edges |

### get-class-dependency-graph parameters

```json
{
  "class": "App\\Services\\PaymentGateway",
  "depth": 4,
  "direction": "inbound",
  "include_bindings": true,
  "page": 1,
  "per_page": 50
}
```

- `direction`: `outbound`, `inbound`, or `both`
- `depth`: 1–10

Payload returns `declared_dependencies`, `hidden_dependencies` (with `type`, `source`, `confidence`, `visibility`), bindings, unresolved types, `graph_completeness`. Check `graph_completeness` before declaring no dependents exist.

---

## GDS (Optional)

`list-gds-procedures` requires GDS plugin; other tools function without it.

Docker compose snippet with APOC and GDS:
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

For graph algorithms → delegate to `neo4j-gds-skill`.

---

## Configuration Reference

```bash
php artisan vendor:publish --tag=neo4j-boost-config
```

Full settings reference → [references/configuration.md](references/configuration.md)

---

## Artisan Commands

| Command | Description |
|---|---|
| `neo4j-boost:setup` | Interactive setup (driver default; binary optional for STDIO) |
| `neo4j-boost:install-mcp` | Download `neo4j-mcp` binary (STDIO only) |
| `neo4j-boost:start-neo4j` | Start local Neo4j Docker container |
| `neo4j-boost:doctor` | Verify transport, binary, credentials, connectivity |
| `neo4j-boost:test-stdio` | End-to-end STDIO handshake test |
| `neo4j-boost:cursor-config` | Generate or update `.cursor/mcp.json` |
| `container:graph` | Export Laravel application graph to Neo4j |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Could not open input file: artisan" | Working directory is not Laravel root | Set workspace to Laravel application root |
| "no commands in 'boost' namespace" | `APP_ENV` is not `local` | Add `"env": {"APP_ENV": "local"}` to `.cursor/mcp.json` |
| "Neo4j password is required for STDIO mode" | `NEO4J_PASSWORD` unset | Define in `.env`; run `php artisan config:clear` |
| STDIO test fails on schema introspection | Missing APOC plugin | Run `php artisan neo4j-boost:start-neo4j --recreate` |
| HTTP 404 on `/mcp` | Editor sends GET instead of POST | Use `php artisan boost:mcp` (Boost STDIO) |
| `container:graph` fails inside container | `NEO4J_URI` points to container localhost | Use host network alias or `NEO4J_DEFAULT_CONNECTION_DSN` |
| "Unknown function 'gds.version'" | GDS plugin absent | Install GDS; core tools unaffected |
| Graph misses facade/helper usages | Static scan paths unset | Set `NEO4J_CONTAINER_GRAPH_STATIC_SCAN_PATHS`; re-run `container:graph` |

---

## References

- [references/configuration.md](references/configuration.md) — env vars, transport settings, configuration file schema
- [App graph prompts](https://github.com/neo4j-php/neo4j-boost/blob/main/docs/PROMPTS.md)
- [Container graph tutorial](https://github.com/neo4j-php/neo4j-boost/blob/main/docs/tutorials/container-graph.md)
- [Neo4j Boost GitHub](https://github.com/neo4j-php/neo4j-boost)
- [Official Neo4j MCP Server](https://github.com/neo4j/mcp)
- [Laravel Boost](https://github.com/laravel/boost)

---

## Checklist
- [ ] `composer require neo4j/laravel-boost` installed
- [ ] `php artisan neo4j-boost:setup` completed
- [ ] `.env` defines `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`; `.env` in `.gitignore`
- [ ] Transport selected: `driver` (default), `stdio` (requires `install-mcp`), or `http`
- [ ] Neo4j running locally via `start-neo4j` or accessible remotely
- [ ] `.cursor/mcp.json` configured with `"env": {"APP_ENV": "local"}`
- [ ] Workspace opened at Laravel root directory
- [ ] `php artisan neo4j-boost:doctor` succeeds
- [ ] Smoke test: `read-cypher` query returns expected status
- [ ] `container:graph` executed before querying dependency graph
- [ ] `NEO4J_CONTAINER_GRAPH_STATIC_SCAN_PATHS` configured if hidden dependencies needed
- [ ] `graph_completeness` checked before declaring class has no dependents
