#!/usr/bin/env python3
"""
audit_questions.py — Post-hoc question language audit for domain YAML files.

Reads one or more domain YAML files from tests/cases/ and runs every question
through the QuestionValidator to find questions that contain Cypher keywords,
graph labels, relationship types, dot-access syntax, or other non-business-
language patterns.

Output is a Markdown report listing violations per domain with the case ID,
question text, and reason for rejection.

Usage:
    uv run --project skill-generation-validation-tools python3 \\
        skill-generation-validation-tools/scripts/audit_questions.py \\
        --cases skill-generation-validation-tools/tests/cases/ \\
        --output audit-report.md

    # Single domain
    uv run --project skill-generation-validation-tools python3 \\
        skill-generation-validation-tools/scripts/audit_questions.py \\
        --cases skill-generation-validation-tools/tests/cases/companies.yml

Makefile target:
    make audit-questions [CASES_DIR=...] [AUDIT_OUTPUT=...]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_HARNESS_DIR = _HERE.parent / "tests" / "harness"
sys.path.insert(0, str(_HARNESS_DIR))

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

try:
    import yaml  # type: ignore

    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

try:
    from question_validator import QuestionValidator  # type: ignore
    _VALIDATOR_AVAILABLE = True
except ImportError:
    try:
        from tests.harness.question_validator import QuestionValidator  # type: ignore
        _VALIDATOR_AVAILABLE = True
    except ImportError:
        _VALIDATOR_AVAILABLE = False


def _require_yaml() -> None:
    if not _YAML_AVAILABLE:
        print("ERROR: pyyaml is required. Install with: uv add pyyaml", file=sys.stderr)
        sys.exit(1)


def _require_validator() -> None:
    if not _VALIDATOR_AVAILABLE:
        print(
            "ERROR: question_validator module not found.\n"
            "Ensure skill-generation-validation-tools/tests/harness/question_validator.py exists.",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Domain YAML loading
# ---------------------------------------------------------------------------


def _collect_yaml_files(cases_path: Path) -> list[Path]:
    """Return a list of domain YAML file paths from a file or directory."""
    if cases_path.is_file():
        return [cases_path]
    elif cases_path.is_dir():
        return sorted(cases_path.glob("*.yml"))
    else:
        print(f"ERROR: {cases_path} is not a file or directory", file=sys.stderr)
        sys.exit(1)


def _load_domain(path: Path) -> Optional[dict[str, Any]]:
    """Load a domain YAML file. Returns None on error."""
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return None
        return data
    except Exception as exc:
        print(f"  WARNING: Failed to load {path}: {exc}", file=sys.stderr)
        return None


def _extract_schema(data: dict[str, Any]) -> dict[str, Any]:
    """
    Extract schema dict compatible with QuestionValidator from domain YAML.

    Handles both old and new (dataset: split) YAML structures.
    """
    # New structure: dataset.schema.nodes / .relationships
    dataset = data.get("dataset", {})
    schema_block = dataset.get("schema", {})

    nodes = schema_block.get("nodes", {})
    rels = schema_block.get("relationships", [])

    # If new structure is empty, check for legacy top-level schema
    if not nodes:
        nodes = data.get("schema", {}).get("nodes", {})
    if not rels:
        rels = data.get("schema", {}).get("relationships", [])

    return {"nodes": nodes, "relationships": rels}


# ---------------------------------------------------------------------------
# Audit logic
# ---------------------------------------------------------------------------


def _audit_domain(
    path: Path,
    data: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], dict[str, int]]:
    """
    Audit all questions in a domain YAML file.

    Returns:
        (domain_name, violations, stats)
        violations: list of {id, question, reason}
        stats: {total, valid, violations}
    """
    domain_name = data.get("dataset", {}).get("name") or path.stem
    cases = data.get("cases", [])

    schema = _extract_schema(data)
    validator = QuestionValidator(schema=schema)

    violations: list[dict[str, Any]] = []
    stats = {"total": 0, "valid": 0, "violations": 0}

    for case in cases:
        if not isinstance(case, dict):
            continue
        question = str(case.get("question", "")).strip()
        case_id = str(case.get("id", "unknown"))

        if not question:
            continue

        stats["total"] += 1
        ok, reason = validator.validate(question)

        if not ok:
            violations.append({
                "id": case_id,
                "difficulty": case.get("difficulty", "unknown"),
                "question": question,
                "reason": reason,
            })
            stats["violations"] += 1
        else:
            stats["valid"] += 1

    return domain_name, violations, stats


# ---------------------------------------------------------------------------
# Markdown report generation
# ---------------------------------------------------------------------------


def _render_report(
    results: list[tuple[str, str, list[dict[str, Any]], dict[str, int]]],
    total_files: int,
) -> str:
    """
    Render the Markdown audit report.

    results: list of (domain_name, file_path, violations, stats)
    """
    lines: list[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines.append("# Question Language Audit Report")
    lines.append(f"\nGenerated: {now}")
    lines.append(f"Domains audited: {total_files}")
    lines.append("")

    # Summary table
    total_cases = sum(r[3]["total"] for r in results)
    total_violations = sum(r[3]["violations"] for r in results)
    total_valid = sum(r[3]["valid"] for r in results)
    pass_rate = (total_valid / total_cases * 100) if total_cases > 0 else 0.0

    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total questions audited | {total_cases} |")
    lines.append(f"| Valid (business language) | {total_valid} ({pass_rate:.1f}%) |")
    lines.append(f"| Violations | {total_violations} |")
    lines.append("")

    # Per-domain summary
    lines.append("## Per-Domain Summary")
    lines.append("")
    lines.append("| Domain | Total | Valid | Violations | Pass Rate |")
    lines.append("|--------|-------|-------|------------|-----------|")
    for domain_name, _path, _violations, stats in results:
        rate = (stats["valid"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
        status = "✓" if stats["violations"] == 0 else "⚠"
        lines.append(
            f"| {status} {domain_name} | {stats['total']} | {stats['valid']} "
            f"| {stats['violations']} | {rate:.1f}% |"
        )
    lines.append("")

    if total_violations == 0:
        lines.append("**All questions pass business-language validation.** No action required.")
        return "\n".join(lines)

    # Per-domain violation details
    lines.append("## Violations by Domain")
    lines.append("")
    lines.append(
        "> Questions marked below contain Cypher syntax, graph labels, relationship types, "
        "or other technical patterns. They should be rewritten in plain business language."
    )
    lines.append("")

    for domain_name, file_path, violations, stats in results:
        if not violations:
            continue

        lines.append(f"### {domain_name} ({len(violations)} violation(s))")
        lines.append(f"File: `{file_path}`")
        lines.append("")
        lines.append("| Case ID | Difficulty | Question | Reason |")
        lines.append("|---------|------------|----------|--------|")
        for v in violations:
            # Escape pipes in question text for table safety
            q = v["question"].replace("|", "\\|")
            r = v["reason"].replace("|", "\\|")
            if len(q) > 80:
                q = q[:77] + "..."
            lines.append(f"| {v['id']} | {v['difficulty']} | {q} | {r} |")
        lines.append("")

    # Guidance
    lines.append("## Remediation Guidance")
    lines.append("")
    lines.append("For each violation:")
    lines.append("1. Open the domain YAML file and locate the case by ID")
    lines.append("2. Rewrite the `question:` field in plain business English:")
    lines.append("   - Remove all Cypher keywords (MATCH, WHERE, RETURN, etc.)")
    lines.append("   - Remove graph labels (`:Organization`, `:Movie`, etc.)")
    lines.append("   - Remove relationship types (`HAS_SUBSIDIARY`, etc.)")
    lines.append("   - Remove dot-access syntax (`n.name`, `movie.title`, etc.)")
    lines.append("3. Run the audit again to confirm the fix: `make audit-questions`")
    lines.append("")
    lines.append("**Example rewrites:**")
    lines.append("")
    lines.append("| Before (technical) | After (business language) |")
    lines.append("|--------------------|---------------------------|")
    lines.append(
        "| MATCH (n:Organization) RETURN n.name | "
        "What are the names of all organizations? |"
    )
    lines.append(
        "| Find (:Movie)-[:ACTED_IN]-(:Person) depth > 2 | "
        "Which actors appeared in more than 2 movies together? |"
    )
    lines.append(
        "| Use COUNT {} subquery to count articles | "
        "How many articles mention each company? |"
    )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit domain YAML test case questions for business-language compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--cases",
        default="tests/cases",
        metavar="PATH",
        help="Path to a domain YAML file or directory of YAML files (default: tests/cases/)",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help="Path to write the Markdown audit report (default: stdout)",
    )
    parser.add_argument(
        "--fail-on-violations",
        action="store_true",
        help="Exit with code 1 if any violations are found (useful in CI)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-file progress to stderr",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    _require_yaml()
    _require_validator()

    args = _parse_args(argv)
    cases_path = Path(args.cases)

    yaml_files = _collect_yaml_files(cases_path)
    if not yaml_files:
        print("No YAML files found to audit.", file=sys.stderr)
        return 0

    results: list[tuple[str, str, list[dict[str, Any]], dict[str, int]]] = []

    for yml_path in yaml_files:
        if args.verbose:
            print(f"  Auditing: {yml_path}", file=sys.stderr)

        data = _load_domain(yml_path)
        if data is None:
            continue

        domain_name, violations, stats = _audit_domain(yml_path, data)

        if args.verbose:
            rate = (stats["valid"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
            print(
                f"    {domain_name}: {stats['total']} total, "
                f"{stats['violations']} violations ({rate:.1f}% pass)",
                file=sys.stderr,
            )

        results.append((domain_name, str(yml_path), violations, stats))

    if not results:
        print("No auditable domain files found.", file=sys.stderr)
        return 0

    # Render report
    report_md = _render_report(results, len(yaml_files))

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(report_md)
        print(f"[audit] Report written to: {output_path}", flush=True)
    else:
        print(report_md)

    # Print a brief summary to stderr for CI visibility
    total_violations = sum(r[3]["violations"] for r in results)
    total_cases = sum(r[3]["total"] for r in results)
    print(
        f"[audit] {total_cases} questions audited — {total_violations} violation(s) found",
        file=sys.stderr,
    )

    if args.fail_on_violations and total_violations > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
