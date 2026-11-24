---
name: neo4j-graphql-skill
description: Build and configure a GraphQL API backed by Neo4j using @neo4j/graphql v7 (current) or v5 (LTS).
  Covers Neo4jGraphQL constructor, getSchema(), assertIndexesAndConstraints(), type definitions with @node,
  @relationship (IN/OUT, queryDirection), @cypher for custom resolvers, @authorization/@authentication for JWT/JWKS
  security, auto-generated queries/mutations, OGM programmatic access, subscriptions via CDC, and Apollo
  Federation. Use when writing typeDefs, securing fields, or wiring Neo4j to Apollo Server.
  Does NOT handle raw Cypher outside resolvers — use neo4j-cypher-skill.
  Does NOT cover Spring Data Neo4j entity mapping — use neo4j-spring-data-skill.
version: 1.0.6
allowed-tools: Bash WebFetch
---

## When to Use

- Creating a GraphQL API from a Neo4j graph schema with `@neo4j/graphql`
- Writing type definitions with `@relationship`, `@cypher`, `@authorization` directives
- Using OGM (v5 only) for server-side programmatic Neo4j access (bypasses GraphQL auth)
- Configuring auto-generated queries, mutations, subscriptions
- Securing types/fields with JWT or JWKS-based `@authorization` rules
- Migrating from v5/v6 to v7 (breaking changes below)

## When NOT to Use

- **Raw Cypher queries outside GraphQL resolvers** → `neo4j-cypher-skill`
- **Spring Data Neo4j / Java entity mapping** → `neo4j-spring-data-skill`
- **Generic GraphQL without Neo4j** — outside scope

---

## Version Matrix

| Version | Status | Notes |
|---|---|---|
| v7 | Current — use ≥ 7.6.4 | `@node` required; `options` removed; explicit `eq` syntax |
| v5 | LTS — use ≥ 5.12.15 | Older syntax; `options: {limit, offset, sort}` still valid |

Default to v7 unless codebase is on v5. Upgrade past these security patches before shipping auth:

| Fix | Fixed in |
|---|---|
| Subscriptions accepted an unverified JWT from WebSocket `connectionParams` (auth/authz bypass) | 7.5.6 / 5.12.14 |
| Field-level `@authentication` on a root custom-resolver field ignored when the operation type also had type-level `@authentication` (privilege escalation) | 7.6.0 / 5.12.15 |
| `@authorization` rules not applied on create-relationship operations | 7.6.2 |
| Source `@authorization` rules not applied to source node on delete-relationship | 7.6.3 |
| Type-level `@authentication` not enforced on entities returned by `@cypher` fields; `none` quantifier inverted in authorization filters | 7.6.4 |

7.6.5 / 5.12.16 fix Apollo Federation `getSubgraphSchema()` only. Prefer latest patch.

---

## Step 1 — Install

```bash
npm install @neo4j/graphql neo4j-driver graphql @apollo/server
```

For subscriptions (CDC required):
```bash
npm install ws graphql-ws express body-parser cors
```

---

## Step 2 — Minimal Server Setup

```javascript
import { ApolloServer } from '@apollo/server';
import { startStandaloneServer } from '@apollo/server/standalone';
import { Neo4jGraphQL } from '@neo4j/graphql';
import neo4j from 'neo4j-driver';

const typeDefs = `#graphql
  type Movie @node {
    id: ID! @id
    title: String!
    actors: [Person!]! @relationship(type: "ACTED_IN", direction: IN)
  }

  type Person @node {
    id: ID! @id
    name: String!
    movies: [Movie!]! @relationship(type: "ACTED_IN", direction: OUT)
  }
`;

const driver = neo4j.driver(
  process.env.NEO4J_URI,
  neo4j.auth.basic(process.env.NEO4J_USERNAME, process.env.NEO4J_PASSWORD)
);

const neoSchema = new Neo4jGraphQL({ typeDefs, driver });

// getSchema() first — assertIndexesAndConstraints() throws if called before it
const schema = await neoSchema.getSchema();

// v7: validates @fulltext/@vector indexes only; creates nothing (no `options.create` in v7)
try {
  await neoSchema.assertIndexesAndConstraints();
} catch (e) {
  console.error(e.message); // e.g. Missing @fulltext index 'ProductName' on Node 'Product'
  process.exit(1);
}

const server = new ApolloServer({ schema });

const { url } = await startStandaloneServer(server, {
  context: async ({ req }) => ({ token: req.headers.authorization }),
  listen: { port: 4000 },
});
```

