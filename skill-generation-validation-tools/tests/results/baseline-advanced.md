# Cypher Skill Test Report — `run-20260320T162017`

**Skill**: `neo4j-cypher-authoring-skill`  
**Started**: 2026-03-20 16:20:17 UTC  
**Completed**: 2026-03-20 16:28:09 UTC  

## Overall Results

| Metric | Value |
|--------|-------|
| Total cases | 10 |
| PASS | 8 |
| WARN | 1 |
| FAIL | 1 |
| Pass rate | 80.0% |

## Per-Difficulty Pass Rates

| Difficulty | Total | PASS | WARN | FAIL | Pass Rate |
|------------|------:|-----:|-----:|-----:|----------:|
| Advanced | 10 | 8 | 1 | 1 | 80.0% |

## DB-Hits Summary (per Difficulty)

Only cases that completed Gate 4 (PROFILE) are included.

| Difficulty | n | Min | Median | Max |
|------------|--:|----:|-------:|----:|
| — | — | — | — | — |

## Test Case Results

| ID | Difficulty | Verdict | Gate | DB Hits | Duration (s) | Question |
|----|------------|---------|-----:|--------:|-------------:|----------|
| `companies-advanced-001` | advanced | PASS | — | — | 7.0 | Using a quantified path expression with the {1,2} quantifie… |
| `companies-advanced-002` | advanced | PASS | — | — | 8.4 | Using a quantified path expression with the {1,} quantifier… |
| `companies-advanced-003` | advanced | PASS | — | — | 4.8 | Find the top 5 organizations with the most total connection… |
| `companies-advanced-004` | advanced | **FAIL** | — | — | 90.0 | Use the db.index.vector.queryNodes procedure to perform a v… |
| `companies-advanced-005` | advanced | PASS | — | — | 10.7 | Use the db.index.fulltext.queryNodes procedure to search th… |
| `companies-advanced-006` | advanced | PASS | — | — | 10.3 | Use a CALL subquery to compute per-organization metrics for… |
| `companies-advanced-007` | advanced | PASS | — | — | 106.1 | Find organizations that appear together in articles with bo… |
| `companies-advanced-008` | advanced | PASS | — | — | 6.3 | Use COUNT subquery expressions to find organizations where … |
| `companies-advanced-009` | advanced | WARN | 4 | — | 222.0 | Find organizations linked to the same HAS_CATEGORY target n… |
| `companies-advanced-010` | advanced | PASS | — | — | 6.3 | Using COLLECT subquery expressions, for each organization r… |

## Failure Analysis

### FAIL (1 cases)

#### No gate (runner error) (1 case(s))

**`companies-advanced-004`** — Use the db.index.vector.queryNodes procedure to perform a vector similarity search on the 'news' vector index. Find the 5 Chunk nodes most similar to a random query vector (use a list of 1536 identical values of 0.1 as the query vector, passed as a literal list in the query). Return the chunk text and the similarity score.

> **Runner error**: Claude invocation failed: Claude invocation timed out after 90s


### WARN (1 cases)

#### Gate 4 (1 case(s))

**`companies-advanced-009`** — Find organizations linked to the same HAS_CATEGORY target node AND both mentioned in the same article. Traverse: (o1)-[:HAS_CATEGORY]->(cat)<-[:HAS_CATEGORY]-(o2) and (a)-[:MENTIONS]->(o1), (a)-[:MENTIONS]->(o2). Return category name, organization pair names, and co-mention count. Limit to 10.

> **Gate 4 WARN**: elapsedTimeMs 112479 ms exceeds warning threshold 30000 ms (CI timing guidance only)

```cypher
CYPHER 25
MATCH (o1:Organization)-[:HAS_CATEGORY]->(cat)<-[:HAS_CATEGORY]-(o2:Organization)
WHERE elementId(o1) < elementId(o2)
MATCH (a:Article)-[:MENTIONS]->(o1)
MATCH (a)-[:MENTIONS]->(o2)
WITH cat.name AS category, o1.name AS org1, o2.name AS org2, count(DISTINCT a) AS coMentionCount
RETURN category, org1, org2, coMentionCount
ORDER BY coMentionCount DESC
LIMIT 10
```

_Metrics_: elapsed=112479 ms


---

_Report generated 2026-03-20T23:53:06Z by `tests/harness/reporter.py`_
