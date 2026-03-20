#!/usr/bin/env python3
"""
exporter.py — Training dataset YAML exporter for the neo4j-cypher-authoring-skill
test harness.

Reads runner JSON output (produced by runner.py) and writes YAML training records
for every test case that passed all four validation gates. Appends to an existing
dataset file without overwriting records (dedup by id).

Each exported record includes:
  - id, question, database, neo4j_version
  - schema_context (labels, relationship_types, indexes) — from --schema file or null
  - property_samples (with inferred_semantic, non_null_count) — from --schema file or null
  - cypher (the validated Cypher query)
  - metadata (difficulty, tags, db_hits, allocated_memory_bytes, runtime_ms,
              passed_gates, generated_at)

Usage:
    uv run python3 tests/harness/exporter.py \\
        --input tests/results/run-20260320T120000.json \\
        --domain companies \\
        --output-dir tests/dataset/ \\
        [--neo4j-version 2026.01] \\
        [--schema tests/results/schema-companies.json] \\
        [--dry-run]

The --schema flag accepts a JSON file produced by generator.py internals (or manually
authored) with keys: labels, relationship_types, indexes, property_samples.
If absent, schema_context and property_samples fields are set to null.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# YAML import
# ---------------------------------------------------------------------------

try:
    import yaml  # type: ignore

    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


def _require_yaml() -> None:
    if not _YAML_AVAILABLE:
        print(
            "ERROR: pyyaml is required. Install with: uv add pyyaml",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Gate constants — must match validator.py
# ---------------------------------------------------------------------------

ALL_FOUR_GATES = {1, 2, 3, 4}

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

# ---------------------------------------------------------------------------
# Schema file loader
# ---------------------------------------------------------------------------


def _load_schema(schema_path: Optional[Path]) -> dict[str, Any]:
    """
    Load an optional schema JSON file.

    Expected keys (all optional):
        labels: list[str]
        relationship_types: list[str]
        indexes: list[dict]
        property_samples: {label: {prop: {samples, non_null_count, inferred_semantic}}}

    Returns an empty dict if schema_path is None or the file cannot be read.
    """
    if schema_path is None:
        return {}

    try:
        with open(schema_path) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            print(
                f"WARNING: schema file {schema_path} is not a JSON object — ignoring",
                file=sys.stderr,
            )
            return {}
        return data
    except Exception as exc:
        print(
            f"WARNING: could not read schema file {schema_path}: {exc} — ignoring",
            file=sys.stderr,
        )
        return {}


def _build_schema_context(schema: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Build a schema_context dict from the loaded schema dict.

    Returns None if schema is empty (no schema file provided).
    """
    if not schema:
        return None

    return {
        "labels": schema.get("labels", []),
        "relationship_types": schema.get("relationship_types", []),
        "indexes": schema.get("indexes", []),
    }


