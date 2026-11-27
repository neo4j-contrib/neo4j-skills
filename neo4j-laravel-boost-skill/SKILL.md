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
version: 1.0.6
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

Detect Boost tip: `composer show neo4j/laravel-boost` prints `dev-main`, **or** `Neo4j\Neo4jLaravel\Neo4jConnection` is present via Boost. Do **not** expect `composer show` to print `1.3.0` — tip `composer.json` still says `1.2.0`; git tag `v1.3.0` is **not** Composer-installable (version mismatch).

| Installed Boost | `neo4j-php/neo4j-laravel` |
|---|---|
| Packagist stable `≤1.2.0` | **Not** required by Boost — `composer require neo4j-php/neo4j-laravel` for DB/Eloquent (gets Packagist latest, currently `0.0.2`) |
| `dev-main` (tip; Packagist lag) | **Required** (`^0.0.1` → resolves **only** `0.0.1`); `container:graph` hard-depends on `Neo4jConnection` / `Neo4jModel` |

| Task | Package | Entry | Read |
|---|---|---|---|
| Neo4j MCP tools; app wiring graph; change-impact | `neo4j/laravel-boost` | Stable: `composer require --dev neo4j/laravel-boost` (= `≤1.2.0`). Tip labels: `composer require --dev neo4j/laravel-boost:dev-main` (no VCS repo) → Steps 2–6 | Steps 1–6, App Knowledge Graph (version-gated), Transport Modes, MCP Tools, Troubleshooting |
| App data: `DB::connection('neo4j')`, query builder, `Neo4jModel`, vector search | `neo4j-php/neo4j-laravel` | Boost `dev-main`: pulled as `0.0.1`. Packagist Boost `≤1.2.0`: `composer require neo4j-php/neo4j-laravel` (gets `0.0.2`) | App Data Access + [references/neo4j-laravel.md](references/neo4j-laravel.md) |
| Schema migrations (`->node()` / `->relationship()`) | `neo4j-php/neo4j-laravel` **dev-main only** | Alias required if Boost is also `dev-main` — see tip install below | Migrations section marked `[dev-main]` |
| Both MCP + app data | both | Boost `≤1.2.0`: install both. Boost `dev-main`: Boost alone (= `0.0.1` APIs). Tip + migrations: alias only | All published sections; skip `[dev-main]` unless on tip |

### Install Boost tip (`dev-main`)

Packagist has **no** installable `1.3.0` — only stable `≤1.2.0` + `dev-main`. Tip graph labels need `dev-main` (Packagist already points at tip — **no** VCS repo step):

```bash
composer require --dev neo4j/laravel-boost:dev-main
composer show neo4j/laravel-boost   # expect `dev-main`, not `1.3.0`
```

**Conflict:** Boost `dev-main` requires `neo4j-php/neo4j-laravel ^0.0.1`. A root require of `^0.0.2` or bare `dev-main` **fails**. Tip + Schema migrations need an alias:

```bash
# Only when Boost is already/also dev-main AND you need Schema::node()/relationship():
composer require neo4j-php/neo4j-laravel:"dev-main as 0.0.1"
```

If upgrading from Packagist Boost `≤1.2.0` that already has `neo4j-laravel ^0.0.2` in root `composer.json`: remove/replace that constraint before requiring Boost `dev-main`.

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

Env var names differ: Boost reads `NEO4J_URI`; `neo4j-laravel` README convention uses `NEO4J_URL` in `config/database.php` (`env()` — package itself only auto-reads `NEO4J_QUERY_CHANNEL`). Point `url` at `NEO4J_URI` to share one var, or set both.

## Requirements

| Requirement | Version |
|---|---|
| PHP | ^8.2 |
| Laravel | ^12.0 or ^13.0 (Boost + `neo4j-laravel` tip). Packagist `neo4j-php/neo4j-laravel` `0.0.2` also allows Illuminate ^11 |
| `neo4j/laravel-boost` | ^1.0 (dev). Packagist `≤1.2.0`: pulls `laravel/boost`, `laudis/neo4j-php-client ^3.4` — **omits** `neo4j-laravel`. `dev-main`: also requires `neo4j-php/neo4j-laravel ^0.0.1` |
| `neo4j-php/neo4j-laravel` | Packagist latest `0.0.2`. Boost `dev-main` pins `^0.0.1` (= only `0.0.1`). Schema migrations need `dev-main as 0.0.1` alias when Boost is tip |
| `laravel/mcp` | Transitive via `laravel/boost` (`^0.7.1\|^0.8\|^0.9\|^1.0`). Do **not** pin `^0.5.1`. Install only if missing |

