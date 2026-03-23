#!/usr/bin/env python3
"""
validator.py — Four-gate Cypher validation logic for the neo4j-cypher-authoring-skill
test harness.

Gate sequence:
  Gate 1: Syntax      — EXPLAIN the query; CypherSyntaxError = FAIL
  Gate 2: Correctness — Execute query; rows < min_results = FAIL
  Gate 3: Quality     — Parse EXPLAIN plan for deprecated operators/syntax;
                        missing CYPHER 25 pragma = WARN
  Gate 4: Performance — PROFILE the query; compare dbHits / rows /
                        allocatedMemory / elapsedTimeMs to thresholds

Write queries execute inside an explicit transaction that is always rolled back
for test isolation (no side-effects on the test database).
CALL IN TRANSACTIONS queries cannot run inside an explicit transaction; they are
executed via session.run() (auto-commit implicit transaction) instead — writes
ARE committed. driver.execute_query() uses explicit transactions internally in
Neo4j 2026.x and must NOT be used for CALL IN TRANSACTIONS queries.
"""

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Verdict constants
# ---------------------------------------------------------------------------

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

# ---------------------------------------------------------------------------
# Deprecated syntax patterns (Gate 3 — source text checks)
# ---------------------------------------------------------------------------

# These regexes are applied to the raw Cypher source string (before execution).
# Each entry: (pattern, description, severity)
DEPRECATED_SYNTAX_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"\[:[A-Z_a-z][A-Z_a-z0-9]*\s*\*", re.IGNORECASE),
        "Old variable-length path syntax [:REL*]; use QPE -[:REL]*- instead",
        FAIL,
    ),
    (
        re.compile(r"\bshortestPath\s*\(", re.IGNORECASE),
        "Deprecated shortestPath() function; use SHORTEST 1 QPE form",
        FAIL,
    ),
    (
        re.compile(r"\ballShortestPaths\s*\(", re.IGNORECASE),
        "Deprecated allShortestPaths() function; use ALL SHORTEST QPE form",
        FAIL,
    ),
    (
        re.compile(r"\bid\s*\(\s*[a-zA-Z_]\w*\s*\)", re.IGNORECASE),
        "Deprecated id() function; use elementId() which returns a stable STRING",
        WARN,
    ),
    (
        re.compile(r"\bcollect\s*\(\s*\)\s*\[", re.IGNORECASE),
        "Deprecated collect()[..N] slice; use COLLECT { MATCH ... RETURN ... LIMIT N }",
        FAIL,
    ),
    (
        re.compile(r"\bCALL\s*\{[^}]*\bWITH\b", re.DOTALL | re.IGNORECASE),
        "Deprecated importing WITH inside CALL { WITH x }; use CALL (x) { ... } scope clause",
        WARN,
    ),
]

# Regex to detect the CYPHER 25 pragma (required on every query)
CYPHER_25_PRAGMA = re.compile(r"^\s*CYPHER\s+25\b", re.IGNORECASE | re.MULTILINE)

# GQL clauses that must never appear in generated queries
GQL_EXCLUDED_CLAUSES = ["LET", "FINISH", "FILTER", "NEXT", "INSERT"]
# Use negative lookbehind for ':' to avoid false positives on relationship type names
# e.g. [:NEXT] is a valid relationship type, not the GQL NEXT clause
_GQL_PATTERNS = [
    (re.compile(rf"(?<!:)\b{clause}\b", re.IGNORECASE), clause)
    for clause in GQL_EXCLUDED_CLAUSES
]

# ---------------------------------------------------------------------------
# CALL IN TRANSACTIONS detection
# ---------------------------------------------------------------------------

_CALL_IN_TXN_RE = re.compile(r"\bIN\s+TRANSACTIONS\b", re.IGNORECASE)


def _is_call_in_transactions(cypher: str) -> bool:
    """Return True if the query contains CALL { ... } IN TRANSACTIONS."""
    return bool(_CALL_IN_TXN_RE.search(cypher))


# ---------------------------------------------------------------------------
# GRAPH TYPE DDL detection (Neo4j Enterprise 2026.02 Preview)
# ---------------------------------------------------------------------------
# These DDL statements cannot be prefixed with EXPLAIN or PROFILE —
# running EXPLAIN on them causes a syntax error from the database.
# Gate 1 is skipped (auto-PASS) for such queries; validation starts at Gate 2.

