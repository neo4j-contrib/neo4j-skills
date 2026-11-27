# Neo4j Laravel Reference (`neo4j-php/neo4j-laravel`)

## Connection Configuration (`config/database.php`)

```php
'connections' => [
    'neo4j' => [
        'driver'      => 'neo4j',
        'url'         => env('NEO4J_URL', 'bolt://localhost:7687'),
        'username'    => env('NEO4J_USERNAME', 'neo4j'),
        'password'    => env('NEO4J_PASSWORD', ''),
        'database'    => env('NEO4J_DATABASE', 'neo4j'),
        'auth_scheme' => env('NEO4J_AUTH_SCHEME', 'basic'),
        'ssl' => [
            'mode'        => env('NEO4J_SSL_MODE', 'from_url'),
            'verify_peer' => env('NEO4J_SSL_VERIFY_PEER', true),
        ],
        'connection' => [
            'timeout'       => env('NEO4J_CONNECTION_TIMEOUT', 30),
            'max_pool_size' => env('NEO4J_MAX_POOL_SIZE', 100),
        ],
    ],
],
```

| Key | Env | Default | Values / Notes |
|---|---|---|---|
| `driver` | — | `neo4j` | Required `neo4j` |
| `url` | `NEO4J_URL` | `bolt://localhost:7687` | Bolt/Neo4j URI (or `host` + `port`). Note: `NEO4J_URL` here vs `NEO4J_URI` in Boost |
| `username` | `NEO4J_USERNAME` | `neo4j` | Auth username |
| `password` | `NEO4J_PASSWORD` | `''` | Auth password |
| `database` | `NEO4J_DATABASE` | `neo4j` | Target database |
| `auth_scheme` | `NEO4J_AUTH_SCHEME` | `basic` | `basic`, `kerberos` (needs `ticket`), `oidc` (needs `auth_token` or `token`), `none` |
| `ssl.mode` | `NEO4J_SSL_MODE` | `from_url` | `from_url`, `enable`, `enable_with_self_signed`, `disable` |
| `ssl.verify_peer` | `NEO4J_SSL_VERIFY_PEER` | `true` | TLS peer verification |
| `connection.timeout` | `NEO4J_CONNECTION_TIMEOUT` | `30` | Connection acquire timeout (seconds) |
| `connection.max_pool_size` | `NEO4J_MAX_POOL_SIZE` | `100` | Driver pool size |

`transaction.timeout` in `config/database.php` is not forwarded into client factory.

---

## Query Builder & Relationship Writes

### Direction markers
- `Type>` or `>Type` — outgoing (`-[:Type]->`)
- `<Type` or `Type<` — incoming (`<-[:Type]-`)
- `Type` — undirected (`-[:Type]-`)

### Single & bulk relationship writes

```php
$people = DB::connection('neo4j')->table('Person');

// Single edge between existing nodes (CREATE — repeats create duplicates)
$people->insertRelationship('ACTED_IN>', 'Movie', ['id' => $personId], ['id' => $movieId], ['roles' => ['Neo']]);

// Bulk edges (one UNWIND statement per call; missing nodes skipped)
$rows = [
    ['from' => ['id' => $keanu],  'to' => ['id' => $matrix], 'properties' => ['roles' => ['Neo']]],
    ['from' => ['id' => $carrie], 'to' => ['id' => $matrix], 'properties' => ['roles' => ['Trinity']]],
];

$people->insertRelationships('ACTED_IN>', 'Movie', $rows); // CREATE
$people->upsertRelationships('ACTED_IN>', 'Movie', $rows); // MERGE + SET
$people->syncRelationships('ACTED_IN>', 'Movie', $rows);   // replace Type edges for listed from-nodes; nodes stay
$people->deleteRelationships('ACTED_IN>', 'Movie', [['from' => ['id' => $keanu]]]); // omit 'to' → delete all Type edges from node
```

### Bulk node upsert

```php
DB::connection('neo4j')->table('Person')->upsert(
    [['email' => 'neo@example.com', 'name' => 'Neo']],
    ['email'],
    ['name']
); // compiles to single UNWIND + MERGE
```

---

## Eloquent Models & Joins

Extend `Neo4j\Neo4jLaravel\Neo4jModel` or use `Neo4j\Neo4jLaravel\Concerns\HasNeo4jConnection`.

- Class name → default Neo4j label (`User` → `:User`)
- Auto-generated UUID `id`; `$model->elementId()` returns Neo4j element ID when full node returned
- Supports `SoftDeletes` (`deleted_at`; hard delete uses `DETACH DELETE`), `paginate()`/`simplePaginate()`/`cursorPaginate()`, `whereIn`/`whereExists` subqueries

### FK-style relations (node properties)