## Step 1 — Install

```bash
composer require --dev neo4j/laravel-boost
composer show neo4j/laravel-boost   # Packagist resolves ≤1.2.0 unless `:dev-main` used
```

Pulls `laravel/boost`, `laudis/neo4j-php-client`. Current `laravel/boost` also pulls `laravel/mcp` — check with `composer show laravel/mcp`; install only if missing (do not pin `^0.5.1`). Boost `dev-main` also pulls `neo4j-php/neo4j-laravel ^0.0.1`. Packagist Boost `≤1.2.0` does **not** pull `neo4j-laravel`.

```bash
# Packagist Boost ≤1.2.0 only (dev-main already has 0.0.1):
composer require neo4j-php/neo4j-laravel
# Schema::node()/relationship() + Boost tip — alias required (see Package Selection):
# composer require neo4j-php/neo4j-laravel:"dev-main as 0.0.1"
```

If fails → verify PHP 8.2+ and Laravel 12/13. **Stop and report.**

## Step 2 — Setup (prefer individual commands)

❌ Do **not** treat `neo4j-boost:setup --no-interaction` as full setup — it **only prints manual instructions** and returns (`SetupCommand`). Post-update hooks using `--no-interaction` are no-ops for install/config.

Interactive `php artisan neo4j-boost:setup` prompts for MCP binary / Cursor config. On **first run** it also calls `neo4j-boost:start-neo4j` (Docker) with no separate confirmation — get user OK before running interactive setup when Docker start is unwanted. Interactive setup also runs `cursor-config` automatically (not a prompt).

Prefer explicit steps (agent-safe):

```bash
# STDIO only — skip if staying on default driver transport.
# --no-cursor-config: install-mcp otherwise auto-runs cursor-config (overwrites mcp.json entry).
php artisan neo4j-boost:install-mcp --no-cursor-config
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

`--recreate` — **destructive** (no volume → data lost). Confirm before. Recreates only when APOC missing or container stopped; running APOC-ready container left alone:
```bash
php artisan neo4j-boost:start-neo4j --recreate
```

## Step 5 — Configure MCP client (Cursor default)

Other editors/agents (Claude Code, VS Code, Windsurf, ...): register a stdio MCP server in that editor's MCP config with `command: php`, `args: ["artisan", "boost:mcp"]`, `env: {APP_ENV: local}`, working directory = Laravel root. Use `install-mcp --no-cursor-config` if downloading STDIO binary — skip bare `cursor-config`.

```bash
php artisan neo4j-boost:cursor-config
```

Writes/merges `.cursor/mcp.json` with **`command` + `args` only** — does **not** write `env`. Replaces whole `laravel-boost` entry + deletes prior `neo4j-boost` key — re-running `install-mcp` / `setup` / `cursor-config` **wipes** a manually added `env.APP_ENV`. Review merge before committing. **Then add `env.APP_ENV=local` manually:**

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

> `APP_ENV=local` (or `APP_DEBUG=true`) required for Boost tools — unless process already inherits that from Laravel `.env` / `BOOST_ENABLED`. Add `env` in `mcp.json` when the MCP process would otherwise run non-local.

If fails → create `.cursor/mcp.json` manually with JSON above. Restart Cursor after edits.

## Step 6 — Verify

```bash
php artisan neo4j-boost:doctor
```

`doctor` checks transport config / STDIO binary / HTTP reachability — **does not verify Bolt/driver connectivity**. Exit code is **always** `SUCCESS` even when Neo4j is down; on `driver` it may still print binary/HTTP noise — ignore. Do **not** treat doctor alone as connectivity proof.

Required smoke (driver default):
- MCP `read-cypher` with `RETURN 1 AS ok`, **or**
- `php artisan container:graph --dry-run`

If doctor reports missing binary on STDIO, or smoke fails → check transport, `.env` credentials, Neo4j running. **Stop and report.**

STDIO only: `php artisan neo4j-boost:test-stdio --tool=get-schema`

## App Knowledge Graph (core feature)

Before any graph query: `composer show neo4j/laravel-boost` — pick the model for **installed** version. Captures **declared** (constructor injection) and **hidden** dependencies (facades, `app()`/`resolve()`, helpers, `new ClassName()`) when scan paths set.

### 1 — Export

Before first write: run `--dry-run`, show node/edge counts + target (`NEO4J_URI` host — export connection hard-codes database `neo4j`; never credentials), get explicit user confirmation. Never run against a production/Aura database without confirmation.

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

Without scan paths → constructor-injected only. Re-export **upserts and deletes stale nodes/edges** (not pure additive `MERGE`), creates constraints, and **deletes every legacy `:Identifier` node** — confirmation gate covers destructive rewrite. If fails → verify DB running + `.env` credentials (`NEO4J_URI` or `NEO4J_DEFAULT_CONNECTION_DSN`). **Stop and report.**

### 2 — Graph model (version-gated)

`:Abstract` / `:Instance` unique key = **`name`** (FQCN or binding key) — never `fqcn`.

**All Boost versions (Packagist `≤1.2.0` + `dev-main`):**

```
(:Route)-[:HANDLED_BY]->(:Abstract)-[:RESOLVES_TO {lifetime}]->(:Instance)
  -[:DEPENDS_ON {type,source,confidence,...}]->(:Dependency)-[:IDENTIFIED_AS]->(:Abstract)
