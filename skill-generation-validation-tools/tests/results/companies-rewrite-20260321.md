# Cypher Skill Test Report — `run-20260321T104141`

**Skill**: `neo4j-cypher-authoring-skill`  
**Started**: 2026-03-21 10:41:41 UTC  
**Completed**: 2026-03-21 10:45:33 UTC  

## Overall Results

| Metric | Value |
|--------|-------|
| Total cases | 35 |
| PASS | 26 |
| WARN | 0 |
| FAIL | 9 |
| Pass rate | 74.3% |

## Per-Difficulty Pass Rates

| Difficulty | Total | PASS | WARN | FAIL | Pass Rate |
|------------|------:|-----:|-----:|-----:|----------:|
| Basic | 10 | 8 | 0 | 2 | 80.0% |
| Intermediate | 10 | 9 | 0 | 1 | 90.0% |
| Advanced | 10 | 7 | 0 | 3 | 70.0% |
| Complex | 5 | 2 | 0 | 3 | 40.0% |

## DB-Hits Summary (per Difficulty)

Only cases that completed Gate 4 (PROFILE) are included.

| Difficulty | n | Min | Median | Max |
|------------|--:|----:|-------:|----:|
| — | — | — | — | — |

## Test Case Results

| ID | Difficulty | Verdict | Gate | DB Hits | Duration (s) | Question |
|----|------------|---------|-----:|--------:|-------------:|----------|
| `companies-basic-001` | basic | PASS | — | — | 12.0 | Which companies in our database are independent — not owned… |
| `companies-basic-002` | basic | PASS | — | — | 3.8 | How many companies are tracked in our database? |
| `companies-basic-003` | basic | **FAIL** | 2 | — | 4.1 | List the first 10 companies in alphabetical order. |
| `companies-basic-004` | basic | PASS | — | — | 6.6 | What are the most positively covered news articles mentioni… |
| `companies-basic-005` | basic | PASS | — | — | 5.4 | Which companies get the most press coverage? Rank the top 1… |
| `companies-basic-006` | basic | **FAIL** | 2 | — | 4.6 | Which companies does Blackstone directly own? List up to 10… |
| `companies-basic-007` | basic | PASS | — | — | 3.8 | What is the average news sentiment score across all article… |
| `companies-basic-008` | basic | PASS | — | — | 5.0 | Which 5 companies are mentioned most frequently in the news… |
| `companies-basic-009` | basic | PASS | — | — | 3.9 | Show me the most positive news articles in our database — a… |
| `companies-basic-010` | basic | PASS | — | — | 5.8 | How many news articles in our database are positive, neutra… |
| `companies-intermediate-001` | intermediate | PASS | — | — | 8.5 | Which companies are attracting the most negative press cove… |
| `companies-intermediate-002` | intermediate | PASS | — | — | 8.2 | Which pairs of companies are most frequently mentioned toge… |
| `companies-intermediate-003` | intermediate | PASS | — | — | 5.6 | Among companies that are not subsidiaries of any other firm… |
| `companies-intermediate-004` | intermediate | PASS | — | — | 7.2 | Search for companies with 'tech' in their name. What do the… |
| `companies-intermediate-005` | intermediate | PASS | — | — | 5.6 | What companies does Blackstone own, including those owned t… |
| `companies-intermediate-006` | intermediate | PASS | — | — | 8.0 | For the 5 most-covered companies in the news, what was the … |
| `companies-intermediate-007` | intermediate | PASS | — | — | 4.6 | How many news article segments are linked to articles that … |
| `companies-intermediate-008` | intermediate | PASS | — | — | 4.8 | Which companies both have subsidiary businesses and appear … |
| `companies-intermediate-009` | intermediate | **FAIL** | 2 | — | 4.1 | Which companies have a supplier relationship with another c… |
| `companies-intermediate-010` | intermediate | PASS | — | — | 4.0 | Which company has the most direct subsidiaries? Return its … |
| `companies-advanced-001` | advanced | PASS | — | — | 4.7 | What companies are within Blackstone's ownership structure … |
| `companies-advanced-002` | advanced | **FAIL** | 1 | — | 4.2 | How large is Blackstone's full corporate family — counting … |
| `companies-advanced-003` | advanced | PASS | — | — | 7.5 | Which 5 companies have the most total connections in our da… |
| `companies-advanced-004` | advanced | **FAIL** | 2 | — | 6.1 | Find the 5 news article segments most semantically relevant… |
| `companies-advanced-005` | advanced | PASS | — | — | 5.6 | Search for companies named 'Amazon' and show all the news a… |
| `companies-advanced-006` | advanced | PASS | — | — | 6.3 | For the 20 most-covered companies in our news database, sho… |
| `companies-advanced-007` | advanced | PASS | — | — | 20.3 | Which company pairs appear in both positive and negative ne… |
| `companies-advanced-008` | advanced | PASS | — | — | 5.2 | Which companies are talked about in the news more often tha… |
| `companies-advanced-009` | advanced | **FAIL** | 2 | — | 9.3 | Which pairs of companies in the same industry category are … |
| `companies-advanced-010` | advanced | PASS | — | — | 5.0 | For companies that have at least one subsidiary, list each … |
| `companies-complex-001` | complex | **FAIL** | 2 | — | 4.9 | For 20 companies in our database, how many news articles me… |
| `companies-complex-002` | complex | **FAIL** | 1 | — | 8.2 | By industry category, give me a comprehensive picture: how … |
| `companies-complex-003` | complex | **FAIL** | 2 | — | 13.0 | Search for Microsoft in our company database. For each matc… |
| `companies-complex-004` | complex | PASS | — | — | 10.2 | For companies with at least 5 subsidiaries, show the most p… |
| `companies-complex-005` | complex | PASS | — | — | 5.8 | Classify every company into one of four groups: those with … |