---

## Key Directives

### @node (v7 required)

```graphql
type Product @node {
  id: ID! @id
  name: String!
}

# Custom label (default = type name)
type Article @node(labels: ["Post", "Content"]) {
  title: String!
}
```

### @relationship — Full Syntax

```graphql
type Person @node {
  # direction: OUT = (this)-[:KNOWS]->(other)
  friends: [Person!]! @relationship(type: "KNOWS", direction: OUT)

  # direction: IN = (other)-[:ACTED_IN]->(this)
  actedIn: [Movie!]! @relationship(type: "ACTED_IN", direction: IN)

  # direction accepts only IN | OUT. Undirected querying = queryDirection
  # v7: DIRECTED (default) | UNDIRECTED; v5: DEFAULT_DIRECTED | DEFAULT_UNDIRECTED | DIRECTED_ONLY | UNDIRECTED_ONLY
  colleagues: [Person!]! @relationship(type: "COLLEAGUE_OF", direction: OUT, queryDirection: UNDIRECTED)

  # Relationship with properties — reference an @relationshipProperties type
  reviews: [Movie!]! @relationship(type: "REVIEWED", direction: OUT, properties: "ReviewedProps")
}

type ReviewedProps @relationshipProperties {  # type, not interface — interface fails schema build
  rating: Int!
  date: Date
}
```

### Querying Relationship Properties — Connection API

For each relationship with `properties:`, a `{field}Connection` field is auto-generated. Access rel properties via `actorsConnection.edges.properties`, not via `actors`:

```graphql
query {
  movies(where: { title: { eq: "The Matrix" } }) {
    title
    actorsConnection {
      edges {
        properties { role }   # maps to @relationshipProperties type
        node { name }
      }
    }
  }
}
```

### @cypher — Custom Resolver

```graphql
type Person @node {
  name: String!

  # columnName must exactly match the RETURN alias — mismatch returns null silently
  friendCount: Int
    @cypher(
      statement: "MATCH (this)-[:KNOWS]->(f:Person) RETURN count(f) AS friendCount"
      columnName: "friendCount"
    )

  recommendedMovies: [Movie!]!
    @cypher(
      statement: """
        MATCH (this)-[:WATCHED]->(m:Movie)<-[:WATCHED]-(o:Person)-[:WATCHED]->(rec:Movie)
        WHERE NOT (this)-[:WATCHED]->(rec)
        RETURN rec
      """
      columnName: "rec"
    )
}

# @cypher on Query field — custom top-level query
type Query {
  topRatedMovies(limit: Int = 10): [Movie!]!
    @cypher(
      statement: "MATCH (m:Movie) WHERE m.rating IS NOT NULL RETURN m ORDER BY m.rating DESC LIMIT $limit"
      columnName: "m"
    )
}
```

`this` refers to the current node in field-level @cypher. Parameters are passed as `$paramName`.

### @cypher — Field Arguments and extend type

```graphql
# extend type adds computed fields without modifying the base type definition
extend type Movie @node {
  avgRating: Float
    @cypher(statement: "MATCH (this)<-[r:RATED]-(:User) RETURN avg(r.rating) AS result", columnName: "result")

  # Field arguments passed as Cypher params; always provide default to avoid null
  recommended(limit: Int = 3): [Movie!]!
    @cypher(
      statement: "MATCH (this)<-[:RATED]-(u:User)-[:RATED]->(rec:Movie) WITH rec, COUNT(u) AS score ORDER BY score DESC RETURN rec LIMIT $limit"
      columnName: "rec"
    )
}
```

### @id and @timestamp

```graphql
type Post @node {
  id: ID! @id                          # auto-generates UUID only; creates no constraint
  createdAt: DateTime! @timestamp(operations: [CREATE])
  updatedAt: DateTime @timestamp(operations: [CREATE, UPDATE])
  title: String!
}
```

### @alias — Map GraphQL field to Neo4j property

```graphql
type User @node {
  id: ID! @id
  email: String! @alias(property: "emailAddress")  # GraphQL: email → DB: emailAddress
}
```

### @fulltext and @vector

Index must exist in Cypher before use. Phrase-capable `@vector` indexes accept `maxPhraseLength` [7.6.0] to cap embedding cost. A `provider` without matching `features.vector` config fails at schema build [7.6.1]. Full syntax, generated query shapes, provider config: [references/search-directives.md](references/search-directives.md).

---

## Security — @authentication and @authorization

### Step 1: Configure JWT in constructor

