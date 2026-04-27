---
name: neo4j-modeling-skill
description: >
  Use when designing or reviewing a Neo4j graph data model: choosing node labels and
  relationship types, deciding what to embed vs reference, normalizing or denormalizing
  for traversal performance, reviewing a schema against graph modeling best practices,
  or migrating a relational/document schema to a graph. Does NOT handle Cypher query
  writing — use neo4j-cypher-skill. Does NOT handle application-side mapping (Spring
  Data Neo4j OGM, GraphQL type definitions) — use neo4j-spring-data-skill or
  neo4j-graphql-skill.
status: draft
version: 0.1.0
allowed-tools: WebFetch
---

# Neo4j Modeling Skill

> **Status: Draft / WIP** — Content is a placeholder. Reference files and checklist rules to be added.

## When to Use

- Designing a graph data model from scratch (domain → nodes, relationships, properties)
- Reviewing an existing model for anti-patterns (generic nodes, unnecessary collections)
- Deciding what to model as a node vs a property vs a relationship
- Migrating a relational or document schema to a graph
- Choosing between embedding data on a node vs creating a dedicated node

## When NOT to Use

- **Writing or optimizing Cypher queries** → use `neo4j-cypher-skill`
- **Spring Data Neo4j entity mapping (@Node, @Relationship)** → use `neo4j-spring-data-skill`
- **GraphQL type definitions** → use `neo4j-graphql-skill`
- **Importing data** → use `neo4j-import-skill`

---

## MCP Tool Usage

When designing or reviewing an existing schema, use `get-schema` first:

| Operation | MCP tool | Notes |
|---|---|---|
| Inspect existing schema | `get-schema` | Run before proposing any changes |
| `SHOW CONSTRAINTS`, `SHOW INDEXES` | `read-cypher` | Verify what already exists |
| `CREATE CONSTRAINT ... IF NOT EXISTS` | `write-cypher` | Safe to run repeatedly |

Never propose schema changes without first inspecting the current state.

---

## Inspect Before Designing

**On an existing database**, always run this before proposing model changes:
```cypher
CALL db.schema.visualization() YIELD nodes, relationships RETURN nodes, relationships;
SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties RETURN name, type, labelsOrTypes, properties;
SHOW INDEXES YIELD name, type, labelsOrTypes, state WHERE state = 'ONLINE' RETURN name, type, labelsOrTypes;
```

---

## Modeling Decision Tree

```
1. Is it a "thing" with identity and multiple query entry points? → Node
2. Is it a connection between two things with direction or properties? → Relationship
3. Is it a simple scalar always queried with its parent? → Property on parent node
4. Is it a fact with its own properties or multiple connections? → Intermediate node
5. Is it a type/category queried separately? → Label (not a property)
```

---

## Core Principles

**Labels** — noun-like, PascalCase, describe what an entity *is* (`:Person`, `:Product`). Avoid generic labels like `:Node` or `:Entity`.

**Relationship types** — verb-like, SCREAMING_SNAKE_CASE, describe the *direction* of the connection (`:KNOWS`, `:PURCHASED`). Avoid generic types like `:RELATED_TO`.

**Properties** — camelCase. Only store what you query. Large blobs (embeddings, full text) belong on dedicated nodes.

**Constraints** — every node type used in MERGE must have a uniqueness constraint on its key property. Apply before importing data.

---

## Schema Review Checklist

- [ ] Every node label has a unique constraint on its identifier property
- [ ] No generic labels (`:Node`, `:Entity`, `:Thing`)
- [ ] No generic relationship types (`:RELATED_TO`, `:HAS`)
- [ ] Relationship direction encodes meaning (not arbitrary)
- [ ] Properties that are never filtered/sorted are not indexed
- [ ] Intermediate nodes used for many-to-many with properties (not bare relationships)
- [ ] Embedding properties stored on dedicated `:Chunk` nodes, not on business nodes
- [ ] Labels are PascalCase; relationship types are SCREAMING_SNAKE_CASE

---

## Output Format (Schema Assessment)

```
## Schema Assessment

### Compliant
- [item checked]

### Issues Found
#### [Issue Title] — Severity: HIGH / MEDIUM / LOW
- Current: [what the model does]
- Problem: [why it is an issue]
- Fix: [specific recommendation]

## Recommended Schema
[nodes, relationships, properties, constraints]
```

---

## References

- [Graph Data Modeling Guide](https://neo4j.com/docs/getting-started/data-modeling/)
- [GraphAcademy: Graph Data Modeling Fundamentals](https://graphacademy.neo4j.com/courses/modeling-fundamentals/)
- [Graph Modeling Tips](https://neo4j.com/developer/guide-data-modeling/)