## Failure Analysis

### FAIL (9 cases)

#### Gate 1 (2 case(s))

**`companies-advanced-002`** — How large is Blackstone's full corporate family — counting every company it owns at any depth of the ownership chain?

> **Gate 1 FAIL**: Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '+': expected '-' (line 3, column 37 (offset: 100))
"MATCH (blackstone)-[:HAS_SUBSIDIARY]+->(subsidiary:Organization)"
                                     ^} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}

```cypher
CYPHER 25
MATCH (blackstone:Organization {name: $name})
MATCH (blackstone)-[:HAS_SUBSIDIARY]+->(subsidiary:Organization)
RETURN count(DISTINCT subsidiary) AS familySize
```

**`companies-complex-002`** — By industry category, give me a comprehensive picture: how many companies are in each category, how many news articles mention them in total, what is the average sentiment of that coverage, and how many subsidiaries exist across the group? Show the top 10 categories by total article count.

> **Gate 1 FAIL**: Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Variable `companies` not defined (line 7, column 8 (offset: 209))
"UNWIND companies AS c"
        ^} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}

```cypher
CYPHER 25
MATCH (cat:Category)<-[:IN_CATEGORY]-(c:Company)
WITH cat, collect(c) AS companies
WITH cat,
     size(companies) AS companyCount,
     [co IN companies | elementId(co)] AS companyIds
UNWIND companies AS c
OPTIONAL MATCH (c)<-[:MENTIONS]-(a:Article)
OPTIONAL MATCH (c)<-[:HAS_SUBSIDIARY]-(sub:Company)
WITH cat, companyCount,
... (10 more lines)
```


#### Gate 2 (7 case(s))

**`companies-basic-003`** — List the first 10 companies in alphabetical order.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 10

```cypher
CYPHER 25
MATCH (c:Company)
RETURN c.name AS name
ORDER BY name ASC
LIMIT 10
```

_Metrics_: elapsed=290 ms

**`companies-basic-006`** — Which companies does Blackstone directly own? List up to 10 of its subsidiaries.

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.ClientError.Statement.ParameterMissing} {message: Expected parameter(s): name} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}

```cypher
CYPHER 25
MATCH (parent:Organization {name: $name})-[:HAS_SUBSIDIARY]->(subsidiary:Organization)
RETURN subsidiary.name AS subsidiaryName
LIMIT 10
```

**`companies-intermediate-009`** — Which companies have a supplier relationship with another company AND also appear in news coverage? Show the company, its supplier, and how many articles mention it. Return the top 10 by coverage.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (c:Company)-[:SUPPLIES]->(other:Company)
MATCH (c)<-[:MENTIONS]-(a:Article)
WITH c, other, count(DISTINCT a) AS articleCount
RETURN c.name AS company, other.name AS supplier, articleCount
ORDER BY articleCount DESC
LIMIT 10
```

_Metrics_: elapsed=290 ms

**`companies-advanced-004`** — Find the 5 news article segments most semantically relevant to a general business query. Return the segment text and how closely it matches.

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.ClientError.Statement.ParameterMissing} {message: Expected parameter(s): embedding} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}

```cypher
CYPHER 25
CALL db.index.vector.queryNodes('news', 5, $embedding)
YIELD node AS chunk, score
RETURN chunk.text AS segment_text, score
ORDER BY score DESC
```

**`companies-advanced-009`** — Which pairs of companies in the same industry category are also covered together in the same news articles? Show the category, the company pair, and how often they appear together.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (cat:Category)<-[:IN_CATEGORY]-(c1:Organization)<-[:MENTIONS]-(a:Article)-[:MENTIONS]->(c2:Organization)-[:IN_CATEGORY]->(cat)
WHERE c1 <> c2
  AND NOT EXISTS { (c1)<-[:HAS_SUBSIDIARY]-() }
  AND NOT EXISTS { (c2)<-[:HAS_SUBSIDIARY]-() }
  AND elementId(c1) < elementId(c2)
RETURN cat.name AS category,
       c1.name AS company1,
       c2.name AS company2,
       count(DISTINCT a) AS co_appearances
... (2 more lines)
```

_Metrics_: elapsed=275 ms

**`companies-complex-001`** — For 20 companies in our database, how many news articles mention each of them? Process the results in small batches.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (c:Company)
WITH c LIMIT 20
CALL (c) {
  MATCH (a:Article)-[:MENTIONS]->(c)
  RETURN count(a) AS articleCount
}
RETURN c.name AS company, articleCount
ORDER BY articleCount DESC
```

_Metrics_: elapsed=256 ms

**`companies-complex-003`** — Search for Microsoft in our company database. For each match, show its industry category, the top 3 news headlines about it, how many news articles mention it, and how many subsidiaries it has.

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.ClientError.Statement.ParameterMissing} {message: Expected parameter(s): searchTerm} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}

```cypher
CYPHER 25
CALL db.index.fulltext.queryNodes('entity', $searchTerm) YIELD node AS org, score
WHERE org:Organization
WITH org, score
ORDER BY score DESC
CALL (org) {
  OPTIONAL MATCH (org)-[:IN_CATEGORY]->(cat:IndustryCategory)
  RETURN collect(DISTINCT cat.name) AS industries
}
CALL (org) {
... (19 more lines)
```


---

_Report generated 2026-03-21T10:45:41Z by `tests/harness/reporter.py`_
