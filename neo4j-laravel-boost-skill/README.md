# neo4j-laravel-boost-skill

Agent skill for [neo4j/laravel-boost](https://github.com/neo4j-php/neo4j-boost) and [neo4j-php/neo4j-laravel](https://github.com/neo4j-php/neo4j-laravel) — Neo4j MCP server, app knowledge graph, and Laravel DB/Eloquent integration.

## What This Skill Covers

- **Laravel DB & Eloquent (`neo4j-php/neo4j-laravel`)**: `DB::connection('neo4j')`, Cypher query builder, `Neo4jModel` / `HasNeo4jConnection`, `matchRelationship()`, bulk edge ops, `Schema::connection('neo4j')->node()` / `relationship()` migrations, transactions, vector search, DI bindings
- **Boost MCP (`neo4j/laravel-boost`)**: `php artisan neo4j-boost:setup`, transport modes (driver default, STDIO, HTTP), Cursor MCP config, `neo4j-boost:doctor`, `neo4j-boost:start-neo4j`
- **App knowledge graph**: `php artisan container:graph`, `get-class-dependency-graph`, `contribute-graph-knowledge`
- **MCP tools**: `get-schema`, `read-cypher`, `write-cypher`, `list-gds-procedures`, `get-class-dependency-graph`, `contribute-graph-knowledge`

## Not Covered

- Raw PHP driver code outside Laravel (`ClientBuilder`, standalone sessions) → use `neo4j-driver-php-skill`
- Cypher query authoring → use `neo4j-cypher-skill`
- Standalone MCP server without Laravel → use `neo4j-mcp-skill`

## Availability

Part of the [agent-skills](https://github.com/neo4j/agent-skills) collection.

## Install

```bash
composer require neo4j/laravel-boost
# Install laravel/mcp if not already present:
composer require laravel/mcp
php artisan neo4j-boost:setup
```

Requirements: PHP 8.2+, Laravel 12 or 13.
