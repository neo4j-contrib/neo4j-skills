---
name: neo4j-driver-php-skill
description: Neo4j PHP Driver (laudis/neo4j-php-client ^3.x) — ClientBuilder, driver
  lifecycle, auto-committed queries, transaction functions (writeTransaction/readTransaction),
  unmanaged transactions (beginTransaction/commit/rollback), result access via CypherList
  and CypherMap, Cypher-to-PHP type mapping, ParameterHelper, URL schemes, SessionConfiguration,
  TransactionConfiguration, Aura and cluster support. Use when writing PHP code that
  connects to Neo4j via Bolt or routed protocol. Package is laudis/neo4j-php-client.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT cover Laravel MCP integration — use neo4j-laravel-boost-skill.
  Does NOT cover driver version migration — use neo4j-migration-skill.
version: 1.0.0
allowed-tools: Bash
---

## When to Use
- Writing PHP code that connects to Neo4j
- Setting up ClientBuilder, transaction functions, or unmanaged transactions
- Debugging result handling, type mapping, or Aura/cluster connectivity
- Reviewing Neo4j driver usage in PHP code

## When NOT to Use
- **Writing/optimizing Cypher** → `neo4j-cypher-skill`
- **Laravel + MCP integration** → `neo4j-laravel-boost-skill`
- **Driver version upgrades** → `neo4j-migration-skill`

---

## Installation

```bash
composer require laudis/neo4j-php-client
```

If `composer require` fails → verify PHP >= 8.0 and extensions `ext-bcmath`, `ext-json`, `ext-sockets` are installed. **Stop and report.**

> HTTP/HTTPS drivers removed in v3.3.0. Use only `bolt://`, `bolt+s://`, `neo4j://`, or `neo4j+s://` URIs.

---

## Environment Variables

Load credentials from environment — never hardcode.

```php
$uri      = getenv('NEO4J_URI')      ?: 'bolt://localhost:7687';
$user     = getenv('NEO4J_USERNAME') ?: 'neo4j';
$password = getenv('NEO4J_PASSWORD') ?: '';
$database = getenv('NEO4J_DATABASE') ?: 'neo4j';
```

`.env` file format:
```
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=secret
NEO4J_DATABASE=neo4j
```

