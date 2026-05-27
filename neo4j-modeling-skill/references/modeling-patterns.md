# Modeling Patterns

## Time-Series Bucket Pattern

Use when a relationship accumulates millions of edges per node (e.g., page views, events).

```cypher
// Instead of: (:User)-[:VIEWED]->(:Page) (millions of rels per user)
// Bucket by hour:
(u:User)-[:VIEWED_IN]->(b:ViewBucket {userId: u.id, hour: '2025-04-28T14'})-[:VIEWED]->(p:Page)

// Query last hour's views without traversing full history:
MATCH (u:User {id: $uid})-[:VIEWED_IN]->(b:ViewBucket {hour: $hour})-[:VIEWED]->(p)
RETURN p.url
```

## Versioning Pattern

Track history of changes to an entity by chaining version nodes.

```cypher
(:Product)-[:CURRENT_VERSION]->(v:ProductVersion {version: "2.1", data: {...}})
(v)-[:PREVIOUS]->(:ProductVersion {version: "2.0", data: {...}})
```

## Multi-Tenancy Pattern

Isolate tenant data with a tenant root node. All tenant-scoped nodes connect to it.

```cypher
(:Tenant {id: "acme-corp"})-[:OWNS]->(:User)-[:CREATED]->(:Order)
```

Query scoped by tenant: `MATCH (t:Tenant {id: $tenantId})-[:OWNS]->(u:User) ...`

## Linked List Pattern

Ordered sequences without array properties. Each node points to next.

```cypher
(:Step {name: "Login"})-[:NEXT]->(:Step {name: "2FA"})-[:NEXT]->(:Step {name: "Dashboard"})
```

## Access Control Pattern

Row-level security via label prefix. Application code filters out `Sec*` labels.

```cypher
(:Document:SecConfidential)-[:AUTHORED_BY]->(:Person)
```

Security labels used for access control should start with a common prefix (e.g. `Sec`) so application code can reliably filter them out of the domain schema.
