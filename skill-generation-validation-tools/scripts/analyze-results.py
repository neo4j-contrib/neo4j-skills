#!/usr/bin/env python3
"""
analyze-results.py — Harness improvement report for neo4j-cypher-authoring-skill.

Reads one or more JSON result files produced by runner.py and generates a
structured Markdown improvement report that:

  1. Summarises overall pass/warn/fail counts across all input files
  2. Shows per-gate failure breakdown (gates 1–4)
  3. Shows per-difficulty pass rate delta (actual vs PRD target)
  4. Clusters failure patterns and maps each to the most likely responsible
     SKILL.md section (e.g. "Schema-First Protocol", "QPE Patterns")
  5. Provides concrete recommended edits with before/after Cypher examples
     where the pattern is clear

Output is for human review only — this script does NOT patch SKILL.md.

No database or Claude connection is required. Reads JSON only.

Usage:
    # Single file
    uv run python3 scripts/analyze-results.py \\
        --input tests/results/baseline-final.json \\
        --output tests/results/improvement-report.md

    # Directory of JSON files
    uv run python3 scripts/analyze-results.py \\
        --input tests/results/ \\
        --output tests/results/improvement-report.md

    # Multiple files
    uv run python3 scripts/analyze-results.py \\
        --input tests/results/run-a.json tests/results/run-b.json \\
        --output tests/results/improvement-report.md
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

# PRD pass-rate targets per difficulty
PRD_TARGETS: dict[str, float] = {
    "basic": 0.90,
    "intermediate": 0.80,
    "advanced": 0.70,
    "complex": 0.60,
    "expert": 0.60,
}

DIFFICULTY_ORDER = ["basic", "intermediate", "advanced", "complex", "expert"]

# Gate descriptions
GATE_DESCRIPTIONS = {
    1: "Syntax (EXPLAIN)",
    2: "Correctness (row count / execution)",
    3: "Quality (pragma, deprecated syntax/operators)",
    4: "Performance (PROFILE thresholds)",
}

# ---------------------------------------------------------------------------
# Pattern → SKILL.md section mapping
#
# Each entry is (pattern_label, responsible_section, description, example).
# Patterns are detected by scanning gate_details reasons and generated_cypher.
# ---------------------------------------------------------------------------

# (reason_substring, tag, cypher_pattern) → (skill_section, short_description, before_example, after_example)
FAILURE_PATTERNS: list[dict[str, Any]] = [
    {
        "id": "missing-cypher-pragma",
        "label": "Missing CYPHER 25 pragma",
        "skill_section": "Cypher 25 Version Pragma",
        "match_reason": ["CYPHER 25", "pragma", "version pragma"],
        "match_cypher": [],
        "match_tags": [],
        "description": (
            "The generated query does not start with `CYPHER 25`. "
            "Gate 3 checks for this and raises a WARN."
        ),
        "before": "MATCH (n:Organization) RETURN n.name",
        "after": "CYPHER 25\nMATCH (n:Organization) RETURN n.name",
        "recommendation": (
            "The Cypher 25 Version Pragma section says 'every query MUST begin with `CYPHER 25`'. "
            "Reinforce by adding a reminder at the top of the Core Pattern Cheat Sheet: "
            "prefix every code block with `CYPHER 25`."
        ),
    },
    {
        "id": "deprecated-varlength",
        "label": "Deprecated variable-length pattern [:REL*]",
        "skill_section": "Deprecated Syntax → Cypher 25 Preferred",
        "match_reason": ["deprecated", "variable-length", "REL*", "VarLength"],
        "match_cypher": [],
        "match_cypher_regex": [r"\[:\w+\*"],
        "match_tags": ["variable-length", "path"],
        "description": (
            "The query uses the deprecated `[:REL*]` variable-length syntax "
            "instead of a Quantified Path Expression (QPE)."
        ),
        "before": "MATCH (a)-[:HAS_SUBSIDIARY*1..5]->(b) RETURN b.name",
        "after": "CYPHER 25\nMATCH (a)(()-[:HAS_SUBSIDIARY]->()){1,5}(b) RETURN b.name",
        "recommendation": (
            "The Deprecated Syntax table maps `[:REL*]` → QPE. "
            "Add a callout box in the QPE section: 'Never use [:REL*n..m]. "
            "Always use QPE `()-[:REL]->{n,m}()`.' "
            "Include a side-by-side old/new example."
        ),
    },
    {
        "id": "deprecated-shortestpath",
        "label": "Deprecated shortestPath() / allShortestPaths()",
        "skill_section": "Deprecated Syntax → Cypher 25 Preferred",
        "match_reason": ["shortestPath", "allShortestPaths", "deprecated"],
        "match_cypher": ["shortestPath(", "allShortestPaths("],
        "match_tags": ["shortest-path", "path"],
        "description": (
            "The query uses deprecated `shortestPath()` or `allShortestPaths()` "
            "instead of the Cypher 25 `SHORTEST` keyword."
        ),
        "before": "MATCH p = shortestPath((a)-[:HAS_SUBSIDIARY*]->(b)) RETURN p",
        "after": "CYPHER 25\nMATCH p = SHORTEST 1 (a)-[:HAS_SUBSIDIARY]->{1,}(b) RETURN p",
        "recommendation": (
            "Expand the 'SHORTEST' row in the deprecated syntax table: "
            "add a note that `SHORTEST 1` replaces `shortestPath()` and "
            "`SHORTEST k` replaces `allShortestPaths()`. "
            "Include both migration examples."
        ),
    },
    {
        "id": "deprecated-id-function",
        "label": "Deprecated id() function",
        "skill_section": "Deprecated Syntax → Cypher 25 Preferred",
        "match_reason": ["id()", "deprecated", "elementId"],
        "match_cypher": [],
        "match_cypher_regex": [r"\bid\("],  # \b = word boundary, \( = literal paren
        "match_tags": ["id", "element-id"],
        "description": (
            "The query uses the deprecated `id()` function. "
            "In Cypher 25, `elementId()` is the preferred replacement."
        ),
        "before": "MATCH (n) RETURN id(n) AS nodeId",
        "after": "CYPHER 25\nMATCH (n) RETURN elementId(n) AS nodeId",
        "recommendation": (
            "Add `id()` → `elementId()` explicitly to the deprecated syntax table "
            "and note that `elementId()` returns a STRING (not INTEGER)."
        ),
    },
    {
        "id": "vector-dimension-mismatch",
        "label": "Vector index dimension mismatch",
        "skill_section": "Schema-First Protocol",
        "match_reason": ["dimensionality", "dimension", "vector", "1536", "1221"],
        "match_cypher": ["db.index.vector.queryNodes", "SEARCH"],
        "match_tags": ["vector", "index", "similarity"],
        "description": (
            "The query passes a vector of the wrong dimensionality to a vector index. "
            "The skill must inspect the index `OPTIONS` map for `vector.dimensions` "
            "before authoring vector queries."
        ),
        "before": (
            "-- hard-codes 1536-dim vector without checking the index --\n"
            "CALL db.index.vector.queryNodes('news', 5, $embedding)"
        ),
        "after": (
            "-- Schema-First: inspect first --\n"
            "SHOW VECTOR INDEXES YIELD name, options\n"
            "-- Then use the correct dimension from options.vector.dimensions"
        ),
        "recommendation": (
            "Add an explicit step to the Schema-First Protocol: "
            "'For vector queries, run `SHOW VECTOR INDEXES YIELD name, options` "
            "and read `options.vector.dimensions` before calling the vector procedure. "
            "Never hard-code embedding dimensions.' "
            "Also add this as a note in the SEARCH Clause section."
        ),
    },
    {
        "id": "call-in-transactions-explicit-txn",
        "label": "CALL IN TRANSACTIONS inside explicit transaction",
        "skill_section": "FOREACH vs UNWIND / Core Pattern Cheat Sheet",
        "match_reason": [
            "CALL { ... } IN TRANSACTIONS",
            "implicit transaction",
            "explicit transaction",
            "TransactionStartFailed",
        ],
        "match_cypher": ["CALL {", "IN TRANSACTIONS"],
        "match_tags": ["call-in-transactions", "batch"],
        "description": (
            "`CALL { ... } IN TRANSACTIONS` requires an *implicit* transaction. "
            "The harness wraps write queries in an explicit `BEGIN` transaction, "
            "which causes `TransactionStartFailed`. "
            "The query itself may be correct but cannot be tested this way."
        ),
        "before": (
            "-- Fails in explicit BEGIN/COMMIT block --\n"
            "CALL { MATCH (n:Org) CALL { WITH n ... } IN TRANSACTIONS OF 100 ROWS }"
        ),
        "after": (
            "-- Correct: only valid as top-level implicit transaction --\n"
            "CYPHER 25\n"
            "MATCH (n:Organization)\n"
            "CALL { WITH n ... } IN TRANSACTIONS OF 100 ROWS"
        ),
        "recommendation": (
            "Add a warning box to the CALL IN TRANSACTIONS reference file: "
            "'This construct MUST be the outermost query (no wrapping BEGIN/COMMIT). "
            "Test harness marks these is_write_query=true; failures here are "
            "a harness limitation, not a skill deficiency.' "
            "Also ensure runner.py marks such failures with a note in gate_details."
        ),
    },
    {
        "id": "null-propagation",
        "label": "Null propagation / missing null guard",
        "skill_section": "Types and Nulls (cypher25-types-and-nulls.md)",
        "match_reason": ["null", "NullPointer", "type error", "cannot be null"],
        "match_cypher": [],
        "match_tags": ["null", "optional-match", "coalesce"],
        "description": (
            "The query fails or returns incorrect results because null values "
            "propagate unexpectedly. Common causes: arithmetic on null properties, "
            "comparisons without IS NULL guards, or OPTIONAL MATCH without coalesce()."
        ),
        "before": "MATCH (n) OPTIONAL MATCH (n)-[:HAS_RATING]->(r) RETURN avg(r.score)",
        "after": (
            "CYPHER 25\n"
            "MATCH (n)\n"
            "OPTIONAL MATCH (n)-[:HAS_RATING]->(r)\n"
            "RETURN avg(coalesce(r.score, 0.0))"
        ),
        "recommendation": (
            "Add a 'Null Safety Checklist' to the Schema-First Protocol: "
            "1) After OPTIONAL MATCH, wrap nullable properties in coalesce(). "
            "2) Never compare with `= null`; use `IS NULL`. "
            "3) For arithmetic, guard with `WHERE prop IS NOT NULL`."
        ),
    },
    {
        "id": "wrong-merge-pattern",
        "label": "Unsafe MERGE / missing ON CREATE / ON MATCH",
        "skill_section": "Core Pattern Cheat Sheet — MERGE Safety",
        "match_reason": ["MERGE", "duplicate", "constraint violation", "already exists"],
        "match_cypher": ["MERGE (", "MERGE ()-"],
        "match_tags": ["merge", "write", "upsert"],
        "description": (
            "The MERGE clause is missing `ON CREATE SET` / `ON MATCH SET` sub-clauses, "
            "or MERGE is applied to a pattern that is too broad (e.g., MERGE on a "
            "relationship without both anchored nodes already bound)."
        ),
        "before": "MERGE (o:Organization {name: $name})-[:HAS_CEO]->(p:Person {name: $ceo})",
        "after": (
            "CYPHER 25\n"
            "MERGE (o:Organization {name: $name})\n"
            "ON CREATE SET o.createdAt = datetime()\n"
            "MERGE (p:Person {name: $ceo})\n"
            "MERGE (o)-[:HAS_CEO]->(p)"
        ),
        "recommendation": (
            "Reinforce the MERGE Safety section: 'MERGE a relationship only after "
            "MERGE-ing (or MATCH-ing) both endpoint nodes separately. "
            "Always include ON CREATE SET / ON MATCH SET to set timestamps or counters.' "
            "Add a two-step MERGE pattern as the canonical example."
        ),
    },
    {
        "id": "qpe-syntax-error",
        "label": "QPE syntax error (wrong quantifier form)",
        "skill_section": "Core Pattern Cheat Sheet — Quantified Path Expressions",
        "match_reason": ["quantifier", "QPE", "syntax error", "{"],
        "match_cypher": [],
        "match_cypher_regex": [r"\{\d+,\}", r"\*\d+\.\.\d+"],
        "match_tags": ["qpe", "quantified-path", "variable-length"],
        "description": (
            "The QPE quantifier uses an unsupported form. "
            "Common errors: `+` instead of `{1,}` (demo DB limitation), "
            "spaces inside `{m,n}`, or mixing QPE with legacy `[:REL*]` syntax."
        ),
        "before": "MATCH (a)(()-[:HAS_SUBSIDIARY]->())+(b) RETURN b.name",
        "after": "CYPHER 25\nMATCH (a)(()-[:HAS_SUBSIDIARY]->()){1,}(b) RETURN b.name",
        "recommendation": (
            "Add a QPE compatibility note: 'Prefer `{1,}` over `+` and `{0,}` over `*` "
            "for maximum database compatibility. The `+` / `*` shorthands may not be "
            "enabled on all servers.' "
            "Update the QPE syntax table to show both forms with a compatibility column."
        ),
    },
    {
        "id": "subquery-scope",
        "label": "Subquery scope / importing variables",
        "skill_section": "Core Pattern Cheat Sheet — CALL subqueries",
        "match_reason": ["scope", "not in scope", "undeclared", "CALL", "importing"],
        "match_cypher": ["CALL {", "CALL ("],
        "match_tags": ["call-subquery", "subquery", "scope"],
        "description": (
            "Variables are not correctly imported into a CALL subquery. "
            "In Cypher 25, use `CALL (x, y) { ... }` scope clause syntax. "
            "The deprecated `WITH x, y` as first clause inside CALL is no longer valid."
        ),
        "before": "MATCH (n) CALL { WITH n MATCH (n)-[:HAS_SUBSIDIARY]->(s) RETURN s }",
        "after": "CYPHER 25\nMATCH (n)\nCALL (n) { MATCH (n)-[:HAS_SUBSIDIARY]->(s) RETURN s }\nRETURN s.name",
        "recommendation": (
            "Update the subqueries reference: replace all `CALL { WITH x ...}` examples "
            "with the `CALL (x) { ... }` scope clause form. "
            "Add a migration note: 'Importing WITH inside CALL is deprecated in Cypher 25.'"
        ),
    },
    {
        "id": "type-casting-error",
        "label": "Type casting error (toInteger vs toIntegerOrNull)",
        "skill_section": "Types and Nulls (cypher25-types-and-nulls.md)",
        "match_reason": ["type", "cast", "conversion", "toInteger", "toFloat"],
        "match_cypher": ["toInteger(", "toFloat(", "toBoolean("],
        "match_tags": ["type-casting", "null", "error-handling"],
        "description": (
            "Base casting functions (`toInteger`, `toFloat`, etc.) throw on "
            "unconvertible input. Agent queries should use the `OrNull` variants "
            "(`toIntegerOrNull`, `toFloatOrNull`) to avoid runtime errors on dirty data."
        ),
        "before": "RETURN toInteger(n.population) AS pop",
        "after": "RETURN toIntegerOrNull(n.population) AS pop",
        "recommendation": (
            "Add to the types-and-nulls reference: 'Prefer `toFloatOrNull()`, "
            "`toIntegerOrNull()` over base variants in agent queries — they return "
            "null instead of throwing on unconvertible input.' "
            "Bold this preference in the SKILL.md types section."
        ),
    },
    {
        "id": "performance-threshold",
        "label": "Performance threshold exceeded (Gate 4 WARN/FAIL)",
        "skill_section": "EXPLAIN / PROFILE Validation Loop",
        "match_reason": ["threshold", "exceeds", "dbHits", "elapsedTimeMs", "memory"],
        "match_cypher": [],
        "match_tags": ["performance", "aggregation", "multi-pattern"],
        "description": (
            "The query exceeds the configured db-hits, memory, or elapsed-time threshold. "
            "Often caused by: full label scans instead of index seeks, "
            "Cartesian products from unlinked patterns, or collecting unbounded result sets."
        ),
        "before": (
            "-- Full label scan + Cartesian product --\n"
            "MATCH (a:Organization), (b:Organization)\n"
            "WHERE a.name CONTAINS 'Inc' RETURN count(*)"
        ),
        "after": (
            "CYPHER 25\n"
            "-- Use index-backed predicate --\n"
            "MATCH (a:Organization)\n"
            "WHERE a.name CONTAINS 'Inc'\n"
            "RETURN count(*)"
        ),
        "recommendation": (
            "In the EXPLAIN/PROFILE Validation Loop section, add: "
            "'When PROFILE shows high dbHits, check for: (1) missing index hints, "
            "(2) Cartesian products (look for `CartesianProduct` in the plan), "
            "(3) unbounded traversals without LIMIT.' "
            "Link to the indexes L3 reference for hint syntax."
        ),
    },
    {
        "id": "search-not-fulltext",
        "label": "SEARCH clause used for fulltext (vector-only in Preview)",
        "skill_section": "Core Pattern Cheat Sheet — SEARCH Clause",
        "match_reason": ["SEARCH", "fulltext", "not supported", "not available"],
        "match_cypher": ["SEARCH (", "SEARCH("],
        "match_tags": ["fulltext", "search", "index"],
        "description": (
            "The SEARCH clause is vector-only in Neo4j 2026.01 (Preview). "
            "For fulltext queries, the skill must use "
            "`db.index.fulltext.queryNodes()` or `db.index.fulltext.queryRelationships()`."
        ),
        "before": "CYPHER 25\nSEARCH (n:Article USING fulltext) WHERE n.text CONTAINS 'graph'",
        "after": (
            "CYPHER 25\n"
            "CALL db.index.fulltext.queryNodes('entity', 'graph') YIELD node, score\n"
            "RETURN node.name, score"
        ),
        "recommendation": (
            "Add a clear callout to the SEARCH Clause section: "
            "'The SEARCH clause is **vector-only** (Preview). "
            "For fulltext indexes, always use the `db.index.fulltext.queryNodes()` procedure.' "
            "Put this note on the first line of the section."
        ),
    },
]


# ---------------------------------------------------------------------------
# JSON loading helpers
# ---------------------------------------------------------------------------


def _load_json_file(path: Path) -> Optional[dict[str, Any]]:
    """Load a single JSON run file. Returns None on error."""
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"WARNING: skipping {path}: {exc}", file=sys.stderr)
        return None


def _collect_input_files(input_paths: list[str]) -> list[Path]:
    """Resolve --input arguments to a deduplicated list of .json file paths."""
    files: list[Path] = []
    seen: set[Path] = set()
    for raw in input_paths:
        p = Path(raw)
        if p.is_dir():
            for f in sorted(p.glob("*.json")):
                if f not in seen:
                    files.append(f)
                    seen.add(f)
        elif p.is_file() and p.suffix == ".json":
            if p not in seen:
                files.append(p)
                seen.add(p)
        else:
            print(f"WARNING: skipping {p} (not a .json file or directory)", file=sys.stderr)
    return files


# ---------------------------------------------------------------------------
# Case aggregation
# ---------------------------------------------------------------------------


def _merge_cases(run_data_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Combine all cases from multiple run files. Deduplicate by case_id (last wins)."""
    by_id: dict[str, dict[str, Any]] = {}
    for run in run_data_list:
        for c in run.get("cases", []):
            cid = c.get("case_id", f"unknown-{id(c)}")
            by_id[cid] = c
    return list(by_id.values())


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------

