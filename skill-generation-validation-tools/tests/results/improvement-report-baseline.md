# Neo4j Cypher Authoring Skill — Harness Improvement Report

**Generated**: 2026-03-21T00:25:35Z  
**Input files**: 1  
  - `baseline-final.json`

## 1. Overall Summary

| Metric | Count |
|--------|------:|
| Total cases (deduplicated) | 35 |
| PASS | 32 |
| WARN | 1 |
| FAIL | 2 |
| Overall pass rate | 91.4% |

## 2. Per-Difficulty Pass Rate vs PRD Targets

| Difficulty | Total | PASS | WARN | FAIL | Actual | Target | Delta |
|------------|------:|-----:|-----:|-----:|-------:|-------:|------:|
| Basic | 10 | 10 | 0 | 0 | 100.0% | 90% | +10.0% |
| Intermediate | 10 | 10 | 0 | 0 | 100.0% | 80% | +20.0% |
| Advanced | 10 | 8 | 1 | 1 | 80.0% | 70% | +10.0% |
| Complex | 5 | 4 | 0 | 1 | 80.0% | 60% | +20.0% |

## 3. Per-Gate Failure Breakdown

| Gate | Description | FAIL | WARN | Total Non-PASS |
|-----:|-------------|-----:|-----:|---------------:|
| 2 | Correctness (row count / execution) | 2 | 0 | 2 |
| 4 | Performance (PROFILE thresholds) | 0 | 1 | 1 |

### Non-PASS Cases Detail

