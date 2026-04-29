---
name: neo4j-graphql-skill
description: Build and configure a GraphQL API backed by Neo4j using @neo4j/graphql v7 (current) or v5 (LTS).
  Covers Neo4jGraphQL constructor, getSchema(), assertIndexesAndConstraints(), type definitions with @node,
  @relationship (IN/OUT/UNDIRECTED), @cypher for custom resolvers, @authorization/@authentication for JWT/JWKS
  security, auto-generated queries/mutations, OGM programmatic access, subscriptions via CDC, and Apollo
  Federation. Use when writing typeDefs, securing fields, or wiring Neo4j to Apollo Server.
  Does NOT handle raw Cypher outside resolvers — use neo4j-cypher-skill.
  Does NOT cover Spring Data Neo4j entity mapping — use neo4j-spring-data-skill.
version: 1.0.0
allowed-tools: Bash WebFetch
---

## When to Use

- Creating a GraphQL API from a Neo4j graph schema with `@neo4j/graphql`
- Writing type definitions with `@relationship`, `@cypher`, `@authorization` directives
- Using OGM for server-side programmatic Neo4j access (bypasses GraphQL auth)
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
| v7 | Current | `@node` required; `options` removed; explicit `eq` syntax |
| v5 | LTS | Older syntax; `options: {limit, offset, sort}` still valid |

Default to v7 unless codebase is on v5.

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

// assertIndexesAndConstraints syncs @id → UNIQUE constraints; wrap in try/catch
await neoSchema.assertIndexesAndConstraints({ options: { create: true } });

const server = new ApolloServer({ schema: await neoSchema.getSchema() });

const { url } = await startStandaloneServer(server, {
  context: async ({ req }) => ({ token: req.headers.authorization }),
  listen: { port: 4000 },
});
```

`assertIndexesAndConstraints` throws if constraints missing. Use `{ create: true }` to auto-create, or run `CREATE CONSTRAINT` manually and retry.

---

## Key Directives

### @node (v7 required)

Every GraphQL type representing a Neo4j node must have `@node`. Without it, v7 ignores the type.

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

  # direction: UNDIRECTED = matches both directions (use sparingly — double-counts)
  colleagues: [Person!]! @relationship(type: "COLLEAGUE_OF", direction: UNDIRECTED)

  # Relationship with properties — reference an @relationshipProperties interface
  reviews: [Movie!]! @relationship(type: "REVIEWED", direction: OUT, properties: "ReviewedProps")
}

interface ReviewedProps @relationshipProperties {
  rating: Int!
  date: Date
}
```

Direction rule: `OUT` = arrow leaves this node. `IN` = arrow enters this node. Both sides of a relationship must declare opposite directions.

### Querying Relationship Properties — Connection API

For each relationship with `properties:`, a `{field}Connection` field is auto-generated. Access rel properties via `actorsConnection.edges.properties`, not via `actors`:

```graphql
query {
  movies(where: { title: { eq: "The Matrix" } }) {
    title
    actorsConnection {
      edges {
        properties { role }   # maps to @relationshipProperties interface
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
  id: ID! @id                          # auto-generates UUID; creates UNIQUE constraint
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
  author: User! @relationship(type: "AUTHORED", direction: IN)
}

# requireAuthentication: false = allow public access without JWT
type Article @node
  @authorization(filter: [
    { requireAuthentication: false, where: { node: { published: { eq: true } } } }
    { where: { node: { author: { id: { eq: "$jwt.sub" } } } } }
  ]) {
  title: String!
  published: Boolean!
}

# validate (throws error) vs filter (silently hides data)
type BankAccount @node
  @authorization(validate: [{
    when: [BEFORE],
    where: { node: { owner: { id: { eq: "$jwt.sub" } } } }
  }]) {
  balance: Float!
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

**filter vs validate**: `filter` silently removes unauthorized data. `validate` throws an error. Use `validate` when data existence should not be revealed to unauthorized users.

**BEFORE vs AFTER**: `CREATE` supports only `AFTER`; `READ` supports only `BEFORE`.

---

## Auto-Generated Operations

For each `@node` type, the library generates:

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

`connectOrCreate` was removed in v7. Use `connect` + `create` separately.

---

## OGM — Programmatic Access

OGM bypasses GraphQL authorization — use only in trusted server-side contexts.

```javascript
import { OGM } from '@neo4j/graphql-ogm';