_GRAPH_TYPE_DDL_RE = re.compile(
    r"^\s*(?:CYPHER\s+25\s+)?"  # optional CYPHER 25 pragma
    r"(?:"
    r"ALTER\s+CURRENT\s+GRAPH\s+TYPE\b"
    r"|EXTEND\s+GRAPH\s+TYPE\b"
    r"|SHOW\s+GRAPH\s+TYPES?\b"
    r"|CREATE\s+GRAPH\s+TYPE\b"
    r"|DROP\s+GRAPH\s+TYPE\b"
    r")",
    re.IGNORECASE | re.MULTILINE,
)


def _is_graph_type_ddl(cypher: str) -> bool:
    """Return True if the query is a GRAPH TYPE DDL statement that cannot be EXPLAIN'd."""
    return bool(_GRAPH_TYPE_DDL_RE.search(cypher))


# ---------------------------------------------------------------------------
# Deprecated operator list (Gate 3 — EXPLAIN plan checks)
# ---------------------------------------------------------------------------

_DEPRECATED_OPERATORS_PATH = Path(__file__).parent / "deprecated_operators.json"


def _load_deprecated_operators() -> list[dict[str, str]]:
    """Load the deprecated_operators.json file from the harness directory."""
    if not _DEPRECATED_OPERATORS_PATH.exists():
        return []
    with open(_DEPRECATED_OPERATORS_PATH) as f:
        data = json.load(f)
    return data.get("operators", [])


