# Cypher 25 — Runtime Hints (`CYPHER runtime=...`)

> Source: Neo4j 2026.x Cypher Manual — Runtime Hints
> Applies to: All editions of Neo4j 2025.06+; Cypher 25

---

## Syntax

```cypher
CYPHER 25 CYPHER runtime=parallel
MATCH (n:Organization)-[:MENTIONS]->(a:Article)
RETURN n.name, count(a) AS articleCount
ORDER BY articleCount DESC
LIMIT 10
```

`CYPHER runtime=<hint>` is placed after the `CYPHER 25` pragma on the same or the next line. Both pragmas must appear before the first query clause.

Valid values:

| Hint | Effect |
|---|---|
| `CYPHER runtime=parallel` | Requests parallel execution across multiple CPU threads. Planner may fall back to pipelined/slotted if the query is not parallelisable. |
| `CYPHER runtime=pipelined` | Requests pipelined (vectorised) execution — the default for most read queries. |
| `CYPHER runtime=slotted` | Requests slotted (row-by-row) execution — used as fallback; rarely needed explicitly. |
| `CYPHER runtime=interpreted` | Requests interpreted execution — slowest, for debugging only. |

---

## When to Use `runtime=parallel`

Use parallel runtime for **analytics queries that scan large portions of the graph** — where `EXPLAIN` or `PROFILE` shows `AllNodesScan`, `NodeByLabelScan`, or large `Expand(All)` operators:

- Full graph aggregations: `MATCH (n:X) RETURN count(n)`, avg/sum over all nodes
- High-fanout traversals: co-occurrence counting, sentiment bucketing across all articles
- Large `ORDER BY` + `LIMIT` when scanning thousands of rows before sorting

**Confirm with `EXPLAIN`** — the plan header shows `Runtime PARALLEL` if the hint was accepted. If the plan falls back (e.g., shows `Runtime PIPELINED`), the query contains operations that prevent parallelisation.

---

## When NOT to Use `runtime=parallel`

| Query type | Reason to avoid |
|---|---|
| **OLTP short-hop lookups** (index seek + 1–3 hops) | Parallel overhead exceeds single-threaded cost; `pipelined` is already optimal |
| **Write queries** (`CREATE`, `MERGE`, `SET`, `DELETE`) | Parallel runtime is **read-only**; planner silently ignores the hint for writes |
| **CALL IN TRANSACTIONS** | Batch-write mechanism; parallel hint ignored |
| **Queries with `ORDER BY` on small result sets** | No benefit; thread coordination overhead dominates |
| **Queries with global locks** (`LOCK ELEMENT`) | Cannot be parallelised |

---

## PROFILE with Parallel Runtime

`PROFILE` works normally with the parallel hint:

```cypher
CYPHER 25 CYPHER runtime=parallel
PROFILE
MATCH (n:Organization)-[:MENTIONS]->(a:Article)
RETURN n.name, count(a) AS articleCount
ORDER BY articleCount DESC
LIMIT 10
```

In the resulting plan look for:
- `Runtime PARALLEL` in the header (confirms hint accepted)
- `Batch size N` — parallel runtime processes rows in batches (typically 128–1024)
- `Pipeline X` labels on operators — parallel operators show `Parallel Pipeline N`; operators that could not be parallelised show `Fused in serial Pipeline N`

If all pipelines show `serial`, the hint was accepted but the planner determined the query cannot benefit from parallelism (e.g., the dominant operator is an index seek returning few rows).

---

## Version Availability

| Version | Status |
|---|---|
| Neo4j 2025.06+ | Available — all editions |
| Neo4j Aura | Available — always-latest feature set |
| Neo4j 4.x / 5.x | `runtime=parallel` is **not available** — use `CYPHER runtime=parallel` only with Cypher 25 targets |

---

## Example: Parallel Aggregation over Large Dataset

```cypher
CYPHER 25 CYPHER runtime=parallel
MATCH (a:Article)
RETURN
  CASE WHEN a.sentiment > 0.1 THEN 'positive'
       WHEN a.sentiment < -0.1 THEN 'negative'
       ELSE 'neutral' END AS bucket,
  count(*) AS articleCount,
  avg(a.sentiment) AS avgSentiment
```

Expected EXPLAIN header: `Runtime PARALLEL`, `Batch size 1024`.

> **Note**: Content truncated to token budget.
