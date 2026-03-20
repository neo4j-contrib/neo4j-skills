# Cypher Skill Test Report — `run-20260320T135448`

**Skill**: `neo4j-cypher-authoring-skill`  
**Started**: 2026-03-20 13:54:48 UTC  
**Completed**: 2026-03-20 16:11:40 UTC  

## Overall Results

| Metric | Value |
|--------|-------|
| Total cases | 35 |
| PASS | 28 |
| WARN | 1 |
| FAIL | 6 |
| Pass rate | 80.0% |

## Per-Difficulty Pass Rates

| Difficulty | Total | PASS | WARN | FAIL | Pass Rate |
|------------|------:|-----:|-----:|-----:|----------:|
| Basic | 10 | 10 | 0 | 0 | 100.0% |
| Intermediate | 10 | 9 | 0 | 1 | 90.0% |
| Advanced | 10 | 7 | 1 | 2 | 70.0% |
| Complex | 5 | 2 | 0 | 3 | 40.0% |

## DB-Hits Summary (per Difficulty)

Only cases that completed Gate 4 (PROFILE) are included.

| Difficulty | n | Min | Median | Max |
|------------|--:|----:|-------:|----:|
| — | — | — | — | — |

## Test Case Results

| ID | Difficulty | Verdict | Gate | DB Hits | Duration (s) | Question |
|----|------------|---------|-----:|--------:|-------------:|----------|
| `companies-basic-001` | basic | PASS | — | — | 17.3 | Find the names of all top-level organizations (companies th… |
| `companies-basic-002` | basic | PASS | — | — | 6.4 | Count the total number of Organization nodes in the databas… |
| `companies-basic-003` | basic | PASS | — | — | 6.7 | Return the names of the first 10 organizations ordered alph… |
| `companies-basic-004` | basic | PASS | — | — | 15.1 | Find the top 10 articles by sentiment score for the organiz… |
| `companies-basic-005` | basic | PASS | — | — | 16.3 | Count how many articles mention each organization. Return t… |
| `companies-basic-006` | basic | PASS | — | — | 7.1 | Find all direct subsidiary organizations of 'Blackstone'. U… |
| `companies-basic-007` | basic | PASS | — | — | 4.1 | Find the average sentiment score across all articles in the… |
| `companies-basic-008` | basic | PASS | — | — | 4.6 | Return the names and descriptions of the 5 organizations th… |
| `companies-basic-009` | basic | PASS | — | — | 4.0 | Find all articles with a positive sentiment (sentiment > 0)… |
| `companies-basic-010` | basic | PASS | — | — | 7.7 | Count the number of articles for each sentiment bucket: pos… |
| `companies-intermediate-001` | intermediate | PASS | — | — | 4.9 | Find all organizations that are mentioned in articles with … |
| `companies-intermediate-002` | intermediate | PASS | — | — | 13.6 | Find pairs of organizations that are both mentioned in the … |
| `companies-intermediate-003` | intermediate | PASS | — | — | 8.6 | For each top-level organization (not a subsidiary), return … |
| `companies-intermediate-004` | intermediate | PASS | — | — | 6.9 | Search for organizations by name using the fulltext index. … |
| `companies-intermediate-005` | intermediate | PASS | — | — | 5.4 | Find all direct and indirect subsidiaries of 'Blackstone' (… |
| `companies-intermediate-006` | intermediate | PASS | — | — | 7.2 | Use a CALL subquery to find, for each of the top 5 most-men… |
| `companies-intermediate-007` | intermediate | PASS | — | — | 8.4 | Count the total number of Chunk nodes linked to articles th… |
| `companies-intermediate-008` | intermediate | PASS | — | — | 8.5 | Find organizations that have at least one subsidiary AND ar… |
| `companies-intermediate-009` | intermediate | **FAIL** | 2 | — | 16.9 | Using MERGE, create or match an Organization node with the … |
| `companies-intermediate-010` | intermediate | PASS | — | — | 5.1 | Find the organization with the most subsidiaries (direct on… |
| `companies-advanced-001` | advanced | PASS | — | — | 7.7 | Using a quantified path expression with the {1,2} quantifie… |
| `companies-advanced-002` | advanced | PASS | — | — | 7.0 | Using a quantified path expression with the {1,} quantifier… |
| `companies-advanced-003` | advanced | **FAIL** | 2 | — | 6338.0 | Find the shortest path (in hops) between 'Blackstone' and '… |
| `companies-advanced-004` | advanced | PASS | — | — | 58.0 | Use the db.index.vector.queryNodes procedure to perform a v… |
| `companies-advanced-005` | advanced | PASS | — | — | 5.8 | Use the db.index.fulltext.queryNodes procedure to search th… |
| `companies-advanced-006` | advanced | **FAIL** | 1 | — | 10.6 | For each top-level organization (not a subsidiary, tested w… |
| `companies-advanced-007` | advanced | PASS | — | — | 105.4 | Find organizations that appear together in articles with bo… |
| `companies-advanced-008` | advanced | PASS | — | — | 6.1 | Use COUNT subquery expressions to find organizations where … |
| `companies-advanced-009` | advanced | WARN | 4 | — | 224.2 | Find organizations linked to the same HAS_CATEGORY target n… |
| `companies-advanced-010` | advanced | PASS | — | — | 9.0 | Using COLLECT subquery expressions, for each organization r… |
| `companies-complex-001` | complex | **FAIL** | 2 | — | 9.3 | Write a query that demonstrates CALL IN TRANSACTIONS syntax… |
| `companies-complex-002` | complex | **FAIL** | 2 | — | 20.3 | Build a multi-level aggregation query: first use CALL subqu… |
| `companies-complex-003` | complex | **FAIL** | 2 | — | 37.5 | Combine vector similarity search with graph traversal using… |
| `companies-complex-004` | complex | PASS | — | — | 8.8 | For each organization with at least 5 subsidiaries, use a C… |
| `companies-complex-005` | complex | PASS | — | — | 8.8 | Write a query that uses EXISTS subquery expressions to clas… |

## Failure Analysis

### FAIL (6 cases)

#### Gate 1 (1 case(s))

**`companies-advanced-006`** — For each top-level organization (not a subsidiary, tested with NOT EXISTS), use a CALL subquery to compute both the count of direct subsidiaries and the average sentiment of all articles mentioning it. Only return organizations that have at least one article. Order by average sentiment ascending, limit to 10.

> **Gate 1 FAIL**: Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input 'WHERE': expected 'ORDER BY', 'CALL', 'CREATE', 'LOAD CSV', 'DELETE', 'DETACH', 'FILTER', 'FINISH', 'FOREACH', 'IN', 'INSERT', 'LET', 'LIMIT', 'MATCH', 'MERGE', 'NEXT', 'NODETACH', 'OFFSET', 'OPTIONAL', 'REMOVE', 'RETURN', 'SET', 'SKIP', 'UNION', 'UNWIND', 'USE', 'WITH' or <EOF> (line 12, column 1 (offset: 317))
"WHERE articleCount > 0"
 ^} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}

```cypher
CYPHER 25
MATCH (o:Organization)
WHERE NOT EXISTS { (o)<-[:HAS_SUBSIDIARY]-() }
CALL (o) {
  OPTIONAL MATCH (o)<-[:HAS_SUBSIDIARY]-(sub:Organization)
  RETURN count(sub) AS subsidiaryCount
}
CALL (o) {
  MATCH (o)<-[:MENTIONS]-(a:Article)
  RETURN count(a) AS articleCount, avg(a.sentiment) AS avgSentiment
... (5 more lines)
```


#### Gate 2 (5 case(s))

**`companies-intermediate-009`** — Using MERGE, create or match an Organization node with the literal name 'Nexus Corp' (do not use parameters). On CREATE set nbrEmployees=500. On MATCH set nbrEmployees=500. Return the node's name and elementId.

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.ClientError.Security.Forbidden} {message: Create node with labels 'Organization' on database 'companies' is not allowed for user 'companies' with roles [PUBLIC, companies].} {gql_status: 42NFF} {gql_status_description: error: syntax error or access rule violation - permission/access denied. Access denied, see the security logs for details.}

```cypher
CYPHER 25
MERGE (o:Organization {name: 'Nexus Corp'})
ON CREATE SET o.nbrEmployees = 500
ON MATCH SET o.nbrEmployees = 500
RETURN o.name, elementId(o)
```

**`companies-advanced-003`** — Find the shortest path (in hops) between 'Blackstone' and 'IBM' through HAS_SUBSIDIARY relationships (undirected). Use the SHORTEST keyword. Return the path length and the names of organizations along the path.

> **Gate 2 FAIL**: Execution error: Failed to DNS resolve address demo.neo4jlabs.com:7687: [Errno 8] nodename nor servname provided, or not known

```cypher
CYPHER 25
MATCH path = SHORTEST 1 (start:Organization {name: 'Blackstone'})-[:HAS_SUBSIDIARY]-+(end:Organization {name: 'IBM'})
RETURN length(path) AS pathLength,
       [n IN nodes(path) | n.name] AS organizationNames
```

**`companies-complex-001`** — Write a query that demonstrates CALL IN TRANSACTIONS syntax. Load the first 5 Organization nodes with a MATCH, then use CALL { ... } IN TRANSACTIONS OF 2 ROWS to collect the name of each organization in each batch. Inside the CALL subquery, use WITH to import the batch variable and RETURN org.name. Outside, count the total. Note: CALL IN TRANSACTIONS requires an implicit transaction (not is_write_query) and is validated for syntax correctness here.

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.DatabaseError.Transaction.TransactionStartFailed} {message: A query with 'CALL { ... } IN TRANSACTIONS' can only be executed in an implicit transaction, but tried to execute in an explicit transaction.} {gql_status: 25N17} {gql_status_description: error: invalid transaction state - implicit transaction required. The attempted operation requires an implicit transaction.}

