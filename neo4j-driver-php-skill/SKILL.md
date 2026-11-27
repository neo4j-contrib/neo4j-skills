---
name: neo4j-driver-php-skill
description: Neo4j PHP Driver (laudis/neo4j-php-client ^3.x) — Client > Driver > Session >
  Transaction architecture, ClientBuilder, driver lifecycle, session-level executeQuery and
  bookmarks, auto-committed queries, transaction functions (writeTransaction/readTransaction),
  unmanaged transactions (beginTransaction/commit/rollback), result access via CypherList
  and CypherMap, Cypher-to-PHP type mapping, ParameterHelper, URL schemes, SessionConfiguration,
  TransactionConfiguration, Aura and cluster support, causal consistency. Use when writing
  PHP code connecting to Neo4j via Bolt or routed protocol.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT cover Laravel DB/Eloquent/Boost MCP (DB::connection('neo4j'), Neo4jModel,
  container:graph) — use neo4j-laravel-boost-skill. Raw laudis ClientBuilder inside Laravel
  (no neo4j-laravel) stays here.
  Does NOT cover driver version migration — use neo4j-migration-skill.
version: 1.0.8
allowed-tools: Bash
---

## When to Use
- Writing PHP code that connects to Neo4j via `laudis/neo4j-php-client`
- Setting up ClientBuilder, sessions, transaction functions, unmanaged transactions
- Preserving causal consistency (read-your-own-writes) across cluster queries
- Debugging result handling, type mapping, Aura/cluster connectivity
- Reviewing Neo4j driver usage in PHP code — including raw `ClientBuilder` / `ClientInterface` inside a Laravel app (container-bound client, no `DB::connection('neo4j')`)

## When NOT to Use
- **Writing/optimizing Cypher** → `neo4j-cypher-skill`
- **Laravel DB / Eloquent / Boost MCP (`DB::connection('neo4j')`, `Neo4jModel`, `container:graph`)** → `neo4j-laravel-boost-skill`
- **Driver version upgrades** → `neo4j-migration-skill`

---

## Installation

```bash
composer require laudis/neo4j-php-client
```

If fails → verify PHP ^8.1, `ext-json`, `ext-mbstring`. Bolt: `ext-bcmath` suggested (composer `suggest`); `ext-sockets` optional — without it driver falls back to stream sockets. **Stop and report.**

> HTTP/HTTPS removed in v3.3.0. Use `bolt://`, `bolt+s://`, `bolt+ssc://`, `neo4j://`, `neo4j+s://`, or `neo4j+ssc://` only.

---

## Environment Variables

Load credentials from env — never hardcode or print values. Read `$_ENV` / `$_SERVER` first — `getenv()` alone fails after phpdotenv `createImmutable()` (no `PutenvAdapter`).

```php
$env = static fn (string $key): ?string =>
    $_ENV[$key] ?? $_SERVER[$key] ?? (getenv($key) !== false ? getenv($key) : null);

$uri      = $env('NEO4J_URI') ?: 'bolt://localhost:7687';
$user     = $env('NEO4J_USERNAME') ?: 'neo4j';
$password = $env('NEO4J_PASSWORD');
$database = $env('NEO4J_DATABASE');  // null/empty → server home/default; set only to deviate

if ($password === null || $password === '') {
    throw new RuntimeException('NEO4J_PASSWORD required');
}
```

`.env` format (set real password; never commit):
```
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=
# NEO4J_DATABASE=neo4j   # omit unless targeting a non-default database
```

Verify `.env` in `.gitignore`. Non-framework scripts: `composer require vlucas/phpdotenv`.

```php
// createImmutable → $_ENV / $_SERVER only. createUnsafeImmutable also enables getenv()/putenv.
Dotenv\Dotenv::createImmutable(__DIR__)->load();
```

---

## Architecture: Client > Driver > Session > Transaction

