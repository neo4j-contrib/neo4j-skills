# Neo4j Cypher Authoring Skill — Harness Improvement Report

**Generated**: 2026-03-21T14:16:42Z  
**Input files**: 3  
  - `companies-run-20260321-150043.json`
  - `recommendations-run-20260321-150047.json`
  - `ucfraud-run-20260321-150418.json`

## 1. Overall Summary

| Metric | Count |
|--------|------:|
| Total cases (deduplicated) | 89 |
| PASS | 73 |
| WARN | 0 |
| FAIL | 16 |
| Overall pass rate | 82.0% |

## 2. Per-Difficulty Pass Rate vs PRD Targets

| Difficulty | Total | PASS | WARN | FAIL | Actual | Target | Delta |
|------------|------:|-----:|-----:|-----:|-------:|-------:|------:|
| Basic | 22 | 21 | 0 | 1 | 95.5% | 90% | +5.5% |
| Intermediate | 22 | 19 | 0 | 3 | 86.4% | 80% | +6.4% |
| Advanced | 22 | 18 | 0 | 4 | 81.8% | 70% | +11.8% |
| Complex | 13 | 10 | 0 | 3 | 76.9% | 60% | +16.9% |
| Expert | 10 | 5 | 0 | 5 | 50.0% | 60% | -10.0% |

## 3. Per-Gate Failure Breakdown

| Gate | Description | FAIL | WARN | Total Non-PASS |
|-----:|-------------|-----:|-----:|---------------:|
| 1 | Syntax (EXPLAIN) | 6 | 0 | 6 |
| 2 | Correctness (row count / execution) | 10 | 0 | 10 |

### Non-PASS Cases Detail