```javascript
// Symmetric secret
const neoSchema = new Neo4jGraphQL({
  typeDefs,
  driver,
  features: {
    authorization: { key: process.env.JWT_SECRET },
  },
});

// JWKS endpoint (production)
const neoSchema = new Neo4jGraphQL({
  typeDefs,
  driver,
  features: {
    authorization: {
      key: { url: 'https://myapp.com/.well-known/jwks.json' },
    },
  },
});
```

### Step 2: Pass token in context

```javascript
context: async ({ req }) => ({ token: req.headers.authorization }),
// Or pass pre-decoded JWT:
context: async ({ req }) => ({ jwt: myDecodeJwt(req.headers.authorization) }),
```

### Step 3: Apply @authentication and @authorization

```graphql
# Require auth on all operations for a type
type Post @node
  @authentication
  @authorization(filter: [{ where: { node: { author: { id: { eq: "$jwt.sub" } } } } }]) {
  title: String!
  author: User @relationship(type: "AUTHORED", direction: IN)  # single rel field must be nullable
}

# requireAuthentication: false = allow public access without JWT
type Article @node
  @authorization(filter: [
    { requireAuthentication: false, where: { node: { published: { eq: true } } } }
    { where: { node: { author: { id: { eq: "$jwt.sub" } } } } }
  ]) {
  title: String!
  published: Boolean!
  author: User @relationship(type: "AUTHORED", direction: IN)
}

# validate (throws error) vs filter (silently hides data)
type BankAccount @node
  @authorization(validate: [{
    when: [BEFORE],
    where: { node: { owner: { id: { eq: "$jwt.sub" } } } }
  }]) {
  balance: Float!
  owner: User @relationship(type: "OWNS", direction: IN)
}

# Role-based with custom JWT claims
type JWT @jwt {
  roles: [String!]! @jwtClaim(path: "myApp.roles")
}

type AdminReport @node
  @authentication(operations: [READ], jwt: { roles: { includes: "admin" } }) {
  data: String!
}
```

**BEFORE vs AFTER**: `CREATE` supports only `AFTER`; `READ` supports only `BEFORE`.

---

## Auto-Generated Operations

| Operation | Generated Name | Example |
|---|---|---|
| Query all | `{plural}` | `movies(where, sort, limit, offset)` |
| Cursor pagination | `{plural}Connection` | `moviesConnection(first, after, where, sort)` |
| Create | `create{Plural}` | `createMovies(input: [MovieCreateInput!]!)` |
| Update | `update{Plural}` | `updateMovies(where, update)` |
| Delete | `delete{Plural}` | `deleteMovies(where, delete)` |

### v7 Filter Syntax (explicit `eq`)

```graphql
# v7: explicit eq required
query {
  movies(where: { title: { eq: "The Matrix" } }) {
    title
    actors { name }
  }
}

# Sort and paginate (v7: direct args, not options wrapper)
query {
  movies(sort: [{ title: ASC }], limit: 10, offset: 0) {
    title
  }
}
```

### Nested Mutations

```graphql
mutation {
  createMovies(input: [{
    title: "Inception"
    actors: {
      create: [{ node: { name: "Leonardo DiCaprio" } }]
      connect: { where: { node: { name: { eq: "Joseph Gordon-Levitt" } } } }
    }
  }]) {
    movies { id title }
  }
}
```

---

## OGM — Programmatic Access