const ogm = new OGM({ typeDefs, driver });
await ogm.init();  // must await before using models

const Movie = ogm.model('Movie');

// find
const movies = await Movie.find({
  where: { title: { eq: 'The Matrix' } },
  selectionSet: `{ id title actors { name } }`,
});

// create
const { movies: created } = await Movie.create({
  input: [{ title: 'Dune', actors: { create: [{ node: { name: 'Timothée Chalamet' } }] } }],
});

// update
await Movie.update({
  where: { id: { eq: movieId } },
  update: { title: { set: 'Dune: Part One' } },
});

// delete
await Movie.delete({ where: { id: { eq: movieId } } });
```

Install separately: `npm install @neo4j/graphql-ogm`

---

## Subscriptions (CDC Required)

Requires Neo4j CDC enabled in `FULL` mode. See [CDC docs](https://neo4j.com/docs/cdc/current/).

```javascript
const neoSchema = new Neo4jGraphQL({
  typeDefs,
  driver,
  features: { subscriptions: true },
});
```

Subscriptions auto-generate for each type:
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
  content: String! @filterable(byValue: false) @sortable(enabled: false)  # perf guard
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
| `assertIndexesAndConstraints` throws | `@id` constraint not in DB | Add `{ options: { create: true } }` or run `CREATE CONSTRAINT` manually |
| Auth not applied | JWT not in context | Pass `token: req.headers.authorization` in context function |
| 0 results with valid data | v7 filter missing `eq` | Use `{ field: { eq: value } }` not `{ field: value }` |
| `connectOrCreate not found` | Removed in v7 | Use `connect` + `create` separately |
| Memory errors on large mutations | Complex Cypher generation | Batch mutations; increase `server.memory.heap.max_size` |
| `@subscription` not generating | v7 requires explicit enable | Add `features: { subscriptions: true }` to constructor |

---

## v6 → v7 Breaking Changes Summary

| v6 | v7 |
|---|---|
| `@node` optional | `@node` required on every node type |
| `options: { limit, sort }` | `limit`, `sort` as direct args |
| `{ field: value }` filter | `{ field: { eq: value } }` |
| `connectOrCreate` nested mutation | Removed — use `connect` + `create` |
| `directed` arg on queries | `queryDirection` in `@relationship` |
| Single rel fields `actor: Person` | Must use list `actors: [Person!]!` |
| `@private` directive | Removed |
| `@unique` directive | Removed |

---

## References

- [Neo4j GraphQL Docs](https://neo4j.com/docs/graphql/current/) — full directive reference, migration guides
- [GraphAcademy: GraphQL Basics](https://graphacademy.neo4j.com/courses/graphql-basics/) — hands-on course
- [GitHub: @neo4j/graphql](https://github.com/neo4j/graphql) — changelog, issues
- [CDC Setup](https://neo4j.com/docs/cdc/current/) — required for subscriptions

---

## Checklist

- [ ] `@node` on every GraphQL type representing a Neo4j node (v7 hard requirement)
- [ ] `@id` on identity fields (triggers `CREATE CONSTRAINT` via `assertIndexesAndConstraints`)
- [ ] `assertIndexesAndConstraints` called on startup with try/catch
- [ ] `@relationship` direction correct: `OUT` = arrow leaves this node, `IN` = arrow enters
- [ ] Both sides of relationship declared with inverse directions
- [ ] `@cypher` `columnName` matches RETURN alias exactly
- [ ] JWT secret or JWKS URL in `features.authorization.key`; token passed in context
- [ ] `@authorization` filter vs validate chosen deliberately (silent hide vs thrown error)
- [ ] v7: filters use explicit `{ field: { eq: value } }` syntax
- [ ] v7: `limit`/`sort` passed as direct query args (not `options` wrapper)
- [ ] OGM: `await ogm.init()` called before any `ogm.model()` usage
- [ ] Subscriptions: CDC enabled in FULL mode before enabling `features.subscriptions`
- [ ] `.env` holds credentials; `.env` in `.gitignore`
