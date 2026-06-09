# Configuration Reference

## DriverConfiguration

Configure how the driver connects to Neo4j:

```php
use Laudis\Neo4j\Databags\DriverConfiguration;
use Laudis\Neo4j\ClientBuilder;

$client = ClientBuilder::create()
    ->withDefaultDriverConfiguration(
        DriverConfiguration::default()
            ->withUserAgent('MyApp/1.0.0')
    )
    ->withDriver('default', 'bolt+s://localhost:7687')
    ->build();
```

| Option | Method | Description |
|---|---|---|
| User agent | `withUserAgent(string)` | Identifies the client to the Neo4j server |

## SessionConfiguration

Configure sessions for access mode and database targeting:

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
| Database | `withDatabase(string)` | Target database name (default: `neo4j`) |
| Access mode | `withAccessMode(AccessMode)` | `READ()` or `WRITE()` |
| Fetch size | `withFetchSize(int)` | Rows fetched at a time |
| Bookmarks | `withBookmarks(...)` | Causal consistency bookmarks (experimental) |

Always set `database` explicitly — omitting causes a round-trip to resolve the home database.

## TransactionConfiguration

Configure individual transactions:

```php
use Laudis\Neo4j\Databags\TransactionConfiguration;

$client = ClientBuilder::create()
    ->withDefaultTransactionConfiguration(
        TransactionConfiguration::default()
            ->withTimeout(5.0)
    )
    ->withDriver('default', 'bolt+s://localhost:7687')
    ->build();
```

| Option | Method | Description |
|---|---|---|
| Timeout | `withTimeout(float)` | Maximum seconds before the transaction times out |
| Metadata | `withMetadata(array)` | Key-value metadata attached to the transaction (experimental) |

## Granular Control — Per-call Config

```php
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

// Override session config for a specific driver access
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

## Result Formatters

The default formatter is `SummarizedResultFormatter`, which wraps results with a summary
(counters, server info, timing, profiled plan).

```php
// Access the summary from the wrapped result
$summarized = $client->run('MATCH (x) RETURN x LIMIT 10');
$summary    = $summarized->getSummary();

// Counters for writes
$summary->getUpdateStatistics()->getNodesCreated();
$summary->getUpdateStatistics()->getRelationshipsCreated();

// Query type
$summary->getQueryType();   // 'r', 'w', 'rw', 's'

// Server info
$summary->getServerInfo()->getAddress();
```

## Authentication Options

```php
use Laudis\Neo4j\Authentication\Authenticate;

// Basic (username + password) — default
Authenticate::basic($user, $password)

// OpenID Connect token
Authenticate::oidc($token)

// Kerberos base64 ticket
Authenticate::kerberos($base64Ticket)

// No auth (anonymous access, if enabled on server)
Authenticate::disabled()
```

## Multiple Drivers (Multi-database / Failover)

```php
$client = ClientBuilder::create()
    ->withDriver('primary',  'neo4j+s://primary.example.com',  Authenticate::basic($u, $p))
    ->withDriver('replica',  'neo4j+s://replica.example.com',  Authenticate::basic($u, $p))
    ->withDriver('local',    'bolt://localhost:7687',           Authenticate::basic('neo4j', 'dev'))
    ->withDefaultDriver('primary')
    ->build();

// Use default
$client->run('MATCH (n) RETURN n LIMIT 1');

// Override to use a specific driver
$client->run('MATCH (n) RETURN n LIMIT 1', [], 'replica');
$client->writeTransaction(fn ($tsx) => $tsx->run('MERGE (n:Node)'), 'local');
```