| Layer | Acquire via | Lifetime | Role |
|---|---|---|---|
| Client | `ClientBuilder::create()->...->build()` | One per app | Maps aliases to drivers; failover by priority; convenience `run`/`*Transaction` (new session per call via retry helper) |
| Driver | `$client->getDriver('alias')` or `Basic\Driver::create($uri, ...)` | One per app | Connection pool, routing table, `verifyConnectivity()`, `getServerInfo()`, `closeConnections()` |
| Session | `$driver->createSession(SessionConfiguration::default())` | One per unit of work / request | Access mode + bookmarks; `executeQuery()`, `close()`. Set database only when non-default — see configuration ref |
| Transaction | `$session->writeTransaction(fn)` / `readTransaction(fn)` / `beginTransaction()` | Atomic unit | Runs Cypher; managed (auto-retry) or unmanaged |

Client convenience methods open a **new session per call** — bookmarks do not chain across `$client->run()` / `*Transaction()` calls. For causal consistency (read-your-own-writes): use one explicit Session, or hand over via `getLastBookmark()` + `withBookmarks([...])`. Bookmarks never cross PHP requests/processes without explicit handover.

---

## Client Lifecycle

One client per app — create at startup, share across requests.

```php
use Laudis\Neo4j\Authentication\Authenticate;
use Laudis\Neo4j\ClientBuilder;
use Laudis\Neo4j\Databags\SessionConfiguration;

$builder = ClientBuilder::create()
    ->withDriver('default', $uri, Authenticate::basic($user, $password))
    ->withDefaultDriver('default');
if ($database) {
    $builder = $builder->withDefaultSessionConfiguration(
        SessionConfiguration::default()->withDatabase($database)
    );
}
$client = $builder->build();
```

Direct Driver instantiation (bypasses ClientBuilder alias map):

```php
use Laudis\Neo4j\Basic\Driver;
use Laudis\Neo4j\Authentication\Authenticate;

$driver = Driver::create($uri, authenticate: Authenticate::basic($user, $password));
try {
    // false on ConnectException (bolt://) or ConnectException|ConnectionPoolException (neo4j://);
    // auth / other Neo4j errors still throw
    if (! $driver->verifyConnectivity()) {
        throw new RuntimeException('Neo4j unreachable');
    }
} catch (\Laudis\Neo4j\Exception\Neo4jException $e) {
    throw new RuntimeException('Neo4j connectivity/auth failed: '.$e->getMessage(), 0, $e);
}
$info = $driver->getServerInfo(); // getAddress(), getProtocol(), getAgent() — no version accessor
```

`$client->getDriver('alias')` eagerly calls `verifyConnectivity` and throws `RuntimeException("Cannot connect to any server on alias…")` on failure — wrap in try/catch.

URI schemes:

| Driver | Scheme | TLS valid cert | TLS self-signed |
|---|---|---|---|
| neo4j (routing) | `neo4j` | `neo4j+s` | `neo4j+ssc` |
| bolt (single) | `bolt` | `bolt+s` | `bolt+ssc` |

Default if omitted: `bolt://localhost:7687` (database = server home/default). Optional URI query: `?database=my-db`.

❌ New client per query (`ClientBuilder::build()` in loop/request).
✅ Build once at startup; inject as singleton.

---

## Choosing the Right Approach

| Approach | Method | Auto-retry | Use when |
|---|---|---|---|
| Transaction functions (Client) | `$client->writeTransaction()` / `readTransaction()` | ✅ TransientError, NotALeader, connection errors | **Default** — production, Aura, clusters, HA |
| Session query | `$session->executeQuery($cypher, $params)` | ✅ same retry; full result loaded | Causal consistency within one session; bookmark handover. Access mode = session config — default `null` (routed as WRITE); pass `->withAccessMode(\Laudis\Neo4j\Enum\AccessMode::READ())` for reads |
| Auto-committed | `$client->run()` / `runStatement()` | ⚠️ connection/routing errors only (no TransientError) | Simple scripts, non-critical reads |
| Multiple auto-committed | `$client->runStatements([...])` | ⚠️ each runs in own auto-commit tx — **not atomic** | Bulk independent statements |
| Unmanaged | `$session->beginTransaction()` | ❌ | Explicit commit/rollback control |

---

## Transaction Functions (Default)

Retries callback on TransientError (max 3 attempts, 100ms pause), NotALeader (clears routing table), connection errors. Routes writes to leader, reads to followers.

