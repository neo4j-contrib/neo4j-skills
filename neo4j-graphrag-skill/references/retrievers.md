# Retriever API Reference

## VectorRetriever

```python
VectorRetriever(
    driver,
    index_name: str,
    embedder=None,           # required if passing query_text; optional if passing query_vector
    return_properties: list[str] = None,  # subset of node props to return
    result_formatter=None,   # callable(neo4j.Record) -> RetrieverResultItem
    neo4j_database: str = None,
)
```

`search()` params: `query_text` | `query_vector`, `top_k=5`, `filters={}`, `effective_search_ratio=1`

## VectorCypherRetriever

```python
VectorCypherRetriever(
    driver,
    index_name: str,
    retrieval_query: str,    # Cypher fragment; receives `node` and `score`
    embedder=None,
    result_formatter=None,
    neo4j_database: str = None,
)
```

`search()` params: `query_text` | `query_vector`, `top_k=5`, `query_params={}`, `filters={}`, `effective_search_ratio=1`

## HybridRetriever

```python
HybridRetriever(
    driver,
    vector_index_name: str,
    fulltext_index_name: str,
    embedder=None,
    return_properties: list[str] = None,
    result_formatter=None,
    neo4j_database: str = None,
)
```

`search()` params: `query_text` (required — used for both vector and fulltext), `top_k=5`, `filters={}`, `effective_search_ratio=1`

## HybridCypherRetriever

```python
HybridCypherRetriever(
    driver,
    vector_index_name: str,
    fulltext_index_name: str,
    retrieval_query: str,
    embedder=None,
    result_formatter=None,
    neo4j_database: str = None,
)
```

`search()` params: `query_text` (required), `top_k=5`, `query_params={}`, `filters={}`, `effective_search_ratio=1`

## Text2CypherRetriever

```python
Text2CypherRetriever(
    driver,
    llm,                     # any LLMInterface implementation
    neo4j_schema: str = None,  # None = auto-fetched; pass trimmed string for large schemas
    examples: list[str] = None,  # few-shot examples as "Q: ... A: MATCH ..."
    neo4j_database: str = None,
)
```

`search()` params: `query_text` (natural language question), `query_params={}`

No embedder needed. LLM generates the Cypher; `neo4j_schema` is injected into prompt.

## ToolsRetriever

```python
ToolsRetriever(
    driver,
    llm,
    tools: list,             # list of retrievers converted via convert_to_tool()
    system_instruction: str = None,
    neo4j_database: str = None,
)
```

Convert a retriever to a tool:
```python
from neo4j_graphrag.tool import convert_to_tool
tool = convert_to_tool(retriever, name="vector_search", description="Searches by embedding similarity")
```

## External Vector DB Retrievers

```python
from neo4j_graphrag.retrievers import (
    WeaviateNeo4jRetriever,
    PineconeNeo4jRetriever,
    QdrantNeo4jRetriever,
)
# Each maps external vector store IDs to Neo4j node IDs
# Requires: pip install neo4j-graphrag[weaviate|pinecone|qdrant]
```

## result_formatter Pattern

```python
from neo4j_graphrag.types import RetrieverResultItem

def my_formatter(record: neo4j.Record) -> RetrieverResultItem:
    return RetrieverResultItem(
        content=f"[{record['article_title']}] {record['chunk_text']}",
        metadata={"orgs": record["mentioned_organizations"], "score": record["score"]},
    )

retriever = VectorCypherRetriever(..., result_formatter=my_formatter)
```

## effective_search_ratio

Controls candidate pool: `candidates = top_k * effective_search_ratio`. Increase (e.g. 2–5) when `retrieval_query` filters reduce results significantly.

## Pre-filter Operators

```python
filters = {
    "property_name": {"$eq": value},
    "property_name": {"$in": [v1, v2]},
    "property_name": {"$between": {"min": 0, "max": 1}},
    "property_name": {"$like": "prefix%"},   # case-sensitive
    "property_name": {"$ilike": "prefix%"},  # case-insensitive
}
# Combine: {"$and": [{...}, {...}]} or {"$or": [{...}, {...}]}
```