(:Route)-[:USES_MIDDLEWARE {order,parameters}]->(:Middleware)-[:IDENTIFIED_AS]->(:Abstract)
(:Event|:Job|:ScheduledTask)-[:HANDLED_BY]->(:Abstract)-[:RESOLVES_TO]->(:Instance)
(:Job)-[:USES_CONNECTION]->(:QueueConnection)
(:Abstract)-[:BINDS_TO {type,source,confidence,...}]->(:Abstract)
(:Instance)-[:CONTEXTUAL_BINDS {needs,needs_kind,reason}]->(:Abstract)
```

**`[dev-main]` tip only** (Packagist has no installable `1.3.0`). Extra labels absent on `≤1.2.0` → queries return empty:

```
(:AuthGuard)-[:USES_PROVIDER]->(:AuthProvider)-[:USES_MODEL]->(:Abstract)
(:PasswordBroker)-[:USES_PROVIDER]->(:AuthProvider)
(:Policy)-[:FOR_MODEL]->(:Abstract)
(:Policy|:GateAbility|:Notification|:Mailable|:BroadcastChannel|:ArtisanCommand)-[:HANDLED_BY]->(:Abstract)
(:Notification)-[:USES_CHANNEL]->(:NotificationChannel)
(:Mailable)-[:USES_MAILER]->(:Mailer)
(:Job|:Mailable)-[:USES_CONNECTION]->(:QueueConnection)
(:ServiceProvider)-[:REGISTERS {type,via}]->(:Abstract)
(:ModelEvent)-[:HANDLED_BY {action}]->(:Abstract)
(:ModelEvent)-[:FOR_MODEL]->(:Abstract)
(:ModelEvent)-[:DISPATCHES]->(:Abstract)
(:ScheduledTask|:ArtisanCommand)-[:HANDLED_BY {action}]->(:Abstract)
```

Key attributes:
- `DEPENDS_ON.type`: `constructor_injection`, `method_injection`, `global_helper`, `instantiation`, `facade`, `service_location`
- `DEPENDS_ON.source` (discovery): `reflection`, `static`, `catalog` — plus `agent`/`user` on contributed edges; also `provenance`, `visibility`, `remarks`
- `Dependency.access` (node prop, not edge `source`): `di`, `facade`, `global_helper`, `service_location`
- `RESOLVES_TO.lifetime`: `singleton`, `bind`
- `BINDS_TO.type`: `normal` / `singleton` (plus `source`/`confidence`/`provenance`/`remarks`)

### 3 — Query

Single class: `get-class-dependency-graph`. Cross-cutting analysis: `read-cypher`:

```cypher
// Full dependency chain from route
MATCH (r:Route)-[:HANDLED_BY]->(:Abstract)-[:RESOLVES_TO]->(root:Instance)
OPTIONAL MATCH path = (root)-[:DEPENDS_ON|IDENTIFIED_AS|RESOLVES_TO|BINDS_TO*0..8]->(n)
RETURN r, root, path LIMIT 50;