After 3 failed attempts: throws plain `\Exception('Failed to execute transaction')` — **not** `Neo4jException`. Real cause in `$e->getPrevious()`. Auto-commit exhaustion throws `Neo4jException` ("Statement execution failed after maximum retries").

```php
use Laudis\Neo4j\Contracts\TransactionInterface;

$result = $client->writeTransaction(static function (TransactionInterface $tsx) {
    return $tsx->run(
        'MERGE (p:Person {email: $email}) RETURN p.name AS name',
        ['email' => 'alice@example.com']
    )->first()->get('name');
});

$names = $client->readTransaction(static function (TransactionInterface $tsx) {
    return $tsx->run('MATCH (p:Person) RETURN p.name AS name')
               ->pluck('name')
               ->toArray();
});
```

Callback **must be idempotent** — driver retries on failure. Keep side effects outside.

```php
// ❌ counter incremented on every retry; ID generated inside callback
$client->writeTransaction(function (TransactionInterface $tsx) use ($counter) {
    $counter->increment();
    $tsx->run('MERGE (x:Node {id: $id})', ['id' => bin2hex(random_bytes(16))]);
});

// ✅ ID generated outside; counter incremented once on success
$id = bin2hex(random_bytes(16));
$client->writeTransaction(static function (TransactionInterface $tsx) use ($id) {
    $tsx->run('MERGE (x:Node {id: $id})', ['id' => $id]);
});
$counter->increment();
```

---

## Session-level Queries (Causal Consistency)

`executeQuery()` auto-retries and buffers full result. Single session preserves bookmarks across calls.

```php
use Laudis\Neo4j\Databags\SessionConfiguration;

$driver  = $client->getDriver('default');
$session = $driver->createSession(SessionConfiguration::default());  // add ->withDatabase(...) only if non-default

$session->executeQuery(
    'MERGE (p:Person {email: $email}) RETURN p',
    ['email' => 'alice@example.com']
);

// Same session → bookmarks guarantee read-your-own-writes
$people = $session->executeQuery('MATCH (p:Person) RETURN p.name AS name');

// Bookmark handover across requests
$bookmark = $session->getLastBookmark();
$session->close();

$session2 = $driver->createSession(
    SessionConfiguration::default()
        ->withBookmarks([$bookmark])   // list<Bookmark>
);
```

---

## Auto-committed Queries

Retries connection/routing errors only — **never** on `TransientError`.

```php
$client->run('MERGE (u:User {email: $email})', ['email' => 'bob@example.com']);

use Laudis\Neo4j\Databags\Statement;

$client->runStatement(new Statement(
    'MERGE (u:User {email: $email})',
    ['email' => 'bob@example.com']
));

// NOT atomic — each statement commits independently
$client->runStatements([
    Statement::create('MERGE (a:A {id: $id})', ['id' => 1]),
    Statement::create('MERGE (b:B {id: $id})', ['id' => 2]),
]);
// ❌ runStatements for atomicity  ✅ Use beginTransaction() instead
```

---

## Unmanaged Transactions

```php
use Laudis\Neo4j\Databags\Statement;

$tsx = $client->beginTransaction(
    [Statement::create('MERGE (x:Person {email: $e})', ['e' => 'a@b.com'])],
    'default'
);
// Initial statement results discarded

try {
    $result  = $tsx->run('MATCH (x) RETURN x LIMIT 100');
    $results = $tsx->runStatements([Statement::create('MATCH (x) RETURN x LIMIT 100')]);
    $tsx->commit();
} catch (\Throwable $e) {
    $tsx->rollback();
    throw $e;
}
```

❌ Omit `commit()` or `rollback()` → transaction leak.
✅ Wrap in try/catch; `rollback()` in catch before re-throw.

---

## Result Access

```php
$results = $client->run('MATCH (p:Person) RETURN p.name AS name, p.age AS age');

foreach ($results as $row) {
    echo $row->get('name');   // throws if missing
    echo $row->get('age', 0); // with default
}

$first = $results->first();                  // throws if empty
$names = $results->pluck('name')->toArray();
$count = $results->count();
```

Node and relationship extraction:

```php
$results = $client->run('MATCH (p:Person)-[r:KNOWS]->(f) RETURN p, r, f');

foreach ($results as $row) {
    $node      = $row->get('p');              // Laudis\Neo4j\Types\Node
    $intId     = $node->getId();              // legacy int ID
    $elementId = $node->getElementId();       // ?string element ID (Neo4j 5+; null on pre-5)

    $rel       = $row->get('r');              // Laudis\Neo4j\Types\Relationship
    $type      = $rel->getType();             // 'KNOWS'
    $startEId  = $rel->getStartNodeElementId();
    $endEId    = $rel->getEndNodeElementId();
}
```

Full mapping reference → [references/type-mapping.md](references/type-mapping.md)

---

## ParameterHelper — List vs Map Disambiguation

Empty PHP `[]` is ambiguous — disambiguate via `ParameterHelper`:

```php
use Laudis\Neo4j\ParameterHelper;

$client->run('MATCH (x) WHERE x.slug IN $slugs RETURN x',
    ['slugs' => ParameterHelper::asList([])]);   // Cypher List

$client->run('CREATE (x:Node $props)',
    ['props' => ParameterHelper::asMap([])]);    // Cypher Map
```

---

## Batch Writes with UNWIND

One transaction per batch — never one tx per item.

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
| New client per query | Build once at startup; share |
| String interpolation in Cypher | Use `$param` placeholders |
| Side effects in `writeTransaction` callback | Move outside — callback retries |
| Non-idempotent callback (random ID generated inside) | Generate ID outside callback; pass via `use` |
| Empty array for list parameter | `ParameterHelper::asList([])` |
| Empty array for map parameter | `ParameterHelper::asMap([])` |
| `http://` or `https://` URI | Removed in v3.3.0 — use `bolt://` or `neo4j://` |
| `beginTransaction` without `commit`/`rollback` | Transaction leak — always close in try/finally or catch |
| `first()` on empty result | Throws — check `count()` first |
| Credentials in code | Load from environment / `.env` |
| Expecting causal consistency across `$client->run()` / `*Transaction()` calls | Use one explicit Session, or hand over `getLastBookmark()` via `withBookmarks([...])` |
| Expecting causal consistency across PHP requests/processes | Pass `getLastBookmark()` forward via `withBookmarks([...])` on a new session |
| `runStatements([...])` expecting atomic execution | Not atomic — use `beginTransaction()` |
| `$node->getId()` expecting element ID | Use `$node->getElementId()` (`?string`, Neo4j 5+; null on pre-5) |
| Catching only `Neo4jException` around `writeTransaction` | Final retry throws plain `\Exception` — check `getPrevious()` |
| `$client->getDriver()` assuming lazy connect | Eager `verifyConnectivity` — can throw `RuntimeException` |

---

## References
- [references/type-mapping.md](references/type-mapping.md) — Cypher-to-PHP type table, temporal types, Point subtypes, Vector
- [references/driver-configuration.md](references/driver-configuration.md) — DriverConfiguration, SessionConfiguration, TransactionConfiguration, summary counters

Docs:
- https://github.com/neo4j-php/neo4j-php-client
- https://packagist.org/packages/laudis/neo4j-php-client

---

## Checklist
- [ ] `laudis/neo4j-php-client` installed via Composer
- [ ] PHP ^8.1, `ext-json`, `ext-mbstring` confirmed (`ext-bcmath` suggested for Bolt; `ext-sockets` optional with stream fallback)
- [ ] One client (or driver) created at startup; shared across requests
- [ ] Credentials loaded from `$_ENV`/`$_SERVER` (or `createUnsafeImmutable`); empty `NEO4J_PASSWORD` fails fast; `.env` in `.gitignore`
- [ ] `writeTransaction` / `readTransaction` used for production writes/reads
- [ ] Callback is idempotent — side effects moved outside
- [ ] `$param` placeholders in all Cypher — no string interpolation
- [ ] `ParameterHelper::asList()` / `asMap()` for empty array params
- [ ] `bolt://` or `neo4j://` URI scheme — no `http://`
- [ ] `beginTransaction()` always paired with `commit()` or `rollback()`
- [ ] Batch writes use UNWIND (not one tx per item)
- [ ] Single session used when causal consistency required
- [ ] `getElementId()` used for Neo4j 5+ element IDs