def _build_property_samples(schema: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Extract property_samples from the loaded schema dict.

    Returns None if schema does not contain property_samples.
    """
    if not schema:
        return None

    raw = schema.get("property_samples")
    if not raw:
        return None

    # Trim each property entry to just inferred_semantic and non_null_count
    # (drop raw sample values to keep the dataset compact)
    result: dict[str, dict[str, Any]] = {}
    for label, props in raw.items():
        if not isinstance(props, dict):
            continue
        result[label] = {}
        for prop, info in props.items():
            if not isinstance(info, dict):
                continue
            entry: dict[str, Any] = {}
            if "inferred_semantic" in info:
                entry["inferred_semantic"] = info["inferred_semantic"]
            if "non_null_count" in info:
                entry["non_null_count"] = info["non_null_count"]
            result[label][prop] = entry

    return result if result else None


# ---------------------------------------------------------------------------
# Runner JSON — record filtering
# ---------------------------------------------------------------------------


def _determine_passed_gates(case_data: dict[str, Any]) -> set[int]:
    """
    Determine which gates passed for a case.

    A case passes all four gates if verdict is PASS or WARN *and* no gate
    is recorded as failed. We inspect gate_details to find which gates were
    evaluated and returned PASS or WARN.
    """
    verdict = case_data.get("verdict", "")
    failed_gate = case_data.get("failed_gate")

    # If the verdict is FAIL, we don't export — but we return partial info
    # for informational purposes.
    if verdict == FAIL:
        # Determine which gates were attempted but not all passed
        gate_details = case_data.get("gate_details", [])
        passed: set[int] = set()
        for gd in gate_details:
            gate_num = gd.get("gate")
            gate_verdict = gd.get("verdict", "")
            if gate_num is not None and gate_verdict in (PASS, WARN):
                passed.add(int(gate_num))
        return passed

    # PASS or WARN verdict — all evaluated gates passed
    gate_details = case_data.get("gate_details", [])
    if gate_details:
        # Use gate_details to determine which gates ran
        passed = set()
        for gd in gate_details:
            gate_num = gd.get("gate")
            gate_verdict = gd.get("verdict", "")
            if gate_num is not None and gate_verdict in (PASS, WARN):
                passed.add(int(gate_num))
        return passed

    # No gate_details available — if PASS/WARN and no failed_gate, assume all four
    if verdict in (PASS, WARN) and failed_gate is None:
        return ALL_FOUR_GATES

    return set()


def _all_four_gates_passed(case_data: dict[str, Any]) -> bool:
    """Return True only if all four gates passed for this case."""
    return ALL_FOUR_GATES.issubset(_determine_passed_gates(case_data))


# ---------------------------------------------------------------------------
# Export record builder
# ---------------------------------------------------------------------------


def _build_export_record(
    case_data: dict[str, Any],
    domain: str,
    database: str,
    neo4j_version: str,
    schema_context: Optional[dict[str, Any]],
    property_samples: Optional[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    """
    Build a single export record from a runner case result.

    Fields follow REQ-F-021:
        id, question, database, neo4j_version,
        schema_context, property_samples, cypher,
        metadata: {difficulty, tags, db_hits, allocated_memory_bytes, runtime_ms,
                   passed_gates, generated_at}
    """
    metrics = case_data.get("metrics") or {}
    passed_gates = sorted(_determine_passed_gates(case_data))

    record: dict[str, Any] = {
        "id": case_data["case_id"],
        "question": case_data["question"],
        "database": database,
        "neo4j_version": neo4j_version,
        "schema_context": schema_context,
        "property_samples": property_samples,
        "cypher": case_data.get("generated_cypher", ""),
        "metadata": {
            "difficulty": case_data.get("difficulty", "basic"),
            "tags": case_data.get("tags", []),
            "db_hits": metrics.get("totalDbHits"),
            "allocated_memory_bytes": metrics.get("totalAllocatedMemory"),
            "runtime_ms": metrics.get("elapsedTimeMs"),
            "passed_gates": passed_gates,
            "generated_at": generated_at,
        },
    }

    return record


# ---------------------------------------------------------------------------
# Dataset file I/O — append-only with dedup
# ---------------------------------------------------------------------------


def _load_existing_dataset(path: Path) -> dict[str, Any]:
    """
    Load the existing dataset YAML file.

    Returns a dict with a 'records' key containing the list of existing records.
    Returns {'records': []} if the file does not exist.
    """
    if not path.exists():
        return {"records": []}

    _require_yaml()
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            print(
                f"WARNING: existing dataset file {path} has unexpected format — "
                "treating as empty",
                file=sys.stderr,
            )
            return {"records": []}
        if "records" not in data:
            # Legacy format: top-level list
            if isinstance(data, list):
                return {"records": data}
            return {"records": []}
        return data
    except Exception as exc:
        print(
            f"WARNING: could not read existing dataset {path}: {exc} — "
            "starting fresh",
            file=sys.stderr,
        )
        return {"records": []}


def _save_dataset(path: Path, dataset: dict[str, Any]) -> None:
    """Write the dataset to a YAML file with human-readable formatting."""
    _require_yaml()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(
            dataset,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=100,
        )


# ---------------------------------------------------------------------------
# Main export function
# ---------------------------------------------------------------------------


def export(
    input_path: Path,
    domain: str,
    output_dir: Path,
    *,
    database: Optional[str] = None,
    neo4j_version: str = "2026.01",
    schema_path: Optional[Path] = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """
    Export all test cases that passed all four gates to the dataset YAML file.

    Args:
        input_path: Path to runner JSON output.
        domain: Domain name (used as output filename prefix).
        output_dir: Directory to write dataset YAML files.
        database: Neo4j database name (default: domain name).
        neo4j_version: Neo4j version string to embed in records.
        schema_path: Optional path to a schema JSON file.
        dry_run: If True, print what would be exported without writing.
        verbose: If True, print per-record details.

    Returns:
        Number of new records exported (0 in dry-run mode).
    """
    # Load runner JSON
    try:
        with open(input_path) as f:
            run_data = json.load(f)
    except Exception as exc:
        print(f"ERROR: could not read input file {input_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    db_name = database or domain
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Load schema context
    schema = _load_schema(schema_path)
    schema_context = _build_schema_context(schema)
    property_samples = _build_property_samples(schema)

    # Filter cases
    all_cases = run_data.get("cases", [])
    qualifying: list[dict[str, Any]] = []

    for case_data in all_cases:
        if _all_four_gates_passed(case_data):
            qualifying.append(case_data)
        elif verbose:
            verdict = case_data.get("verdict", "?")
            gates = _determine_passed_gates(case_data)
            print(
                f"  SKIP {case_data.get('case_id', '?')} "
                f"(verdict={verdict}, gates_passed={sorted(gates)})",
                flush=True,
            )

    print(
        f"[exporter] {len(qualifying)}/{len(all_cases)} case(s) passed all four gates",
        flush=True,
    )

    if not qualifying:
        print("[exporter] Nothing to export.", flush=True)
        return 0

    output_path = output_dir / f"{domain}.yml"

    # Load existing records (for dedup)
    existing_dataset = _load_existing_dataset(output_path)
    existing_records: list[dict[str, Any]] = existing_dataset.get("records", [])
    existing_ids: set[str] = {r["id"] for r in existing_records if "id" in r}

    # Build new records
    new_records: list[dict[str, Any]] = []
    for case_data in qualifying:
        record = _build_export_record(
            case_data,
            domain=domain,
            database=db_name,
            neo4j_version=neo4j_version,
            schema_context=schema_context,
            property_samples=property_samples,
            generated_at=generated_at,
        )
        record_id = record["id"]

        if record_id in existing_ids:
            if verbose:
                print(f"  SKIP (duplicate) {record_id}", flush=True)
            continue

        new_records.append(record)
        existing_ids.add(record_id)

        if verbose:
            diff_str = case_data.get("difficulty", "?")
            print(f"  EXPORT {record_id} ({diff_str})", flush=True)

    print(
        f"[exporter] {len(new_records)} new record(s) to export "
        f"({len(qualifying) - len(new_records)} duplicate(s) skipped)",
        flush=True,
    )

    if dry_run:
        print(
            f"[exporter] DRY RUN — would write to: {output_path}",
            flush=True,
        )
        for r in new_records:
            print(f"  - {r['id']} ({r['metadata']['difficulty']}): {r['question'][:80]}", flush=True)
        return 0

    if not new_records:
        print("[exporter] No new records to write.", flush=True)
        return 0

    # Append and save
    merged_records = existing_records + new_records
    existing_dataset["records"] = merged_records

    _save_dataset(output_path, existing_dataset)
    print(
        f"[exporter] Wrote {len(new_records)} new record(s) to {output_path} "
        f"(total: {len(merged_records)})",
        flush=True,
    )
    return len(new_records)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export validated Cypher training records from runner output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to runner JSON output file (produced by runner.py)",
    )
    parser.add_argument(
        "--domain",
        required=True,
        help="Domain name used as the output filename prefix (e.g. 'companies')",
    )
    parser.add_argument(
        "--output-dir",
        default="tests/dataset",
        help="Directory to write dataset YAML files (default: tests/dataset)",
    )
    parser.add_argument(
        "--database",
        default=None,
        help=(
            "Neo4j database name to embed in records "
            "(default: same as --domain)"
        ),
    )
    parser.add_argument(
        "--neo4j-version",
        default="2026.01",
        help="Neo4j version string to embed in records (default: 2026.01)",
    )
    parser.add_argument(
        "--schema",
        default=None,
        help=(
            "Optional path to a schema JSON file with keys: "
            "labels, relationship_types, indexes, property_samples. "
            "If absent, schema_context and property_samples are set to null."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be exported without writing any files",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-record details",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    _require_yaml()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    schema_path = Path(args.schema) if args.schema else None

    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        return 1

    export(
        input_path=input_path,
        domain=args.domain,
        output_dir=output_dir,
        database=args.database,
        neo4j_version=args.neo4j_version,
        schema_path=schema_path,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    return 0


# ---------------------------------------------------------------------------
# Smoke tests (run when invoked directly with no args)
# ---------------------------------------------------------------------------


def _run_smoke_tests() -> None:
    """
    Offline smoke tests — no Neo4j connection or file I/O required.
    Tests key logic: gate detection, dedup, record building.
    """
    import tempfile
    import os

    print("Running exporter smoke tests...", flush=True)
    errors: list[str] = []

    # ----- Test 1: _all_four_gates_passed logic -----

    # PASS with 4 gate_details all passing
    case_pass = {
        "case_id": "tc-001",
        "question": "Find all orgs",
        "verdict": PASS,
        "failed_gate": None,
        "warned_gate": None,
        "generated_cypher": "CYPHER 25\nMATCH (o:Organization) RETURN o.name",
        "difficulty": "basic",
        "tags": ["match"],
        "metrics": {"totalDbHits": 100, "totalAllocatedMemory": 204800, "elapsedTimeMs": 5.0},
        "gate_details": [
            {"gate": 1, "verdict": PASS, "reason": "syntax ok", "details": {}},
            {"gate": 2, "verdict": PASS, "reason": "rows ok", "details": {}},
            {"gate": 3, "verdict": PASS, "reason": "quality ok", "details": {}},
            {"gate": 4, "verdict": PASS, "reason": "perf ok", "details": {}},
        ],
        "error": None,
        "duration_s": 3.5,
    }
    assert _all_four_gates_passed(case_pass), "TC-001: PASS case should export"

    # WARN — still passes (warned_gate is non-None but not failed)
    case_warn = {
        "case_id": "tc-002",
        "question": "Find orgs with slow query",
        "verdict": WARN,
        "failed_gate": None,
        "warned_gate": 4,
        "generated_cypher": "CYPHER 25\nMATCH (o:Organization) RETURN count(o)",
        "difficulty": "basic",
        "tags": ["aggregation"],
        "metrics": {"totalDbHits": 50000, "totalAllocatedMemory": 1048576, "elapsedTimeMs": 500.0},
        "gate_details": [
            {"gate": 1, "verdict": PASS, "reason": "syntax ok", "details": {}},
            {"gate": 2, "verdict": PASS, "reason": "rows ok", "details": {}},
            {"gate": 3, "verdict": PASS, "reason": "quality ok", "details": {}},
            {"gate": 4, "verdict": WARN, "reason": "slow", "details": {}},
        ],
        "error": None,
        "duration_s": 4.0,
    }
    assert _all_four_gates_passed(case_warn), "TC-002: WARN case should export (all 4 gates present)"

    # FAIL — must NOT export
    case_fail = {
        "case_id": "tc-003",
        "question": "Bad query",
        "verdict": FAIL,
        "failed_gate": 1,
        "warned_gate": None,
        "generated_cypher": "MATCH (x:BadSyntax",
        "difficulty": "basic",
        "tags": [],
        "metrics": {},
        "gate_details": [
            {"gate": 1, "verdict": FAIL, "reason": "syntax error", "details": {}},
        ],
        "error": None,
        "duration_s": 0.5,
    }
    assert not _all_four_gates_passed(case_fail), "TC-003: FAIL case must not export"

    # PASS with no gate_details (assume all four passed)
    case_no_details = {
        "case_id": "tc-004",
        "question": "Simple match",
        "verdict": PASS,
        "failed_gate": None,
        "warned_gate": None,
        "generated_cypher": "CYPHER 25\nMATCH (n) RETURN count(n)",
        "difficulty": "basic",
        "tags": [],
        "metrics": {},
        "gate_details": [],
        "error": None,
        "duration_s": 1.0,
    }
    assert _all_four_gates_passed(case_no_details), "TC-004: PASS+no details → assume all 4 passed"

    print("  PASS: gate detection logic", flush=True)

    # ----- Test 2: _build_export_record fields -----

    record = _build_export_record(
        case_pass,
        domain="companies",
        database="companies",
        neo4j_version="2026.01",
        schema_context=None,
        property_samples=None,
        generated_at="2026-03-20T12:00:00Z",
    )

    required_top = ["id", "question", "database", "neo4j_version",
                    "schema_context", "property_samples", "cypher", "metadata"]
    for field in required_top:
        if field not in record:
            errors.append(f"Missing top-level field: {field}")

    required_meta = ["difficulty", "tags", "db_hits", "allocated_memory_bytes",
                     "runtime_ms", "passed_gates", "generated_at"]
    meta = record.get("metadata", {})
    for field in required_meta:
        if field not in meta:
            errors.append(f"Missing metadata field: {field}")

    assert record["id"] == "tc-001", "record id mismatch"
    assert record["database"] == "companies", "record database mismatch"
    assert record["neo4j_version"] == "2026.01", "record neo4j_version mismatch"
    assert record["metadata"]["db_hits"] == 100, "db_hits mismatch"
    assert record["metadata"]["passed_gates"] == [1, 2, 3, 4], "passed_gates mismatch"
    assert record["schema_context"] is None, "schema_context should be None"
    assert record["property_samples"] is None, "property_samples should be None"

    print("  PASS: record field structure", flush=True)

    # ----- Test 3: dedup logic (write then re-run) -----

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        output_path = output_dir / "test_domain.yml"

        # Build a minimal runner JSON
        run_data = {
            "run_id": "run-test",
            "started_at": "2026-03-20T12:00:00Z",
            "completed_at": "2026-03-20T12:01:00Z",
            "skill": "neo4j-cypher-authoring-skill",
            "summary": {"total": 2, "passed": 1, "warned": 0, "failed": 1, "pass_rate": 0.5},
            "cases": [case_pass, case_fail],
        }

        input_path = output_dir / "run.json"
        with open(input_path, "w") as f:
            json.dump(run_data, f)

        # First export
        count1 = export(
            input_path=input_path,
            domain="test_domain",
            output_dir=output_dir,
            database="test",
            neo4j_version="2026.01",
        )
        assert count1 == 1, f"Expected 1 new record, got {count1}"
        assert output_path.exists(), "Output file should exist"

        # Check YAML is valid
        import yaml as _yaml
        with open(output_path) as f:
            loaded = _yaml.safe_load(f)
        assert "records" in loaded, "Missing 'records' key in output YAML"
        assert len(loaded["records"]) == 1, f"Expected 1 record, got {len(loaded['records'])}"
        assert loaded["records"][0]["id"] == "tc-001", "Wrong record id"

        # Second export — same input — dedup should produce 0 new records
        count2 = export(
            input_path=input_path,
            domain="test_domain",
            output_dir=output_dir,
            database="test",
            neo4j_version="2026.01",
        )
        assert count2 == 0, f"Expected 0 new records on re-run (dedup), got {count2}"

        # Verify record count still 1 after dedup run
        with open(output_path) as f:
            loaded2 = _yaml.safe_load(f)
        assert len(loaded2["records"]) == 1, f"Record count should still be 1 after dedup run"

    print("  PASS: dedup logic and YAML round-trip", flush=True)

    # ----- Test 4: schema context loading -----

    schema_data = {
        "labels": ["Organization", "Article"],
        "relationship_types": ["MENTIONS"],
        "indexes": [{"name": "entity", "type": "FULLTEXT", "state": "ONLINE",
                     "labelsOrTypes": ["Organization"], "properties": ["name"]}],
        "property_samples": {
            "Organization": {
                "name": {"samples": ["Acme"], "non_null_count": 1000, "inferred_semantic": "freetext"},
            },
        },
    }
    sc = _build_schema_context(schema_data)
    ps = _build_property_samples(schema_data)
    assert sc is not None, "schema_context should not be None when schema provided"
    assert ps is not None, "property_samples should not be None when schema provided"
    assert sc["labels"] == ["Organization", "Article"], "labels mismatch"
    assert "Organization" in ps, "Organization missing from property_samples"
    assert ps["Organization"]["name"]["inferred_semantic"] == "freetext", "semantic mismatch"
    # Raw sample values should be stripped from exported property_samples
    assert "samples" not in ps["Organization"]["name"], "raw samples should be excluded"

    print("  PASS: schema context loading", flush=True)

    # ----- Test 5: output-dir is created if missing -----
    with tempfile.TemporaryDirectory() as tmpdir:
        nested_dir = Path(tmpdir) / "deeply" / "nested" / "dataset"
        run_data = {
            "run_id": "run-test2",
            "started_at": "2026-03-20T12:00:00Z",
            "completed_at": "2026-03-20T12:00:01Z",
            "skill": "neo4j-cypher-authoring-skill",
            "summary": {"total": 1, "passed": 1, "warned": 0, "failed": 0, "pass_rate": 1.0},
            "cases": [case_pass],
        }
        input_path2 = Path(tmpdir) / "run2.json"
        with open(input_path2, "w") as f:
            json.dump(run_data, f)

        count3 = export(
            input_path=input_path2,
            domain="companies",
            output_dir=nested_dir,
            database="companies",
        )
        assert count3 == 1, f"Expected 1 new record, got {count3}"
        assert (nested_dir / "companies.yml").exists(), "Output file should exist in nested dir"

    print("  PASS: output directory created if missing", flush=True)

    # ----- Summary -----
    if errors:
        print("\nFAIL — errors:", flush=True)
        for e in errors:
            print(f"  {e}", flush=True)
        sys.exit(1)
    else:
        print("\nAll smoke tests passed.", flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No args — run smoke tests
        _run_smoke_tests()
    else:
        sys.exit(main())