// Inbound dependents on target service — key is `name`, not `fqcn`
MATCH (dep)-[:DEPENDS_ON]->(:Dependency)-[:IDENTIFIED_AS]->(:Abstract {name: 'App\\Services\\PaymentGateway'})
RETURN dep LIMIT 50;
```

Before traversal via MCP: run `COUNT(*)` sizing query (or add `LIMIT`). **`read-cypher` rejects `EXPLAIN`/`PROFILE`** — classifier routes them to `write-cypher` (also rejects write keywords as whole words anywhere, including string literals). No `LIMIT` → warn. Default `LIMIT 25`. Check `graph_completeness` before concluding zero dependents. On Packagist `≤1.2.0`, do not query Policy/Mailable/Notification/… tip-only labels.

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

`get-class-dependency-graph` + `contribute-graph-knowledge` **always** use direct Bolt via `container_graph` / `bolt` config — ignore `NEO4J_MCP_TRANSPORT`. In `stdio`/`http` mode, Laravel `.env` still needs reachable `NEO4J_URI` + credentials for those two tools.

### STDIO

```env
NEO4J_MCP_TRANSPORT=stdio
```

Download binary: `php artisan neo4j-boost:install-mcp --no-cursor-config` (omit flag only when Cursor mcp.json rewrite is wanted).

> Defaults `NEO4J_MCP_VERSION=v1.4.0`; passes v1.x `NEO4J_*` env vars (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`). `neo4j-mcp` 2.0+ requires `NEO4J_MCP_*` + `NEO4J_MCP_DATABASE` — keep `v1.4.0` (1.x) or override `transport.stdio.env` in `config/neo4j-boost.php`.

### HTTP

```env
NEO4J_MCP_TRANSPORT=http
NEO4J_MCP_URL=http://localhost:8080/mcp
```

`[verify]` **HTTP Basic Auth broken in Boost ≤1.2.0 and tip:** `Neo4jHttpClient` reads `config('neo4j-boost.http.username|password')` but shipped config nests keys under `transport.http.*` → auth always skipped. Prefer **driver** transport. Workarounds if HTTP required: publish config and duplicate credentials under top-level `http` key, or open upstream issue. `doctor` health probe reads the correct nested keys — false confidence.

Intended design (docs/README): credentials stay in Laravel `.env`; do **not** put `NEO4J_USERNAME`/`NEO4J_PASSWORD` on the MCP container. Until auth bug fixed, container-without-credentials setup likely returns 401.

```bash
# Linux: add --add-host=host.docker.internal:host-gateway when Neo4j is on the host
docker run --rm -p 8080:8080 \
  -e NEO4J_URI=bolt://host.docker.internal:7687 \
  -e NEO4J_DATABASE=neo4j \
  -e NEO4J_TRANSPORT_MODE=http \
  neo4j/mcp:v1.6.1
```

Laravel `.env`: `NEO4J_MCP_TRANSPORT=http` + `NEO4J_MCP_URL=http://localhost:8080/mcp` (+ credentials for intended Basic Auth once fixed).

> Pin `neo4j/mcp:v1.6.1`. MCP 2.x (`latest`) needs `/db/{database}/mcp` + `NEO4J_MCP_*` headers — unsupported by Boost v1.x HTTP client → `neo4j-mcp-skill`.

## Available MCP Tools

`php artisan boost:mcp` exposes Neo4j + Laravel Boost tools:

| Tool | Type | Description |
|---|---|---|
| `get-schema` | read | Labels, relationship types, property keys (APOC `meta.schema` or `db.labels`/`db.relationshipTypes` fallback — **no indexes**) |
| `read-cypher` | read | Read-only Cypher (`query`, `params`) — rejects `EXPLAIN`/`PROFILE` and write keywords |
| `write-cypher` | write | Mutating Cypher (`query`, `params`) — also accepts EXPLAIN/PROFILE |
| `list-gds-procedures` | read | GDS procedures (requires GDS plugin) |
| `get-class-dependency-graph` | read | App knowledge graph for specified class — **always Bolt** |
| `contribute-graph-knowledge` | write | Add missing DEPENDS_ON or BINDS_TO edges — **always Bolt** |

Confirm before `DELETE` / `DETACH DELETE` / `CALL IN TRANSACTIONS` / bulk `write-cypher`.

`get-class-dependency-graph`: `class` (FQCN), `depth` 1–10 (default 4), `direction` `outbound`|`inbound`|`both`, `include_bindings` (default true), `page`, `per_page` (default 100, max 500). Check `graph_completeness` before zero-dependents claims.

`contribute-graph-knowledge`: `relationship`, `from`, `to`, `confidence` (required), `confirmed`, `reason`, `shared`, `depends_on_type`.

