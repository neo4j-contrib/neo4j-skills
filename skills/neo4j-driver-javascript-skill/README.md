# neo4j-driver-javascript-skill

Skill for the official Neo4j JavaScript/TypeScript Driver (v6) — covering:

- Driver setup, connection URIs, and authentication
- `executeQuery` (default API), `executeRead/Write` (managed transactions), `session.run` (implicit transactions)
- Integer handling (`neo4j.int`, `disableLosslessIntegers`, `useBigInt`) and JSON serialization
- Record access (`.get()`) and common serialization pitfalls
- Async/await patterns and session close safety (`finally` block)
- TypeScript types (`Driver`, `Session`, `ManagedTransaction`, `Node<Integer>`)
- Error handling (`Neo4jError`, `SERVICE_UNAVAILABLE`, retriable errors)
- Batch writes with `UNWIND`

**Not covered** (see sibling skills):
- Cypher query authoring → `neo4j-cypher-skill`
- Driver version migration → `neo4j-migration-skill`

**Compatibility**: `neo4j-driver` v6; Node.js >=18; browser via bundler (webpack/Vite/Rollup)

**Install:**
```bash
npm install neo4j-driver
```
