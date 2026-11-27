# neo4j-laravel-boost-skill

Agent skill for [neo4j/laravel-boost](https://github.com/neo4j-php/neo4j-boost) and [neo4j-php/neo4j-laravel](https://github.com/neo4j-php/neo4j-laravel) — Neo4j MCP server, app knowledge graph, and Laravel DB/Eloquent integration.

## What This Skill Covers

- **Laravel DB & Eloquent (`neo4j-php/neo4j-laravel`)**: `DB::connection('neo4j')`, Cypher query builder, `Neo4jModel` / `HasNeo4jConnection`, `matchRelationship()`, bulk edge ops, transactions, vector search (array embeddings on Packagist; string embeddings / `Schema::node()` migrations on `dev-main` only), DI bindings
- **Boost MCP (`neo4j/laravel-boost`)**: `php artisan neo4j-boost:setup`, transport modes (driver default, STDIO, HTTP), Cursor MCP config, `neo4j-boost:doctor`, `neo4j-boost:start-neo4j`
- **App knowledge graph**: `php artisan container:graph`, `get-class-dependency-graph`, `contribute-graph-knowledge`
- **MCP tools**: `get-schema`, `read-cypher`, `write-cypher`, `list-gds-procedures`, `get-class-dependency-graph`, `contribute-graph-knowledge`

## Not Covered

- Raw laudis `ClientBuilder` / `ClientInterface` (including inside Laravel without `neo4j-laravel`) → use `neo4j-driver-php-skill`
- Cypher query authoring → use `neo4j-cypher-skill`
- Standalone MCP server without Laravel → use `neo4j-mcp-skill`

## Availability

Part of the [agent-skills](https://github.com/neo4j/agent-skills) collection.

## Install

```bash
composer require --dev neo4j/laravel-boost
composer show neo4j/laravel-boost laravel/mcp   # Packagist ≤1.2.0; mcp usually transitive
# Packagist Boost ≤1.2.0 only — GitHub ≥1.3.0 / tip already pulls neo4j-laravel ^0.0.1:
composer require neo4j-php/neo4j-laravel
# Prefer individual commands — setup --no-interaction only prints instructions:
php artisan neo4j-boost:cursor-config   # then add env.APP_ENV=local manually
```

Tip graph (`≥1.3.0` labels): `composer config repositories.neo4j-boost vcs https://github.com/neo4j-php/neo4j-boost.git` then `composer require --dev neo4j/laravel-boost:dev-main`.

Requirements: PHP 8.2+, Laravel 12 or 13. Packagist Boost `≤1.2.0` does not pull `neo4j-php/neo4j-laravel`; GitHub `≥1.3.0` / `dev-main` requires it (`^0.0.1` → only `0.0.1`). Schema migrations need `neo4j-laravel:dev-main`. Check `composer show` before tip-only APIs.
