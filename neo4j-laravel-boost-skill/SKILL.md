---
name: neo4j-laravel-boost-skill
description: Use when integrating Neo4j into Laravel 12/13 apps — neo4j/laravel-boost (app knowledge graph, container:graph,
  MCP server via driver/STDIO/HTTP, neo4j-boost:setup, doctor, Cursor MCP config) and
  neo4j-php/neo4j-laravel (DB::connection('neo4j'), Cypher query builder, Neo4jModel,
  HasNeo4jConnection, matchRelationship, Schema::node()/relationship() migrations, vector
  search, DI bindings).
  Does NOT handle raw PHP driver code outside Laravel — use neo4j-driver-php-skill.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT handle standalone MCP server setup — use neo4j-mcp-skill.
version: 1.0.2
allowed-tools: Bash
---

## When to Use
- Integrating Neo4j into Laravel 12/13 via `DB::connection('neo4j')`, query builder, `Neo4jModel`, or migrations (`neo4j-php/neo4j-laravel`)
- Querying Laravel app wiring: routes, jobs, events, tasks, policies, mailables (`neo4j/laravel-boost`)
- Change impact analysis, uncovering hidden dependencies (facades, `app()`/`resolve()`, helpers, `new`), contributing graph edges
- Adding Neo4j MCP tools to Laravel Boost (`php artisan boost:mcp`), Cursor MCP config, `neo4j-boost:doctor`

## When NOT to Use
- **Raw PHP driver code outside Laravel (`ClientBuilder`, standalone sessions)** → `neo4j-driver-php-skill`
- **Writing/optimizing Cypher** → `neo4j-cypher-skill`
- **Standalone MCP server without Laravel** → `neo4j-mcp-skill`
- **Provisioning Aura instances** → `neo4j-aura-provisioning-skill`

## Package Selection

Two independent packages — Boost does **not** install `neo4j-php/neo4j-laravel`. Pick row by task; read only the matching sections.

| Task | Package | Entry | Read |
|---|---|---|---|
| Neo4j MCP tools in Laravel Boost; app wiring graph (`container:graph`); change-impact analysis | `neo4j/laravel-boost` | `composer require --dev neo4j/laravel-boost` → `php artisan neo4j-boost:setup` | Steps 1–6, App Knowledge Graph, Transport Modes, MCP Tools, Troubleshooting |
| App data access: `DB::connection('neo4j')`, query builder, `Neo4jModel`, migrations, vector search | `neo4j-php/neo4j-laravel` | `composer require neo4j-php/neo4j-laravel` | App Data Access + [references/neo4j-laravel.md](references/neo4j-laravel.md) |
| Both | both | Install Boost (`--dev`) and `neo4j-php/neo4j-laravel` separately | All |

Env var names differ: Boost reads `NEO4J_URI`; `neo4j-php/neo4j-laravel` reads `NEO4J_URL`. Set both when using both packages.

## Requirements

| Requirement | Version |
|---|---|
| PHP | ^8.2 |
| Laravel | ^12.0 or ^13.0 (Boost); `neo4j-php/neo4j-laravel` also supports Illuminate ^11 |
| `neo4j/laravel-boost` | ^1.0 (dev dependency; pulls `laravel/boost` + `laudis/neo4j-php-client ^3.4`) |
| `neo4j-php/neo4j-laravel` | ^0.0.1 (pre-release; caret pins exactly 0.0.1 — install separately) |
| `laravel/mcp` | ^0.5.1 (dev; not pulled by Boost — install if missing) |

---

## Step 1 — Install

```bash
composer require --dev neo4j/laravel-boost
```

Pulls `laravel/boost`, `laudis/neo4j-php-client`. Does **not** install `neo4j-php/neo4j-laravel` or `laravel/mcp`.

```bash
composer require --dev laravel/mcp   # if missing
composer require neo4j-php/neo4j-laravel   # only when app data access / Neo4jModel needed
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

Verify `.env` in `.gitignore`. Never commit or print credentials. Check `.env` before prompting; prompt only on missing-var failure.

---

## Step 4 — Start local Neo4j

```bash
php artisan neo4j-boost:start-neo4j
```

Runs Docker on `bolt://localhost:7687` and `http://localhost:7474` (APOC enabled). If fails → verify Docker daemon running and ports 7474/7687 free. **Stop and report.**

