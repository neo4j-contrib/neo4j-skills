---
name: neo4j-laravel-boost-skill
description: Use when integrating Neo4j into Laravel 12/13 apps — neo4j/laravel-boost (app knowledge graph, container:graph,
  MCP server via driver/STDIO/HTTP, neo4j-boost:setup, doctor, Cursor MCP config) and
  neo4j-php/neo4j-laravel (DB::connection('neo4j'), Cypher query builder, Neo4jModel,
  HasNeo4jConnection, matchRelationship, vector search, DI bindings; Schema::node()/relationship()
  migrations on neo4j-laravel dev-main only).
  Does NOT handle raw PHP driver / ClientBuilder (including inside Laravel without
  neo4j-laravel) — use neo4j-driver-php-skill.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT handle standalone MCP server setup — use neo4j-mcp-skill.
version: 1.0.5
allowed-tools: Bash
---

## When to Use
- Integrating Neo4j into Laravel 12/13 via `DB::connection('neo4j')`, query builder, `Neo4jModel` (`neo4j-php/neo4j-laravel`); Schema migrations only on `dev-main`
- Querying Laravel app wiring via Boost graph (`container:graph`); labels vary by Boost version — see App Knowledge Graph
- Change impact analysis, uncovering hidden dependencies (facades, `app()`/`resolve()`, helpers, `new`), contributing graph edges
- Adding Neo4j MCP tools to Laravel Boost (`php artisan boost:mcp`), Cursor MCP config, `neo4j-boost:doctor`

## When NOT to Use
- **Raw laudis `ClientBuilder` / `ClientInterface` (even inside Laravel, no `DB::connection('neo4j')`)** → `neo4j-driver-php-skill`
- **Writing/optimizing Cypher** → `neo4j-cypher-skill`
- **Standalone MCP server without Laravel** → `neo4j-mcp-skill`
- **Provisioning Aura instances** → `neo4j-aura-provisioning-skill`

## Package Selection

Two packages. Run `composer show neo4j/laravel-boost neo4j-php/neo4j-laravel` (or read `composer.lock`) before assuming deps. Pick row by **installed** versions; read only matching sections.

| Installed Boost (`composer show`) | `neo4j-php/neo4j-laravel` |
|---|---|
| Packagist `≤1.2.0` (Packagist latest as of review) | **Not** required by Boost — `composer require neo4j-php/neo4j-laravel` for DB/Eloquent |
| GitHub `≥1.3.0` / `dev-main` (Packagist may lag) | **Required** (`^0.0.1` → resolves **only** `0.0.1`); `container:graph` hard-depends on `Neo4jConnection` / `Neo4jModel` |

| Task | Package | Entry | Read |
|---|---|---|---|
| Neo4j MCP tools; app wiring graph (`container:graph`); change-impact | `neo4j/laravel-boost` | Packagist: `composer require --dev neo4j/laravel-boost` (= `≤1.2.0`). Tip graph (`≥1.3.0`): VCS/`dev-main` below → then Steps 2–6 individually | Steps 1–6, App Knowledge Graph (version-gated), Transport Modes, MCP Tools, Troubleshooting |
| App data access: `DB::connection('neo4j')`, query builder, `Neo4jModel`, vector search | `neo4j-php/neo4j-laravel` | Boost `≥1.3.0`/`dev-main`: pulled as `0.0.1`. Packagist Boost `≤1.2.0`: `composer require neo4j-php/neo4j-laravel` (gets `0.0.2`) | App Data Access + [references/neo4j-laravel.md](references/neo4j-laravel.md) |
| Schema migrations (`->node()` / `->relationship()`) | `neo4j-php/neo4j-laravel` **dev-main only** | `composer require neo4j-php/neo4j-laravel:dev-main` (not on Packagist `0.0.x`) | Migrations section marked `[dev-main]` |
| Both MCP + app data | both | Boost `≤1.2.0`: install both. Boost `≥1.3.0`: Boost alone (still only `0.0.1` APIs) | All published sections; skip `[dev-main]` unless on `dev-main` |

### Install Boost `≥1.3.0` / tip (Packagist lags at `1.2.0`)