Add `.env` to `.gitignore`. Use [vlucas/phpdotenv](https://github.com/vlucas/phpdotenv) only if no built-in mechanism exists (Laravel and Symfony load `.env` automatically):

```bash
composer require vlucas/phpdotenv
```
```php
$dotenv = Dotenv\Dotenv::createImmutable(__DIR__);
$dotenv->load();
```

---

## Client Lifecycle

Create **one client per application**. Expensive to create; reuse across requests.

```php
use Laudis\Neo4j\Authentication\Authenticate;
use Laudis\Neo4j\ClientBuilder;

$client = ClientBuilder::create()
    ->withDriver('default', $uri, Authenticate::basic($user, $password))
    ->withDefaultDriver('default')
    ->build();
```

For Aura or cluster with routing:

```php
use Laudis\Neo4j\Authentication\Authenticate;

$client = ClientBuilder::create()
    ->withDriver('aura', 'neo4j+s://xxxx.databases.neo4j.io',
        Authenticate::basic($user, $password))
    ->withDefaultDriver('aura')
    ->build();
```

URI schemes:

| Driver | Scheme | TLS valid cert | TLS self-signed |
|---|---|---|---|
| neo4j (routing) | `neo4j` | `neo4j+s` | `neo4j+ssc` |
| bolt (single) | `bolt` | `bolt+s` | `bolt+ssc` |

Default if no scheme given: `bolt://localhost:7687?database=neo4j`.

❌ Never create a new client per query — create one instance per script execution and share it.

---

## Choosing the Right Approach

| Approach | Method | Auto-retry | Use when |
|---|---|---|---|
| Transaction functions | `writeTransaction()` / `readTransaction()` | ✅ | **Default** — production, Aura, clusters, any HA setup |
| Auto-committed | `run()` / `runStatement()` | ❌ | Simple scripts, one-offs, non-critical reads |
| Unmanaged | `beginTransaction()` | ❌ | Need explicit commit/rollback control |

---

## Transaction Functions (Default)

Default for all production code. Driver re-executes callback on transient errors, commits on success, rolls back on timeout, and routes to the correct server (leader for writes, followers for reads).

```php
use Laudis\Neo4j\Contracts\TransactionInterface;

// Write
$result = $client->writeTransaction(static function (TransactionInterface $tsx) {
    $result = $tsx->run(
        'MERGE (p:Person {email: $email}) RETURN p.name AS name',
        ['email' => 'alice@example.com']
    );
    return $result->first()->get('name');
});

// Read
$names = $client->readTransaction(static function (TransactionInterface $tsx) {
    return $tsx->run('MATCH (p:Person) RETURN p.name AS name')
               ->pluck('name')
               ->toArray();
});
```

> **ATTENTION**: The callback must be **idempotent** — the driver re-runs it on retry.
> Move side effects (HTTP calls, emails, external counters) **outside** the callback.

```php
// BAD — external counter incremented on every retry
$client->writeTransaction(function (TransactionInterface $tsx) use ($counter) {
    $counter->increment();
    $tsx->run('MERGE (x:Node {id: $id})', ['id' => Uuid::v4()]);
});

// GOOD — generate ID outside, pass in; counter incremented once after success
$id = Uuid::v4();
$client->writeTransaction(static function (TransactionInterface $tsx) use ($id) {
    $tsx->run('MERGE (x:Node {id: $id})', ['id' => $id]);
});
$counter->increment();
```

---

## Auto-committed Queries

Use for simple, non-critical queries only. No automatic retry.

```php
// Single query — optional params, optional connection alias
$client->run(
    'MERGE (user:User {email: $email})',
    ['email' => 'bob@example.com'],
    'default'           // connection alias (optional)
);

// Statement object
use Laudis\Neo4j\Databags\Statement;

$statement = new Statement(
    'MERGE (user:User {email: $email})',
    ['email' => 'bob@example.com']
);
$client->runStatement($statement);

// Multiple statements in one call
$client->runStatements([
    Statement::create('MERGE (a:A {id: $id})', ['id' => 1]),
    Statement::create('MERGE (b:B {id: $id})', ['id' => 2]),
]);
```

---

## Unmanaged Transactions

Use for explicit commit/rollback control (see decision table above).

```php
use Laudis\Neo4j\Databags\Statement;

// Open transaction with optional initial statements
$tsx = $client->beginTransaction(
    [Statement::create('MERGE (x:Person {email: $e})', ['e' => 'a@b.com'])],
    'default'   // connection alias
);

// Run statements within the open transaction
$result  = $tsx->run('MATCH (x) RETURN x LIMIT 100');
$results = $tsx->runStatements([
    Statement::create('MATCH (x) RETURN x LIMIT 100'),
]);

// Finish
$tsx->commit();
// or:
$tsx->rollback();
```

> `beginTransaction()` returns only the transaction object — results of initial statements are discarded.

Always pair `beginTransaction()` with `commit()` or `rollback()`. If an exception occurs before `commit()` → call `rollback()` in a `catch` block to prevent transaction leaks.

---

## Result Access

Results are returned as a `CypherList` of `CypherMap` rows.

```php
$results = $client->run('MATCH (p:Person) RETURN p.name AS name, p.age AS age');

// Iterate rows
foreach ($results as $row) {
    echo $row->get('name');   // by key; throws if absent
    echo $row->get('age', 0); // with default
}

// First row only
$first = $results->first();

// Pluck a single column
$names = $results->pluck('name')->toArray();

// Check count
$count = $results->count();
```

Node and relationship access:

```php
$results = $client->run('MATCH (p:Person)-[r:KNOWS]->(f) RETURN p, r, f');

foreach ($results as $row) {
    $node = $row->get('p');           // Laudis\Neo4j\Types\Node
    $name = $node->getProperty('name');
    $id   = $node->getId();           // internal integer ID (element ID on newer Neo4j/driver versions)

    $rel  = $row->get('r');           // Laudis\Neo4j\Types\Relationship
    $type = $rel->getType();          // 'KNOWS'
}
```

Full type mapping table → [references/type-mapping.md](references/type-mapping.md)

---

## ParameterHelper — List vs Map Disambiguation

Use `ParameterHelper` for empty array params — PHP arrays are ambiguous (list vs map):

```php
use Laudis\Neo4j\ParameterHelper;

// Explicit empty list (CypherList)
$client->run(
    'MATCH (x) WHERE x.slug IN $slugs RETURN x',
    ['slugs' => ParameterHelper::asList([])]
);

// Explicit empty map (CypherMap)
$client->run(
    'CREATE (x:Node $props)',
    ['props' => ParameterHelper::asMap([])]
);
```

---

## Batch Writes with UNWIND

Pass arrays of maps for bulk operations. One transaction for the whole batch — never one per item.

```php
$people = [
    ['name' => 'Alice', 'age' => 30],
    ['name' => 'Bob',   'age' => 25],
];

$client->writeTransaction(static function (TransactionInterface $tsx) use ($people) {
    $tsx->run(
        'UNWIND $rows AS row MERGE (p:Person {name: row.name}) SET p.age = row.age',
        ['rows' => $people]
    );
});
```

---

## Common Errors

| Mistake | Fix |
|---|---|
| Multiple clients per script | Create one client instance and share it |
| String interpolation in Cypher | Always use `$param` placeholders |
| Side effects inside `writeTransaction` callback | Move outside — callback may retry |
| Non-idempotent callback (random ID inside) | Generate ID before the callback; pass via `use` |
| Empty array for list parameter | Use `ParameterHelper::asList([])` |
| Empty array for map parameter | Use `ParameterHelper::asMap([])` |
| `http://` or `https://` URI | Removed in v3.3.0 — use `bolt://` or `neo4j://` |
| Calling `beginTransaction` without `commit` | Transaction leaks — always `commit()` or `rollback()` |
| `first()` on empty result | Throws — check `$results->count()` first |
| Credentials hardcoded | Load from env or `.env` file |

---

## References
- [references/type-mapping.md](references/type-mapping.md) — complete Cypher-to-PHP type table,
  `DateTimeInterface` behavior, Point subtypes, Vector
- [references/configuration.md](references/configuration.md) — DriverConfiguration, SessionConfiguration,
  TransactionConfiguration, access modes, Result Shape

Docs:
- https://github.com/neo4j-php/neo4j-php-client
- https://packagist.org/packages/laudis/neo4j-php-client

---

## Checklist
- [ ] `laudis/neo4j-php-client` installed via Composer (not `neo4j-php-client`)
- [ ] One client created at startup; shared across all requests
- [ ] Credentials loaded from env vars; `.env` in `.gitignore`
- [ ] `writeTransaction` / `readTransaction` used for production code (not `run`)
- [ ] Transaction callback is idempotent — side effects moved outside
- [ ] `$param` placeholders used in all Cypher — no string interpolation
- [ ] `ParameterHelper::asList()` / `asMap()` used for empty array params
- [ ] `bolt://` or `neo4j://` URI scheme — no `http://`
- [ ] `beginTransaction()` always paired with `commit()` or `rollback()`
- [ ] Batch writes use UNWIND with array parameter (not one tx per item)
