#!/usr/bin/env python3
"""
reporter.py — Markdown report generator for the neo4j-cypher-authoring-skill
test harness.

Reads a runner JSON output file (produced by runner.py) and writes a
self-contained Markdown report that includes:

  - Overall pass/warn/fail counts and pass rate
  - Per-difficulty pass rate table
  - Full results table (verdict + key metrics per test case)
  - db-hits summary statistics (min/median/max) per difficulty
  - Failure analysis section grouped by gate with query excerpts

Usage:
    uv run python3 tests/harness/reporter.py \\
        --input  tests/results/run-20260320T120000.json \\
        --output tests/results/run-20260320T120000.md

Or import and call generate_report() directly from runner.py.
"""

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Verdict constants (mirrored from validator.py — no import to stay standalone)
# ---------------------------------------------------------------------------

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

DIFFICULTY_ORDER = ["basic", "intermediate", "advanced", "complex"]


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(report_data: dict[str, Any]) -> str:
    """
    Generate a Markdown report from a runner JSON report dict.

    Args:
        report_data: dict as produced by runner.report_to_dict() and loaded
                     from the JSON file written by runner.write_report().

    Returns:
        A self-contained Markdown string.
    """
    lines: list[str] = []

    run_id = report_data.get("run_id", "unknown")
    skill = report_data.get("skill", "unknown")
    started_at = report_data.get("started_at", "")
    completed_at = report_data.get("completed_at", "")
    summary = report_data.get("summary", {})
    cases = report_data.get("cases", [])

    total = summary.get("total", len(cases))
    passed = summary.get("passed", 0)
    warned = summary.get("warned", 0)
    failed = summary.get("failed", 0)
    pass_rate = summary.get(
        "pass_rate", (passed / total) if total else 0.0
    )

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    lines.append(f"# Cypher Skill Test Report — `{run_id}`")
    lines.append("")
    lines.append(f"**Skill**: `{skill}`  ")
    lines.append(f"**Started**: {_fmt_ts(started_at)}  ")
    lines.append(f"**Completed**: {_fmt_ts(completed_at)}  ")
    lines.append("")

    # -----------------------------------------------------------------------
    # Overall summary
    # -----------------------------------------------------------------------
    lines.append("## Overall Results")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total cases | {total} |")
    lines.append(f"| PASS | {passed} |")
    lines.append(f"| WARN | {warned} |")
    lines.append(f"| FAIL | {failed} |")
    lines.append(f"| Pass rate | {pass_rate:.1%} |")
    lines.append("")

    # -----------------------------------------------------------------------
    # Per-difficulty breakdown
    # -----------------------------------------------------------------------
    by_difficulty: dict[str, list[dict[str, Any]]] = {}
    for c in cases:
        d = c.get("difficulty", "basic")
        by_difficulty.setdefault(d, []).append(c)

    if by_difficulty:
        lines.append("## Per-Difficulty Pass Rates")
        lines.append("")
        lines.append("| Difficulty | Total | PASS | WARN | FAIL | Pass Rate |")
        lines.append("|------------|------:|-----:|-----:|-----:|----------:|")

        for diff in DIFFICULTY_ORDER:
            if diff not in by_difficulty:
                continue
            group = by_difficulty[diff]
            g_total = len(group)
            g_pass = sum(1 for c in group if c.get("verdict") == PASS)
            g_warn = sum(1 for c in group if c.get("verdict") == WARN)
            g_fail = sum(1 for c in group if c.get("verdict") == FAIL)
            g_rate = g_pass / g_total if g_total else 0.0
            lines.append(
                f"| {diff.capitalize()} | {g_total} | {g_pass} | {g_warn} | {g_fail} | {g_rate:.1%} |"
            )

        # Also show any unlisted difficulty levels
        for diff, group in sorted(by_difficulty.items()):
            if diff in DIFFICULTY_ORDER:
                continue
            g_total = len(group)
            g_pass = sum(1 for c in group if c.get("verdict") == PASS)
            g_warn = sum(1 for c in group if c.get("verdict") == WARN)
            g_fail = sum(1 for c in group if c.get("verdict") == FAIL)
            g_rate = g_pass / g_total if g_total else 0.0
            lines.append(
                f"| {diff.capitalize()} | {g_total} | {g_pass} | {g_warn} | {g_fail} | {g_rate:.1%} |"
            )
        lines.append("")

    # -----------------------------------------------------------------------
    # DB-hits summary statistics per difficulty
    # -----------------------------------------------------------------------
    lines.append("## DB-Hits Summary (per Difficulty)")
    lines.append("")
    lines.append("Only cases that completed Gate 4 (PROFILE) are included.")
    lines.append("")
    lines.append("| Difficulty | n | Min | Median | Max |")
    lines.append("|------------|--:|----:|-------:|----:|")

    any_db_hits = False
    for diff in DIFFICULTY_ORDER + [
        d for d in sorted(by_difficulty) if d not in DIFFICULTY_ORDER
    ]:
        if diff not in by_difficulty:
            continue
        group = by_difficulty[diff]
        db_hits_values = [
            c["metrics"]["totalDbHits"]
            for c in group
            if (c.get("metrics") or {}).get("totalDbHits") is not None
        ]
        if not db_hits_values:
            continue
        any_db_hits = True
        n = len(db_hits_values)
        mn = min(db_hits_values)
        mx = max(db_hits_values)
        med = statistics.median(db_hits_values)
        lines.append(
            f"| {diff.capitalize()} | {n} | {mn:,} | {med:,.0f} | {mx:,} |"
        )

    if not any_db_hits:
        lines.append("| — | — | — | — | — |")
    lines.append("")

    # -----------------------------------------------------------------------
    # Full results table
    # -----------------------------------------------------------------------
    lines.append("## Test Case Results")
    lines.append("")
    lines.append("| ID | Difficulty | Verdict | Gate | DB Hits | Duration (s) | Question |")
    lines.append("|----|------------|---------|-----:|--------:|-------------:|----------|")

    for c in cases:
        case_id = c.get("case_id", "?")
        diff = c.get("difficulty", "?")
        verdict = c.get("verdict", "?")
        failed_gate = c.get("failed_gate") or c.get("warned_gate") or "—"
        db_hits = (c.get("metrics") or {}).get("totalDbHits")
        db_hits_str = f"{db_hits:,}" if db_hits is not None else "—"
        duration = c.get("duration_s")
        duration_str = f"{duration:.1f}" if duration is not None else "—"
        question = _truncate(c.get("question", ""), 60)

        # Emoji-free verdict marker
        verdict_badge = {"PASS": "PASS", "WARN": "WARN", "FAIL": "**FAIL**"}.get(
            verdict, verdict
        )

        lines.append(
            f"| `{case_id}` | {diff} | {verdict_badge} | {failed_gate} | {db_hits_str} | {duration_str} | {question} |"
        )

    lines.append("")

    # -----------------------------------------------------------------------
    # Failure analysis section
    # -----------------------------------------------------------------------
    failed_cases = [c for c in cases if c.get("verdict") == FAIL]
    warned_cases = [c for c in cases if c.get("verdict") == WARN]

    if failed_cases or warned_cases:
        lines.append("## Failure Analysis")
        lines.append("")

    if failed_cases:
        lines.append(f"### FAIL ({len(failed_cases)} cases)")
        lines.append("")
        # Group by gate
        by_gate: dict[Any, list[dict[str, Any]]] = {}
        for c in failed_cases:
            gate = c.get("failed_gate") or "unknown"
            by_gate.setdefault(gate, []).append(c)

        for gate in sorted(by_gate.keys(), key=lambda g: (str(g) == "unknown", g)):
            gate_cases = by_gate[gate]
            gate_label = f"Gate {gate}" if gate != "unknown" else "No gate (runner error)"
            lines.append(f"#### {gate_label} ({len(gate_cases)} case(s))")
            lines.append("")
            for c in gate_cases:
                lines.append(_format_case_detail(c))
            lines.append("")

    if warned_cases:
        lines.append(f"### WARN ({len(warned_cases)} cases)")
        lines.append("")
        # Group by warned gate
        by_gate_w: dict[Any, list[dict[str, Any]]] = {}
        for c in warned_cases:
            gate = c.get("warned_gate") or "unknown"
            by_gate_w.setdefault(gate, []).append(c)

        for gate in sorted(by_gate_w.keys(), key=lambda g: (str(g) == "unknown", g)):
            gate_cases = by_gate_w[gate]
            gate_label = f"Gate {gate}" if gate != "unknown" else "No gate"
            lines.append(f"#### {gate_label} ({len(gate_cases)} case(s))")
            lines.append("")
            for c in gate_cases:
                lines.append(_format_case_detail(c))
            lines.append("")

    if not failed_cases and not warned_cases:
        lines.append("## Failure Analysis")
        lines.append("")
        lines.append("_No failures or warnings._")
        lines.append("")

    # -----------------------------------------------------------------------
    # Footer
    # -----------------------------------------------------------------------
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines.append("---")
    lines.append("")
    lines.append(f"_Report generated {generated_at} by `tests/harness/reporter.py`_")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helper formatters