| ID | Difficulty | Verdict | Gate | Tags | Reason |
|----|------------|---------|-----:|------|--------|
| `companies-basic-010` | basic | FAIL | 1 | match, aggregation, case-when, sentiment | Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Inva |
| `companies-advanced-004` | advanced | FAIL | 1 | vector, index, similarity, procedure | Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Inva |
| `companies-advanced-009` | advanced | FAIL | 2 | match, multi-pattern, relationship, aggr | Query returned 0 rows, expected ≥ 1 |
| `companies-complex-001` | complex | FAIL | 1 | call-in-transactions, batch, read | Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Inva |
| `rec-advanced-006` | advanced | FAIL | 2 | fulltext, index, search, match | Execution error: {neo4j_code: Neo.ClientError.Procedure.ProcedureCallFailed} {me |
| `rec-expert-003` | expert | FAIL | 2 | vector, index, similarity, search | Execution error: {neo4j_code: Neo.ClientError.Procedure.ProcedureCallFailed} {me |
| `ucf-intermediate-003` | intermediate | FAIL | 2 | match, temporal, aggregation | Query returned 0 rows, expected ≥ 1 |
| `ucf-intermediate-004` | intermediate | FAIL | 2 | match, traversal, fraud, shared-identifi | Query returned 0 rows, expected ≥ 1 |
| `ucf-intermediate-005` | intermediate | FAIL | 2 | match, aggregation, filter, email | Query returned 0 rows, expected ≥ 1 |
| `ucf-advanced-001` | advanced | FAIL | 1 | qpe, fraud-ring, quantified-path | Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Inva |
| `ucf-complex-001` | complex | FAIL | 2 | fraud-ring, shared-identifiers, call-sub | Query returned 0 rows, expected ≥ 1 |
| `ucf-complex-002` | complex | FAIL | 2 | temporal, aggregation, fraud, with | Query returned 0 rows, expected ≥ 1 |
| `ucf-expert-002` | expert | FAIL | 1 | all-shortest, qpe, fraud-ring, paths | Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Inva |
| `ucf-expert-003` | expert | FAIL | 1 | qpe, money-laundering, traversal, deep-p | Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Inva |
| `ucf-expert-004` | expert | FAIL | 2 | call-in-transactions, batch, write, frau | Execution error: {neo4j_code: Neo.DatabaseError.Transaction.TransactionStartFail |
| `ucf-expert-005` | expert | FAIL | 2 | fulltext, qpe, fraud-ring, hybrid | Query returned 0 rows, expected ≥ 1 |

## 4. Failure Pattern Analysis

Each detected pattern is mapped to the most likely responsible SKILL.md section.

### Detected Patterns Summary

| # | Pattern | Cases | SKILL.md Section |
|---|---------|------:|-----------------|
| 1 | QPE syntax error (wrong quantifier form) | 10 | Core Pattern Cheat Sheet — Quantified Path Expressions |
| 2 | Subquery scope / importing variables | 7 | Core Pattern Cheat Sheet — CALL subqueries |
| 3 | Performance threshold exceeded (Gate 4 WARN/FAIL) | 5 | EXPLAIN / PROFILE Validation Loop |
| 4 | SEARCH clause used for fulltext (vector-only in Preview) | 4 | Core Pattern Cheat Sheet — SEARCH Clause |
| 5 | Vector index dimension mismatch | 3 | Schema-First Protocol |
| 6 | Unsafe MERGE / missing ON CREATE / ON MATCH | 3 | Core Pattern Cheat Sheet — MERGE Safety |
| 7 | CALL IN TRANSACTIONS inside explicit transaction | 2 | FOREACH vs UNWIND / Core Pattern Cheat Sheet |

### Pattern Details and Recommendations

#### Pattern 1: QPE syntax error (wrong quantifier form)

**SKILL.md Section**: `Core Pattern Cheat Sheet — Quantified Path Expressions`  
**Affected cases**: 10  

The QPE quantifier uses an unsupported form. Common errors: `+` instead of `{1,}` (demo DB limitation), spaces inside `{m,n}`, or mixing QPE with legacy `[:REL*]` syntax.

**Affected test cases**:

- `companies-basic-010` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input 'a': expec
- `companies-advanced-004` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '-': expec
- `companies-complex-001` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input 'IN': expe
- `rec-advanced-006` (FAIL): Execution error: {neo4j_code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to inv
- `rec-expert-003` (FAIL): Execution error: {neo4j_code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to inv
- `ucf-advanced-001` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '-': expec
- `ucf-expert-002` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '+': expec
- `ucf-expert-003` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '-': expec
- `ucf-expert-004` (FAIL): Execution error: {neo4j_code: Neo.DatabaseError.Transaction.TransactionStartFailed} {message: A quer
- `ucf-expert-005` (FAIL): Query returned 0 rows, expected ≥ 1

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

#### Pattern 2: Subquery scope / importing variables

**SKILL.md Section**: `Core Pattern Cheat Sheet — CALL subqueries`  
**Affected cases**: 7  

Variables are not correctly imported into a CALL subquery. In Cypher 25, use `CALL (x, y) { ... }` scope clause syntax. The deprecated `WITH x, y` as first clause inside CALL is no longer valid.

**Affected test cases**:

- `companies-basic-010` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input 'a': expec
- `companies-advanced-004` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '-': expec
- `companies-complex-001` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input 'IN': expe
- `rec-advanced-006` (FAIL): Execution error: {neo4j_code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to inv
- `rec-expert-003` (FAIL): Execution error: {neo4j_code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to inv
- `ucf-complex-001` (FAIL): Query returned 0 rows, expected ≥ 1
- `ucf-expert-004` (FAIL): Execution error: {neo4j_code: Neo.DatabaseError.Transaction.TransactionStartFailed} {message: A quer

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

#### Pattern 3: Performance threshold exceeded (Gate 4 WARN/FAIL)

**SKILL.md Section**: `EXPLAIN / PROFILE Validation Loop`  
**Affected cases**: 5  

The query exceeds the configured db-hits, memory, or elapsed-time threshold. Often caused by: full label scans instead of index seeks, Cartesian products from unlinked patterns, or collecting unbounded result sets.

**Affected test cases**:

- `companies-basic-010` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input 'a': expec
- `companies-advanced-009` (FAIL): Query returned 0 rows, expected ≥ 1
- `ucf-intermediate-003` (FAIL): Query returned 0 rows, expected ≥ 1
- `ucf-intermediate-005` (FAIL): Query returned 0 rows, expected ≥ 1
- `ucf-complex-002` (FAIL): Query returned 0 rows, expected ≥ 1

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

#### Pattern 4: SEARCH clause used for fulltext (vector-only in Preview)

**SKILL.md Section**: `Core Pattern Cheat Sheet — SEARCH Clause`  
**Affected cases**: 4  

The SEARCH clause is vector-only in Neo4j 2026.01 (Preview). For fulltext queries, the skill must use `db.index.fulltext.queryNodes()` or `db.index.fulltext.queryRelationships()`.

**Affected test cases**:

- `companies-advanced-004` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '-': expec
- `rec-advanced-006` (FAIL): Execution error: {neo4j_code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to inv
- `rec-expert-003` (FAIL): Execution error: {neo4j_code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to inv
- `ucf-expert-005` (FAIL): Query returned 0 rows, expected ≥ 1

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

#### Pattern 5: Vector index dimension mismatch

**SKILL.md Section**: `Schema-First Protocol`  
**Affected cases**: 3  

The query passes a vector of the wrong dimensionality to a vector index. The skill must inspect the index `OPTIONS` map for `vector.dimensions` before authoring vector queries.

**Affected test cases**:

- `companies-advanced-004` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '-': expec
- `rec-advanced-006` (FAIL): Execution error: {neo4j_code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to inv
- `rec-expert-003` (FAIL): Execution error: {neo4j_code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to inv

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

#### Pattern 6: Unsafe MERGE / missing ON CREATE / ON MATCH

**SKILL.md Section**: `Core Pattern Cheat Sheet — MERGE Safety`  
**Affected cases**: 3  

The MERGE clause is missing `ON CREATE SET` / `ON MATCH SET` sub-clauses, or MERGE is applied to a pattern that is too broad (e.g., MERGE on a relationship without both anchored nodes already bound).

**Affected test cases**:

- `companies-basic-010` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input 'a': expec
- `companies-advanced-004` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '-': expec
- `ucf-expert-004` (FAIL): Execution error: {neo4j_code: Neo.DatabaseError.Transaction.TransactionStartFailed} {message: A quer

**Before (problematic pattern)**:

```cypher
MERGE (o:Organization {name: $name})-[:HAS_CEO]->(p:Person {name: $ceo})
```

**After (recommended pattern)**:

```cypher
CYPHER 25
MERGE (o:Organization {name: $name})
ON CREATE SET o.createdAt = datetime()
MERGE (p:Person {name: $ceo})
MERGE (o)-[:HAS_CEO]->(p)
```

**Recommended SKILL.md edit**:

> Reinforce the MERGE Safety section: 'MERGE a relationship only after MERGE-ing (or MATCH-ing) both endpoint nodes separately. Always include ON CREATE SET / ON MATCH SET to set timestamps or counters.' Add a two-step MERGE pattern as the canonical example.

#### Pattern 7: CALL IN TRANSACTIONS inside explicit transaction

**SKILL.md Section**: `FOREACH vs UNWIND / Core Pattern Cheat Sheet`  
**Affected cases**: 2  

`CALL { ... } IN TRANSACTIONS` requires an *implicit* transaction. The harness wraps write queries in an explicit `BEGIN` transaction, which causes `TransactionStartFailed`. The query itself may be correct but cannot be tested this way.

**Affected test cases**:

- `companies-complex-001` (FAIL): Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input 'IN': expe
- `ucf-expert-004` (FAIL): Execution error: {neo4j_code: Neo.DatabaseError.Transaction.TransactionStartFailed} {message: A quer

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

## 5. Unclassified Failures

The following non-PASS cases did not match any known pattern. Manual review required.

**`ucf-intermediate-004`** (intermediate / FAIL)

> Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (a:Account)-[:SHARED_IDENTIFIERS]->(b:Account)
WHERE a.accountNumber < b.accountNumber
RETURN a.accountNumber AS account1, b.accountNumber AS account2
ORDER BY account1, account2
```

## 6. Tag Cluster Analysis

Frequency of tags appearing in non-PASS cases:

| Tag | Occurrences |
|-----|------------:|
| `match` | 6 |
| `aggregation` | 5 |
| `qpe` | 4 |
| `fraud-ring` | 4 |
| `index` | 3 |
| `fraud` | 3 |
| `vector` | 2 |
| `similarity` | 2 |
| `call-in-transactions` | 2 |
| `batch` | 2 |
| `fulltext` | 2 |
| `search` | 2 |
| `temporal` | 2 |
| `traversal` | 2 |
| `shared-identifiers` | 2 |
| `case-when` | 1 |
| `sentiment` | 1 |
| `procedure` | 1 |
| `multi-pattern` | 1 |
| `relationship` | 1 |
| `category` | 1 |
| `read` | 1 |
| `filter` | 1 |
| `email` | 1 |
| `quantified-path` | 1 |
| `call-subquery` | 1 |
| `with` | 1 |
| `all-shortest` | 1 |
| `paths` | 1 |
| `money-laundering` | 1 |
| `deep-path` | 1 |
| `write` | 1 |
| `fraud-flagging` | 1 |
| `hybrid` | 1 |

---

_This report was generated by `scripts/analyze-results.py` at 2026-03-21T14:16:42Z. It is for human review only — no automatic changes are made to SKILL.md._