Packagist has **no** `1.3.0` release — only `≤1.2.0` + `dev-main`. Tip graph labels need GitHub tip:

```bash
composer config repositories.neo4j-boost vcs https://github.com/neo4j-php/neo4j-boost.git
composer require --dev neo4j/laravel-boost:dev-main
```

Then `composer show neo4j/laravel-boost` — confirm version before using `[≥1.3.0]` graph entities.

### `neo4j-laravel` feature matrix — check before using

| Feature | `0.0.1` | Packagist `0.0.2` | `dev-main` |
|---|---|---|---|
| `DB::connection('neo4j')`, query builder, `Neo4jModel`, `matchRelationship` | ✅ | ✅ | ✅ |
| `whereVectorSimilarTo` with embedding **array** | ✅ | ✅ | ✅ |
| Debugbar Cypher capture | ✅ | ✅ | ✅ |
| TransientError retry / nested-tx overrides | ❌ | ✅ | ✅ |
| `whereVectorSimilarTo` with **string** (+ `laravel/ai` `toEmbeddings`) | ❌ | ❌ | ✅ `[dev-main]` |
| `useVectorSimilarityFunction()` | ❌ | ❌ | ✅ `[dev-main]` |
| `Schema::connection('neo4j')->node()` / `relationship()` / `:_LaravelMigration` | ❌ | ❌ | ✅ `[dev-main]` |

Env var names differ: Boost reads `NEO4J_URI`; `neo4j-php/neo4j-laravel` reads `NEO4J_URL`. Set both when using both packages.

## Requirements

| Requirement | Version |
|---|---|
| PHP | ^8.2 |
| Laravel | ^12.0 or ^13.0 (Boost + `neo4j-laravel` tip). Packagist `neo4j-php/neo4j-laravel` `0.0.2` also allows Illuminate ^11 |
| `neo4j/laravel-boost` | ^1.0 (dev). Packagist `≤1.2.0`: pulls `laravel/boost`, `laudis/neo4j-php-client ^3.4` — **omits** `neo4j-laravel`. GitHub `≥1.3.0`/`dev-main`: also requires `neo4j-php/neo4j-laravel ^0.0.1` |
| `neo4j-php/neo4j-laravel` | Packagist latest `0.0.2`. Boost `≥1.3.0` pins `^0.0.1` (= only `0.0.1`). Schema migrations need `dev-main` |
| `laravel/mcp` | Transitive via `laravel/boost` (`^0.7.1\|^0.8\|^0.9\|^1.0`). Do **not** pin `^0.5.1`. Install only if missing |

## Step 1 — Install

```bash
composer require --dev neo4j/laravel-boost
composer show neo4j/laravel-boost   # Packagist resolves ≤1.2.0 unless VCS/dev-main used
```

Pulls `laravel/boost`, `laudis/neo4j-php-client`. Current `laravel/boost` also pulls `laravel/mcp` — check with `composer show laravel/mcp`; install only if missing (do not pin `^0.5.1`). GitHub Boost `≥1.3.0`/`dev-main` also pulls `neo4j-php/neo4j-laravel ^0.0.1`. Packagist Boost `≤1.2.0` does **not** pull `neo4j-laravel`.

```bash
# Packagist Boost ≤1.2.0 only (GitHub ≥1.3.0 already has 0.0.1):
composer require neo4j-php/neo4j-laravel
# Schema::node()/relationship() migrations — only if intentionally on tip:
# composer require neo4j-php/neo4j-laravel:dev-main
```

If fails → verify PHP 8.2+ and Laravel 12/13. **Stop and report.**

## Step 2 — Setup (prefer individual commands)

❌ Do **not** treat `neo4j-boost:setup --no-interaction` as full setup — it **only prints manual instructions** and returns (`SetupCommand`). Post-update hooks using `--no-interaction` are no-ops for install/config.

Interactive `php artisan neo4j-boost:setup` prompts for MCP binary / Cursor config. On **first run** it also calls `neo4j-boost:start-neo4j` (Docker) with no separate confirmation — get user OK before running interactive setup when Docker start is unwanted.

Prefer explicit steps (agent-safe):