## GDS (Optional)

`list-gds-procedures` needs GDS; other tools work without. Docker: `NEO4J_PLUGINS: '["apoc", "graph-data-science"]'` + allowlist `apoc.*,gds.*`. Algorithms → `neo4j-gds-skill`.

## Configuration Reference

`php artisan vendor:publish --tag=neo4j-boost-config` → [references/boost-configuration.md](references/boost-configuration.md)

## Artisan Commands

| Command | Description |
|---|---|
| `neo4j-boost:setup` | Interactive setup; `--no-interaction` prints manual steps (no-op for install); runs `cursor-config` unless `--no-cursor-config` |
| `neo4j-boost:install-mcp` | Download `neo4j-mcp` binary (STDIO); also runs `cursor-config` unless `--no-cursor-config` |
| `neo4j-boost:start-neo4j` | Start local Neo4j Docker container (confirm before first run) |
| `neo4j-boost:doctor` | Transport/binary/HTTP checks — **not** Bolt proof; always exit SUCCESS; smoke with `read-cypher` |
| `neo4j-boost:test-stdio` | End-to-end STDIO handshake test |
| `neo4j-boost:cursor-config` | Write `.cursor/mcp.json` `command`+`args` only — wipes prior `env`; add `APP_ENV` manually |
| `container:graph` | Export app graph (write — confirm; upserts/deletes stale + drops legacy `:Identifier`) |

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

Packagist Boost `≤1.2.0`: `composer require neo4j-php/neo4j-laravel` → Packagist latest (`0.0.2`). Boost `dev-main`: pulls `0.0.1`. Run `composer show neo4j-php/neo4j-laravel` + feature matrix before tip-only APIs.

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
- [ ] Tip graph only after `:dev-main` (expect `dev-main` in `composer show`, not `1.3.0`) — Packagist alone = `≤1.2.0` labels; `BINDS_TO`/`CONTEXTUAL_BINDS` on all versions
- [ ] `neo4j-php/neo4j-laravel` present when app data / Eloquent needed (Boost `≤1.2.0`: install separately; `dev-main`: pulled as `0.0.1`)
- [ ] Tip + Schema migrations use alias `neo4j-php/neo4j-laravel:"dev-main as 0.0.1"` — bare `dev-main` / `^0.0.2` conflicts with Boost tip
- [ ] Setup via individual commands (`install-mcp --no-cursor-config` / `start-neo4j` gated / `cursor-config`) — not `--no-interaction` alone
- [ ] `.env` defines `NEO4J_URI` (Boost) and `NEO4J_URL` or shared URI (`neo4j-laravel` if used), `NEO4J_USERNAME`, non-empty `NEO4J_PASSWORD`; `.env` in `.gitignore`
- [ ] Transport selected: prefer `driver`; `stdio` needs `install-mcp`; avoid `http` until Basic Auth bug fixed (`[verify]`)
- [ ] Neo4j running locally via `start-neo4j` (password set; user confirmed) or accessible remotely
- [ ] `.cursor/mcp.json` has `command`/`args` **plus** manual `"env": {"APP_ENV": "local"}` when needed; not wiped by later `install-mcp`/`cursor-config`
- [ ] Workspace opened at Laravel root directory
- [ ] Smoke test passed (`read-cypher` or `container:graph --dry-run`) — doctor alone not sufficient (always SUCCESS)
- [ ] `container:graph --dry-run` shown + user confirmation before write (stale delete/replace + `:Identifier` wipe)
- [ ] User confirmation obtained before `neo4j-boost:start-neo4j --recreate`
- [ ] `container:graph` executed before querying dependency graph; queries use `:Abstract {name: ...}`
- [ ] `NEO4J_CONTAINER_GRAPH_STATIC_SCAN_PATHS` configured if hidden dependencies needed
- [ ] `graph_completeness` checked before declaring class has no dependents
- [ ] `COUNT(*)` (not `EXPLAIN` via `read-cypher`) before unbounded MCP traversals (default `LIMIT 25`)
- [ ] User confirmation obtained before destructive `write-cypher` (`DELETE`, `DETACH DELETE`, bulk writes)
- [ ] If using `neo4j-laravel`: `DB_CONNECTION=neo4j`, `SESSION_DRIVER=file`, `'neo4j'` in `config/database.php`
- [ ] Schema `->node()`/`->relationship()` migrations + TransientError retry used only on versions that support them
