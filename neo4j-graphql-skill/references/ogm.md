# OGM — Programmatic Access

Moved from SKILL.md to keep it under the 500-line budget.

## OGM — Programmatic Access

OGM bypasses GraphQL authorization — use only in trusted server-side contexts.

**v5 only — no v7 OGM.** `@neo4j/graphql-ogm` (npm `latest` 5.11.4, `lts` 5.12.16; peer `neo4j-driver ^5.8.0`) bundles `@neo4j/graphql` 5.x: accepts v7 typeDefs but uses v5 filter/update syntax (`{ title: 'x' }`, not `{ title: { eq: 'x' } }`). On v7 without OGM, run GraphQL operations against the schema or use the driver directly.

```javascript
import { OGM } from '@neo4j/graphql-ogm';

const ogm = new OGM({ typeDefs, driver });
await ogm.init();  // must await before using models

const Movie = ogm.model('Movie');

// find
const movies = await Movie.find({
  where: { title: 'The Matrix' },   // v5 syntax — { eq: ... } fails
  selectionSet: `{ id title actors { name } }`,
});

// create
const { movies: created } = await Movie.create({
  input: [{ title: 'Dune', actors: { create: [{ node: { name: 'Timothée Chalamet' } }] } }],
});

// update
await Movie.update({
  where: { id: movieId },
  update: { title: 'Dune: Part One' },
});

// delete
await Movie.delete({ where: { id: movieId } });
```

Install separately: `npm install @neo4j/graphql-ogm`

---
