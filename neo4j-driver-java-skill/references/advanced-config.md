# Advanced Configuration — Neo4j Java Driver

## Full `Config.builder()` options

```java
import org.neo4j.driver.Config;
import org.neo4j.driver.Logging;
import org.neo4j.driver.net.ServerAddress;
import org.neo4j.driver.NotificationConfig;
import org.neo4j.driver.NotificationSeverity;
import java.util.concurrent.TimeUnit;

var driver = GraphDatabase.driver(uri, auth,
    Config.builder()
        // Connection pool
        .withMaxConnectionPoolSize(50)                           // default: 100
        .withConnectionAcquisitionTimeout(30, TimeUnit.SECONDS) // wait for free conn
        .withMaxConnectionLifetime(1, TimeUnit.HOURS)
        .withConnectionLivenessCheckTimeout(30, TimeUnit.MINUTES)

        // Custom resolver — useful for local dev against a cluster
        .withResolver(address -> Set.of(ServerAddress.of("localhost", 7687)))

        // TLS
        .withEncryption()
        .withTrustStrategy(Config.TrustStrategy.trustAllCertificates()) // dev ONLY

        // Notification filtering — reduce noise in logs
        .withNotificationConfig(NotificationConfig.defaultConfig()
            .enableMinimumSeverity(NotificationSeverity.WARNING))

        // Logging
        .withLogging(Logging.slf4j())           // production
        // .withLogging(Logging.console(Level.DEBUG))  // debug

        // Record fetch size (controls Bolt batching)
        .withFetchSize(1000)                    // default: 1000

        .build());
```

## Session-level auth (multi-tenant)

Cheaper than a new `Driver` per tenant — reuses the connection pool:

```java
var session = driver.session(SessionConfig.builder()
    .withDatabase("tenant_db")
    .withAuthToken(AuthTokens.basic("tenant-user", "pass"))
    .build());
```

## User impersonation

Requires `IMPERSONATE` privilege on the executing user:

```java
var session = driver.session(SessionConfig.builder()
    .withDatabase("neo4j")
    .withImpersonatedUser("jane")
    .build());
```

## Connection pool diagnosis

| Error message | Cause | Fix |
|---|---|---|
| `Unable to acquire connection from the pool within configured maximum time` | Pool exhausted | Increase `maxConnectionPoolSize` or fix session leaks |
| `Connection to the database terminated` / `ServiceUnavailableException` | Network/server issue | Check server health, firewall, TLS |
| Session hangs with no error | Session leak — connection never returned | Add try-with-resources; audit all code paths |

## Spatial Types

```java
import org.neo4j.driver.Values;

// Create points — Values.point(srid, x, y) / Values.point(srid, x, y, z)
var cartesian2d = Values.point(7203,  1.23, 4.56);           // Cartesian 2D
var cartesian3d = Values.point(9157,  1.23, 4.56, 7.89);     // Cartesian 3D
var wgs84_2d    = Values.point(4326, -0.118092, 51.509865);  // WGS-84 2D (lon, lat)
var wgs84_3d    = Values.point(4979, -0.0865, 51.5045, 310); // WGS-84 3D (lon, lat, height)

// Read point from result
var pt = result.records().get(0).get("location");
double x    = pt.asPoint().x();     // longitude for WGS-84
double y    = pt.asPoint().y();     // latitude for WGS-84
double z    = pt.asPoint().z();     // height/z (NaN for 2D)
int    srid = pt.asPoint().srid();  // 4326, 4979, 7203, or 9157

// Pass as parameter
driver.executableQuery("CREATE (p:Place {location: $loc})")
    .withParameters(Map.of("loc", wgs84_2d))
    .withConfig(QueryConfig.builder().withDatabase("neo4j").build())
    .execute();

// Distance — same SRID only
driver.executableQuery("RETURN point.distance($p1, $p2) AS distance")
    .withParameters(Map.of("p1", Values.point(7203, 1.0, 1.0),
                            "p2", Values.point(7203, 10.0, 10.0)))
    .withConfig(QueryConfig.builder().withDatabase("neo4j").build())
    .execute()
    .records().get(0).get("distance").asDouble();
```

SRID table: `4326` = WGS-84 2D, `4979` = WGS-84 3D, `7203` = Cartesian 2D, `9157` = Cartesian 3D.

## Causal consistency — cross-session bookmarks

Within a single session: automatic. Across parallel sessions, pass bookmarks explicitly:

```java
import org.neo4j.driver.Bookmark;

List<Bookmark> bookmarks = new ArrayList<>();

try (var sessionA = driver.session(SessionConfig.builder().withDatabase("neo4j").build())) {
    sessionA.executeWriteWithoutResult(tx -> createPerson(tx, "Alice"));
    bookmarks.addAll(sessionA.lastBookmarks());
}
try (var sessionB = driver.session(SessionConfig.builder().withDatabase("neo4j").build())) {
    sessionB.executeWriteWithoutResult(tx -> createPerson(tx, "Bob"));
    bookmarks.addAll(sessionB.lastBookmarks());
}

// sessionC waits until both Alice and Bob exist
try (var sessionC = driver.session(SessionConfig.builder()
        .withDatabase("neo4j")
        .withBookmarks(bookmarks)
        .build())) {
    sessionC.executeWriteWithoutResult(tx -> connectPeople(tx, "Alice", "Bob"));
}
```

`executableQuery` shares a `BookmarkManager` automatically — prefer it over explicit bookmarks except for complex cross-session coordination.
