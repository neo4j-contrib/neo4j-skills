# Cypher Skill Test Report — `run-20260321T120914`

**Skill**: `neo4j-cypher-authoring-skill`  
**Started**: 2026-03-21 12:09:14 UTC  
**Completed**: 2026-03-21 12:12:30 UTC  

## Overall Results

| Metric | Value |
|--------|-------|
| Total cases | 27 |
| PASS | 13 |
| WARN | 0 |
| FAIL | 14 |
| Pass rate | 48.1% |

## Per-Difficulty Pass Rates

| Difficulty | Total | PASS | WARN | FAIL | Pass Rate |
|------------|------:|-----:|-----:|-----:|----------:|
| Basic | 6 | 4 | 0 | 2 | 66.7% |
| Intermediate | 6 | 4 | 0 | 2 | 66.7% |
| Advanced | 6 | 2 | 0 | 4 | 33.3% |
| Complex | 4 | 2 | 0 | 2 | 50.0% |
| Expert | 5 | 1 | 0 | 4 | 20.0% |

## DB-Hits Summary (per Difficulty)

Only cases that completed Gate 4 (PROFILE) are included.

| Difficulty | n | Min | Median | Max |
|------------|--:|----:|-------:|----:|
| — | — | — | — | — |

## Test Case Results

| ID | Difficulty | Verdict | Gate | DB Hits | Duration (s) | Question |
|----|------------|---------|-----:|--------:|-------------:|----------|
| `rec-basic-001` | basic | PASS | — | — | 6.2 | Show me a sample of movies in our catalogue — just give me … |
| `rec-basic-002` | basic | PASS | — | — | 3.5 | How many movies are in our catalogue in total? |
| `rec-basic-003` | basic | **FAIL** | 2 | — | 4.0 | What are the 10 most recently released movies in our catalo… |
| `rec-basic-004` | basic | PASS | — | — | 3.6 | What genres are available in our movie catalogue? |
| `rec-basic-005` | basic | **FAIL** | 2 | — | 4.6 | Who were the actors in The Matrix? |
| `rec-basic-006` | basic | PASS | — | — | 4.2 | How many movie ratings have been submitted by users in tota… |
| `rec-intermediate-001` | intermediate | PASS | — | — | 8.2 | What are the top 10 highest-rated movies, among those that … |
| `rec-intermediate-002` | intermediate | PASS | — | — | 3.9 | Which genres have more than 20 movies? Show the genre name … |
| `rec-intermediate-003` | intermediate | **FAIL** | 2 | — | 3.7 | What movies has Tom Hanks appeared in? Show titles and rele… |
| `rec-intermediate-004` | intermediate | PASS | — | — | 5.1 | Which users have been the most active reviewers — rating mo… |
| `rec-intermediate-005` | intermediate | PASS | — | — | 11.1 | Which genres tend to receive the highest IMDb ratings on av… |
| `rec-intermediate-006` | intermediate | **FAIL** | 2 | — | 10.8 | Which directors have the most films in our catalogue? Show … |
| `rec-advanced-001` | advanced | **FAIL** | 2 | — | 8.1 | For active users who have rated at least 3 movies, which fi… |
| `rec-advanced-002` | advanced | PASS | — | — | 12.2 | Show all movies alongside their average user rating. Movies… |
| `rec-advanced-003` | advanced | **FAIL** | 2 | — | 6.8 | What movies would you recommend to User 1 based on what sim… |
| `rec-advanced-004` | advanced | PASS | — | — | 8.2 | For each genre, what are the five best-reviewed movies base… |
| `rec-advanced-005` | advanced | **FAIL** | 2 | — | 5.5 | Which actors have worked with cast members from The Matrix,… |
| `rec-advanced-006` | advanced | **FAIL** | 2 | — | 5.0 | Search for movies with 'star wars' in the title. What are t… |
| `rec-complex-001` | complex | **FAIL** | 2 | — | 9.7 | What are the top 5 movies I should recommend to User 534? B… |
| `rec-complex-002` | complex | PASS | — | — | 4.8 | Which people in our database have both acted in and directe… |
| `rec-complex-003` | complex | **FAIL** | 1 | — | 6.7 | Which genres have the most consistent audience ratings — me… |
| `rec-complex-004` | complex | PASS | — | — | 8.3 | For the 10 most-rated movies in our catalogue, what genres … |
| `rec-expert-001` | expert | **FAIL** | 2 | — | 9.4 | What is the shortest connection between Tom Hanks and Kevin… |
| `rec-expert-002` | expert | **FAIL** | 2 | — | 4.9 | Starting from The Matrix, what other movies can you reach b… |
| `rec-expert-003` | expert | **FAIL** | 2 | — | 8.6 | Which 5 movies in our catalogue have the most similar story… |
| `rec-expert-004` | expert | **FAIL** | 2 | — | 15.0 | What are the top 10 movies to recommend to User 1, factorin… |
| `rec-expert-005` | expert | PASS | — | — | 13.6 | Which users have the broadest influence in our community — … |

