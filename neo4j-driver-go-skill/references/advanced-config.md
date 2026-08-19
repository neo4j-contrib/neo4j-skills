# Advanced Driver Configuration

## Connection Pool

```go
import "github.com/neo4j/neo4j-go-driver/v6/neo4j/config"

driver, _ := neo4j.NewDriver(uri, auth,
    func(conf *config.Config) {
        conf.MaxConnectionPoolSize = 50              // default: 100
        conf.ConnectionAcquisitionTimeout = 30 * time.Second
        conf.MaxConnectionLifetime = 1 * time.Hour
    },
)
```

## Custom Address Resolver + Notifications + Logging

```go
import (
    "github.com/neo4j/neo4j-go-driver/v6/neo4j/config"
    "github.com/neo4j/neo4j-go-driver/v6/neo4j/notifications"
)

driver, err := neo4j.NewDriver(uri, auth,
    func(conf *config.Config) {
        // Custom address resolver (e.g. local dev against a cluster)
        conf.AddressResolver = func(addr config.ServerAddress) []config.ServerAddress {
            return []config.ServerAddress{
                neo4j.NewServerAddress("localhost", "7687"),
            }
        }

        // Reduce notification noise
        conf.NotificationsMinSeverity = notifications.WarningLevel
        conf.NotificationsDisabledClassifications = notifications.DisableClassifications(
            notifications.Hint, notifications.Generic,
        )

        // Bolt-level debug logging
        conf.Log = neo4j.ConsoleLogger(neo4j.DEBUG)
    },
)
```

## Auth Options

```go
neo4j.BasicAuth(user, password, "")           // username + password
neo4j.BearerAuth(token)                        // SSO / JWT
neo4j.KerberosAuth(base64EncodedTicket)        // Kerberos
neo4j.NoAuth()                                 // unauthenticated (dev only)
```

## URI Schemes

| Scheme | When to use |
|--------|-------------|
| `neo4j://` | Unencrypted, cluster-routing |
| `neo4j+s://` | Encrypted (TLS), cluster-routing — use for Aura |
| `bolt://` | Unencrypted, single instance |
| `bolt+s://` | Encrypted, single instance |

## Result Summary — deprecated accessors [v6.2.0]

| Deprecated | Replacement |
|---|---|
| `summary.Profile()` / `ProfiledPlan` | `summary.QueryProfile()` / `QueryProfile` |
| `summary.Notifications()` | `summary.GqlStatusObjects()` |
| `summary.StatementType()` | `summary.QueryType()` |

`QueryProfile` metrics return `(value, recorded bool)` — check the bool instead of treating absent stats as `0`:
```go
profile := summary.QueryProfile()
if hits, ok := profile.DbHits(); ok {
    fmt.Printf("%s dbHits=%d\n", profile.Operator(), hits)
}
for _, child := range profile.Children() { /* recurse */ }
```

`neo4j/db` summary types (`Plan`, `ProfiledPlan`, `StreamSummary`, `GqlStatusObject`, `InputPosition`, `Summary`, `QueryType` alias) are internal as of v6.2.0 — depend on the `neo4j` package types only.
