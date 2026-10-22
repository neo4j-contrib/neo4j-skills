# Configuration Reference

## DriverConfiguration

```php
use Laudis\Neo4j\Databags\DriverConfiguration;
use Laudis\Neo4j\ClientBuilder;

$client = ClientBuilder::create()
    ->withDefaultDriverConfiguration(
        DriverConfiguration::default()->withUserAgent('MyApp/1.0.0')
    )
    ->withDriver('default', 'bolt+s://localhost:7687')
    ->build();
```

| Option | Method | Description |
|---|---|---|
| User agent | `withUserAgent(string)` | Identifies client to the Neo4j server |

## SessionConfiguration

```php
use Laudis\Neo4j\Databags\SessionConfiguration;
use Laudis\Neo4j\Enum\AccessMode;

$client = ClientBuilder::create()
    ->withDefaultSessionConfiguration(
        SessionConfiguration::default()
            ->withDatabase('my-database')
            ->withAccessMode(AccessMode::READ())
            ->withFetchSize(200)
    )
    ->withDriver('default', 'neo4j://localhost:7687')
    ->build();
```

| Option | Method | Description |
|---|---|---|
| Database | `withDatabase(string)` | Target database name |
| Access mode | `withAccessMode(AccessMode)` | `READ()` or `WRITE()` |
| Fetch size | `withFetchSize(int)` | Rows fetched per batch |
| Bookmarks | `withBookmarks(...)` | Causal consistency bookmarks (experimental in 3.6.x) |

Do NOT set `database` unless deviating from server default.

## TransactionConfiguration

```php
use Laudis\Neo4j\Databags\TransactionConfiguration;

$client = ClientBuilder::create()
    ->withDefaultTransactionConfiguration(
        TransactionConfiguration::default()->withTimeout(5.0)
    )
    ->withDriver('default', 'bolt+s://localhost:7687')
    ->build();
```

| Option | Method | Description |
|---|---|---|
| Timeout | `withTimeout(float)` | Max seconds before transaction times out |
| Metadata | `withMetaData(array)` | Key-value metadata attached to the transaction (capital D; experimental) |

## Granular Control — Per-call Config

```php
use Laudis\Neo4j\Databags\DriverConfiguration;
use Laudis\Neo4j\ClientBuilder;
use Laudis\Neo4j\Databags\SessionConfiguration;
use Laudis\Neo4j\Databags\TransactionConfiguration;

$client = ClientBuilder::create()
    ->withDefaultDriverConfiguration(
        DriverConfiguration::default()->withUserAgent('MyApp/1.0.0')
    )
    ->withDefaultSessionConfiguration(
        SessionConfiguration::default()->withDatabase('app-database')
    )
    ->withDefaultTransactionConfiguration(
        TransactionConfiguration::default()->withTimeout(5.0)
    )
    ->withDriver('default', 'bolt+s://localhost:7687')
    ->build();

// Override per-access
$driver  = $client->getDriver('default');
$session = $driver->createSession(
    SessionConfiguration::default()->withDatabase('management-database')
);
$tsx = $session->beginTransaction(
    null,
    TransactionConfiguration::default()->withTimeout(200)
);
$tsx->run('SOME LONG MANAGEMENT QUERY');
$tsx->commit();
```

## Result Shape — Counters and Query Type

```php
$result  = $client->run('MATCH (x) RETURN x LIMIT 10');
$summary = $result->getSummary();

// Write counters — use getCounters(), not getUpdateStatistics()
$counters = $summary->getCounters();
$counters->nodesCreated();
$counters->relationshipsCreated();
$counters->propertiesSet();

// Query type — Laudis\Neo4j\Enum\QueryTypeEnum: READ_ONLY, READ_WRITE, WRITE_ONLY, SCHEMA_WRITE
$summary->getQueryType();

// Server info
$summary->getServerInfo()->getAddress();
```

## Authentication Options

```php
use Laudis\Neo4j\Authentication\Authenticate;

Authenticate::basic($user, $password)    // username + password (default)
Authenticate::oidc($token)               // OpenID Connect token
Authenticate::kerberos($base64Ticket)    // Kerberos base64 ticket
Authenticate::disabled()                 // no auth (anonymous, if server allows)
```

## Multiple Drivers (Failover)

Drivers sharing the same alias form a failover group. Fourth argument is priority — higher goes first.

```php
$client = ClientBuilder::create()
    ->withDriver('primary', 'neo4j+s://primary.example.com', Authenticate::basic($u, $p), 2)
    ->withDriver('primary', 'neo4j+s://replica.example.com', Authenticate::basic($u, $p), 1)
    ->withDriver('local',   'bolt://localhost:7687',         Authenticate::basic('neo4j', 'dev'))
    ->withDefaultDriver('primary')
    ->build();

$client->run('MATCH (n) RETURN n LIMIT 1');                                  // uses 'primary' group
$client->writeTransaction(fn ($tsx) => $tsx->run('MERGE (n:Node)'), 'local'); // specific alias
```