Standard Eloquent relations (`hasOne`, `hasMany`, `belongsTo`, `belongsToMany` via pivot node label, `hasOneThrough`, `hasManyThrough`, `morphOne`/`morphMany`/`morphTo`/`morphToMany`/`morphedByMany`) compile to multi-node `MATCH` + `WHERE`:

```php
public function roles(): BelongsToMany
{
    return $this->belongsToMany(Role::class, 'RoleUser', 'user_id', 'role_id'); // :RoleUser pivot node label
}
```

### Graph relations (`MatchRelationship`)

```php
use Neo4j\Neo4jLaravel\Relations\MatchRelationship;

public function movies(): MatchRelationship
{
    return $this->matchRelationship(Movie::class, 'ACTED_IN>');
}

$person->movies()->attach($movie->id, ['roles' => ['Neo']]);
$person->movies()->sync([$matrix->id]);
$person->movies()->detach($movie->id);
$person->movies()->create(['title' => 'The Matrix'], ['roles' => ['Neo']]);
Person::with('movies')->get();
```

`whereHas` / `withCount` on `MatchRelationship` are not supported yet.

---

## Transactions & Dependency Injection

```php
// Retries on Neo.TransientError.* (deadlocks)
DB::connection('neo4j')->transaction(function () use ($movie) {
    $person = Person::create(['name' => 'Keanu Reeves']);
    $person->movies()->attach($movie->id, ['roles' => ['Neo']]);
}, attempts: 3);
```

- Nested transactions share outer Neo4j tx (no savepoints — nested `rollBack()` rolls back everything; further outer queries throw `LogicException` until outer rolled back).
- `transactionLevel()`, `DB::afterCommit()`, `ShouldDispatchAfterCommit` supported.
- Container bindings (`ClientInterface`, `DriverInterface`, `SessionInterface`) wrap client calls for query logging + Debugbar capture; manually instantiated clients bypass capture.

---

## Vector Search

```php
DB::connection('neo4j')->createVectorIndex('document_embedding', 'Document', 'embedding', 3);

Document::query()
    ->whereVectorSimilarTo('embedding', [1.0, 0.0, 0.0], minSimilarity: 0.9)
    ->limit(10)
    ->get();
```

- Query vector accepts `float[]`, `Collection`, `Arrayable`, Neo4j list, or `string` (requires `laravel/ai` `Stringable::toEmbeddings` macro; throws `InvalidArgumentException` without it).
- Cosine score = `(1 + cosine) / 2` (default `minSimilarity: 0.6`).
- Filtered or unlimited queries score nodes via `vector.similarity.cosine()` (exact scan). For euclidean indexes, chain `->useVectorSimilarityFunction('euclidean')`.

---

## Migrations (`Schema::connection('neo4j')`)

Reuses Laravel `Migrator` + Artisan commands (`--database=neo4j`); history stored on `:_LaravelMigration` nodes (`migration`, `batch`, `migrated_at`).

| Rule | Detail |
|---|---|
| `Schema::create` / `hasTable` / `drop` | Unsupported — throws. Use `Schema::connection('neo4j')->node()` / `relationship()` / `dropIndex()` / `dropConstraint()` |
| Schema transactions | `supportsSchemaTransactions` is `false` — Neo4j DDL not wrapped in Bolt tx |
| Rollback safety | Dropping indexes/constraints keeps existing nodes and relationships |
| Default names | `{owner}_{properties}_{unique\|index\|vector}` lowercase; pass 2nd arg to override |
| Neo4j version | DDL Cypher targets Neo4j 5.x |

---

## Logging & Debugbar

- `NEO4J_QUERY_CHANNEL` (merged in `config/neo4j-laravel.php`): flushes in-memory query log as `debug` after HTTP request/console command to named channel (or default logger if empty/missing).
- Install `barryvdh/laravel-debugbar` (`^3`) or `fruitcake/laravel-debugbar` (`^4`): Cypher from `DB::connection('neo4j')` and container-resolved `ClientInterface`/`SessionInterface` appears in Debugbar **Queries** tab.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Default Neo4j connection '…' is not configured or invalid` | Set `DB_CONNECTION=neo4j` and configure `'neo4j'` under `database.connections` |
| `Missing required URL or host/port` | Set `url` (`NEO4J_URL`) or both `host` and `port` |
| Session/auth errors with `DB_CONNECTION=neo4j` | Set `SESSION_DRIVER=file` (or `redis`); keep auth relational unless storing users in Neo4j |
| `Schema::create() is not supported for Neo4j` | Use `Schema::connection('neo4j')->node()` / `relationship()` |
| Cypher missing from Debugbar | Enable `queries` collector; resolve client/session from container |
