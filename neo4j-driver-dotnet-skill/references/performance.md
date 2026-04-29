# Performance, Type Extras — Neo4j .NET Driver

## Spatial Types

```csharp
using Neo4j.Driver;

// Create points — new Point(srid, x, y) / new Point(srid, x, y, z)
var cartesian2d = new Point(7203, 1.23, 4.56);            // Cartesian 2D (SRID 7203)
var cartesian3d = new Point(9157, 1.23, 4.56, 7.89);      // Cartesian 3D (SRID 9157)
var london      = new Point(4326, -0.118092, 51.509865);   // WGS-84 2D (lon, lat) (SRID 4326)
var shard       = new Point(4979, -0.0865, 51.5045, 310);  // WGS-84 3D (SRID 4979)

// Pass as parameter — driver serializes automatically
await driver.ExecutableQuery("CREATE (p:Place {location: $loc})")
    .WithParameters(new { loc = london })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync();

// Read from result
var pt = record.Get<Point>("location");
Console.WriteLine($"X={pt.X} Y={pt.Y} Z={pt.Z} SRID={pt.SrId}");
// For WGS-84: X=longitude, Y=latitude, Z=height (NaN for 2D)

// Distance (same SRID only — different SRIDs return null)
var dist = (await driver
    .ExecutableQuery("RETURN point.distance($p1, $p2) AS distance")
    .WithParameters(new { p1 = new Point(7203, 1, 1), p2 = new Point(7203, 10, 10) })
    .WithConfig(new QueryConfig(database: "neo4j"))
    .ExecuteAsync()).Result[0].Get<double>("distance");
```

SRID: `4326` = WGS-84 2D, `4979` = WGS-84 3D, `7203` = Cartesian 2D, `9157` = Cartesian 3D.

---

# Performance — Connection Pool, Streaming, CancellationToken

## Always Specify the Database

Omitting database causes an extra network round-trip on every call:

```csharp
// ExecutableQuery:
.WithConfig(new QueryConfig(database: "neo4j"))

// Session:
driver.AsyncSession(conf => conf.WithDatabase("neo4j"))
```

## Route Reads to Replicas

```csharp
// ExecutableQuery:
.WithConfig(new QueryConfig(database: "neo4j", routing: RoutingControl.Readers))

// Managed transaction — ExecuteReadAsync routes automatically
await session.ExecuteReadAsync(async tx => { ... });
```

## Large Results — Lazy Streaming

`ExecutableQuery` is always eager — fine for moderate result sets.

For large results, stream lazily inside `ExecuteReadAsync`:

```csharp
await using var session = driver.AsyncSession(conf => conf.WithDatabase("neo4j"));
await session.ExecuteReadAsync(async tx =>
{
    var cursor = await tx.RunAsync("MATCH (p:Person) RETURN p.name AS name");
    while (await cursor.FetchAsync())
    {
        ProcessRecord(cursor.Current.Get<string>("name"));
    }
});
```

## Connection Pool Tuning

```csharp
await using var driver = GraphDatabase.Driver(uri, auth, conf => conf
    .WithMaxConnectionPoolSize(50)
    .WithConnectionAcquisitionTimeout(TimeSpan.FromSeconds(30))
    .WithMaxConnectionLifetime(TimeSpan.FromHours(1))
    .WithConnectionIdleTimeout(TimeSpan.FromMinutes(10)));
```

Default pool size: 100. Reduce if running many app instances to avoid overwhelming the server.

## CancellationToken — Propagate End-to-End

In web apps, always propagate the request cancellation token. Without it, abandoned requests keep running on the server, exhausting the connection pool under load.

```csharp
// ASP.NET Core controller
[HttpGet("people")]
public async Task<IActionResult> GetPeople(CancellationToken cancellationToken)
{
    var (records, _, _) = await driver
        .ExecutableQuery("MATCH (p:Person) RETURN p.name AS name")
        .WithConfig(new QueryConfig(database: "neo4j"))
        .ExecuteAsync(cancellationToken);
    return Ok(records.Select(r => r.Get<string>("name")));
}

// Session-based
return await session.ExecuteReadAsync(async tx =>
{
    var cursor = await tx.RunAsync(
        "MATCH (p:Person) RETURN p.name AS name",
        cancellationToken: cancellationToken);
    return await cursor.ToListAsync(r => r.Get<string>("name"), cancellationToken);
}, cancellationToken: cancellationToken);

// Explicit transaction
await using var tx = await session.BeginTransactionAsync(cancellationToken);
await tx.RunAsync("CREATE (p:Person {name: $name})", new { name }, cancellationToken);
await tx.CommitAsync(cancellationToken);
```
