# neo4j-laravel-boost-skill

Agent skill for [neo4j/laravel-boost](https://github.com/neo4j-php/neo4j-boost) —
Laravel integration for the official Neo4j MCP server.

## What This Skill Covers

- Installing `neo4j/laravel-boost` with `laravel/boost` and `laravel/mcp`
- Running `php artisan neo4j-boost:setup` (interactive STDIO-first setup)
- Transport modes: STDIO (default), HTTP, driver (in-process Bolt)
- Cursor MCP configuration via `php artisan neo4j-boost:cursor-config`
- Starting local Neo4j with `neo4j-boost:start-neo4j` (Docker)
- Container graph DI export (`php artisan container:graph`)
- Available MCP tools: get-schema, read-cypher, write-cypher, list-gds-procedures, get-class-dependency-graph
- Diagnostics with `neo4j-boost:doctor` and `neo4j-boost:test-stdio`
- Single-server Boost MCP pattern (one server for Boost + Neo4j tools)
- Troubleshooting common Cursor and transport issues

## Not Covered

- Raw PHP driver code (ClientBuilder, transactions) → use `neo4j-driver-php-skill`
- Cypher query authoring → use `neo4j-cypher-skill`
- Standalone MCP server without Laravel → use `neo4j-mcp-skill`

## Availability

Part of the [neo4j-skills](https://github.com/neo4j-contrib/neo4j-skills) collection.

## Install

```bash
composer require laravel/boost laravel/mcp neo4j/laravel-boost
php artisan neo4j-boost:setup
```

Requirements: PHP 8.2+, Laravel 12 or 13.
