CREATE (:Chunk {
  id: 'chunk-1',
  text: 'Graph databases store connected data.',
  source: 'docs',
  lang: 'en',
  embedding: [0.1, 0.2, 0.3]
});

CREATE (:Chunk {
  id: 'chunk-2',
  text: 'Relational databases store tabular data.',
  source: 'docs',
  lang: 'en',
  embedding: [0.2, 0.1, 0.0]
});

CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS { indexConfig: { `vector.dimensions`: 3, `vector.similarity_function`: 'cosine' } };

CALL db.awaitIndexes(30);