```bash
# STDIO only — skip if staying on default driver transport:
php artisan neo4j-boost:install-mcp
# Local Docker Neo4j — confirm with user first (starts container):
php artisan neo4j-boost:start-neo4j
php artisan neo4j-boost:cursor-config   # writes command+args only — add APP_ENV after (Step 5)
```

Interactive flags: `--install-mcp`, `--skip-mcp`, `--no-cursor-config`. Default transport = **driver** (no binary).

## Step 3 — Configure .env

```env
NEO4J_URI=bolt://localhost:7687
# Aura: NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=
```

Set real passwords in `.env` / secrets — never commit or print. Verify `.env` in `.gitignore`. Prompt only on missing-var failure.

## Step 4 — Start local Neo4j

Requires `NEO4J_PASSWORD` in `.env` or `--password=...`. Without either → command exits; set password then retry.

```bash
php artisan neo4j-boost:start-neo4j
```

Runs Docker on `bolt://localhost:7687` and `http://localhost:7474` (APOC enabled). If fails → verify Docker daemon running, ports 7474/7687 free, and password set. **Stop and report.**

Wipe/recreate — **destructive**. Confirm before:
```bash
php artisan neo4j-boost:start-neo4j --recreate
```

## Step 5 — Configure MCP client (Cursor default)

Other editors/agents (Claude Code, VS Code, Windsurf, ...): register a stdio MCP server in that editor's MCP config with `command: php`, `args: ["artisan", "boost:mcp"]`, `env: {APP_ENV: local}`, working directory = Laravel root. Skip `neo4j-boost:cursor-config`.

```bash
php artisan neo4j-boost:cursor-config
```

Writes/merges `.cursor/mcp.json` with **`command` + `args` only** — does **not** write `env`. Replaces any existing `neo4j-boost` / prior Boost MCP server entry — review merge before committing. **Then add `env.APP_ENV=local` manually:**

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

If fails → create `.cursor/mcp.json` manually with JSON above. Restart Cursor after edits.

## Step 6 — Verify

```bash
php artisan neo4j-boost:doctor
```

`doctor` checks transport config / STDIO binary / HTTP reachability — **does not verify Bolt/driver connectivity**. Exit code is often `SUCCESS` even when Neo4j is down. Do **not** treat doctor alone as connectivity proof.

Required smoke (driver default):
- MCP `read-cypher` with `RETURN 1 AS ok`, **or**
- `php artisan container:graph --dry-run`

If doctor reports missing binary on STDIO, or smoke fails → check transport, `.env` credentials, Neo4j running. **Stop and report.**

STDIO only: `php artisan neo4j-boost:test-stdio --tool=get-schema`

## App Knowledge Graph (core feature)

Before any graph query: `composer show neo4j/laravel-boost` — pick the model for **installed** version. Captures **declared** (constructor injection) and **hidden** dependencies (facades, `app()`/`resolve()`, helpers, `new ClassName()`) when scan paths set.

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

Without scan paths → constructor-injected only. Re-export **upserts and deletes stale nodes/edges** (not pure additive `MERGE`) — confirmation gate covers destructive rewrite. If fails → verify DB running + `.env` credentials (`NEO4J_URI` or `NEO4J_DEFAULT_CONNECTION_DSN`). **Stop and report.**

### 2 — Graph model (version-gated)

`:Abstract` / `:Instance` unique key = **`name`** (FQCN or binding key) — never `fqcn`.

**Packagist `≤1.2.0` (default `composer require`):**

```
(:Route)-[:HANDLED_BY]->(:Abstract)-[:RESOLVES_TO {lifetime}]->(:Instance)
  -[:DEPENDS_ON {type,source,confidence,...}]->(:Dependency)-[:IDENTIFIED_AS]->(:Abstract)
(:Route)-[:USES_MIDDLEWARE {order,parameters}]->(:Middleware)-[:IDENTIFIED_AS]->(:Abstract)
(:Event|:Job|:ScheduledTask)-[:HANDLED_BY]->(:Abstract)-[:RESOLVES_TO]->(:Instance)
(:Job)-[:USES_CONNECTION]->(:QueueConnection)
```