| ID | Difficulty | Verdict | Gate | Tags | Reason |
|----|------------|---------|-----:|------|--------|
| `companies-advanced-004` | advanced | FAIL | 2 | vector, index, similarity, procedure | Execution error: {neo4j_code: Neo.ClientError.Statement.TypeError} {message: Ind |
| `companies-advanced-009` | advanced | WARN | 4 | match, multi-pattern, relationship, aggr | elapsedTimeMs 109885 ms exceeds warning threshold 30000 ms (CI timing guidance o |
| `companies-complex-001` | complex | FAIL | 2 | call-in-transactions, batch, read | Execution error: {neo4j_code: Neo.DatabaseError.Transaction.TransactionStartFail |

## 4. Failure Pattern Analysis

Each detected pattern is mapped to the most likely responsible SKILL.md section.

### Detected Patterns Summary

| # | Pattern | Cases | SKILL.md Section |
|---|---------|------:|-----------------|
| 1 | QPE syntax error (wrong quantifier form) | 2 | Core Pattern Cheat Sheet — Quantified Path Expressions |
| 2 | Vector index dimension mismatch | 1 | Schema-First Protocol |
| 3 | CALL IN TRANSACTIONS inside explicit transaction | 1 | FOREACH vs UNWIND / Core Pattern Cheat Sheet |
| 4 | Subquery scope / importing variables | 1 | Core Pattern Cheat Sheet — CALL subqueries |
| 5 | Type casting error (toInteger vs toIntegerOrNull) | 1 | Types and Nulls (cypher25-types-and-nulls.md) |
| 6 | Performance threshold exceeded (Gate 4 WARN/FAIL) | 1 | EXPLAIN / PROFILE Validation Loop |
| 7 | SEARCH clause used for fulltext (vector-only in Preview) | 1 | Core Pattern Cheat Sheet — SEARCH Clause |

### Pattern Details and Recommendations

#### Pattern 1: QPE syntax error (wrong quantifier form)

**SKILL.md Section**: `Core Pattern Cheat Sheet — Quantified Path Expressions`  
**Affected cases**: 2  

The QPE quantifier uses an unsupported form. Common errors: `+` instead of `{1,}` (demo DB limitation), spaces inside `{m,n}`, or mixing QPE with legacy `[:REL*]` syntax.

**Affected test cases**:

- `companies-advanced-004` (FAIL): Execution error: {neo4j_code: Neo.ClientError.Statement.TypeError} {message: Index query vector has 
- `companies-complex-001` (FAIL): Execution error: {neo4j_code: Neo.DatabaseError.Transaction.TransactionStartFailed} {message: A quer

**Before (problematic pattern)**:

```cypher
MATCH (a)(()-[:HAS_SUBSIDIARY]->())+(b) RETURN b.name
```

**After (recommended pattern)**:

```cypher
CYPHER 25
MATCH (a)(()-[:HAS_SUBSIDIARY]->()){1,}(b) RETURN b.name
```

**Recommended SKILL.md edit**:

> Add a QPE compatibility note: 'Prefer `{1,}` over `+` and `{0,}` over `*` for maximum database compatibility. The `+` / `*` shorthands may not be enabled on all servers.' Update the QPE syntax table to show both forms with a compatibility column.

#### Pattern 2: Vector index dimension mismatch

**SKILL.md Section**: `Schema-First Protocol`  
**Affected cases**: 1  

The query passes a vector of the wrong dimensionality to a vector index. The skill must inspect the index `OPTIONS` map for `vector.dimensions` before authoring vector queries.

**Affected test cases**:

- `companies-advanced-004` (FAIL): Execution error: {neo4j_code: Neo.ClientError.Statement.TypeError} {message: Index query vector has 

**Before (problematic pattern)**:

```cypher
-- hard-codes 1536-dim vector without checking the index --
CALL db.index.vector.queryNodes('news', 5, $embedding)
```

**After (recommended pattern)**:

```cypher
-- Schema-First: inspect first --
SHOW VECTOR INDEXES YIELD name, options
-- Then use the correct dimension from options.vector.dimensions
```

**Recommended SKILL.md edit**:

> Add an explicit step to the Schema-First Protocol: 'For vector queries, run `SHOW VECTOR INDEXES YIELD name, options` and read `options.vector.dimensions` before calling the vector procedure. Never hard-code embedding dimensions.' Also add this as a note in the SEARCH Clause section.

#### Pattern 3: CALL IN TRANSACTIONS inside explicit transaction

**SKILL.md Section**: `FOREACH vs UNWIND / Core Pattern Cheat Sheet`  
**Affected cases**: 1  

`CALL { ... } IN TRANSACTIONS` requires an *implicit* transaction. The harness wraps write queries in an explicit `BEGIN` transaction, which causes `TransactionStartFailed`. The query itself may be correct but cannot be tested this way.

**Affected test cases**:

- `companies-complex-001` (FAIL): Execution error: {neo4j_code: Neo.DatabaseError.Transaction.TransactionStartFailed} {message: A quer

**Before (problematic pattern)**:

```cypher
-- Fails in explicit BEGIN/COMMIT block --
CALL { MATCH (n:Org) CALL { WITH n ... } IN TRANSACTIONS OF 100 ROWS }
```

**After (recommended pattern)**:

```cypher
-- Correct: only valid as top-level implicit transaction --
CYPHER 25
MATCH (n:Organization)
CALL { WITH n ... } IN TRANSACTIONS OF 100 ROWS
```

**Recommended SKILL.md edit**:

> Add a warning box to the CALL IN TRANSACTIONS reference file: 'This construct MUST be the outermost query (no wrapping BEGIN/COMMIT). Test harness marks these is_write_query=true; failures here are a harness limitation, not a skill deficiency.' Also ensure runner.py marks such failures with a note in gate_details.

#### Pattern 4: Subquery scope / importing variables

**SKILL.md Section**: `Core Pattern Cheat Sheet — CALL subqueries`  
**Affected cases**: 1  

Variables are not correctly imported into a CALL subquery. In Cypher 25, use `CALL (x, y) { ... }` scope clause syntax. The deprecated `WITH x, y` as first clause inside CALL is no longer valid.

**Affected test cases**:

- `companies-complex-001` (FAIL): Execution error: {neo4j_code: Neo.DatabaseError.Transaction.TransactionStartFailed} {message: A quer

**Before (problematic pattern)**:

```cypher
MATCH (n) CALL { WITH n MATCH (n)-[:HAS_SUBSIDIARY]->(s) RETURN s }
```

**After (recommended pattern)**:

```cypher
CYPHER 25
MATCH (n)
CALL (n) { MATCH (n)-[:HAS_SUBSIDIARY]->(s) RETURN s }
RETURN s.name
```

**Recommended SKILL.md edit**:

> Update the subqueries reference: replace all `CALL { WITH x ...}` examples with the `CALL (x) { ... }` scope clause form. Add a migration note: 'Importing WITH inside CALL is deprecated in Cypher 25.'

#### Pattern 5: Type casting error (toInteger vs toIntegerOrNull)

**SKILL.md Section**: `Types and Nulls (cypher25-types-and-nulls.md)`  
**Affected cases**: 1  

Base casting functions (`toInteger`, `toFloat`, etc.) throw on unconvertible input. Agent queries should use the `OrNull` variants (`toIntegerOrNull`, `toFloatOrNull`) to avoid runtime errors on dirty data.

**Affected test cases**:

- `companies-advanced-004` (FAIL): Execution error: {neo4j_code: Neo.ClientError.Statement.TypeError} {message: Index query vector has 

**Before (problematic pattern)**:

```cypher
RETURN toInteger(n.population) AS pop
```

**After (recommended pattern)**:

```cypher
RETURN toIntegerOrNull(n.population) AS pop
```

**Recommended SKILL.md edit**:

> Add to the types-and-nulls reference: 'Prefer `toFloatOrNull()`, `toIntegerOrNull()` over base variants in agent queries — they return null instead of throwing on unconvertible input.' Bold this preference in the SKILL.md types section.

#### Pattern 6: Performance threshold exceeded (Gate 4 WARN/FAIL)

**SKILL.md Section**: `EXPLAIN / PROFILE Validation Loop`  
**Affected cases**: 1  

The query exceeds the configured db-hits, memory, or elapsed-time threshold. Often caused by: full label scans instead of index seeks, Cartesian products from unlinked patterns, or collecting unbounded result sets.

**Affected test cases**:

- `companies-advanced-009` (WARN): elapsedTimeMs 109885 ms exceeds warning threshold 30000 ms (CI timing guidance only)

**Before (problematic pattern)**:

```cypher
-- Full label scan + Cartesian product --
MATCH (a:Organization), (b:Organization)
WHERE a.name CONTAINS 'Inc' RETURN count(*)
```

**After (recommended pattern)**:

```cypher
CYPHER 25
-- Use index-backed predicate --
MATCH (a:Organization)
WHERE a.name CONTAINS 'Inc'
RETURN count(*)
```

**Recommended SKILL.md edit**:

> In the EXPLAIN/PROFILE Validation Loop section, add: 'When PROFILE shows high dbHits, check for: (1) missing index hints, (2) Cartesian products (look for `CartesianProduct` in the plan), (3) unbounded traversals without LIMIT.' Link to the indexes L3 reference for hint syntax.

#### Pattern 7: SEARCH clause used for fulltext (vector-only in Preview)

**SKILL.md Section**: `Core Pattern Cheat Sheet — SEARCH Clause`  
**Affected cases**: 1  

The SEARCH clause is vector-only in Neo4j 2026.01 (Preview). For fulltext queries, the skill must use `db.index.fulltext.queryNodes()` or `db.index.fulltext.queryRelationships()`.

**Affected test cases**:

- `companies-advanced-004` (FAIL): Execution error: {neo4j_code: Neo.ClientError.Statement.TypeError} {message: Index query vector has 

**Before (problematic pattern)**:

```cypher
CYPHER 25
SEARCH (n:Article USING fulltext) WHERE n.text CONTAINS 'graph'
```

**After (recommended pattern)**:

```cypher
CYPHER 25
CALL db.index.fulltext.queryNodes('entity', 'graph') YIELD node, score
RETURN node.name, score
```

**Recommended SKILL.md edit**:

> Add a clear callout to the SEARCH Clause section: 'The SEARCH clause is **vector-only** (Preview). For fulltext indexes, always use the `db.index.fulltext.queryNodes()` procedure.' Put this note on the first line of the section.

## 6. Tag Cluster Analysis

Frequency of tags appearing in non-PASS cases:

| Tag | Occurrences |
|-----|------------:|
| `vector` | 1 |
| `index` | 1 |
| `similarity` | 1 |
| `procedure` | 1 |
| `match` | 1 |
| `multi-pattern` | 1 |
| `relationship` | 1 |
| `aggregation` | 1 |
| `category` | 1 |
| `call-in-transactions` | 1 |
| `batch` | 1 |
| `read` | 1 |

---

_This report was generated by `scripts/analyze-results.py` at 2026-03-21T00:25:35Z. It is for human review only — no automatic changes are made to SKILL.md._
