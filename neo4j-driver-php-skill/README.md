# neo4j-driver-php-skill

Agent skill for the [Neo4j PHP Client](https://github.com/neo4j-php/neo4j-php-client)
(`laudis/neo4j-php-client`).

## What This Skill Covers

- Installing `laudis/neo4j-php-client` via Composer
- Building a client with `ClientBuilder`
- Transaction functions (`writeTransaction` / `readTransaction`) — default for production
- Auto-committed queries (`run` / `runStatement`)
- Unmanaged transactions (`beginTransaction` / `commit` / `rollback`)
- Result access via `CypherList` and `CypherMap`
- Cypher-to-PHP type mapping
- `ParameterHelper` for list/map disambiguation
- URL schemes (bolt, neo4j, TLS variants)
- `SessionConfiguration`, `TransactionConfiguration`, auth options
- UNWIND batch writes
- Aura and cluster support

## Availability

Part of the [neo4j-skills](https://github.com/neo4j-contrib/neo4j-skills) collection.

## Install the Package

```bash
composer require laudis/neo4j-php-client
```

PHP >= 8.0, with `ext-bcmath`, `ext-json`, `ext-sockets`.