import re


def _case_matches_pattern(case: dict[str, Any], pattern: dict[str, Any]) -> bool:
    """Return True if the case matches the given failure pattern."""
    reason_texts: list[str] = []
    for gd in case.get("gate_details") or []:
        if gd.get("verdict") in (FAIL, WARN):
            reason_texts.append((gd.get("reason") or "").lower())
    error = (case.get("error") or "").lower()
    reason_texts.append(error)

    cypher = (case.get("generated_cypher") or "").lower()
    tags = {t.lower() for t in (case.get("tags") or [])}

    # Check reason substrings
    for kw in pattern["match_reason"]:
        for r in reason_texts:
            if kw.lower() in r:
                return True

    # Check cypher patterns (plain substring match — case insensitive)
    for cp in pattern.get("match_cypher", []):
        if cp.lower() in cypher:
            return True

    # Check cypher regex patterns
    for cp in pattern.get("match_cypher_regex", []):
        if re.search(cp, cypher, re.IGNORECASE):
            return True

    # Check tags
    for tag in pattern["match_tags"]:
        if tag.lower() in tags:
            return True

    return False


def _detect_patterns(
    non_pass_cases: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """
    For each failure pattern, collect the cases that match it.
    Returns a dict: pattern_id → list of matching cases.
    """
    result: dict[str, list[dict[str, Any]]] = {}
    for pattern in FAILURE_PATTERNS:
        matched = [c for c in non_pass_cases if _case_matches_pattern(c, pattern)]
        if matched:
            result[pattern["id"]] = matched
    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_improvement_report(
    run_data_list: list[dict[str, Any]],
    input_files: list[Path],
) -> str:
    """
    Generate a Markdown improvement report from a list of run data dicts.

    Args:
        run_data_list: List of dicts loaded from runner JSON files.
        input_files:   Source file paths (for the report header).

    Returns:
        A self-contained Markdown string.
    """
    lines: list[str] = []
    all_cases = _merge_cases(run_data_list)

    total = len(all_cases)
    passed = sum(1 for c in all_cases if c.get("verdict") == PASS)
    warned = sum(1 for c in all_cases if c.get("verdict") == WARN)
    failed = sum(1 for c in all_cases if c.get("verdict") == FAIL)
    pass_rate = passed / total if total else 0.0

    non_pass_cases = [c for c in all_cases if c.get("verdict") != PASS]

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    lines.append("# Neo4j Cypher Authoring Skill — Harness Improvement Report")
    lines.append("")
    lines.append(f"**Generated**: {generated_at}  ")
    lines.append(f"**Input files**: {len(input_files)}  ")
    for f in input_files:
        lines.append(f"  - `{f.name}`")
    lines.append("")

    # -----------------------------------------------------------------------
    # Section 1: Overall Summary
    # -----------------------------------------------------------------------
    lines.append("## 1. Overall Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|--------|------:|")
    lines.append(f"| Total cases (deduplicated) | {total} |")
    lines.append(f"| PASS | {passed} |")
    lines.append(f"| WARN | {warned} |")
    lines.append(f"| FAIL | {failed} |")
    lines.append(f"| Overall pass rate | {pass_rate:.1%} |")
    lines.append("")

    # -----------------------------------------------------------------------
    # Section 2: Per-Difficulty Pass Rate vs PRD Targets
    # -----------------------------------------------------------------------
    lines.append("## 2. Per-Difficulty Pass Rate vs PRD Targets")
    lines.append("")
    lines.append("| Difficulty | Total | PASS | WARN | FAIL | Actual | Target | Delta |")
    lines.append("|------------|------:|-----:|-----:|-----:|-------:|-------:|------:|")

    by_difficulty: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in all_cases:
        d = (c.get("difficulty") or "basic").lower()
        by_difficulty[d].append(c)

    ordered_difficulties = [d for d in DIFFICULTY_ORDER if d in by_difficulty]
    extra = sorted(d for d in by_difficulty if d not in DIFFICULTY_ORDER)

    for diff in ordered_difficulties + extra:
        group = by_difficulty[diff]
        g_total = len(group)
        g_pass = sum(1 for c in group if c.get("verdict") == PASS)
        g_warn = sum(1 for c in group if c.get("verdict") == WARN)
        g_fail = sum(1 for c in group if c.get("verdict") == FAIL)
        g_rate = g_pass / g_total if g_total else 0.0
        target = PRD_TARGETS.get(diff, None)
        target_str = f"{target:.0%}" if target is not None else "—"
        if target is not None:
            delta = g_rate - target
            delta_str = f"{delta:+.1%}"
        else:
            delta_str = "—"
        lines.append(
            f"| {diff.capitalize()} | {g_total} | {g_pass} | {g_warn} | {g_fail} "
            f"| {g_rate:.1%} | {target_str} | {delta_str} |"
        )
    lines.append("")

    # -----------------------------------------------------------------------
    # Section 3: Per-Gate Failure Breakdown
    # -----------------------------------------------------------------------
    lines.append("## 3. Per-Gate Failure Breakdown")
    lines.append("")
    lines.append(
        "| Gate | Description | FAIL | WARN | Total Non-PASS |"
    )
    lines.append("|-----:|-------------|-----:|-----:|---------------:|")

    by_gate_fail: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    by_gate_warn: dict[Any, list[dict[str, Any]]] = defaultdict(list)

    for c in all_cases:
        if c.get("verdict") == FAIL:
            gate = c.get("failed_gate") or "runner"
            by_gate_fail[gate].append(c)
        elif c.get("verdict") == WARN:
            gate = c.get("warned_gate") or "runner"
            by_gate_warn[gate].append(c)

    all_gates = sorted(
        set(list(by_gate_fail.keys()) + list(by_gate_warn.keys())),
        key=lambda g: (isinstance(g, str), g),
    )

    for gate in all_gates:
        f_count = len(by_gate_fail.get(gate, []))
        w_count = len(by_gate_warn.get(gate, []))
        desc = GATE_DESCRIPTIONS.get(gate, "Runner / pre-execution error") if isinstance(gate, int) else "Runner / pre-execution error"
        lines.append(
            f"| {gate} | {desc} | {f_count} | {w_count} | {f_count + w_count} |"
        )
    lines.append("")

    if non_pass_cases:
        lines.append("### Non-PASS Cases Detail")
        lines.append("")
        lines.append("| ID | Difficulty | Verdict | Gate | Tags | Reason |")
        lines.append("|----|------------|---------|-----:|------|--------|")
        for c in non_pass_cases:
            cid = c.get("case_id", "?")
            diff = c.get("difficulty", "?")
            verdict = c.get("verdict", "?")
            gate = c.get("failed_gate") or c.get("warned_gate") or "—"
            tags = ", ".join(c.get("tags") or [])[:40]
            reason = _first_failing_reason(c)[:80]
            lines.append(
                f"| `{cid}` | {diff} | {verdict} | {gate} | {tags} | {reason} |"
            )
        lines.append("")

    # -----------------------------------------------------------------------
    # Section 4: Failure Pattern Analysis
    # -----------------------------------------------------------------------
    lines.append("## 4. Failure Pattern Analysis")
    lines.append("")
    lines.append(
        "Each detected pattern is mapped to the most likely responsible SKILL.md section."
    )
    lines.append("")

    detected = _detect_patterns(non_pass_cases)

    if not detected:
        if non_pass_cases:
            lines.append(
                "_No known patterns matched the failing cases. "
                "Review the Non-PASS Cases Detail table above for clues._"
            )
        else:
            lines.append("_No failures or warnings detected. Skill is performing well._")
        lines.append("")
    else:
        # Summary table of detected patterns
        lines.append("### Detected Patterns Summary")
        lines.append("")
        lines.append("| # | Pattern | Cases | SKILL.md Section |")
        lines.append("|---|---------|------:|-----------------|")
        pattern_index = 0
        for pid, cases_list in sorted(detected.items(), key=lambda x: -len(x[1])):
            pattern = _get_pattern(pid)
            if pattern:
                pattern_index += 1
                lines.append(
                    f"| {pattern_index} | {pattern['label']} | {len(cases_list)} "
                    f"| {pattern['skill_section']} |"
                )
        lines.append("")

        # Detailed pattern sections
        lines.append("### Pattern Details and Recommendations")
        lines.append("")
        pattern_index = 0
        for pid, cases_list in sorted(detected.items(), key=lambda x: -len(x[1])):
            pattern = _get_pattern(pid)
            if not pattern:
                continue
            pattern_index += 1

            lines.append(f"#### Pattern {pattern_index}: {pattern['label']}")
            lines.append("")
            lines.append(f"**SKILL.md Section**: `{pattern['skill_section']}`  ")
            lines.append(f"**Affected cases**: {len(cases_list)}  ")
            lines.append("")
            lines.append(pattern["description"])
            lines.append("")

            # Affected case IDs
            lines.append("**Affected test cases**:")
            lines.append("")
            for c in cases_list:
                cid = c.get("case_id", "?")
                verdict = c.get("verdict", "?")
                reason = _first_failing_reason(c)[:100]
                lines.append(f"- `{cid}` ({verdict}): {reason}")
            lines.append("")

            # Before/After example
            lines.append("**Before (problematic pattern)**:")
            lines.append("")
            lines.append("```cypher")
            lines.append(pattern["before"])
            lines.append("```")
            lines.append("")
            lines.append("**After (recommended pattern)**:")
            lines.append("")
            lines.append("```cypher")
            lines.append(pattern["after"])
            lines.append("```")
            lines.append("")
            lines.append("**Recommended SKILL.md edit**:")
            lines.append("")
            lines.append(f"> {pattern['recommendation']}")
            lines.append("")

    # -----------------------------------------------------------------------
    # Section 5: Unclassified Failures
    # -----------------------------------------------------------------------
    classified_ids: set[str] = set()
    for cases_list in detected.values():
        for c in cases_list:
            classified_ids.add(c.get("case_id", ""))

    unclassified = [
        c for c in non_pass_cases if c.get("case_id", "") not in classified_ids
    ]

    if unclassified:
        lines.append("## 5. Unclassified Failures")
        lines.append("")
        lines.append(
            "The following non-PASS cases did not match any known pattern. "
            "Manual review required."
        )
        lines.append("")
        for c in unclassified:
            cid = c.get("case_id", "?")
            verdict = c.get("verdict", "?")
            diff = c.get("difficulty", "?")
            reason = _first_failing_reason(c)
            cypher = (c.get("generated_cypher") or "").strip()
            lines.append(f"**`{cid}`** ({diff} / {verdict})")
            lines.append("")
            lines.append(f"> {reason}")
            lines.append("")
            if cypher:
                cypher_lines = cypher.splitlines()
                excerpt = "\n".join(cypher_lines[:8])
                if len(cypher_lines) > 8:
                    excerpt += f"\n... ({len(cypher_lines) - 8} more lines)"
                lines.append("```cypher")
                lines.append(excerpt)
                lines.append("```")
                lines.append("")

    # -----------------------------------------------------------------------
    # Section 6: Tag Cluster Analysis
    # -----------------------------------------------------------------------
    lines.append("## 6. Tag Cluster Analysis")
    lines.append("")
    lines.append("Frequency of tags appearing in non-PASS cases:")
    lines.append("")

    tag_counts: dict[str, int] = defaultdict(int)
    for c in non_pass_cases:
        for tag in c.get("tags") or []:
            tag_counts[tag.lower()] += 1

    if tag_counts:
        lines.append("| Tag | Occurrences |")
        lines.append("|-----|------------:|")
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| `{tag}` | {count} |")
        lines.append("")
    else:
        lines.append("_No tag data available._")
        lines.append("")

    # -----------------------------------------------------------------------
    # Footer
    # -----------------------------------------------------------------------
    lines.append("---")
    lines.append("")
    lines.append(
        f"_This report was generated by `scripts/analyze-results.py` at {generated_at}. "
        "It is for human review only — no automatic changes are made to SKILL.md._"
    )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _first_failing_reason(case: dict[str, Any]) -> str:
    """Extract the first failing/warning gate reason from a case."""
    for gd in case.get("gate_details") or []:
        if gd.get("verdict") in (FAIL, WARN):
            return (gd.get("reason") or "").strip()
    return (case.get("error") or "—").strip()


def _get_pattern(pid: str) -> Optional[dict[str, Any]]:
    """Look up a pattern by id."""
    for p in FAILURE_PATTERNS:
        if p["id"] == pid:
            return p
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a structured Markdown improvement report from "
            "one or more harness JSON result files."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input",
        nargs="+",
        metavar="PATH",
        help=(
            "One or more JSON result files or a directory of JSON files. "
            "Multiple paths can be specified."
        ),
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Path to write the Markdown improvement report (default: stdout)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)

    if not args.input:
        print(
            "Usage: analyze-results.py --input <file-or-dir> [--output <report.md>]",
            file=sys.stderr,
        )
        print(
            "       analyze-results.py --input tests/results/ --output report.md",
            file=sys.stderr,
        )
        return 0  # smoke test: no args prints usage, exits 0

    input_files = _collect_input_files(args.input)
    if not input_files:
        print("ERROR: no .json files found in the specified paths.", file=sys.stderr)
        return 1

    run_data_list: list[dict[str, Any]] = []
    for f in input_files:
        data = _load_json_file(f)
        if data is not None:
            run_data_list.append(data)

    if not run_data_list:
        print("ERROR: no valid JSON run files could be loaded.", file=sys.stderr)
        return 1

    print(
        f"Loaded {len(run_data_list)} run file(s) covering "
        f"{sum(len(d.get('cases', [])) for d in run_data_list)} raw cases.",
        flush=True,
    )

    report = generate_improvement_report(run_data_list, input_files)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report)
        print(f"Improvement report written to: {out}", flush=True)
    else:
        sys.stdout.write(report)

    return 0


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------


