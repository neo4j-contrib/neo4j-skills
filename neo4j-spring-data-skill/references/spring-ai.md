# Spring AI — Neo4jVectorStore

Moved from SKILL.md to keep it under the 500-line budget.

## Spring AI — Neo4jVectorStore

### Dependency

Boot BOM does not manage Spring AI — import `spring-ai-bom`, or Maven fails: `'dependencies.dependency.version' ... is missing`. Spring AI 2.0.x → Boot 4.0/4.1; 1.1.x → Boot 3.4/3.5.

```xml
<dependencyManagement><dependencies><dependency>
    <groupId>org.springframework.ai</groupId><artifactId>spring-ai-bom</artifactId>
    <version>2.0.2</version><type>pom</type><scope>import</scope>   <!-- Boot 3.4/3.5: 1.1.x -->
</dependency></dependencies></dependencyManagement>

<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-starter-vector-store-neo4j</artifactId>
</dependency>
```

### application.yml

```yaml
spring:
  ai:
    vectorstore:
      neo4j:
        initialize-schema: true         # creates vector index on first run
        index-name: my-index
        embedding-dimension: 1536       # must match your embedding model
        distance-type: cosine           # cosine (default) or euclidean
        label: Document                 # node label for stored chunks
        embedding-property: embedding   # property for the vector
```

Requires Neo4j 5.15+. Reuses `spring.neo4j.*` connection config.

### Usage

```java
@Autowired VectorStore vectorStore;

// Store
vectorStore.add(List.of(new Document("text", Map.of("author", "alice"))));

// Similarity search
List<Document> results = vectorStore.similaritySearch(
    SearchRequest.builder().query("spring neo4j").topK(5).similarityThreshold(0.75).build()
);

// With metadata filter
vectorStore.similaritySearch(
    SearchRequest.builder().query("spring neo4j").topK(5)
        .filterExpression("author == 'alice'").build()
);
```

---