Read [references/ogm.md](references/ogm.md#ogm--programmatic-access) when you need this.

## Subscriptions (CDC Required)

Requires Neo4j CDC enabled in `FULL` mode — Enterprise Edition or Aura Business Critical/VDC only (on Community `getSchema()` fails: no procedure `db.cdc.current`). See [CDC docs](https://neo4j.com/docs/cdc/current/).

v7: feature flag alone generates no Subscription type. Add `extend schema @subscription` (all types) or `@subscription` on individual types. v5 generates subscriptions from the flag alone.

```javascript
const typeDefs = `#graphql
  type Movie @node { title: String }
  extend schema @subscription   # v7 required
`;
const neoSchema = new Neo4jGraphQL({
  typeDefs,
  driver,
  features: { subscriptions: true },
});
```

Authenticate subscriptions with a verified `token` in the WebSocket context; a pre-decoded `jwt` is trusted only when set server-side (7.5.6 / 5.12.14 stopped trusting client-supplied `connectionParams` JWTs).

```graphql
subscription {
  movieCreated(where: { title: { eq: "The Matrix" } }) {
    createdMovie { title }
  }
}
# Also: movieUpdated, movieDeleted
```

---

## Schema Control Directives

```graphql
type ReadOnlyData @node @mutation(operations: []) { value: String! }  # disable mutations

type HeavyDoc @node {
  id: ID! @id
  content: String! @filterable(byValue: false) @sortable(byValue: false)  # perf guard
  title: String!
}

type Series @node @plural(value: "seriesList") { title: String! }  # irregular plural fix
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Type 'X' not found` | Missing `@node` on type (v7) | Add `@node` to every node type |
| `@cypher` field returns null | `columnName` mismatch with RETURN alias | Match `columnName` exactly to RETURN alias |
| Relationship direction mismatch | Both sides declare same direction | Inverse: if A has `direction: OUT`, B must have `direction: IN` |
| `You must await .getSchema() before .assertIndexesAndConstraints()` | Called before `getSchema()` | `await neoSchema.getSchema()` first |
| `Missing @fulltext index …` / `Missing @vector index …` | Index not in DB; v7 never creates it | `CREATE FULLTEXT INDEX` / `CREATE VECTOR INDEX` in Cypher first |
| Auth not applied | JWT not in context | Pass `token: req.headers.authorization` in context function |
| 0 results with valid data | v7 filter missing `eq` | Use `{ field: { eq: value } }` not `{ field: value }` |
| `connectOrCreate not found` | Removed in v7 | Use `connect` + `create` separately |
| Memory errors on large mutations | Complex Cypher generation | Batch mutations; increase `server.memory.heap.max_size` |
| Subscription type missing | v7 requires flag + directive | `features: { subscriptions: true }` AND `extend schema @subscription` in typeDefs; CDC enabled |

---

## v6 → v7 Breaking Changes Summary

| v6 | v7 |
|---|---|
| `@node` optional | `@node` required on every node type |
| `options: { limit, sort }` | `limit`, `sort` as direct args |
| `{ field: value }` filter | `{ field: { eq: value } }` |
| `connectOrCreate` nested mutation | Removed — use `connect` + `create` |
| `directed` arg on queries | `queryDirection` in `@relationship` |
| Single rel fields `actor: Person` | Allowed from 7.5.0 but must be nullable (`actor: Person`, not `Person!`); else use list |
| `@private` directive | Removed |
| `@unique` directive | Removed — create uniqueness constraints in Cypher |

---

## References

- [Neo4j GraphQL Docs](https://neo4j.com/docs/graphql/current/) — full directive reference, migration guides
- [GraphAcademy: GraphQL Basics](https://graphacademy.neo4j.com/courses/graphql-basics/) — hands-on course
- [GitHub: @neo4j/graphql](https://github.com/neo4j/graphql) — changelog, issues
- [CDC Setup](https://neo4j.com/docs/cdc/current/) — required for subscriptions
- [references/search-directives.md](references/search-directives.md) — `@fulltext`, `@vector`, `maxPhraseLength`

---

## Checklist

- [ ] `@node` on every GraphQL type representing a Neo4j node (v7 hard requirement)
- [ ] `@id` on identity fields (UUID only) + uniqueness constraint created in Cypher: `CREATE CONSTRAINT movie_id IF NOT EXISTS FOR (m:Movie) REQUIRE m.id IS UNIQUE`
- [ ] `assertIndexesAndConstraints()` called after `await getSchema()`, in try/catch; `@fulltext`/`@vector` indexes created first
- [ ] `@relationship` direction correct: `OUT` = arrow leaves this node, `IN` = arrow enters
- [ ] Both sides of relationship declared with inverse directions
- [ ] `@cypher` `columnName` matches RETURN alias exactly
- [ ] JWT secret or JWKS URL in `features.authorization.key`; token passed in context
- [ ] `@authorization` filter vs validate chosen deliberately (silent hide vs thrown error)
- [ ] v7: filters use explicit `{ field: { eq: value } }` syntax
- [ ] v7: `limit`/`sort` passed as direct query args (not `options` wrapper)
- [ ] OGM: v5 only, v5 filter syntax; `await ogm.init()` before any `ogm.model()` usage
- [ ] Subscriptions: CDC enabled in FULL mode (Enterprise / Aura BC/VDC); v7 also `extend schema @subscription`
- [ ] `@neo4j/graphql` ≥ 7.6.4 (v7) or ≥ 5.12.15 (LTS) — earlier versions have auth bypasses
- [ ] `.env` holds credentials; `.env` in `.gitignore`
