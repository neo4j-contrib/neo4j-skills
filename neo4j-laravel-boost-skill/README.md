# neo4j-laravel-boost-skill

Agent skill for [neo4j/laravel-boost](https://github.com/neo4j-php/neo4j-boost) —
Laravel integration for the official Neo4j MCP server.

## What This Skill Covers

- Installing `neo4j/laravel-boost` (pulls `laravel/boost`; install `laravel/mcp` if missing)
- Running `php artisan neo4j-boost:setup` (in-process driver default; optional `neo4j-mcp` binary for STDIO)
- Transport modes: driver (in-process Bolt, default), STDIO, HTTP
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

Part of the [agent-skills](https://github.com/neo4j/agent-skills) collection.

## Install

```bash
composer require neo4j/laravel-boost
# Install laravel/mcp if not already present:
composer require laravel/mcp
php artisan neo4j-boost:setup
```

Requirements: PHP 8.2+, Laravel 12 or 13.
