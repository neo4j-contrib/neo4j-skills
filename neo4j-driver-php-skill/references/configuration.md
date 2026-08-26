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
| Database | `withDatabase(string)` | Target database name |
| Access mode | `withAccessMode(AccessMode)` | `READ()` or `WRITE()` |
| Fetch size | `withFetchSize(int)` | Rows fetched at a time |
| Bookmarks | `withBookmarks(...)` | Causal consistency bookmarks (experimental) |

Do NOT set `database` explicitly unless deviating from the server-configured default.

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

## Result Shape

Queries return a `SummarizedResult` object, which contains both the result rows and execution summary.

```php
$result = $client->run('MATCH (x) RETURN x LIMIT 10');

// Iterate through result rows
foreach ($result as $row) {
    // $row is a CypherMap
}

// Access the execution summary
$summary = $result->getSummary();

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

To configure failover, multiple drivers must share the **same alias**. You can then configure their priority as the fourth argument.

```php
$client = ClientBuilder::create()
    // Failover group sharing the 'primary' alias
    ->withDriver('primary', 'neo4j+s://primary.example.com', Authenticate::basic($u, $p), 2)
    ->withDriver('primary', 'neo4j+s://replica.example.com', Authenticate::basic($u, $p), 1)
    
    // Separate database alias
    ->withDriver('local',   'bolt://localhost:7687',         Authenticate::basic('neo4j', 'dev'))
    
    ->withDefaultDriver('primary')
    ->build();

// Uses the 'primary' group (will attempt primary.example.com first due to higher priority)
$client->run('MATCH (n) RETURN n LIMIT 1');

// Override to use a specific driver by its alias
$client->writeTransaction(fn ($tsx) => $tsx->run('MERGE (n:Node)'), 'local');
```