**`[≥1.3.0]` / `dev-main` only** (VCS install — Packagist has no `1.3.0`). Extra labels absent on `≤1.2.0` → queries return empty:

```
(:AuthGuard)-[:USES_PROVIDER]->(:AuthProvider)-[:USES_MODEL]->(:Abstract)
(:Policy)-[:FOR_MODEL]->(:Abstract)
(:Policy|:GateAbility|:Notification|:Mailable|:BroadcastChannel|:ArtisanCommand)-[:HANDLED_BY]->(:Abstract)
(:Job|:Mailable)-[:USES_CONNECTION]->(:QueueConnection)
(:ServiceProvider)-[:REGISTERS {type,via}]->(:Abstract)
(:ModelEvent)-[:HANDLED_BY {action}]->(:Abstract)
(:ModelEvent)-[:FOR_MODEL]->(:Abstract)
(:ModelEvent)-[:DISPATCHES]->(:Abstract)
(:Abstract)-[:BINDS_TO]->(:Abstract)
(:Instance)-[:CONTEXTUAL_BINDS {needs,reason}]->(:Abstract)
```

Key attributes:
- `DEPENDS_ON.type`: `constructor_injection`, `method_injection`, `global_helper`, `instantiation`, `facade`, `service_location`
- `DEPENDS_ON.source` (discovery): `reflection`, `static`, `catalog` — plus `agent`/`user` on contributed edges
- `Dependency.access` (node prop, not edge `source`): `di`, `facade`, `global_helper`, `service_location`
- `RESOLVES_TO.lifetime`: `singleton`, `bind`

### 3 — Query

Single class: `get-class-dependency-graph`. Cross-cutting analysis: `read-cypher`:

```cypher
// Full dependency chain from route
MATCH (r:Route)-[:HANDLED_BY]->(:Abstract)-[:RESOLVES_TO]->(root:Instance)
OPTIONAL MATCH path = (root)-[:DEPENDS_ON|IDENTIFIED_AS|RESOLVES_TO*0..8]->(n)
RETURN r, root, path LIMIT 50;

// Inbound dependents on target service — key is `name`, not `fqcn`
MATCH (dep)-[:DEPENDS_ON]->(:Dependency)-[:IDENTIFIED_AS]->(:Abstract {name: 'App\\Services\\PaymentGateway'})
RETURN dep LIMIT 50;
```

Before traversal via MCP: run `EXPLAIN` or `COUNT(*)`. No `LIMIT` → warn. Default `LIMIT 25`. Check `graph_completeness` before concluding zero dependents. On Packagist `≤1.2.0`, do not query Policy/Mailable/Notification/… labels.

### 4 — Contribute missing edges

Use `contribute-graph-knowledge` when static analysis misses runtime wiring:

- `confidence: medium` or `low` → returns `confirmation_required`; prompt user, re-call with `confirmed: true` (`source: user`).
- `confidence: high` → written immediately (`source: agent`).
- Contributed `DEPENDS_ON` edges default `type: service_location`.

