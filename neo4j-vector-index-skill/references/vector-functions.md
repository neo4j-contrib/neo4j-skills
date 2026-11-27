# Vector Functions

Moved from SKILL.md to keep it under the 500-line budget.

## Vector Functions

Ad-hoc similarity (not for kNN search — use index for that):
```cypher
MATCH (a:Chunk {id: $id1}), (b:Chunk {id: $id2})
RETURN vector.similarity.cosine(a.embedding, b.embedding) AS sim
// vector.similarity.euclidean(a, b) — same signature, 0–1 range
```

`vector_distance`, `vector_dimension_count`, `vector_norm` (Cypher 25, 2025.10+) take `VECTOR` arguments. Driver-written embeddings are `LIST<FLOAT>` → convert with `vector(list, dims, FLOAT32)`. Only `vector.similarity.*` accept lists. Metric and coordinate-type names are unquoted keywords — quoted strings fail (`42I62` unknown metric, `42I53` unknown coordinate type).
```cypher
CYPHER 25
MATCH (a:Chunk {id: $id1}), (b:Chunk {id: $id2})
// vector_distance — metrics: EUCLIDEAN, EUCLIDEAN_SQUARED, MANHATTAN, COSINE, DOT, HAMMING
// Returns distance (lower = more similar, inverse of similarity)
RETURN vector_distance(vector(a.embedding, 1536, FLOAT32), vector(b.embedding, 1536, FLOAT32), COSINE) AS dist,
       vector_dimension_count(vector(a.embedding, 1536, FLOAT32)) AS dims,
       // vector_norm — metrics: EUCLIDEAN, MANHATTAN
       vector_norm(vector(a.embedding, 1536, FLOAT32), EUCLIDEAN) AS norm
```

Convert LIST to typed VECTOR:
```cypher
// vector(value, dimension, coordinateType)
// coordinateType (unquoted keyword): FLOAT64, FLOAT32, INTEGER8/16/32/64
WITH vector([1.0, 2.0, 3.0], 3, FLOAT32) AS v
RETURN vector_dimension_count(v)
```

---
