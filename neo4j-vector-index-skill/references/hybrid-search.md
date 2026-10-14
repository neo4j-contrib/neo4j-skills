# Hybrid Search

Hybrid search is useful when one retrieval signal is not enough:
- Semantic vector search finds paraphrases; misses exact names, acronyms, codes, and domain terms.
- Lexical fulltext search finds exact words; misses related concepts that do not share words.
- Structural search uses graph topology, paths, communities, or GDS node embeddings; captures relationships text does not contain.

Combining ranked sources improves recall and can boost results that are supported by more than one signal. The common pattern is vector + fulltext, but the same query shape works for any two or more ranked/scored sources: several vector indexes, title/body fulltext indexes, GDS-written structural embeddings, graph-derived candidate scores, or external retrieval scores.

Use when the user asks for custom Cypher hybrid search, WRRF/RRF, vector + fulltext, semantic + lexical + structural search, multiple vector indexes, or combining two+ ranked/scored retrieval sources.

## When NOT to Use
- `neo4j-graphrag` package `HybridRetriever` / `HybridCypherRetriever` -> use `neo4j-graphrag-skill`
- Fulltext-only / keyword-only search -> use `neo4j-cypher-skill`
- Single vector search -> use main `neo4j-vector-index-skill`

## Rules
- Run each source independently.
- Rank each source by `score DESC, stable_id ASC`.
- Do not compare raw scores from different sources.
- Compute `contribution = sourceWeight / (rrfConstant + sourceRank)`.
- Sum contributions per node.
- Order final rows by `wrrf DESC, stable_id ASC`.
- Use `sourceK > finalK`; combine before final limiting.
- Use stable unique property for tie breaks. If no stable key exists, add one before production use.
- Keep `LIMIT $sourceK` inside `SEARCH`; Cypher rejects a `LET` alias there.
- For structural vector sources, compute/write GDS embeddings first, then create a vector index over that property.

## Index Setup

Vector index:
```cypher
CYPHER 25
CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }
};
```

Fulltext index:
```cypher
CYPHER 25
CREATE FULLTEXT INDEX chunk_fulltext IF NOT EXISTS
FOR (c:Chunk) ON EACH [c.text];
```

If fulltext compatibility, analyzer, multi-property, or Lucene query syntax details matter, load `neo4j-cypher-skill`.

## Parameters

```json
{
  "query": "graph database search",
  "queryVector": [0.12, -0.03, 0.45],
  "sourceK": 20,
  "finalK": 10,
  "rrfConstant": 60.0,
  "sourceWeights": {
    "fulltext": 1.0,
    "vector": 1.0
  }
}
```

## Query Template

```cypher
CYPHER 25
LET
  query = $query,
  queryVector = $queryVector,
  finalK = $finalK,
  rrfConstant = $rrfConstant,
  sourceWeights = $sourceWeights

CALL (query, queryVector, rrfConstant, sourceWeights) {
  MATCH (chunk:Chunk)
    SEARCH chunk IN (
      FULLTEXT INDEX chunk_fulltext
      FOR query
      LIMIT $sourceK
    ) SCORE AS score
  ORDER BY score DESC, chunk.id ASC
  WITH collect(chunk) AS chunks, rrfConstant, sourceWeights
  LET weight = coalesce(sourceWeights['fulltext'], 1.0)
  UNWIND CASE WHEN size(chunks) = 0 THEN [] ELSE range(0, size(chunks) - 1) END AS rankIndex
  RETURN
    chunks[rankIndex] AS chunk,
    weight / (rrfConstant + rankIndex + 1) AS contribution

  UNION ALL

  MATCH (chunk:Chunk)
    SEARCH chunk IN (
      VECTOR INDEX chunk_embedding
      FOR queryVector
      LIMIT $sourceK
    ) SCORE AS score
  ORDER BY score DESC, chunk.id ASC
  WITH collect(chunk) AS chunks, rrfConstant, sourceWeights
  LET weight = coalesce(sourceWeights['vector'], 1.0)
  UNWIND CASE WHEN size(chunks) = 0 THEN [] ELSE range(0, size(chunks) - 1) END AS rankIndex
  RETURN
    chunks[rankIndex] AS chunk,
    weight / (rrfConstant + rankIndex + 1) AS contribution
}
WITH chunk, finalK, sum(contribution) AS wrrf
ORDER BY wrrf DESC, chunk.id ASC
WITH collect({chunk: chunk, wrrf: wrrf}) AS orderedRows, finalK
LET limitedRows = orderedRows[..finalK]
UNWIND limitedRows AS row
RETURN row.chunk.id AS id, row.chunk.text AS text, row.wrrf AS wrrf
ORDER BY row.wrrf DESC, row.chunk.id ASC;
```

## Add More Sources

Add one `UNION ALL` branch per source. Each branch must return:

```cypher
RETURN
  matchedNode AS chunk,
  weight / (rrfConstant + rankIndex + 1) AS contribution
```

Examples:
- second vector index with different embedding model -> `sourceWeights['vector_large']`
- vector index over GDS FastRP/Node2Vec embeddings -> `sourceWeights['structural_vector']`
- fulltext index over title fields -> `sourceWeights['title_fulltext']`
- graph-derived candidate score converted to source rank -> `sourceWeights['graph']`

## Checklist
- [ ] Vector and fulltext indexes `ONLINE`
- [ ] Query embedding generated with same model as stored embeddings
- [ ] Structural embeddings/scores already produced before query
- [ ] `sourceK` larger than `finalK`
- [ ] Stable unique property used for tie-breaks
- [ ] Raw scores not compared across sources
- [ ] Missing source weights intentionally default to `1.0`
- [ ] Additional source branches return same columns