Prompts/tutorial → [`docs/PROMPTS.md`](https://github.com/neo4j-php/neo4j-boost/blob/main/docs/PROMPTS.md), [`docs/tutorials/container-graph.md`](https://github.com/neo4j-php/neo4j-boost/blob/main/docs/tutorials/container-graph.md).

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

Boost sends Neo4j credentials **per request** in HTTP mode — **do not** set `NEO4J_USERNAME` / `NEO4J_PASSWORD` on the MCP container. Credentials stay in Laravel `.env`.

```bash
# Linux: add --add-host=host.docker.internal:host-gateway when Neo4j is on the host
docker run --rm -p 8080:8080 \
  -e NEO4J_URI=bolt://host.docker.internal:7687 \
  -e NEO4J_DATABASE=neo4j \
  -e NEO4J_TRANSPORT_MODE=http \
  neo4j/mcp:v1.6.1
```

Laravel `.env` holds credentials (`NEO4J_USERNAME`/`NEO4J_PASSWORD`) + `NEO4J_MCP_TRANSPORT=http` + `NEO4J_MCP_URL=http://localhost:8080/mcp` — not container `-e`.

> Pin `neo4j/mcp:v1.6.1`. MCP 2.x (`latest`) needs `/db/{database}/mcp` + `NEO4J_MCP_*` headers — unsupported by Boost v1.x HTTP client → `neo4j-mcp-skill`.

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

Confirm before `DELETE` / `DETACH DELETE` / `CALL IN TRANSACTIONS` / bulk `write-cypher`.

`get-class-dependency-graph`: `class` (FQCN), `depth` 1–10 (default 4), `direction` `outbound`|`inbound`|`both`, `include_bindings`, `page`, `per_page` (default 100, max 500). Check `graph_completeness` before zero-dependents claims.

## GDS (Optional)

`list-gds-procedures` needs GDS; other tools work without. Docker: `NEO4J_PLUGINS: '["apoc", "graph-data-science"]'` + allowlist `apoc.*,gds.*`. Algorithms → `neo4j-gds-skill`.

## Configuration Reference

`php artisan vendor:publish --tag=neo4j-boost-config` → [references/boost-configuration.md](references/boost-configuration.md)

## Artisan Commands

| Command | Description |
|---|---|
| `neo4j-boost:setup` | Interactive setup only; `--no-interaction` prints manual steps (no-op for install) |
| `neo4j-boost:install-mcp` | Download `neo4j-mcp` binary (STDIO only) |
| `neo4j-boost:start-neo4j` | Start local Neo4j Docker container (confirm before first run) |
| `neo4j-boost:doctor` | Transport/binary/HTTP checks — **not** Bolt proof; smoke with `read-cypher` |
| `neo4j-boost:test-stdio` | End-to-end STDIO handshake test |
| `neo4j-boost:cursor-config` | Write `.cursor/mcp.json` `command`+`args` only — add `env.APP_ENV` manually |
| `container:graph` | Export Laravel application graph to Neo4j (write — confirm target first) |

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

## App Data Access (`neo4j-php/neo4j-laravel`)

Packagist Boost `≤1.2.0`: `composer require neo4j-php/neo4j-laravel` → Packagist latest (`0.0.2`). Boost `≥1.3.0`/`dev-main`: pulls `0.0.1`. Run `composer show neo4j-php/neo4j-laravel` + feature matrix before tip-only APIs.

### Connection (`config/database.php`)

Register `'neo4j'` (no `vendor:publish`). **`DB_CONNECTION=neo4j` required** (secondary-only unsupported). `SESSION_DRIVER=file` keeps sessions/auth off Neo4j.

```env
DB_CONNECTION=neo4j
SESSION_DRIVER=file
NEO4J_URL=bolt://localhost:7687   # neo4j-laravel (Boost uses NEO4J_URI)
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=
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

Laudis `Driver::verifyConnectivity()` (not on the Laravel connection object) → `false` on connect failure; auth / other Neo4j errors still throw — wrap in try/catch. Prefer `DB::connection('neo4j')->select('RETURN 1 AS ok')` for Laravel smoke tests.

### Query / Eloquent (published `0.0.x`)

```php
use Neo4j\Neo4jLaravel\Neo4jModel;
use Neo4j\Neo4jLaravel\Relations\MatchRelationship;

final class Person extends Neo4jModel
{
    protected $fillable = ['name', 'email'];

    public function movies(): MatchRelationship
    {
        return $this->matchRelationship(Movie::class, 'ACTED_IN>');
    }
}

$person = Person::create(['name' => 'Keanu', 'email' => 'keanu@example.com']);
$person->movies()->attach($movie->id, ['roles' => ['Neo']]);
Person::with('movies')->where('email', 'keanu@example.com')->first();
```

- Raw: `DB::connection('neo4j')->select($cypher, $params)`
- Builder: `->table('Person')->matchRelationship('ACTED_IN>', 'Movie', 'role', 'film')` (`Type>` out, `<Type` in, `Type` undirected)
- Class name = label; auto UUID `id`; `$model->elementId()`; `attach`/`sync`/`detach`. `whereHas`/`withCount` unsupported on `MatchRelationship`
- TransientError retry / nested-tx overrides → **`0.0.2+` only** (Boost tip pins `0.0.1` — stock Laravel `transaction()`)

Full examples, bulk edges, transactions, DI, Debugbar → [references/neo4j-laravel.md](references/neo4j-laravel.md)

### Migrations — `[dev-main]` only

**Absent on Packagist `0.0.1` / `0.0.2`.** Needs `neo4j-php/neo4j-laravel:dev-main`. On `0.0.x` → Cypher DDL (`CREATE INDEX` / `CREATE CONSTRAINT`) instead.

❌ `Schema::create()` (SQL-only — throws).
✅ `Schema::connection('neo4j')->node('Person', fn ($n) => $n->unique('email')->index('name'))` / `->relationship(...)`.
Artisan: `migrate --database=neo4j` (history `:_LaravelMigration`). Details → [references/neo4j-laravel.md](references/neo4j-laravel.md)

## References
- [references/neo4j-laravel.md](references/neo4j-laravel.md) — `neo4j-php/neo4j-laravel` config, bulk relationships, Eloquent joins, transactions, DI, vector search, migrations, Debugbar
- [references/boost-configuration.md](references/boost-configuration.md) — Boost env vars, transport settings, `config/neo4j-boost.php` schema
- [App graph prompts](https://github.com/neo4j-php/neo4j-boost/blob/main/docs/PROMPTS.md) · [Container graph tutorial](https://github.com/neo4j-php/neo4j-boost/blob/main/docs/tutorials/container-graph.md)
- [Neo4j Boost GitHub](https://github.com/neo4j-php/neo4j-boost) · [Official Neo4j MCP Server](https://github.com/neo4j/mcp) · [Laravel Boost](https://github.com/laravel/boost)

## Checklist
- [ ] `composer require --dev neo4j/laravel-boost` installed; `composer show laravel/mcp` present (transitive via `laravel/boost` — install only if missing)
- [ ] `composer show neo4j/laravel-boost neo4j-php/neo4j-laravel` checked; graph model + feature matrix match **installed** versions
- [ ] Tip graph (`≥1.3.0`) only after VCS/`dev-main` install — Packagist alone = `≤1.2.0` labels
- [ ] `neo4j-php/neo4j-laravel` present when app data / Eloquent needed (Boost `≤1.2.0`: install separately; `≥1.3.0`: pulled as `0.0.1`)
- [ ] Setup via individual commands (`install-mcp` / `start-neo4j` gated / `cursor-config`) — not `--no-interaction` alone
- [ ] `.env` defines `NEO4J_URI` (Boost) and `NEO4J_URL` (`neo4j-laravel` if used), `NEO4J_USERNAME`, non-empty `NEO4J_PASSWORD`; `.env` in `.gitignore`
- [ ] Transport selected: `driver` (default), `stdio` (requires `install-mcp`), or `http` (no credentials on MCP container)
- [ ] Neo4j running locally via `start-neo4j` (password set; user confirmed) or accessible remotely
- [ ] `.cursor/mcp.json` has `command`/`args` from `cursor-config` **plus** manual `"env": {"APP_ENV": "local"}`
- [ ] Workspace opened at Laravel root directory
- [ ] Smoke test passed (`read-cypher` or `container:graph --dry-run`) — doctor alone not sufficient
- [ ] `container:graph --dry-run` shown + user confirmation obtained before `container:graph` write (stale delete/replace)
- [ ] User confirmation obtained before `neo4j-boost:start-neo4j --recreate`
- [ ] `container:graph` executed before querying dependency graph; queries use `:Abstract {name: ...}`
- [ ] `NEO4J_CONTAINER_GRAPH_STATIC_SCAN_PATHS` configured if hidden dependencies needed
- [ ] `graph_completeness` checked before declaring class has no dependents
- [ ] `EXPLAIN` or `COUNT(*)` run before unbounded MCP traversals (default `LIMIT 25`)
- [ ] User confirmation obtained before destructive `write-cypher` (`DELETE`, `DETACH DELETE`, bulk writes)
- [ ] If using `neo4j-laravel`: `DB_CONNECTION=neo4j`, `SESSION_DRIVER=file`, `'neo4j'` in `config/database.php` (`NEO4J_URL`)
- [ ] Schema `->node()`/`->relationship()` migrations + TransientError retry used only on versions that support them
