#!/usr/bin/env python3
"""
runner.py — Main test executor for the neo4j-cypher-authoring-skill test harness.

Loads test case YAML files, submits each question to Claude Code headless
with the skill loaded, extracts the first Cypher code block from the response,
passes it through all four validator gates, and records pass/warn/fail verdicts.

Usage:
    uv run python3 tests/harness/runner.py \\
        --cases tests/cases/ \\
        --skill neo4j-cypher-authoring-skill \\
        --report tests/results/run-$(date +%Y%m%d).json

Exit codes:
    0 — all test cases PASS
    1 — at least one FAIL
    2 — at least one WARN, no FAIL
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Path setup — allow running from repo root or harness dir
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_HERE))

from validator import FAIL, PASS, WARN, ValidationResult, validate  # noqa: E402

# ---------------------------------------------------------------------------
# Optional YAML import — fallback to stdlib json for dry-run only
# ---------------------------------------------------------------------------

try:
    import yaml  # type: ignore

    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


def _load_yaml(path: Path) -> Any:
    """Load a YAML file; raise ImportError if PyYAML not installed."""
    if not _YAML_AVAILABLE:
        raise ImportError(
            "PyYAML is required to load test cases. "
            "Install with: uv add pyyaml"
        )
    with open(path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TestCase:
    """A single test case loaded from YAML."""

    id: str
    question: str
    database: str = "neo4j"
    difficulty: str = "basic"
    tags: list[str] = field(default_factory=list)
    domain: str = ""
    # Validation thresholds (optional — None = unchecked)
    min_results: int = 0
    max_db_hits: Optional[int] = None
    max_allocated_memory_bytes: Optional[int] = None
    max_runtime_ms: Optional[float] = None
    is_write_query: bool = False
    # Source file (set by loader)
    source_file: str = ""


@dataclass
class TestCaseResult:
    """Result of running a single test case through the full harness."""

    case_id: str
    question: str
    difficulty: str
    tags: list[str]
    verdict: str  # PASS | WARN | FAIL
    failed_gate: Optional[int]
    warned_gate: Optional[int]
    generated_cypher: str
    metrics: dict[str, Any]
    gate_details: list[dict[str, Any]]
    error: Optional[str]  # Runner-level error (e.g. Claude invocation failed)
    duration_s: float


@dataclass
class RunReport:
    """Aggregate report for a complete harness run."""

    run_id: str
    started_at: str
    completed_at: str
    skill: str
    total: int
    passed: int
    warned: int
    failed: int
    cases: list[TestCaseResult]

    @property
    def exit_code(self) -> int:
        if self.failed > 0:
            return 1
        if self.warned > 0:
            return 2
        return 0


# ---------------------------------------------------------------------------
# Test case loader
# ---------------------------------------------------------------------------

_VALID_DIFFICULTIES = {"basic", "intermediate", "advanced", "complex", "expert"}


def load_cases(
    path: Path,
    *,
    difficulty_filter: Optional[str] = None,
    domain_filter: Optional[str] = None,
) -> list[TestCase]:
    """
    Load test cases from a YAML file or directory of YAML files.

    YAML structure expected:
        cases:
          - id: tc-001
            question: "Find all organizations"
            database: companies
            difficulty: basic
            tags: [match, label]
            domain: companies
            min_results: 1
            max_db_hits: 10000
            max_allocated_memory_bytes: 10485760
            max_runtime_ms: 2000
            is_write_query: false

    Args:
        path: Path to a .yml file or directory containing .yml files.
        difficulty_filter: If set, only load cases with this difficulty.
        domain_filter: If set, only load cases from this domain.

    Returns:
        List of TestCase objects.
    """
    files: list[Path] = []
    if path.is_dir():
        files = sorted(path.glob("*.yml")) + sorted(path.glob("*.yaml"))
    elif path.is_file():
        files = [path]
    else:
        raise FileNotFoundError(f"Test cases path not found: {path}")

    cases: list[TestCase] = []
    for f in files:
        data = _load_yaml(f)
        raw_cases = data.get("cases", [])
        for raw in raw_cases:
            tc = TestCase(
                id=str(raw["id"]),
                question=str(raw["question"]),
                database=str(raw.get("database", "neo4j")),
                difficulty=str(raw.get("difficulty", "basic")),
                tags=list(raw.get("tags", [])),
                domain=str(raw.get("domain", f.stem)),
                min_results=int(raw.get("min_results", 0)),
                max_db_hits=raw.get("max_db_hits"),
                max_allocated_memory_bytes=raw.get("max_allocated_memory_bytes"),
                max_runtime_ms=raw.get("max_runtime_ms"),
                is_write_query=bool(raw.get("is_write_query", False)),
                source_file=str(f),
            )

            if difficulty_filter and tc.difficulty != difficulty_filter:
                continue
            if domain_filter and tc.domain != domain_filter:
                continue

            cases.append(tc)

    return cases


# ---------------------------------------------------------------------------
# Cypher extraction from model response
# ---------------------------------------------------------------------------

_CYPHER_BLOCK_RE = re.compile(
    r"```(?:cypher|CYPHER)\s*\n(.*?)```",
    re.DOTALL,
)


def extract_cypher(response_text: str) -> Optional[str]:
    """
    Extract the first ```cypher ... ``` code block from the model response.

    Returns the Cypher source string (stripped), or None if no block found.
    """
    m = _CYPHER_BLOCK_RE.search(response_text)
    if m:
        return m.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# Claude Code headless invocation
# ---------------------------------------------------------------------------


def _build_claude_prompt(tc: TestCase) -> str:
    """
    Build the prompt sent to Claude Code for a test case.

    Includes database context so the model can write targeted Cypher.
    """
    lines = [
        f"Database: {tc.database}",
        f"Difficulty: {tc.difficulty}",
    ]
    if tc.tags:
        lines.append(f"Tags: {', '.join(tc.tags)}")
    lines.append("")
    lines.append(
        "Write a Cypher query to answer the following question. "
        "Output ONLY a single ```cypher ... ``` code block — no explanation."
    )
    lines.append("")
    lines.append(tc.question)
    return "\n".join(lines)


def _load_skill_content(skill_name: str) -> Optional[str]:
    """
    Load SKILL.md content for the given skill name or path.

    Searches:
    1. Relative path: <skill_name>/SKILL.md  (from repo root)
    2. Skill directory convention: neo4j-<skill_name>-skill/SKILL.md
    3. Absolute path if provided

    Returns the content string, or None if not found.
    """
    # _REPO_ROOT is skill-generation-validation-tools/; skills live one level up
    _GIT_ROOT = _REPO_ROOT.parent
    candidates = [
        Path(skill_name) / "SKILL.md",
        _REPO_ROOT / skill_name / "SKILL.md",
        _REPO_ROOT / f"neo4j-{skill_name}-skill" / "SKILL.md",
        _GIT_ROOT / skill_name / "SKILL.md",
        _GIT_ROOT / f"neo4j-{skill_name}-skill" / "SKILL.md",
        Path(skill_name + "/SKILL.md"),
    ]
    for p in candidates:
        if p.exists():
            return p.read_text()
    return None


def invoke_claude(
    prompt: str,
    skill_name: str,
    *,
    timeout_s: int = 120,
) -> tuple[str, Optional[str]]:
    """
    Invoke Claude Code headless and return (response_text, error_message).

    Loads the skill's SKILL.md and appends it as a system prompt via
    --append-system-prompt. Falls back to --skill flag if SKILL.md cannot
    be found (for forward compatibility when --skill is implemented).

    Returns:
        (response_text, None) on success
        ("", error_message) on failure
    """
    skill_content = _load_skill_content(skill_name)

    if skill_content:
        cmd = [
            "claude",
            "--append-system-prompt", skill_content,
            "--print",
            "--output-format", "text",
        ]
    else:
        # Fallback: try --skill flag (may work in newer CLI versions)
        cmd = [
            "claude",
            "--skill", skill_name,
            "--print",
            "--output-format", "text",
        ]

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env={**os.environ},
        )
        if result.returncode != 0:
            err = result.stderr.strip() or f"claude exited {result.returncode}"
            return "", err
        return result.stdout, None
    except subprocess.TimeoutExpired:
        return "", f"Claude invocation timed out after {timeout_s}s"
    except FileNotFoundError:
        return "", (
            "claude CLI not found. Install Claude Code and ensure 'claude' is on PATH. "
            "In CI, set ANTHROPIC_API_KEY and install the claude CLI."
        )
    except Exception as exc:
        return "", f"Unexpected error invoking claude: {exc}"


# ---------------------------------------------------------------------------
# Neo4j driver setup
# ---------------------------------------------------------------------------


def _get_driver(
    uri: Optional[str],
    username: Optional[str],
    password: Optional[str],
) -> Any:
    """
    Create a neo4j driver from environment variables or explicit args.

    Falls back to env vars NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD.
    Returns None if neo4j package not installed (dry-run mode still works).
    """
    try:
        import neo4j  # type: ignore
    except ImportError:
        return None

    uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    username = username or os.environ.get("NEO4J_USERNAME", "neo4j")
    password = password or os.environ.get("NEO4J_PASSWORD", "neo4j")

    return neo4j.GraphDatabase.driver(uri, auth=(username, password))


# ---------------------------------------------------------------------------
# Single test case runner
# ---------------------------------------------------------------------------


def _verdict_from_validation(vr: ValidationResult) -> str:
    return vr.verdict


def run_case(
    tc: TestCase,
    skill_name: str,
    driver: Any,
    *,
    dry_run: bool = False,
    claude_timeout_s: int = 120,
) -> TestCaseResult:
    """
    Run a single test case end-to-end.

    Dry-run mode skips Claude invocation and Neo4j execution; validates only
    that the TestCase struct loaded correctly and returns a synthetic PASS.
    """
    t0 = time.monotonic()
    error: Optional[str] = None
    generated_cypher = ""
    validation: Optional[ValidationResult] = None

    if dry_run:
        return TestCaseResult(
            case_id=tc.id,
            question=tc.question,
            difficulty=tc.difficulty,
            tags=tc.tags,
            verdict=PASS,
            failed_gate=None,
            warned_gate=None,
            generated_cypher="",
            metrics={},
            gate_details=[],
            error=None,
            duration_s=round(time.monotonic() - t0, 3),
        )

    # Step 1: invoke Claude Code headless
    prompt = _build_claude_prompt(tc)
    response_text, invoke_error = invoke_claude(
        prompt, skill_name, timeout_s=claude_timeout_s
    )

    if invoke_error:
        error = f"Claude invocation failed: {invoke_error}"
        return TestCaseResult(
            case_id=tc.id,
            question=tc.question,
            difficulty=tc.difficulty,
            tags=tc.tags,
            verdict=FAIL,
            failed_gate=None,
            warned_gate=None,
            generated_cypher="",
            metrics={},
            gate_details=[],
            error=error,
            duration_s=round(time.monotonic() - t0, 3),
        )

    # Step 2: extract Cypher from response
    generated_cypher = extract_cypher(response_text) or ""
    if not generated_cypher:
        error = "No ```cypher block found in model response"
        return TestCaseResult(
            case_id=tc.id,
            question=tc.question,
            difficulty=tc.difficulty,
            tags=tc.tags,
            verdict=FAIL,
            failed_gate=None,
            warned_gate=None,
            generated_cypher="",
            metrics={},
            gate_details=[],
            error=error,
            duration_s=round(time.monotonic() - t0, 3),
        )

    # Step 3: validate through all four gates
    if driver is None:
        error = (
            "Neo4j driver unavailable (neo4j package not installed or no connection). "
            "Set NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD or install 'neo4j' package."
        )
        return TestCaseResult(
            case_id=tc.id,
            question=tc.question,
            difficulty=tc.difficulty,
            tags=tc.tags,
            verdict=FAIL,
            failed_gate=None,
            warned_gate=None,
            generated_cypher=generated_cypher,
            metrics={},
            gate_details=[],
            error=error,
            duration_s=round(time.monotonic() - t0, 3),
        )

    try:
        validation = validate(
            generated_cypher,
            driver,
            database=tc.database,
            is_write_query=tc.is_write_query,
            min_results=tc.min_results,
            max_db_hits=tc.max_db_hits,
            max_allocated_memory_bytes=tc.max_allocated_memory_bytes,
            max_runtime_ms=tc.max_runtime_ms,
        )
    except Exception as exc:
        error = f"Validator raised unexpected exception: {exc}"
        return TestCaseResult(
            case_id=tc.id,
            question=tc.question,
            difficulty=tc.difficulty,
            tags=tc.tags,
            verdict=FAIL,
            failed_gate=None,
            warned_gate=None,
            generated_cypher=generated_cypher,
            metrics={},
            gate_details=[],
            error=error,
            duration_s=round(time.monotonic() - t0, 3),
        )

    gate_details = [
        {
            "gate": g.gate,
            "verdict": g.verdict,
            "reason": g.reason,
            "details": g.details,
        }
        for g in validation.gates
    ]

    return TestCaseResult(
        case_id=tc.id,
        question=tc.question,
        difficulty=tc.difficulty,
        tags=tc.tags,
        verdict=validation.verdict,
        failed_gate=validation.failed_gate(),
        warned_gate=validation.warned_gate(),
        generated_cypher=generated_cypher,
        metrics=validation.metrics,
        gate_details=gate_details,
        error=error,
        duration_s=round(time.monotonic() - t0, 3),
    )


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------


def run_all(
    cases: list[TestCase],
    skill_name: str,
    driver: Any,
    *,
    dry_run: bool = False,
    claude_timeout_s: int = 120,
    verbose: bool = False,
) -> RunReport:
    """
    Run all test cases and return an aggregate RunReport.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"

    results: list[TestCaseResult] = []
    passed = warned = failed = 0

    for i, tc in enumerate(cases, 1):
        if verbose:
            print(
                f"[{i}/{len(cases)}] {tc.id} ({tc.difficulty}) — {tc.question[:60]}...",
                flush=True,
            )

        result = run_case(
            tc, skill_name, driver,
            dry_run=dry_run,
            claude_timeout_s=claude_timeout_s,
        )
        results.append(result)

        if result.verdict == PASS:
            passed += 1
        elif result.verdict == WARN:
            warned += 1
        else:
            failed += 1

        if verbose:
            gate_info = ""
            if result.failed_gate:
                gate_info = f" [GATE {result.failed_gate}]"
            elif result.warned_gate:
                gate_info = f" [GATE {result.warned_gate}]"
            symbol = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗"}.get(result.verdict, "?")
            print(f"  {symbol} {result.verdict}{gate_info}", flush=True)

    completed_at = datetime.now(timezone.utc).isoformat()

    return RunReport(
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
        skill=skill_name,
        total=len(cases),
        passed=passed,
        warned=warned,
        failed=failed,
        cases=results,
    )