## Failure Analysis

### FAIL (14 cases)

#### Gate 1 (1 case(s))

**`rec-complex-003`** — Which genres have the most consistent audience ratings — meaning the least variation between reviewers? Only include genres with at least 50 ratings, and rank from most to least consistent.

> **Gate 1 FAIL**: Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Type mismatch: expected Float but was List<Boolean>, List<Float>, List<Integer>, List<Number>, List<Point>, List<String>, List<Duration>, List<Date>, List<Time>, List<LocalTime>, List<LocalDateTime>, List<DateTime>, List<Vector>, List<List<Boolean>>, List<List<Float>>, List<List<Integer>>, List<List<Number>>, List<List<Point>>, List<List<String>>, List<List<Duration>>, List<List<Date>>, List<List<Time>>, List<List<LocalTime>>, List<List<LocalDateTime>> or List<List<DateTime>> (line 5, column 19 (offset: 171))
"WITH genre, stDev([x IN ratings | x]) AS ratingStdDev, size(ratings) AS ratingCount"
                   ^} {gql_status: 22G03} {gql_status_description: error: data exception - invalid value type}

```cypher
CYPHER 25
MATCH (g:Genre)<-[:IN_GENRE]-(m:Movie)<-[r:RATED]-(:User)
WITH g.name AS genre, collect(r.rating) AS ratings
WHERE size(ratings) >= 50
WITH genre, stDev([x IN ratings | x]) AS ratingStdDev, size(ratings) AS ratingCount
RETURN genre, ratingStdDev, ratingCount
ORDER BY ratingStdDev ASC
```


#### Gate 2 (13 case(s))

**`rec-basic-003`** — What are the 10 most recently released movies in our catalogue from after the year 2000?

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 10

```cypher
CYPHER 25
MATCH (m:Movie)
WHERE m.released > 2000
RETURN m.title, m.released
ORDER BY m.released DESC
LIMIT 10
```

_Metrics_: elapsed=282 ms

**`rec-basic-005`** — Who were the actors in The Matrix?

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (p:Person)-[:ACTED_IN]->(m:Movie {title: 'The Matrix'})
RETURN p.name AS actor
```

_Metrics_: elapsed=294 ms

**`rec-intermediate-003`** — What movies has Tom Hanks appeared in? Show titles and release years, most recent first.

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.ClientError.Statement.ParameterMissing} {message: Expected parameter(s): name} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}

```cypher
CYPHER 25
MATCH (p:Person {name: $name})-[:ACTED_IN]->(m:Movie)
RETURN m.title AS title, m.released AS released
ORDER BY m.released DESC
```

**`rec-intermediate-006`** — Which directors have the most films in our catalogue? Show directors with more than 3 films and how many they've directed.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (d:Director)-[:DIRECTED]->(f:Film)
WITH d, count(f) AS filmCount
WHERE filmCount > 3
RETURN d.name AS director, filmCount
ORDER BY filmCount DESC
```

_Metrics_: elapsed=252 ms

**`rec-advanced-001`** — For active users who have rated at least 3 movies, which films did they give a perfect 5-star rating to? Show each user alongside their personal list of top-rated movies.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (u:User)-[r:RATED]->(m:Movie)
WHERE u.active = true
WITH u, count(r) AS totalRatings, collect(CASE WHEN r.rating = 5 THEN m.title ELSE null END) AS allTopMovies
WHERE totalRatings >= 3
WITH u, [x IN allTopMovies WHERE x IS NOT NULL] AS topRatedMovies
WHERE size(topRatedMovies) > 0
RETURN u.name AS user, topRatedMovies
ORDER BY u.name
```

_Metrics_: elapsed=268 ms

**`rec-advanced-003`** — What movies would you recommend to User 1 based on what similar users enjoyed? Suggest films that User 1 hasn't seen yet but were highly rated by people with overlapping tastes. Show the top 10.

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.ClientError.Statement.ParameterMissing} {message: Expected parameter(s): userId} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}

```cypher
CYPHER 25
MATCH (u1:User {id: $userId})-[r1:RATED]->(m:Movie)<-[r2:RATED]-(similar:User)
WHERE r1.rating >= 3.5 AND r2.rating >= 3.5 AND similar <> u1
WITH u1, similar, count(m) AS overlap
WHERE overlap >= 2
MATCH (similar)-[r3:RATED]->(rec:Movie)
WHERE r3.rating >= 4.0
  AND NOT EXISTS { (u1)-[:RATED]->(rec) }