# ---------------------------------------------------------------------------


def _fmt_ts(ts: str) -> str:
    """Format an ISO-8601 timestamp for display; return as-is on failure."""
    if not ts:
        return "—"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except ValueError:
        return ts


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with an ellipsis if longer than max_len."""
    text = text.replace("|", "\\|").replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _format_case_detail(c: dict[str, Any]) -> str:
    """Format a single failed/warned case as a Markdown block."""
    case_id = c.get("case_id", "?")
    question = c.get("question", "")
    cypher = c.get("generated_cypher", "")
    error = c.get("error")
    gate_details = c.get("gate_details") or []
    metrics = c.get("metrics") or {}

    parts: list[str] = []
    parts.append(f"**`{case_id}`** — {question}")
    parts.append("")

    # Runner-level error (Claude invocation failed, no Cypher extracted, etc.)
    if error:
        parts.append(f"> **Runner error**: {error}")
        parts.append("")

    # Gate reasons
    failing_gates = [
        g for g in gate_details if g.get("verdict") in (FAIL, WARN)
    ]
    for g in failing_gates:
        verdict = g.get("verdict", "?")
        gate_num = g.get("gate", "?")
        reason = g.get("reason", "")
        parts.append(f"> **Gate {gate_num} {verdict}**: {reason}")

    if failing_gates:
        parts.append("")

    # Generated Cypher (excerpt — first 10 lines max)
    if cypher:
        cypher_lines = cypher.splitlines()
        excerpt = "\n".join(cypher_lines[:10])
        if len(cypher_lines) > 10:
            excerpt += f"\n... ({len(cypher_lines) - 10} more lines)"
        parts.append("```cypher")
        parts.append(excerpt)
        parts.append("```")
        parts.append("")

    # Metrics summary (only if present)
    if any(v is not None for v in metrics.values()):
        db_hits = metrics.get("totalDbHits")
        mem = metrics.get("totalAllocatedMemory")
        elapsed = metrics.get("elapsedTimeMs")
        rows = metrics.get("totalRows")
        metric_parts = []
        if db_hits is not None:
            metric_parts.append(f"dbHits={db_hits:,}")
        if rows is not None:
            metric_parts.append(f"rows={rows:,}")
        if mem is not None:
            metric_parts.append(f"memory={mem / 1_048_576:.1f} MB")
        if elapsed is not None:
            metric_parts.append(f"elapsed={elapsed:.0f} ms")
        if metric_parts:
            parts.append(f"_Metrics_: {', '.join(metric_parts)}")
            parts.append("")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def report_from_file(input_path: Path) -> str:
    """Load a JSON run report from disk and return a Markdown string."""
    with open(input_path) as f:
        data = json.load(f)
    return generate_report(data)


def write_markdown_report(input_path: Path, output_path: Path) -> None:
    """Read JSON run report, generate Markdown, write to output_path."""
    md = report_from_file(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(md)
    print(f"Markdown report written to: {output_path}", flush=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown test report from a runner JSON output file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the runner JSON output file",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write the Markdown report",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        write_markdown_report(input_path, output_path)
    except json.JSONDecodeError as exc:
        print(f"ERROR: failed to parse JSON input: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------


def _run_smoke_tests() -> None:
    """
    Run offline unit tests for the reporter module. No DB required.

    Verifies:
    - generate_report() produces valid Markdown for a minimal report dict.
    - Per-difficulty table is correct.
    - DB-hits median is computed correctly.
    - Failure analysis section appears for FAIL cases and absent for all-PASS.
    - _truncate() works.
    - _fmt_ts() handles ISO-8601 and empty strings.
    """
    errors: list[str] = []

    # ---- Build a minimal synthetic report --------------------------------
    def _make_case(
        case_id: str,
        difficulty: str,
        verdict: str,
        failed_gate: Optional[int] = None,
        warned_gate: Optional[int] = None,
        db_hits: Optional[int] = None,
        duration: float = 1.5,
        question: str = "Find all nodes",
        cypher: str = "CYPHER 25\nMATCH (n) RETURN n",
        gate_reason: str = "",
    ) -> dict[str, Any]:
        gate_details = []
        if gate_reason:
            gate_details.append({
                "gate": failed_gate or warned_gate or 1,
                "verdict": verdict,
                "reason": gate_reason,
                "details": {},
            })
        return {
            "case_id": case_id,
            "question": question,
            "difficulty": difficulty,
            "tags": [],
            "verdict": verdict,
            "failed_gate": failed_gate,
            "warned_gate": warned_gate,
            "generated_cypher": cypher,
            "metrics": {
                "totalDbHits": db_hits,
                "totalAllocatedMemory": None,
                "elapsedTimeMs": 42.5,
                "totalRows": 10,
            },
            "gate_details": gate_details,
            "error": None,
            "duration_s": duration,
        }

    report_data: dict[str, Any] = {
        "run_id": "run-20260320T120000",
        "started_at": "2026-03-20T12:00:00+00:00",
        "completed_at": "2026-03-20T12:05:30+00:00",
        "skill": "neo4j-cypher-authoring-skill",
        "summary": {
            "total": 5,
            "passed": 3,
            "warned": 1,
            "failed": 1,
            "pass_rate": 0.6,
        },
        "cases": [
            _make_case("tc-001", "basic", PASS, db_hits=100),
            _make_case("tc-002", "basic", PASS, db_hits=200),
            _make_case("tc-003", "intermediate", PASS, db_hits=500),
            _make_case(
                "tc-004", "intermediate", WARN, warned_gate=3,
                db_hits=800, gate_reason="Missing CYPHER 25 pragma",
            ),
            _make_case(
                "tc-005", "advanced", FAIL, failed_gate=1,
                db_hits=None, gate_reason="Syntax error: unexpected token",
            ),
        ],
    }

    md = generate_report(report_data)

    # ---- Assertions -------------------------------------------------------

    # Header
    if "run-20260320T120000" not in md:
        errors.append("run_id not in report header")

    # Overall summary
    if "Pass rate" not in md:
        errors.append("'Pass rate' not in overall summary")
    if "60.0%" not in md:
        errors.append("Pass rate 60.0% not in report")

    # Per-difficulty
    if "Per-Difficulty Pass Rates" not in md:
        errors.append("Per-Difficulty section missing")
    if "Basic" not in md:
        errors.append("'Basic' difficulty row missing")
    if "Intermediate" not in md:
        errors.append("'Intermediate' difficulty row missing")
    if "Advanced" not in md:
        errors.append("'Advanced' difficulty row missing")

    # DB-hits summary — basic median should be 150 (median of [100, 200])
    if "150" not in md:
        errors.append("Median db_hits for basic (150) not found in report")

    # Results table
    if "Test Case Results" not in md:
        errors.append("Test Case Results section missing")
    if "tc-001" not in md:
        errors.append("tc-001 not in results table")
    if "**FAIL**" not in md:
        errors.append("FAIL badge not formatted correctly")

    # Failure analysis
    if "Failure Analysis" not in md:
        errors.append("Failure Analysis section missing")
    if "Gate 1" not in md:
        errors.append("Gate 1 failure group not in Failure Analysis")
    if "Syntax error" not in md:
        errors.append("Gate reason not in failure detail block")
    if "Gate 3" not in md:
        errors.append("Gate 3 warn group not in Failure Analysis")

    # Cypher excerpt
    if "MATCH (n) RETURN n" not in md:
        errors.append("Generated Cypher excerpt missing from failure detail")

    # All-PASS report should say "No failures"
    all_pass_data = {
        "run_id": "run-allpass",
        "started_at": "",
        "completed_at": "",
        "skill": "test",
        "summary": {"total": 1, "passed": 1, "warned": 0, "failed": 0, "pass_rate": 1.0},
        "cases": [_make_case("tc-x", "basic", PASS, db_hits=50)],
    }
    md_pass = generate_report(all_pass_data)
    if "No failures or warnings" not in md_pass:
        errors.append("All-PASS report should say 'No failures or warnings'")

    # _truncate
    assert _truncate("hello world", 5) == "hell…", "_truncate short failed"
    assert _truncate("hi", 10) == "hi", "_truncate no-op failed"
    assert _truncate("a|b", 10) == "a\\|b", "_truncate pipe escape failed"

    # _fmt_ts
    assert "2026" in _fmt_ts("2026-03-20T12:00:00+00:00"), "_fmt_ts year missing"
    assert _fmt_ts("") == "—", "_fmt_ts empty not '—'"

    if errors:
        print("SMOKE TEST FAILURES:")
        for e in errors:
            print(f"  FAIL: {e}")
        raise SystemExit(1)
    else:
        print(f"All smoke tests passed ({len(errors)} failures)")
        print("reporter.py smoke tests: OK")


if __name__ == "__main__":
    # When run directly, execute smoke tests
    if len(sys.argv) == 1:
        _run_smoke_tests()
    else:
        sys.exit(main())
