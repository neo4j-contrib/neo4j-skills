# neo4j-driver-java-skill

Skill for writing Java (and Kotlin) code with the official Neo4j Java Driver v6.

**Covers:**
- Maven/Gradle dependency setup
- Driver creation, `verifyConnectivity`, lifecycle management
- `executableQuery` — recommended default API
- Managed transactions (`executeRead` / `executeWrite`) with result lifecycle rules
- Explicit transactions, rollback safety, commit uncertainty
- Async API (`CompletableFuture` / `CompletionStage`)
- Reactive API (Project Reactor `RxSession`)
- Error handling (`ServiceUnavailableException`, `TransientException`, `Neo4jException`)
- Data type mapping and null-safety (`asString`, `isNull`, `containsKey`)
- Batch writes with `UNWIND` and parameter type rules
- Connection pool tuning
- Causal consistency and cross-session bookmarks

**Compatibility:** Neo4j Java Driver v6 · Java 17+ · Kotlin 1.9+

**Not covered:**
- Cypher query authoring → `neo4j-cypher-skill`
- Driver version migrations → `neo4j-migration-skill`
- Spring Data Neo4j (`@Node`, `Neo4jRepository`) → `neo4j-spring-data-skill`

**Install:**
```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-driver-java-skill
```

Or paste into your coding assistant:
https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-driver-java-skill