WITH rec, count(DISTINCT similar) AS recommenders, avg(r3.rating) AS avgRating
RETURN rec.title AS movie,
... (4 more lines)
```

**`rec-advanced-005`** — Which actors have worked with cast members from The Matrix, but never appeared in The Matrix themselves? Show their names.

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.ClientError.Statement.ParameterMissing} {message: Expected parameter(s): title} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}

```cypher
CYPHER 25
MATCH (matrix:Movie {title: $title})<-[:ACTED_IN]-(matrixActor:Person)
MATCH (matrixActor)<-[:ACTED_IN]-(sharedMovie:Movie)<-[:ACTED_IN]-(actor:Person)
WHERE NOT EXISTS { MATCH (actor)-[:ACTED_IN]->(matrix) }
  AND actor <> matrixActor
RETURN DISTINCT actor.name AS name
```

**`rec-advanced-006`** — Search for movies with 'star wars' in the title. What are their release years and IMDb ratings?

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to invoke procedure `db.index.fulltext.queryNodes`: Caused by: java.lang.IllegalArgumentException: There is no such fulltext schema index: movieTitles} {gql_status: 52N37} {gql_status_description: error: procedure exception - procedure execution error. Execution of the procedure db.index.fulltext.queryNodes() failed.}

```cypher
CYPHER 25
CALL db.index.fulltext.queryNodes('movieTitles', 'star wars') YIELD node AS movie, score
RETURN movie.title AS title,
       movie.released AS releaseYear,
       movie.imdbRating AS imdbRating
ORDER BY releaseYear ASC;
```

**`rec-complex-001`** — What are the top 5 movies I should recommend to User 534? Base it on what users with similar viewing histories rated highly, excluding anything User 534 has already seen.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (target:User {id: 534})-[:RATED]->(seen:Movie)
WITH target, collect(seen) AS seenMovies

MATCH (target)-[:RATED]->(common:Movie)<-[:RATED]-(similar:User)
WHERE similar <> target
WITH target, seenMovies, similar, count(common) AS sharedMovies
ORDER BY sharedMovies DESC
LIMIT 50

... (11 more lines)
```

_Metrics_: elapsed=282 ms

**`rec-expert-001`** — What is the shortest connection between Tom Hanks and Kevin Bacon through shared movie appearances? List the films on the path.

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.ClientError.Statement.ParameterMissing} {message: Expected parameter(s): tom, kevin} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}

```cypher
CYPHER 25
MATCH path = SHORTEST 1 (tom:Person {name: $tom})(()-[:ACTED_IN]->(:Movie)<-[:ACTED_IN]-())+(kevin:Person {name: $kevin})
RETURN [n IN nodes(path) WHERE n:Movie | n.title] AS films
```

**`rec-expert-002`** — Starting from The Matrix, what other movies can you reach by following chains of shared cast members — up to three films away? Show all the reachable titles.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (start:Movie {title: 'The Matrix'})
MATCH (start)(()-[:IN_GENRE|ACTED_IN]-()-[:ACTED_IN|IN_GENRE]->()){1,3}(other:Movie)
WHERE other <> start
RETURN DISTINCT other.title AS reachableMovie
ORDER BY reachableMovie
```

_Metrics_: elapsed=263 ms

**`rec-expert-003`** — Which 5 movies in our catalogue have the most similar storylines to The Matrix, based on their plot descriptions?

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (m:Movie {title: 'The Matrix'})
CALL db.index.vector.queryNodes('moviePlots', 6, m.plotEmbedding)
YIELD node AS similar, score
WHERE similar <> m
RETURN similar.title AS title, score
ORDER BY score DESC
LIMIT 5
```

_Metrics_: elapsed=281 ms

**`rec-expert-004`** — What are the top 10 movies to recommend to User 1, factoring in both what similar users enjoyed and whether the movie's genres match their viewing history? Weight peer ratings more heavily than genre overlap.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (targetUser:User {userId: 1})-[r1:RATED]->(m1:Movie)
WITH targetUser, collect(m1) AS watchedMovies, avg(r1.rating) AS avgRating

// Find similar users who rated the same movies highly
MATCH (targetUser)-[r2:RATED]->(commonMovie:Movie)<-[r3:RATED]-(similarUser:User)
WHERE similarUser <> targetUser AND r2.rating >= 3.5 AND r3.rating >= 3.5
WITH targetUser, watchedMovies, similarUser, count(commonMovie) AS commonCount

// Find movies that similar users enjoyed but target user hasn't seen
... (25 more lines)
```

_Metrics_: elapsed=312 ms


---

_Report generated 2026-03-21T12:12:34Z by `tests/harness/reporter.py`_
