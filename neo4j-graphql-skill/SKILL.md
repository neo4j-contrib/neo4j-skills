---
name: neo4j-graphql-skill
description: >
  Use when building a GraphQL API backed by Neo4j using the Neo4j GraphQL Library:
  type definitions, @relationship directive, @cypher directive for custom resolvers,
  @authorization for field-level security, auto-generated queries and mutations,
  OGM (Object Graph Mapper) usage, or schema augmentation. Does NOT handle raw
  Cypher queries — use neo4j-cypher-skill. Does NOT handle Spring Data Neo4j
  entity mapping — use neo4j-spring-data-skill.
status: draft
version: 0.1.0
allowed-tools: Bash, WebFetch
---

# Neo4j GraphQL Skill

> **Status: Draft / WIP** — Content is a placeholder. Reference files to be added.

## When to Use

- Creating a GraphQL API from a Neo4j graph schema with `@neo4j/graphql`
- Writing type definitions with `@relationship`, `@cypher`, `@authorization` directives
- Using the OGM (Object Graph Mapper) for server-side programmatic access
- Configuring auto-generated queries, mutations, and subscriptions
- Securing fields with JWT-based `@authorization` rules

## When NOT to Use

- **Raw Cypher queries outside GraphQL resolvers** → use `neo4j-cypher-skill`
- **Spring Data Neo4j / Java entity mapping** → use `neo4j-spring-data-skill`
- **GraphQL without Neo4j** (generic GraphQL) — outside scope of this skill

---

## Setup

```bash
npm install @neo4j/graphql neo4j-driver graphql @apollo/server
```

---

## Core Pattern

```javascript
import { Neo4jGraphQL } from '@neo4j/graphql'
import neo4j from 'neo4j-driver'
import { ApolloServer } from '@apollo/server'

const typeDefs = `#graphql
  type Person {
    id: ID! @id
    name: String!
    friends: [Person!]! @relationship(type: "KNOWS", direction: OUT)
    posts: [Post!]! @relationship(type: "POSTED", direction: OUT)
  }

  type Post {
    id: ID! @id
    title: String!
    author: Person! @relationship(type: "POSTED", direction: IN)
  }
`

const driver = neo4j.driver(
  process.env.NEO4J_URI,
  neo4j.auth.basic(process.env.NEO4J_USERNAME, process.env.NEO4J_PASSWORD)
)

const neoSchema = new Neo4jGraphQL({ typeDefs, driver })
const schema = await neoSchema.getSchema()

const server = new ApolloServer({ schema })
```

### @cypher directive (custom resolver)

```graphql
type Person {
  name: String!
  friendCount: Int!
    @cypher(
      statement: "MATCH (this)-[:KNOWS]->(f:Person) RETURN count(f) AS friendCount"
      columnName: "friendCount"
    )
}
```

### @authorization (field-level security)

> **Important**: `@authorization` is passive — if the JWT is missing or invalid, `$jwt.sub` evaluates to `null` and the rule may silently pass or fail depending on your condition. To explicitly reject unauthenticated requests, add `isAuthenticated: true` to the rule or validate the JWT upstream in your server middleware before it reaches GraphQL.

```graphql
type Post @authorization(
  validate: [{
    when: [BEFORE],
    requireAuthentication: true,   # rejects if JWT missing
    where: { node: { author: { id: "$jwt.sub" } } }
  }]
) {
  title: String!
  author: Person!
}
```

---

## Checklist

- [ ] `@id` on all identity fields (generates unique constraint in Neo4j)
- [ ] `@relationship` direction matches actual graph direction
- [ ] `@cypher` `columnName` matches the RETURN alias **exactly** — mismatch returns null silently
- [ ] `@authorization` rules tested with missing JWT (not just invalid) — passive by default
- [ ] `neoSchema.assertIndexesAndConstraints()` called on startup — wrap in try/catch; throws if constraints missing, which means `@id` fields weren't synced to DB yet: run `CREATE CONSTRAINT` manually then retry

---

## References

- [Neo4j GraphQL Library Docs](https://neo4j.com/docs/graphql/)
- [GraphAcademy: Introduction to Neo4j & GraphQL](https://graphacademy.neo4j.com/courses/graphql-basics/)
- [Neo4j GraphQL GitHub](https://github.com/neo4j/graphql)