```cypher
CYPHER 25
MATCH (org:Organization)
WITH org LIMIT 5
CALL (org) {
  RETURN org.name AS orgName
} IN TRANSACTIONS OF 2 ROWS
RETURN count(orgName) AS total
```

**`companies-complex-002`** — Build a multi-level aggregation query: first use CALL subqueries to compute per-organization metrics (article count, avg sentiment, subsidiary count), then aggregate at the category level (via HAS_CATEGORY) to return: category name, number of orgs, total articles, avg sentiment, and total subsidiaries. Limit to 10 categories.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (org:Organization)-[:HAS_CATEGORY]->(cat:Category)
CALL (org) {
  MATCH (org)<-[:MENTIONS]-(a:Article)
  RETURN count(a) AS articleCount, avg(a.sentiment) AS avgSentiment
}
CALL (org) {
  MATCH (org)-[:HAS_SUBSIDIARY]->(sub:Organization)
  RETURN count(sub) AS subsidiaryCount
}
... (17 more lines)
```

_Metrics_: elapsed=279 ms

**`companies-complex-003`** — Combine vector similarity search with graph traversal using db.index.vector.queryNodes: find the 10 Chunk nodes most similar to a vector of 1536 values of 0.1 (use a literal list in the query). For each chunk, traverse to its parent Article via HAS_CHUNK and then to all Organizations mentioned in that article via MENTIONS. Return chunk text, article title, and collected list of distinct mentioned organization names.

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.ClientError.Statement.TypeError} {message: Index query vector has a dimensionality of 881, but provided vector has 1536.} {gql_status: 52N37} {gql_status_description: error: procedure exception - procedure execution error. Execution of the procedure db.index.vector.queryNodes() failed.}

```cypher
CYPHER 25
CALL db.index.vector.queryNodes('news', 10, [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]) YIELD node AS chunk, score
MATCH (article:Article)-[:HAS_CHUNK]->(chunk)
OPTIONAL MATCH (article)-[:MENTIONS]->(org:Organization)
RETURN chunk.text AS chunkText,
       article.title AS articleTitle,
       collect(DISTINCT org.name) AS mentionedOrganizations
```


### WARN (1 cases)

#### Gate 4 (1 case(s))

**`companies-advanced-009`** — Find organizations linked to the same HAS_CATEGORY target node AND both mentioned in the same article. Traverse: (o1)-[:HAS_CATEGORY]->(cat)<-[:HAS_CATEGORY]-(o2) and (a)-[:MENTIONS]->(o1), (a)-[:MENTIONS]->(o2). Return category name, organization pair names, and co-mention count. Limit to 10.

> **Gate 4 WARN**: elapsedTimeMs 109783 ms exceeds warning threshold 30000 ms (CI timing guidance only)

```cypher
CYPHER 25
MATCH (o1:Organization)-[:HAS_CATEGORY]->(cat)<-[:HAS_CATEGORY]-(o2:Organization)
WHERE elementId(o1) < elementId(o2)
MATCH (a:Article)-[:MENTIONS]->(o1)
MATCH (a)-[:MENTIONS]->(o2)
RETURN cat.name AS category,
       o1.name AS org1,
       o2.name AS org2,
       count(a) AS coMentionCount
ORDER BY coMentionCount DESC
... (1 more lines)
```

_Metrics_: elapsed=109783 ms


---

_Report generated 2026-03-20T17:05:32Z by `tests/harness/reporter.py`_