Wipe and recreate — **destructive**: removes the container and its data. State target container/volume; require explicit user confirmation before running:
```bash
php artisan neo4j-boost:start-neo4j --recreate
```

---

## Step 5 — Configure MCP client (Cursor default)

Other editors/agents (Claude Code, VS Code, Windsurf, ...): register a stdio MCP server in that editor's MCP config with `command: php`, `args: ["artisan", "boost:mcp"]`, `env: {APP_ENV: local}`, working directory = Laravel root. Skip `neo4j-boost:cursor-config`.

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

If fails → create `.cursor/mcp.json` manually. Restart Cursor after edits.

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

Before first write: run `--dry-run`, show node/edge counts + target (`NEO4J_URI` host/database, never credentials), get explicit user confirmation. Never run against a production/Aura database without confirmation.

```bash
php artisan container:graph --dry-run  # preview counts (no write)
php artisan container:graph --print-cypher
php artisan container:graph            # write to Neo4j — confirmed only
```

Capture hidden dependencies — set scan paths:
```env
NEO4J_CONTAINER_GRAPH_STATIC_SCAN_PATHS=/abs/path/to/app/Services
NEO4J_CONTAINER_GRAPH_STATIC_SCAN_PROVIDER_PATHS=/abs/path/to/app/Providers
```

Without scan paths → constructor-injected only. Idempotent (`MERGE`). If fails → verify DB running + `.env` credentials (`NEO4J_URI` or `NEO4J_DEFAULT_CONNECTION_DSN`). **Stop and report.**

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

Before traversal via MCP: run `EXPLAIN` or `COUNT(*)`. No `LIMIT` → warn. Default `LIMIT 25`. Check `graph_completeness` before concluding zero dependents.

### 4 — Contribute missing edges

Use `contribute-graph-knowledge` when static analysis misses runtime wiring:

- `confidence: medium` or `low` → returns `confirmation_required`; prompt user, re-call with `confirmed: true` (`source: user`).
- `confidence: high` → written immediately (`source: agent`).
- Contributed `DEPENDS_ON` edges default `type: service_location`.

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