DEPRECATED_OPERATORS = _load_deprecated_operators()

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class GateResult:
    """Result of a single validation gate."""

    gate: int  # 1–4
    verdict: str  # PASS | WARN | FAIL
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Aggregate result of all four gates for a single test case."""

    verdict: str  # worst of the four gate verdicts
    gates: list[GateResult] = field(default_factory=list)
    cypher: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)

    def failed_gate(self) -> Optional[int]:
        """Return the number of the first FAIL gate, or None."""
        for g in self.gates:
            if g.verdict == FAIL:
                return g.gate
        return None

    def warned_gate(self) -> Optional[int]:
        """Return the number of the first WARN gate, or None."""
        for g in self.gates:
            if g.verdict == WARN:
                return g.gate
        return None


# ---------------------------------------------------------------------------
# Syntax checks (Gate 3 — source-level, before execution)
# ---------------------------------------------------------------------------


def check_deprecated_syntax(cypher: str) -> list[GateResult]:
    """
    Run source-level deprecated syntax checks.

    Returns a list of GateResult objects (gate=3) for each pattern that matches.
    Empty list means all patterns passed.
    """
    results = []

    # Check CYPHER 25 pragma
    if not CYPHER_25_PRAGMA.search(cypher):
        results.append(
            GateResult(
                gate=3,
                verdict=WARN,
                reason="Missing CYPHER 25 pragma; query will execute under Cypher 5 semantics",
            )
        )

    # Check GQL-excluded clauses
    for pattern, clause in _GQL_PATTERNS:
        if pattern.search(cypher):
            results.append(
                GateResult(
                    gate=3,
                    verdict=FAIL,
                    reason=f"GQL-excluded clause '{clause}' found; use the pure Cypher equivalent",
                )
            )

    # Check deprecated syntax patterns
    for pat, description, severity in DEPRECATED_SYNTAX_PATTERNS:
        if pat.search(cypher):
            results.append(
                GateResult(gate=3, verdict=severity, reason=description)
            )

    return results


def check_deprecated_operators_in_plan(plan_text: str) -> list[GateResult]:
    """
    Scan EXPLAIN plan text for deprecated or error-indicating operators.

    Returns a list of GateResult objects (gate=3) for each match.
    Empty list means all operators are clean.
    """
    results = []
    plan_lower = plan_text.lower()
    for op in DEPRECATED_OPERATORS:
        name = op["name"].lower()
        if name in plan_lower:
            results.append(
                GateResult(
                    gate=3,
                    verdict=op["severity"],
                    reason=op["reason"],
                    details={"operator": op["name"]},
                )
            )
    return results


# ---------------------------------------------------------------------------
# PROFILE metrics extraction (Gate 4)
# ---------------------------------------------------------------------------


def extract_profile_metrics(profile_result: Any) -> dict[str, Any]:
    """
    Extract the four performance metrics from a PROFILE result.

    Accepts either:
    - A neo4j driver ProfiledPlan object (summary.profile)
    - A dict with Neo4j driver summary attributes
    - Raw PROFILE text (string) — parsed heuristically

    Returns a dict with keys:
      totalDbHits        (int)
      totalAllocatedMemory (int, bytes)
      elapsedTimeMs      (float)
      totalRows          (int)

    Returns None values for metrics that cannot be extracted.
    """
    metrics: dict[str, Any] = {
        "totalDbHits": None,
        "totalAllocatedMemory": None,
        "elapsedTimeMs": None,
        "totalRows": None,
    }

    if profile_result is None:
        return metrics

    # neo4j Python driver: summary.profile has .db_hits, .rows, .children
    # summary.result_available_after / summary.result_consumed_after for timing
    # summary.profile.arguments has 'GlobalMemory'
    if hasattr(profile_result, "db_hits"):
        # Recurse through plan tree to total up all db_hits and rows
        metrics["totalDbHits"] = _sum_plan_attr(profile_result, "db_hits")
        metrics["totalRows"] = _sum_plan_attr(profile_result, "rows")

        # GlobalMemory is on root plan arguments
        args = getattr(profile_result, "arguments", {}) or {}
        if "GlobalMemory" in args:
            metrics["totalAllocatedMemory"] = args["GlobalMemory"]

    elif isinstance(profile_result, dict):
        # Accept dict form (e.g. from mocked tests or JSON-serialized plan)
        metrics["totalDbHits"] = profile_result.get("totalDbHits")
        metrics["totalAllocatedMemory"] = profile_result.get("totalAllocatedMemory")
        metrics["elapsedTimeMs"] = profile_result.get("elapsedTimeMs")
        metrics["totalRows"] = profile_result.get("totalRows")

    elif isinstance(profile_result, str):
        # Heuristic parse of PROFILE text output (e.g. from browser or cypher-shell)
        metrics.update(_parse_profile_text(profile_result))

    return metrics


def _sum_plan_attr(plan: Any, attr: str) -> int:
    """Recursively sum an attribute across all nodes of a plan tree."""
    total = getattr(plan, attr, 0) or 0
    for child in getattr(plan, "children", []) or []:
        total += _sum_plan_attr(child, attr)
    return total


def _parse_profile_text(text: str) -> dict[str, Any]:
    """Heuristic extraction of metrics from PROFILE text output."""
    metrics: dict[str, Any] = {
        "totalDbHits": None,
        "totalAllocatedMemory": None,
        "elapsedTimeMs": None,
        "totalRows": None,
    }
    # Pattern: "db hits: 42" or "db_hits=42"
    m = re.search(r"db\s*hits?\s*[=:]\s*(\d+)", text, re.IGNORECASE)
    if m:
        metrics["totalDbHits"] = int(m.group(1))
    m = re.search(r"rows?\s*[=:]\s*(\d+)", text, re.IGNORECASE)
    if m:
        metrics["totalRows"] = int(m.group(1))
    m = re.search(r"memory\s*[=:]\s*(\d+)", text, re.IGNORECASE)
    if m:
        metrics["totalAllocatedMemory"] = int(m.group(1))
    m = re.search(r"elapsed\s*(?:time)?\s*(?:ms)?\s*[=:]\s*([\d.]+)", text, re.IGNORECASE)
    if m:
        metrics["elapsedTimeMs"] = float(m.group(1))
    return metrics


def check_performance(
    metrics: dict[str, Any],
    *,
    min_results: int = 0,
    max_db_hits: Optional[int] = None,
    max_allocated_memory_bytes: Optional[int] = None,
    max_runtime_ms: Optional[float] = None,
) -> list[GateResult]:
    """
    Run Gate 4 performance checks against thresholds.

    Args:
        metrics: dict from extract_profile_metrics()
        min_results: minimum expected result rows (0 = no check)
        max_db_hits: FAIL if totalDbHits exceeds this (None = no check)
        max_allocated_memory_bytes: FAIL if totalAllocatedMemory exceeds this (None = no check)
        max_runtime_ms: WARN (not FAIL — CI env varies) if elapsedTimeMs exceeds this

    Returns a list of GateResult objects (gate=4).
    """
    results = []

    db_hits = metrics.get("totalDbHits")
    rows = metrics.get("totalRows")
    memory = metrics.get("totalAllocatedMemory")
    elapsed = metrics.get("elapsedTimeMs")

    # Row count check
    if min_results > 0 and rows is not None and rows < min_results:
        results.append(
            GateResult(
                gate=4,
                verdict=FAIL,
                reason=f"Result rows {rows} < required minimum {min_results}",
                details={"actual_rows": rows, "min_results": min_results},
            )
        )

    # dbHits threshold
    if max_db_hits is not None and db_hits is not None and db_hits > max_db_hits:
        results.append(
            GateResult(
                gate=4,
                verdict=FAIL,
                reason=f"dbHits {db_hits:,} exceeds threshold {max_db_hits:,}",
                details={"totalDbHits": db_hits, "max_db_hits": max_db_hits},
            )
        )

    # Allocated memory threshold
    if (
        max_allocated_memory_bytes is not None
        and memory is not None
        and memory > max_allocated_memory_bytes
    ):
        mb = memory / 1_048_576
        max_mb = max_allocated_memory_bytes / 1_048_576
        results.append(
            GateResult(
                gate=4,
                verdict=FAIL,
                reason=f"allocatedMemory {mb:.1f} MB exceeds threshold {max_mb:.1f} MB",
                details={
                    "totalAllocatedMemory": memory,
                    "max_allocated_memory_bytes": max_allocated_memory_bytes,
                },
            )
        )

    # Runtime (WARN only — CI environments vary)
    if max_runtime_ms is not None and elapsed is not None and elapsed > max_runtime_ms:
        results.append(
            GateResult(
                gate=4,
                verdict=WARN,
                reason=f"elapsedTimeMs {elapsed:.0f} ms exceeds warning threshold {max_runtime_ms:.0f} ms (CI timing guidance only)",
                details={"elapsedTimeMs": elapsed, "max_runtime_ms": max_runtime_ms},
            )
        )

    return results


# ---------------------------------------------------------------------------
# Four-gate validator — main entry point
# ---------------------------------------------------------------------------


def validate(
    cypher: str,
    driver: Any,
    *,
    database: str = "neo4j",
    is_write_query: bool = False,
    min_results: int = 0,
    max_db_hits: Optional[int] = None,
    max_allocated_memory_bytes: Optional[int] = None,
    max_runtime_ms: Optional[float] = None,
) -> ValidationResult:
    """
    Run all four validation gates on `cypher` against the given Neo4j driver.

    Write queries are executed inside an explicit transaction that is ALWAYS
    ROLLED BACK after execution — ensuring no side-effects on the test database.

    Args:
        cypher:   The Cypher query string to validate.
        driver:   An open neo4j.GraphDatabase driver instance.
        database: Database to run queries against (default: "neo4j").
        is_write_query: If True, execute inside a rolled-back explicit txn.
        min_results: Minimum row count for Gate 2 (correctness) check.
        max_db_hits: Gate 4 FAIL threshold for totalDbHits.
        max_allocated_memory_bytes: Gate 4 FAIL threshold for allocatedMemory.
        max_runtime_ms: Gate 4 WARN threshold for elapsedTimeMs.

    Returns:
        ValidationResult with .verdict (PASS/WARN/FAIL), .gates, .metrics.
    """
    gates: list[GateResult] = []

    # ------------------------------------------------------------------
    # Gate 3 source checks — run before any execution (fail fast on GQL)
    # ------------------------------------------------------------------
    syntax_issues = check_deprecated_syntax(cypher)
    # If any GQL-excluded clause is found, skip execution entirely
    gql_fails = [g for g in syntax_issues if g.verdict == FAIL and "GQL-excluded" in g.reason]
    if gql_fails:
        gates.extend(syntax_issues)
        return _build_result(cypher, gates, {})

    # ------------------------------------------------------------------
    # Gate 1: Syntax — EXPLAIN (skipped for GRAPH TYPE DDL)
    # ------------------------------------------------------------------
    gate1 = GateResult(gate=1, verdict=PASS)
    plan_text = ""

    if _is_graph_type_ddl(cypher):
        # GRAPH TYPE DDL statements (ALTER CURRENT GRAPH TYPE, EXTEND GRAPH TYPE, etc.)
        # cannot be prefixed with EXPLAIN — Neo4j rejects it as a syntax error.
        # Skip Gate 1 with an auto-PASS and proceed directly to Gate 2 execution.
        gate1.reason = "Gate 1 skipped: GRAPH TYPE DDL cannot be EXPLAIN'd; syntax validated by Gate 2 execution"
        gates.append(gate1)
    else:
        explain_cypher = _prepend_explain(cypher)

        try:
            records, summary, _ = driver.execute_query(
                explain_cypher, database_=database
            )
            # Capture the plan as text for Gate 3 operator scan
            if hasattr(summary, "plan") and summary.plan:
                plan_text = _plan_to_text(summary.plan)
            gate1.verdict = PASS
            gate1.reason = "EXPLAIN succeeded"
        except Exception as exc:
            gate1.verdict = FAIL
            gate1.reason = f"Syntax error: {exc}"
            gates.append(gate1)
            return _build_result(cypher, gates, {})

        gates.append(gate1)

    # ------------------------------------------------------------------
    # Gate 2: Correctness — execute and check row count
    # ------------------------------------------------------------------
    gate2 = GateResult(gate=2, verdict=PASS)
    actual_rows = 0
    elapsed_ms: Optional[float] = None

    try:
        if is_write_query and _is_call_in_transactions(cypher):
            # CALL IN TRANSACTIONS requires an implicit (auto-commit) transaction.
            # driver.execute_query() internally uses an explicit transaction in Neo4j
            # 2026.x — so use session.run() directly for implicit auto-commit semantics.
            # Writes ARE committed; acceptable for local/writable test databases.
            t0 = time.monotonic()
            with driver.session(database=database) as _session:
                _result = _session.run(cypher)
                records = list(_result)
                actual_rows = len(records)
            elapsed_ms = (time.monotonic() - t0) * 1000.0
        elif is_write_query:
            # Non-CALL-IN-TRANSACTIONS write queries: explicit txn, always roll back
            actual_rows, elapsed_ms = _execute_write_rollback(
                cypher, driver, database=database
            )
        else:
            t0 = time.monotonic()
            records, summary, _ = driver.execute_query(
                cypher, database_=database
            )
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            actual_rows = len(records)

        if min_results > 0 and actual_rows < min_results:
            gate2.verdict = FAIL
            gate2.reason = (
                f"Query returned {actual_rows} rows, expected ≥ {min_results}"
            )
            gate2.details = {"actual_rows": actual_rows, "min_results": min_results}
        else:
            gate2.reason = f"Returned {actual_rows} rows (min: {min_results})"

    except Exception as exc:
        gate2.verdict = FAIL
        gate2.reason = f"Execution error: {exc}"
        gates.append(gate2)
        return _build_result(cypher, gates, {})

    gates.append(gate2)

    # ------------------------------------------------------------------
    # Gate 3: Quality — deprecated syntax + operator plan scan
    # ------------------------------------------------------------------
    # Source-level checks (already computed above, minus GQL which was handled)
    source_issues = [g for g in syntax_issues if "GQL-excluded" not in g.reason]
    gates.extend(source_issues)

    # Operator-level plan scan
    if plan_text:
        operator_issues = check_deprecated_operators_in_plan(plan_text)
        gates.extend(operator_issues)

    # Add a PASS gate-3 marker if no issues found so far in gate 3
    if not source_issues and not (plan_text and check_deprecated_operators_in_plan(plan_text)):
        gates.append(GateResult(gate=3, verdict=PASS, reason="No deprecated syntax or operators detected"))

    # ------------------------------------------------------------------
    # Gate 4: Performance — PROFILE (skipped for GRAPH TYPE DDL)
    # ------------------------------------------------------------------
    gate4_metrics: dict[str, Any] = {}

    if _is_graph_type_ddl(cypher):
        # GRAPH TYPE DDL statements cannot be prefixed with PROFILE.
        # Skip Gate 4 with an auto-PASS (timing captured in Gate 2 elapsed_ms).
        if elapsed_ms is not None:
            gate4_metrics["elapsedTimeMs"] = round(elapsed_ms, 2)
        gates.append(
            GateResult(
                gate=4,
                verdict=PASS,
                reason="Gate 4 skipped: GRAPH TYPE DDL cannot be PROFILE'd; no performance thresholds apply",
                details=gate4_metrics,
            )
        )
        return _build_result(cypher, gates, gate4_metrics)

    profile_cypher = _prepend_profile(cypher)

    try:
        if is_write_query and not _is_call_in_transactions(cypher):
            # Normal write queries: PROFILE inside rolled-back explicit txn
            profile_metrics_raw, _ = _profile_write_rollback(
                profile_cypher, driver, database=database
            )
            gate4_metrics = profile_metrics_raw or {}
        elif is_write_query and _is_call_in_transactions(cypher):
            # CALL IN TRANSACTIONS: PROFILE also requires implicit (auto-commit) txn.
            # Use session.run() to avoid explicit-transaction rejection.
            # NOTE: this commits the write again — acceptable for write-enabled test DBs.
            t0 = time.monotonic()
            with driver.session(database=database) as _session:
                _result = _session.run(profile_cypher)
                _summary = _result.consume()
                plan = getattr(_summary, "profile", None)
                gate4_metrics = extract_profile_metrics(plan)
            profile_elapsed = (time.monotonic() - t0) * 1000.0
            if gate4_metrics.get("elapsedTimeMs") is None:
                gate4_metrics["elapsedTimeMs"] = profile_elapsed
        else:
            t0 = time.monotonic()
            _, summary, _ = driver.execute_query(
                profile_cypher, database_=database
            )
            profile_elapsed = (time.monotonic() - t0) * 1000.0
            plan = getattr(summary, "profile", None)
            gate4_metrics = extract_profile_metrics(plan)
            if gate4_metrics.get("elapsedTimeMs") is None:
                gate4_metrics["elapsedTimeMs"] = profile_elapsed

    except Exception as exc:
        gates.append(
            GateResult(
                gate=4,
                verdict=WARN,
                reason=f"PROFILE execution failed (Gate 4 skipped): {exc}",
            )
        )
        return _build_result(cypher, gates, gate4_metrics)

    perf_issues = check_performance(
        gate4_metrics,
        min_results=min_results,
        max_db_hits=max_db_hits,
        max_allocated_memory_bytes=max_allocated_memory_bytes,
        max_runtime_ms=max_runtime_ms,
    )

    if perf_issues:
        gates.extend(perf_issues)
    else:
        db_hits = gate4_metrics.get("totalDbHits", "n/a")
        mem = gate4_metrics.get("totalAllocatedMemory", "n/a")
        gates.append(
            GateResult(
                gate=4,
                verdict=PASS,
                reason=f"Performance within thresholds (dbHits={db_hits}, memory={mem} bytes)",
                details=gate4_metrics,
            )
        )

    # Merge elapsed time from Gate 2 if Gate 4 lacks it
    if gate4_metrics.get("elapsedTimeMs") is None and elapsed_ms is not None:
        gate4_metrics["elapsedTimeMs"] = round(elapsed_ms, 2)

    return _build_result(cypher, gates, gate4_metrics)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_result(
    cypher: str, gates: list[GateResult], metrics: dict[str, Any]
) -> ValidationResult:
    """Compute aggregate verdict and wrap into a ValidationResult."""
    # Worst verdict wins: FAIL > WARN > PASS
    verdict = PASS
    for g in gates:
        if g.verdict == FAIL:
            verdict = FAIL
            break
        if g.verdict == WARN:
            verdict = WARN
    return ValidationResult(verdict=verdict, gates=gates, cypher=cypher, metrics=metrics)


def _prepend_explain(cypher: str) -> str:
    """Prepend EXPLAIN to a Cypher query, preserving existing CYPHER 25 pragma."""
    stripped = cypher.strip()
    if CYPHER_25_PRAGMA.match(stripped):
        # Insert EXPLAIN after the pragma line
        lines = stripped.splitlines()
        return lines[0] + "\nEXPLAIN " + "\n".join(lines[1:]).lstrip()
    return "EXPLAIN " + stripped


def _prepend_profile(cypher: str) -> str:
    """Prepend PROFILE to a Cypher query, preserving existing CYPHER 25 pragma."""
    stripped = cypher.strip()
    if CYPHER_25_PRAGMA.match(stripped):
        lines = stripped.splitlines()
        return lines[0] + "\nPROFILE " + "\n".join(lines[1:]).lstrip()
    return "PROFILE " + stripped


def _plan_to_text(plan: Any) -> str:
    """Convert a Neo4j plan object to a flat string for operator scanning."""
    parts: list[str] = []

    def _walk(node: Any) -> None:
        op_type = getattr(node, "operator_type", "") or ""
        parts.append(op_type)
        for child in getattr(node, "children", []) or []:
            _walk(child)

    _walk(plan)
    return " ".join(parts)


def _execute_write_rollback(
    cypher: str, driver: Any, *, database: str
) -> tuple[int, Optional[float]]:
    """
    Execute a write query inside an explicit transaction that is always rolled back.

    Returns (row_count, elapsed_ms).
    """
    with driver.session(database=database) as session:
        t0 = time.monotonic()
        tx = session.begin_transaction()
        try:
            result = tx.run(cypher)
            records = list(result)
            row_count = len(records)
        finally:
            tx.rollback()
        elapsed_ms = (time.monotonic() - t0) * 1000.0
    return row_count, elapsed_ms


def _profile_write_rollback(
    profile_cypher: str, driver: Any, *, database: str
) -> tuple[dict[str, Any], Optional[float]]:
    """
    Run PROFILE on a write query inside an always-rolled-back transaction.

    Returns (metrics_dict, elapsed_ms).
    """
    with driver.session(database=database) as session:
        t0 = time.monotonic()
        tx = session.begin_transaction()
        try:
            result = tx.run(profile_cypher)
            list(result)  # consume records
            summary = result.consume()
            plan = getattr(summary, "profile", None)
            metrics = extract_profile_metrics(plan)
        finally:
            tx.rollback()
        elapsed_ms = (time.monotonic() - t0) * 1000.0
    if metrics.get("elapsedTimeMs") is None:
        metrics["elapsedTimeMs"] = round(elapsed_ms, 2)
    return metrics, elapsed_ms


# ---------------------------------------------------------------------------
# Standalone smoke test (run without Neo4j connection)
# ---------------------------------------------------------------------------


def _run_smoke_tests() -> None:
    """Run offline unit tests for source-level checks. No DB required."""
    errors: list[str] = []

    # --- deprecated syntax detection ---
    test_cases = [
        # (cypher, expect_fail_reason_fragment, expect_warn_reason_fragment)
        ("CYPHER 25\nMATCH (a)-[:KNOWS*1..3]->(b) RETURN a", "variable-length path", None),
        ("CYPHER 25\nMATCH p = shortestPath((a)-[*]->(b)) RETURN p", "shortestPath", None),
        ("CYPHER 25\nMATCH p = allShortestPaths((a)-[*]->(b)) RETURN p", "allShortestPaths", None),
        ("CYPHER 25\nMATCH (n) RETURN id(n)", None, "id()"),
        ("MATCH (n) RETURN n.name LIMIT 10", None, "CYPHER 25"),  # missing pragma → WARN
        ("CYPHER 25\nMATCH (n) RETURN LET n.x = 1", "GQL-excluded", None),
    ]

    for cypher, expect_fail_frag, expect_warn_frag in test_cases:
        issues = check_deprecated_syntax(cypher)
        fails = [g for g in issues if g.verdict == FAIL]
        warns = [g for g in issues if g.verdict == WARN]

        if expect_fail_frag:
            matching = [f for f in fails if expect_fail_frag.lower() in f.reason.lower()]
            if not matching:
                errors.append(
                    f"Expected FAIL containing '{expect_fail_frag}' for: {cypher[:60]!r}\n"
                    f"  Got: {[g.reason for g in fails]}"
                )
        if expect_warn_frag:
            matching = [w for w in warns if expect_warn_frag.lower() in w.reason.lower()]
            if not matching:
                errors.append(
                    f"Expected WARN containing '{expect_warn_frag}' for: {cypher[:60]!r}\n"
                    f"  Got: {[g.reason for g in warns]}"
                )

    # --- performance check ---
    metrics = {"totalDbHits": 1500, "totalAllocatedMemory": 200_000_000, "elapsedTimeMs": 5000, "totalRows": 5}
    results = check_performance(
        metrics,
        min_results=10,
        max_db_hits=1000,
        max_allocated_memory_bytes=100_000_000,
        max_runtime_ms=2000,
    )
    verdicts = {g.verdict for g in results}
    if FAIL not in verdicts:
        errors.append("Expected FAIL from performance check (rows < min and dbHits exceeded)")
    if WARN not in verdicts:
        errors.append("Expected WARN from performance check (elapsedTimeMs exceeded)")

    # --- deprecated operators json loaded ---
    if not DEPRECATED_OPERATORS:
        errors.append("deprecated_operators.json failed to load or is empty")

    required_op_names = {"VarLengthExpand(Pruning)", "RelationshipCountFromCountStore"}
    loaded_names = {op["name"] for op in DEPRECATED_OPERATORS}
    for name in required_op_names:
        if name not in loaded_names:
            errors.append(f"Expected operator '{name}' in deprecated_operators.json")

    # --- EXPLAIN/PROFILE prefix helpers ---
    q = "CYPHER 25\nMATCH (n) RETURN n"
    assert "EXPLAIN" in _prepend_explain(q), "EXPLAIN prefix missing"
    assert "PROFILE" in _prepend_profile(q), "PROFILE prefix missing"
    assert _prepend_explain(q).startswith("CYPHER 25"), "CYPHER 25 pragma must come first in EXPLAIN"
    assert _prepend_profile(q).startswith("CYPHER 25"), "CYPHER 25 pragma must come first in PROFILE"

    # --- GRAPH TYPE DDL detection ---
    graph_type_ddl_cases = [
        ("CYPHER 25\nALTER CURRENT GRAPH TYPE SET (::Customer { id :: STRING NOT NULL })", True),
        ("CYPHER 25\nEXTEND GRAPH TYPE WITH (::Transaction { amount :: FLOAT NOT NULL })", True),
        ("CYPHER 25\nSHOW GRAPH TYPES", True),
        ("CYPHER 25\nSHOW GRAPH TYPE", True),
        ("CYPHER 25\nCREATE GRAPH TYPE MyType (::Person { name :: STRING })", True),
        ("CYPHER 25\nDROP GRAPH TYPE MyType", True),
        # Must NOT match normal Cypher queries
        ("CYPHER 25\nMATCH (n:Person) RETURN n", False),
        ("CYPHER 25\nMATCH (n) WHERE n.type = 'graph' RETURN n", False),
        # Must NOT match GQL-excluded INSERT keyword inside GRAPH TYPE context
        ("CYPHER 25\nINSERT (p:Person {name: 'Alice'})", False),  # INSERT is GQL-excluded, not DDL
    ]
    for ddl_cypher, expect_match in graph_type_ddl_cases:
        got = _is_graph_type_ddl(ddl_cypher)
        if got != expect_match:
            errors.append(
                f"_is_graph_type_ddl({ddl_cypher[:60]!r}) = {got}, expected {expect_match}"
            )

    # Verify GQL-excluded clauses still correctly fire (not affected by DDL detection)
    gql_test_cases = [
        ("CYPHER 25\nLET x = 1 RETURN x", "LET"),
        ("CYPHER 25\nFINISH", "FINISH"),
        ("CYPHER 25\nFILTER n IN [1,2,3] RETURN n", "FILTER"),
        ("CYPHER 25\nNEXT", "NEXT"),
        ("CYPHER 25\nINSERT (p:Person)", "INSERT"),
    ]
    for cypher, clause in gql_test_cases:
        issues = check_deprecated_syntax(cypher)
        gql_fails = [g for g in issues if g.verdict == FAIL and "GQL-excluded" in g.reason]
        if not gql_fails:
            errors.append(f"Expected GQL-excluded FAIL for '{clause}' in: {cypher[:60]!r}")

    if errors:
        print("SMOKE TEST FAILURES:")
        for e in errors:
            print(f"  FAIL: {e}")
        raise SystemExit(1)
    else:
        print(f"All smoke tests passed ({len(test_cases)} syntax cases + performance + operators + {len(graph_type_ddl_cases)} DDL detection + {len(gql_test_cases)} GQL clause checks)")


if __name__ == "__main__":
    _run_smoke_tests()
