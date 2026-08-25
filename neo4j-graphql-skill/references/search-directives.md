# @fulltext and @vector — Search Directives

Neither directive creates its index. Create it in Cypher first — `assertIndexesAndConstraints` covers `@id` constraints only.

## @fulltext

```graphql
type Product @node
  @fulltext(indexes: [{ indexName: "ProductName", queryName: "productsByName", fields: ["name"] }]) {
  name: String!
}
```

```cypher
CREATE FULLTEXT INDEX ProductName FOR (n:Product) ON EACH [n.name]
```

| Field | Required | Notes |
|---|---|---|
| `indexName` | yes | must match the Cypher index name |
| `fields` | yes | node properties covered by the index |
| `queryName` | no | default generated name is `{plural}Fulltext{indexName}` |

```graphql
query {
  productsByName(phrase: "Hot sauce", where: { score: { min: 1.1 } }, sort: [{ product: { name: ASC } }], limit: 10) {
    score
    product { name }
  }
}
```

`where.score` takes `{ min, max }` FLOAT bounds; `where.product` takes the normal `ProductWhere` input.

## @vector

Prerequisites: Neo4j 5.15+; embeddings already written to the node property; all embeddings from the same provider and model. Vector queries cannot span multiple labels. Aura Console Data APIs do not support `@vector`.

| `VectorIndexInput` field | Required | Notes |
|---|---|---|
| `indexName` | yes | Cypher vector index name |
| `embeddingProperty` | yes | node property holding the embedding |
| `queryName` | yes | name of the generated top-level query |
| `provider` | no | GenAI provider enum (`OPEN_AI`, …) — enables `phrase` argument |
| `callback` | no | server-side function producing the embedding — alternative to `provider` |
| `maxPhraseLength` | no | [7.6.0] max `phrase` length in Unicode code points, min `1` |

### Query by vector

```graphql
type Product @node @vector(indexes: [{
  indexName: "productDescriptionIndex",
  embeddingProperty: "descriptionVector",
  queryName: "searchByDescription"
}]) {
  id: ID!
  name: String!
  description: String!
}
```

```graphql
query FindSimilarProducts($vector: [Float]!) {
  searchByDescription(vector: $vector) {
    edges {
      cursor
      score
      node { id name description }
    }
  }
}
```

### Query by phrase

Requires GenAI plugin credentials in the constructor:

```javascript
const neoSchema = new Neo4jGraphQL({
  typeDefs,
  driver,
  features: {
    vector: {
      OpenAI: { token: process.env.OPENAI_API_KEY, model: 'text-embedding-3-small' },
    },
  },
});
```

```graphql
type Product @node @vector(indexes: [{
  indexName: "productDescriptionIndex",
  embeddingProperty: "descriptionVector",
  provider: OPEN_AI,
  queryName: "searchByPhrase",
  maxPhraseLength: 100
}]) {
  id: ID!
  name: String!
  description: String!
}
```

```graphql
query SearchProductsByPhrase($phrase: String!) {
  searchByPhrase(phrase: $phrase) {
    edges { cursor score node { id name description } }
  }
}
```

`maxPhraseLength` rejects over-length `phrase` values with `Neo4jGraphQLError` before Cypher generation and before any embedding provider call — caps embedding spend per index. It does not constrain the `vector` argument.

| Error | Cause | Fix |
|---|---|---|
| Schema build fails on `maxPhraseLength` | index has no `provider` or `callback` | Set `maxPhraseLength` only on phrase-capable indexes |
| `Neo4jGraphQLError` on a valid-looking phrase | phrase longer than `maxPhraseLength` | Truncate client-side or raise the limit |
| Vector query returns no `score` | reading `node` outside `edges` | Select `edges { score node { … } }` |
| Provider errors on `phrase` query | `features.vector.<Provider>` credentials missing | Add provider token + model to the constructor |