> Defaults `NEO4J_MCP_VERSION=v1.4.0`; passes v1.x `NEO4J_*` env vars (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`). `neo4j-mcp` 2.0+ requires `NEO4J_MCP_*` + `NEO4J_MCP_DATABASE` — keep `v1.4.0` (1.x) or override `transport.stdio.env` in `config/neo4j-boost.php`.

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
  neo4j/mcp:v1.6.1
```

> Pin 1.x image (`neo4j/mcp:v1.6.1`); revisit when `neo4j/laravel-boost` supports MCP 2.x. `neo4j/mcp:latest` (2.0+) requires `/db/{database}/mcp`, `NEO4J_MCP_TRANSPORT_MODE=http`, `NEO4J_MCP_HTTP_ALLOWED_URIS`, `X-Neo4j-MCP-URI` header (see `neo4j-mcp-skill`) — unsupported by `neo4j/laravel-boost` v1.x HTTP client.

---

## Available MCP Tools

`php artisan boost:mcp` exposes Neo4j + Laravel Boost tools:

| Tool | Type | Description |
|---|---|---|
| `get-schema` | read | Labels, relationship types, property keys, indexes |
| `read-cypher` | read | Read-only Cypher queries (MATCH, RETURN, SHOW) |
| `write-cypher` | write | Mutating Cypher queries (MERGE, CREATE, SET, DELETE) |
| `list-gds-procedures` | read | GDS procedures (requires GDS plugin) |
| `get-class-dependency-graph` | read | App knowledge graph for specified class |
| `contribute-graph-knowledge` | write | Add missing DEPENDS_ON or BINDS_TO edges |

Show query + estimated impact and get explicit user confirmation before executing `DELETE`, `DETACH DELETE`, `CALL IN TRANSACTIONS`, or bulk writes via `write-cypher`.

### get-class-dependency-graph parameters

```json
{
  "class": "App\\Services\\PaymentGateway",
  "depth": 4,
  "direction": "inbound",
  "include_bindings": true,
  "page": 1,
  "per_page": 100
}
```

- `direction`: `outbound`, `inbound`, or `both`
- `depth`: 1–10; `per_page` default 100 (max 500)

Returns `declared_dependencies`, `hidden_dependencies` (`type`, `source`, `confidence`, `visibility`), bindings, unresolved types, `graph_completeness`. Check `graph_completeness` before declaring zero dependents.

---

## GDS (Optional)

`list-gds-procedures` requires GDS plugin; other tools work without it.

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

Full settings reference → [references/boost-configuration.md](references/boost-configuration.md)

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
| `container:graph` | Export Laravel application graph to Neo4j (write — confirm target first) |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Could not open input file: artisan" | Working directory is not Laravel root | Set workspace to Laravel application root |
| "no commands in 'boost' namespace" | `APP_ENV` is not `local` | Add `"env": {"APP_ENV": "local"}` to `.cursor/mcp.json` |
| "Neo4j password is required for STDIO mode" | `NEO4J_PASSWORD` unset | Define in `.env`; run `php artisan config:clear` |
| STDIO test fails on schema introspection | STDIO `neo4j-mcp` expects APOC; driver transport falls back to `db.labels`/`db.relationshipTypes` | Install APOC on target DB. Local Docker: `neo4j-boost:start-neo4j --recreate` (**destructive** — confirm first) |
| HTTP 404 on `/mcp` | Editor sends GET instead of POST | Use `php artisan boost:mcp` (Boost STDIO) |
| `container:graph` fails inside container | `NEO4J_URI` points to container localhost | Use host network alias or `NEO4J_DEFAULT_CONNECTION_DSN` |
| "Unknown function 'gds.version'" | GDS plugin absent | Install GDS; core tools unaffected |
| Graph misses facade/helper usages | Static scan paths unset | Set `NEO4J_CONTAINER_GRAPH_STATIC_SCAN_PATHS`; re-run `container:graph` |

---

## App Data Access (`neo4j-php/neo4j-laravel`)

Requires separate install: `composer require neo4j-php/neo4j-laravel` (not pulled by Boost).

### Connection (`config/database.php`)

Register `'neo4j'` connection (no `vendor:publish`). **Set `DB_CONNECTION=neo4j` as default** — resolving `Client` / `DB::connection('neo4j')` requires default connection to be Neo4j (secondary-only not supported by provider bootstrap yet). Set `SESSION_DRIVER=file` to keep Laravel sessions/auth off Neo4j.

```env
DB_CONNECTION=neo4j
SESSION_DRIVER=file
NEO4J_URL=bolt://localhost:7687   # neo4j-laravel reads NEO4J_URL (Boost reads NEO4J_URI)
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j
```

```php
// config/database.php -> 'connections'
'neo4j' => [
    'driver'   => 'neo4j',
    'url'      => env('NEO4J_URL', 'bolt://localhost:7687'),
    'username' => env('NEO4J_USERNAME', 'neo4j'),
    'password' => env('NEO4J_PASSWORD', ''),
    'database' => env('NEO4J_DATABASE', 'neo4j'),
],
```

Verify: `app(\Laudis\Neo4j\Contracts\ClientInterface::class)->verifyConnectivity()` → `bool` (`true`/`false`; does not throw).

### Raw Cypher, Query Builder, Graph Edges

```php
$db = DB::connection('neo4j');
$rows = $db->select('MATCH (m:Movie {title: $title}) RETURN m.title AS title', ['title' => 'The Matrix']);

// Query builder + Cypher relationship pattern (Type> outgoing, <Type incoming, Type undirected)
$db->table('Person')
    ->matchRelationship('ACTED_IN>', 'Movie', 'role', 'film')
    ->where('film.title', 'The Matrix')
    ->select(['n', 'role', 'film'])
    ->get();
```

### Eloquent (`Neo4jModel` / `HasNeo4jConnection`)

Class name = label (`Movie` → `:Movie`), auto UUID `id`, `$model->elementId()`.

```php
use Neo4j\Neo4jLaravel\Neo4jModel;
use Neo4j\Neo4jLaravel\Relations\MatchRelationship;

class Person extends Neo4jModel
{
    protected $fillable = ['name'];

    public function movies(): MatchRelationship
    {
        return $this->matchRelationship(Movie::class, 'ACTED_IN>');
    }
}

$person->movies()->attach($movie->id, ['roles' => ['Neo']]);
Person::with('movies')->get();
```

`whereHas` / `withCount` on `MatchRelationship` unsupported. Stock Eloquent FK/polymorphic relations work against node properties.

### Migrations (`Schema::connection('neo4j')`)

❌ `Schema::create()` (throws — SQL-only).
✅ `Schema::connection('neo4j')->node()` / `relationship()`:

```php
Schema::connection('neo4j')->node('Person', function ($node) {
    $node->unique('email'); // person_email_unique
    $node->index('name');   // person_name_index
});
Schema::connection('neo4j')->relationship('ACTED_IN', fn ($r) => $r->index('role'));
```

Run stock Artisan commands with `--database=neo4j` (`migrate`, `migrate:status`, `migrate:rollback`; history in `:_LaravelMigration`).

Full `neo4j-laravel` reference (bulk edge ops, transactions, DI container wrappers, vector search, query logging/Debugbar, troubleshooting) → [references/neo4j-laravel.md](references/neo4j-laravel.md)

---

## References

- [references/neo4j-laravel.md](references/neo4j-laravel.md) — `neo4j-php/neo4j-laravel` config, bulk relationships, Eloquent joins, transactions, DI, vector search, migrations, Debugbar
- [references/boost-configuration.md](references/boost-configuration.md) — Boost env vars, transport settings, `config/neo4j-boost.php` schema
- [App graph prompts](https://github.com/neo4j-php/neo4j-boost/blob/main/docs/PROMPTS.md)
- [Container graph tutorial](https://github.com/neo4j-php/neo4j-boost/blob/main/docs/tutorials/container-graph.md)
- [Neo4j Boost GitHub](https://github.com/neo4j-php/neo4j-boost)
- [Official Neo4j MCP Server](https://github.com/neo4j/mcp)
- [Laravel Boost](https://github.com/laravel/boost)

---

## Checklist
- [ ] `composer require --dev neo4j/laravel-boost` installed; `laravel/mcp` present
- [ ] `neo4j-php/neo4j-laravel` installed separately when app data access needed
- [ ] `php artisan neo4j-boost:setup` completed
- [ ] `.env` defines `NEO4J_URI` (Boost) and `NEO4J_URL` (`neo4j-laravel` if used), `NEO4J_USERNAME`, `NEO4J_PASSWORD`; `.env` in `.gitignore`
- [ ] Transport selected: `driver` (default), `stdio` (requires `install-mcp`), or `http`
- [ ] Neo4j running locally via `start-neo4j` or accessible remotely
- [ ] `.cursor/mcp.json` configured with `"env": {"APP_ENV": "local"}`
- [ ] Workspace opened at Laravel root directory
- [ ] `php artisan neo4j-boost:doctor` succeeds
- [ ] Smoke test: `read-cypher` query returns expected status
- [ ] `container:graph --dry-run` shown + user confirmation obtained before `container:graph` write
- [ ] User confirmation obtained before `neo4j-boost:start-neo4j --recreate`
- [ ] `container:graph` executed before querying dependency graph
- [ ] `NEO4J_CONTAINER_GRAPH_STATIC_SCAN_PATHS` configured if hidden dependencies needed
- [ ] `graph_completeness` checked before declaring class has no dependents
- [ ] `EXPLAIN` or `COUNT(*)` run before unbounded MCP traversals (default `LIMIT 25`)
- [ ] User confirmation obtained before destructive `write-cypher` (`DELETE`, `DETACH DELETE`, bulk writes)
- [ ] If using `neo4j-laravel`: `DB_CONNECTION=neo4j`, `SESSION_DRIVER=file`, `'neo4j'` in `config/database.php` (`NEO4J_URL`), migrations use `Schema::connection('neo4j')->node()`/`relationship()`
