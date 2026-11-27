# neo4j-laravel-boost-skill

Agent skill for [neo4j/laravel-boost](https://github.com/neo4j-php/neo4j-boost) — Neo4j MCP server and Laravel app knowledge graph.

## What This Skill Covers

- **Boost MCP (`neo4j/laravel-boost`)**: `php artisan neo4j-boost:setup`, transport modes (driver default, STDIO, HTTP), Cursor MCP config, `neo4j-boost:doctor`, `neo4j-boost:start-neo4j`
- **App knowledge graph**: `php artisan container:graph`, `get-class-dependency-graph`, `contribute-graph-knowledge`
- **MCP tools**: `get-schema`, `read-cypher`, `write-cypher`, `list-gds-procedures`, `get-class-dependency-graph`, `contribute-graph-knowledge`

## Not Covered

- `neo4j-php/neo4j-laravel` app data access (`DB::connection('neo4j')`, `Neo4jModel`, migrations) — separate package; out of scope
- Raw laudis `ClientBuilder` / `ClientInterface` → use `neo4j-driver-php-skill`
- Cypher query authoring → use `neo4j-cypher-skill`
- Standalone MCP server without Laravel → use `neo4j-mcp-skill`

## Availability

Part of the [agent-skills](https://github.com/neo4j/agent-skills) collection.

## Install

```bash
composer require --dev neo4j/laravel-boost
composer show neo4j/laravel-boost laravel/mcp   # Packagist ≤1.2.0; mcp usually transitive
# Prefer individual commands — setup --no-interaction only prints instructions:
php artisan neo4j-boost:cursor-config   # then add env.APP_ENV=local manually
```

Tip graph labels: `composer require --dev neo4j/laravel-boost:dev-main` (no VCS repo; `composer show` prints `dev-main`, not `1.3.0`). Tip pulls `neo4j-php/neo4j-laravel` transitively for `container:graph` — this skill still does not document that package's DB/Eloquent APIs.

Requirements: PHP 8.2+, Laravel 12 or 13. Prefer driver transport — HTTP Basic Auth is broken in current Boost (`[verify]`).