# ---------------------------------------------------------------------------
# Report serialization
# ---------------------------------------------------------------------------


def _result_to_dict(r: TestCaseResult) -> dict[str, Any]:
    return {
        "case_id": r.case_id,
        "question": r.question,
        "difficulty": r.difficulty,
        "tags": r.tags,
        "verdict": r.verdict,
        "failed_gate": r.failed_gate,
        "warned_gate": r.warned_gate,
        "generated_cypher": r.generated_cypher,
        "metrics": r.metrics,
        "gate_details": r.gate_details,
        "error": r.error,
        "duration_s": r.duration_s,
    }


def report_to_dict(report: RunReport) -> dict[str, Any]:
    return {
        "run_id": report.run_id,
        "started_at": report.started_at,
        "completed_at": report.completed_at,
        "skill": report.skill,
        "summary": {
            "total": report.total,
            "passed": report.passed,
            "warned": report.warned,
            "failed": report.failed,
            "pass_rate": round(report.passed / report.total, 4) if report.total else 0.0,
        },
        "cases": [_result_to_dict(r) for r in report.cases],
    }


def write_report(report: RunReport, path: Path) -> None:
    """Write the run report as JSON to the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(report_to_dict(report), f, indent=2)
    print(f"Report written to: {path}", flush=True)


# ---------------------------------------------------------------------------
# YAML structure validation (dry-run mode)
# ---------------------------------------------------------------------------


def validate_yaml_structure(cases: list[TestCase]) -> list[str]:
    """
    Validate that each test case has all required fields and valid values.

    Returns a list of error messages; empty list = all valid.
    """
    errors: list[str] = []
    seen_ids: set[str] = set()

    for tc in cases:
        prefix = f"[{tc.id}]"

        if not tc.id:
            errors.append(f"{prefix} Missing required field: id")
        if tc.id in seen_ids:
            errors.append(f"{prefix} Duplicate test case id: {tc.id!r}")
        seen_ids.add(tc.id)

        if not tc.question:
            errors.append(f"{prefix} Missing required field: question")

        if tc.difficulty not in _VALID_DIFFICULTIES:
            errors.append(
                f"{prefix} Invalid difficulty {tc.difficulty!r}; "
                f"must be one of {sorted(_VALID_DIFFICULTIES)}"
            )

        if tc.min_results < 0:
            errors.append(f"{prefix} min_results must be >= 0, got {tc.min_results}")

    return errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the neo4j-cypher-authoring-skill test harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--cases",
        required=True,
        help="Path to a test case YAML file or directory of YAML files",
    )
    parser.add_argument(
        "--skill",
        default="neo4j-cypher-authoring-skill",
        help="Skill name or path to pass to claude --skill (default: neo4j-cypher-authoring-skill)",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Output path for the JSON run report (default: tests/results/run-<timestamp>.json)",
    )
    parser.add_argument(
        "--difficulty",
        choices=sorted(_VALID_DIFFICULTIES),
        default=None,
        help="Filter test cases by difficulty",
    )
    parser.add_argument(
        "--domain",
        default=None,
        help="Filter test cases by domain (e.g. 'companies')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate YAML structure without executing queries or invoking Claude",
    )
    parser.add_argument(
        "--neo4j-uri",
        default=None,
        help="Neo4j connection URI (overrides NEO4J_URI env var)",
    )
    parser.add_argument(
        "--neo4j-username",
        default=None,
        help="Neo4j username (overrides NEO4J_USERNAME env var)",
    )
    parser.add_argument(
        "--neo4j-password",
        default=None,
        help="Neo4j password (overrides NEO4J_PASSWORD env var)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout in seconds for each Claude invocation (default: 120)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-case progress to stdout",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)

    cases_path = Path(args.cases)

    # Load test cases
    try:
        cases = load_cases(
            cases_path,
            difficulty_filter=args.difficulty,
            domain_filter=args.domain,
        )
    except ImportError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if not cases:
        print("No test cases found (check --difficulty / --domain filters)", file=sys.stderr)
        return 0

    print(f"Loaded {len(cases)} test case(s) from {cases_path}", flush=True)

    # Dry-run: validate YAML structure only
    if args.dry_run:
        errors = validate_yaml_structure(cases)
        if errors:
            for err in errors:
                print(f"YAML ERROR: {err}", file=sys.stderr)
            return 1
        print(
            f"Dry-run OK: {len(cases)} case(s) validated (no queries executed)",
            flush=True,
        )
        # Print planned output files
        if args.report:
            print(f"Would write report to: {args.report}", flush=True)
        for tc in cases:
            print(f"  - {tc.id} ({tc.difficulty}): {tc.question[:80]}", flush=True)
        return 0

    # Set up Neo4j driver
    driver = _get_driver(args.neo4j_uri, args.neo4j_username, args.neo4j_password)

    # Determine report output path
    if args.report:
        report_path = Path(args.report)
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        report_path = _REPO_ROOT / "tests" / "results" / f"run-{timestamp}.json"

    # Run all cases
    report = run_all(
        cases,
        args.skill,
        driver,
        dry_run=False,
        claude_timeout_s=args.timeout,
        verbose=args.verbose,
    )

    # Print summary
    print(
        f"\nResults: {report.passed}/{report.total} PASS, "
        f"{report.warned} WARN, {report.failed} FAIL",
        flush=True,
    )

    # Write report
    write_report(report, report_path)

    # Clean up driver
    if driver is not None:
        try:
            driver.close()
        except Exception:
            pass

    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