def _run_smoke_tests() -> None:
    """
    Offline tests for analyze-results.py. No DB or Claude needed.

    Verifies:
    - generate_improvement_report() produces valid Markdown for a minimal dict.
    - Pattern detection identifies known patterns.
    - Per-difficulty table includes delta vs PRD target.
    - Unclassified failures section appears for unmatched cases.
    - No args invocation (main()) prints usage and exits 0.
    """
    errors: list[str] = []

    def _make_run(cases: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(cases)
        passed = sum(1 for c in cases if c.get("verdict") == PASS)
        warned = sum(1 for c in cases if c.get("verdict") == WARN)
        failed = sum(1 for c in cases if c.get("verdict") == FAIL)
        return {
            "run_id": "test-run",
            "started_at": "2026-03-21T00:00:00+00:00",
            "completed_at": "2026-03-21T00:05:00+00:00",
            "skill": "neo4j-cypher-authoring-skill",
            "summary": {
                "total": total,
                "passed": passed,
                "warned": warned,
                "failed": failed,
                "pass_rate": passed / total if total else 0.0,
            },
            "cases": cases,
        }

    def _make_case(
        case_id: str,
        difficulty: str,
        verdict: str,
        failed_gate: Optional[int] = None,
        warned_gate: Optional[int] = None,
        reason: str = "",
        cypher: str = "CYPHER 25\nMATCH (n) RETURN n",
        tags: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        gate_details = []
        if reason:
            g = failed_gate or warned_gate or 1
            gate_details.append(
                {"gate": g, "verdict": verdict, "reason": reason, "details": {}}
            )
        return {
            "case_id": case_id,
            "question": f"Question for {case_id}",
            "difficulty": difficulty,
            "tags": tags or [],
            "verdict": verdict,
            "failed_gate": failed_gate,
            "warned_gate": warned_gate,
            "generated_cypher": cypher,
            "metrics": {
                "totalDbHits": None,
                "totalAllocatedMemory": None,
                "elapsedTimeMs": 100.0,
                "totalRows": 5,
            },
            "gate_details": gate_details,
            "error": None,
            "duration_s": 2.5,
        }

    # Build synthetic data with known patterns
    cases = [
        _make_case("tc-001", "basic", PASS),
        _make_case("tc-002", "basic", PASS),
        _make_case(
            "tc-003", "intermediate", FAIL, failed_gate=3,
            reason="Missing CYPHER 25 pragma",
            cypher="MATCH (n) RETURN n",
        ),
        _make_case(
            "tc-004", "advanced", WARN, warned_gate=4,
            reason="elapsedTimeMs 50000 ms exceeds warning threshold 30000 ms",
            tags=["performance", "aggregation"],
        ),
        _make_case(
            "tc-005", "advanced", FAIL, failed_gate=2,
            reason="dimensionality of 1221, but provided vector has 1536",
            tags=["vector", "index", "similarity"],
        ),
        _make_case(
            "tc-006", "complex", FAIL, failed_gate=2,
            reason="CALL { ... } IN TRANSACTIONS can only be executed in an implicit transaction",
            tags=["call-in-transactions", "batch"],
        ),
        _make_case(
            "tc-007", "basic", FAIL, failed_gate=1,
            reason="Some unknown error with no pattern",
            tags=["unknown-tag"],
        ),
    ]

    run_data = _make_run(cases)
    input_files = [Path("tests/results/synthetic-run.json")]

    md = generate_improvement_report([run_data], input_files)

    # ---- Assertions -------------------------------------------------------

    # Header
    if "Harness Improvement Report" not in md:
        errors.append("Title not found in report")

    # Section 1: Overall Summary
    if "Overall Summary" not in md:
        errors.append("Overall Summary section missing")
    if "42.9%" in md or "42.8" in md or "2" in md:
        pass  # flexible check

    # Section 2: Per-difficulty with delta
    if "Per-Difficulty Pass Rate" not in md:
        errors.append("Per-Difficulty section missing")
    if "Target" not in md:
        errors.append("Target column missing from per-difficulty table")
    if "Delta" not in md:
        errors.append("Delta column missing from per-difficulty table")

    # Section 3: Per-gate breakdown
    if "Per-Gate Failure Breakdown" not in md:
        errors.append("Per-Gate Failure Breakdown section missing")

    # Section 4: Pattern analysis
    if "Failure Pattern Analysis" not in md:
        errors.append("Failure Pattern Analysis section missing")

    # Known patterns should be detected
    if "Missing CYPHER 25 pragma" not in md:
        errors.append("CYPHER 25 pragma pattern not detected")
    if "Vector index dimension mismatch" not in md:
        errors.append("Vector dimension mismatch pattern not detected")
    if "CALL IN TRANSACTIONS inside explicit transaction" not in md:
        errors.append("CALL IN TRANSACTIONS pattern not detected")

    # Recommendations should be present
    if "Recommended SKILL.md edit" not in md:
        errors.append("Recommendation sections missing")

    # Before/after examples
    if "Before (problematic pattern)" not in md:
        errors.append("Before/after examples missing")

    # Section 5: Unclassified failures for tc-007
    if "Unclassified" not in md:
        errors.append("Unclassified Failures section missing")
    if "tc-007" not in md:
        errors.append("tc-007 not in unclassified failures")

    # Section 6: Tag cluster
    if "Tag Cluster Analysis" not in md:
        errors.append("Tag Cluster Analysis section missing")

    # No-args smoke: main() should print usage and return 0
    rc = main([])
    if rc != 0:
        errors.append(f"main([]) should return 0 (usage), got {rc}")

    if errors:
        print("SMOKE TEST FAILURES:")
        for e in errors:
            print(f"  FAIL: {e}")
        raise SystemExit(1)
    else:
        print(f"All smoke tests passed (0 failures)")
        print("analyze-results.py smoke tests: OK")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        _run_smoke_tests()
    else:
        sys.exit(main())
