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
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_print_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Path setup — allow running from repo root or harness dir
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_HERE))

from validator import FAIL, PASS, WARN, ValidationResult, validate  # noqa: E402

SKIPPED = "SKIPPED"

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
    # Minimum Neo4j version required to run this test (YYYY.MM format, e.g. "2026.02")
    # Cases with min_version > detected server version are SKIPPED rather than FAIL.
    min_version: Optional[str] = None
    # Source file (set by loader)
    source_file: str = ""


@dataclass
class TestCaseResult:
    """Result of running a single test case through the full harness."""

    case_id: str
    question: str
    difficulty: str
    tags: list[str]
    verdict: str  # PASS | WARN | FAIL | SKIPPED
    failed_gate: Optional[int]
    warned_gate: Optional[int]
    generated_cypher: str
    metrics: dict[str, Any]
    gate_details: list[dict[str, Any]]
    error: Optional[str]  # Runner-level error (e.g. Claude invocation failed)
    duration_s: float
    skip_reason: Optional[str] = None  # Non-None when verdict == SKIPPED


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
    skipped: int
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
                min_version=str(raw["min_version"]) if raw.get("min_version") else None,
                source_file=str(f),
            )

            if difficulty_filter and tc.difficulty != difficulty_filter:
                continue
            if domain_filter and tc.domain != domain_filter:
                continue

            cases.append(tc)

    return cases


# ---------------------------------------------------------------------------
# Schema loading and formatting
# ---------------------------------------------------------------------------


def _format_schema_text(schema: dict[str, Any]) -> str:
    """
    Format a schema JSON dict as a compact, prompt-injectable text block.

    The formatted block is injected into the Claude prompt so the model can
    use exact label, relationship-type, property, and index names.
    """
    lines = ["=== DATABASE SCHEMA ==="]

    labels = schema.get("labels", [])
    rel_types = schema.get("relationship_types", [])
    indexes = schema.get("indexes", [])
    node_props = schema.get("node_properties", {})
    rel_props = schema.get("rel_properties", {})
    notes = schema.get("_notes", [])

    if labels:
        lines.append(f"Node Labels: {', '.join(labels)}")
    if rel_types:
        lines.append(f"Relationship Types: {', '.join(rel_types)}")

    online_indexes = [i for i in indexes if i.get("state") == "ONLINE"]
    if online_indexes:
        lines.append("Indexes (ONLINE):")
        for idx in online_indexes:
            lots = ", ".join(idx.get("labelsOrTypes") or [])
            props = ", ".join(idx.get("properties") or [])
            lines.append(f"  {idx['name']} — {idx['type']} on {lots}({props})")

    if node_props:
        lines.append("Node Properties:")
        for label, props in node_props.items():
            if props:
                lines.append(f"  {label}: {', '.join(props)}")

    rel_with_props = {rt: ps for rt, ps in rel_props.items() if ps}
    if rel_with_props:
        lines.append("Relationship Properties:")
        for rt, ps in rel_with_props.items():
            lines.append(f"  {rt}: {', '.join(ps)}")

    if notes:
        lines.append("Notes:")
        for note in notes:
            lines.append(f"  - {note}")

    lines.append("=========================")
    return "\n".join(lines)


def _load_domain_schema(domain: str, schema_dir: Path) -> Optional[str]:
    """
    Load a schema JSON file for a domain and return formatted schema text.

    Looks for {schema_dir}/{domain}.json or {schema_dir}/{domain}-schema.json.
    Returns None if no file is found.
    """
    candidates = [
        schema_dir / f"{domain}.json",
        schema_dir / f"{domain}-schema.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                with open(p) as f:
                    schema = json.load(f)
                return _format_schema_text(schema)
            except Exception as exc:
                print(
                    f"WARNING: could not load schema {p}: {exc}",
                    file=sys.stderr,
                )
    return None


def load_dataset_schemas(path: Path) -> dict[str, dict[str, Any]]:
    """
    Load dataset schema sections from YAML test case files.

    Reads the `dataset:` top-level key from each YAML file in the given path.
    Returns a dict mapping domain name → dataset dict.

    This is the primary mechanism for schema injection — schema is co-located
    with test cases in the same YAML file, not a separate schema directory.
    """
    files: list[Path] = []
    if path.is_dir():
        files = sorted(path.glob("*.yml")) + sorted(path.glob("*.yaml"))
    elif path.is_file():
        files = [path]
    else:
        return {}

    schemas: dict[str, dict[str, Any]] = {}
    for f in files:
        if f.name.endswith("-generated.yml"):
            continue  # Skip generator output stubs
        try:
            data = _load_yaml(f)
        except Exception:
            continue
        dataset = data.get("dataset")
        if dataset and isinstance(dataset, dict):
            domain = str(dataset.get("name") or f.stem)
            schemas[domain] = dataset
    return schemas


def _format_dataset_schema(dataset: dict[str, Any]) -> str:
    """
    Format a structured `dataset:` dict into a compact, prompt-injectable text block.

    The formatted block tells the model exactly which labels, relationship types,
    properties (with types, ranges, sample values), and indexes exist — so it
    uses correct names and avoids hallucinating schema elements.
    """
    lines: list[str] = []

    name = dataset.get("name", "unknown")
    database = dataset.get("database", name)
    description = str(dataset.get("description", "")).strip()
    connection = dataset.get("connection", {})
    schema = dataset.get("schema", {})
    notes = dataset.get("notes", [])

    lines.append(f"=== DATASET SCHEMA: {name} (database: {database}) ===")

    if description:
        lines.append(description)

    if connection:
        uri = connection.get("uri", "")
        user = connection.get("username", "")
        lines.append(f"Connection: {uri} | user: {user}")

    # ── Nodes ──────────────────────────────────────────────────────────────────
    nodes = schema.get("nodes", {})
    if nodes:
        lines.append("")
        lines.append("NODES:")
        for label, node_info in nodes.items():
            if not isinstance(node_info, dict):
                lines.append(f"  :{label}")
                continue
            node_desc = node_info.get("description", "")
            node_note = node_info.get("note", "")
            header = f"  :{label}"
            if node_desc:
                header += f"  — {node_desc}"
            if node_note:
                header += f"  [{node_note}]"
            lines.append(header)

            props = node_info.get("properties", {})
            for prop, prop_info in props.items():
                if not isinstance(prop_info, dict):
                    lines.append(f"    {prop}")
                    continue
                ptype = prop_info.get("type", "")
                parts = [f"    {prop}: {ptype}"]

                # Dimensions for VECTOR
                if "dimensions" in prop_info:
                    parts.append(f"({prop_info['dimensions']} dims)")
                # Numeric range
                if "min" in prop_info and "max" in prop_info:
                    parts.append(f"  range: {prop_info['min']}–{prop_info['max']}")
                elif "min" in prop_info:
                    parts.append(f"  min: {prop_info['min']}")
                # Enum values
                if "values" in prop_info:
                    vals = ", ".join(f'"{v}"' for v in prop_info["values"])
                    parts.append(f"  values: [{vals}]")
                # Sample values
                if "sample" in prop_info:
                    samples = prop_info["sample"]
                    if isinstance(samples, list) and samples:
                        # Skip nested lists (e.g. LIST_STRING sample lists)
                        flat = [s for s in samples if not isinstance(s, list)]
                        if flat:
                            sample_str = ", ".join(f'"{s}"' for s in flat[:3])
                            parts.append(f"  e.g. {sample_str}")
                # Description / note
                if "description" in prop_info:
                    parts.append(f"  — {prop_info['description']}")
                if "note" in prop_info:
                    parts.append(f"  [{prop_info['note']}]")

                lines.append("".join(parts))

    # ── Relationships ──────────────────────────────────────────────────────────
    relationships = schema.get("relationships", [])
    if relationships:
        lines.append("")
        lines.append("RELATIONSHIPS:")
        for rel in relationships:
            if not isinstance(rel, dict):
                continue
            rtype = rel.get("type", "?")
            rfrom = rel.get("from", "?")
            rto = rel.get("to", "?")
            rdesc = rel.get("description", "")
            rel_props = rel.get("properties", {})

            line = f"  (:{rfrom})-[:{rtype}]->(:{rto})"
            if rdesc:
                line += f"  — {rdesc}"
            lines.append(line)

            if isinstance(rel_props, dict):
                for prop, pinfo in rel_props.items():
                    if isinstance(pinfo, dict):
                        ptype = pinfo.get("type", "")
                        pdesc = pinfo.get("description", "")
                        pline = f"    .{prop}: {ptype}"
                        if pdesc:
                            pline += f" — {pdesc}"
                        lines.append(pline)

    # ── Indexes ────────────────────────────────────────────────────────────────
    indexes = schema.get("indexes", [])
    if indexes:
        lines.append("")
        lines.append("INDEXES:")
        for idx in indexes:
            if not isinstance(idx, dict):
                continue
            iname = idx.get("name", "?")
            itype = idx.get("type", "?")
            ion = idx.get("on", "?")
            icall = idx.get("call", "")
            idesc = idx.get("description", "")
            idims = idx.get("dimensions")

            line = f"  {iname} — {itype} on {ion}"
            if idims:
                line += f" [{idims} dims]"
            if idesc:
                line += f"  ({idesc})"
            lines.append(line)
            if icall:
                lines.append(f"    Usage: {icall}")

    # ── Notes ──────────────────────────────────────────────────────────────────
    if notes:
        lines.append("")
        lines.append("IMPORTANT NOTES:")
        for note in notes:
            lines.append(f"  - {note}")

    lines.append("")
    lines.append("=========================")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cypher extraction from model response
# ---------------------------------------------------------------------------

_CYPHER_BLOCK_RE = re.compile(
    r"```(?:cypher|CYPHER)\s*\n(.*?)```",
    re.DOTALL,
)

_YAML_BLOCK_RE = re.compile(
    r"```(?:yaml|YAML)\s*\n(.*?)```",
    re.DOTALL,
)


def extract_cypher(response_text: str) -> Optional[str]:
    """
    Extract Cypher from a model response.

    Handles two output formats:
    1. Dual YAML format (preferred): ```yaml block with query_literals key
    2. Raw cypher block: ```cypher ... ``` (legacy / fallback)

    For the harness we prefer query_literals (uses literal values, executable
    without parameter injection). Falls back to query_parametrized if literals
    absent. Finally falls back to raw ```cypher block.

    Returns the Cypher source string (stripped), or None if not found.
    """
    # Try YAML dual-format block first
    yaml_m = _YAML_BLOCK_RE.search(response_text)
    if yaml_m and _YAML_AVAILABLE:
        try:
            data = yaml.safe_load(yaml_m.group(1))
            if isinstance(data, dict):
                # Prefer literals for harness execution (no parameter injection needed)
                for key in ("query_literals", "query_parametrized"):
                    if key in data and data[key]:
                        return str(data[key]).strip()
        except Exception:
            pass  # Fall through to raw cypher block

    # Fallback: raw ```cypher block
    m = _CYPHER_BLOCK_RE.search(response_text)
    if m:
        return m.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# Claude Code headless invocation
# ---------------------------------------------------------------------------


def _collect_value_hints(dataset: dict[str, Any]) -> Optional[str]:
    """
    Collect sample/enum/range data from the dataset schema into a compact hint block.

    Returns a formatted string of representative property values that Claude can use
    to write executable queries (real IDs, names, codes, etc.) rather than placeholder
    values.  Returns None when no schema value information is available.

    This is supplementary context — all fields (values, sample, min, max) are optional.
    """
    schema = dataset.get("schema", {})
    nodes = schema.get("nodes", {})
    if not nodes:
        return None

    hint_lines: list[str] = []

    for label, node_info in nodes.items():
        if not isinstance(node_info, dict):
            continue
        props = node_info.get("properties", {})
        label_hints: list[str] = []

        for prop, pinfo in props.items():
            if not isinstance(pinfo, dict):
                continue
            parts: list[str] = []

            # Enum / allowed values
            vals = pinfo.get("values")
            if vals and isinstance(vals, list):
                parts.append(f"values: {vals[:6]}")

            # Sample instances
            samples = pinfo.get("sample")
            if samples and isinstance(samples, list):
                flat = [s for s in samples if not isinstance(s, list)]
                if flat:
                    parts.append(f"e.g. {flat[:3]}")

            # Numeric range
            mn, mx = pinfo.get("min"), pinfo.get("max")
            if mn is not None and mx is not None:
                parts.append(f"range {mn}–{mx}")
            elif mn is not None:
                parts.append(f"min {mn}")
            elif mx is not None:
                parts.append(f"max {mx}")

            if parts:
                label_hints.append(f"  .{prop}: {'; '.join(parts)}")

        if label_hints:
            hint_lines.append(f":{label}")
            hint_lines.extend(label_hints)

    if not hint_lines:
        return None

    return (
        "REPRESENTATIVE DATA VALUES (use these for concrete parameters):\n"
        + "\n".join(hint_lines)
    )


def _build_claude_prompt(
    tc: TestCase,
    schema_text: Optional[str] = None,
    value_hints: Optional[str] = None,
) -> str:
    """
    Build the prompt sent to Claude Code for a test case.

    When schema_text is provided it is injected at the top of the prompt so
    the model can use exact label, relationship-type, property, and index names.

    When value_hints is provided (derived from schema sample/values/range data),
    it is appended after the schema block so the model can use realistic concrete
    values rather than placeholders — improving the executability of generated queries.
    """
    lines: list[str] = []

    # Schema context — injected first so the model sees it before the question
    if schema_text:
        lines.append(schema_text)
        lines.append("")

    # Value hints — real IDs, names, codes for concrete parameters
    if value_hints:
        lines.append(value_hints)
        lines.append("")

    lines.append(f"Database: {tc.database}")
    lines.append(f"Difficulty: {tc.difficulty}")
    if tc.tags:
        lines.append(f"Tags: {', '.join(str(t) for t in tc.tags)}")
    lines.append("")
    lines.append(
        "Write a Cypher 25 query to answer the following question.\n"
        "Return your answer as a ```yaml block with keys:\n"
        "  query_literals:      (query with literal values, directly executable)\n"
        "  query_parametrized:  (same query with $param placeholders)\n"
        "  parameters:          (map of param name → value)\n"
        "Also include a ```cypher block containing the literal query for quick reference."
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
# Version comparison utilities
# ---------------------------------------------------------------------------

_MIN_VERSION_RE = re.compile(r"^\d{4}\.\d+(\.\d+)?$")


def _parse_version(v: str) -> tuple[int, ...]:
    """
    Parse a Neo4j version string into a comparable tuple.

    Accepts YYYY.MM (e.g. "2026.02") or YYYY.MM.PATCH (e.g. "2026.02.1").
    Returns a tuple of ints for comparison, e.g. (2026, 2) or (2026, 2, 1).
    """
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def _version_satisfies(detected: str, required: str) -> bool:
    """
    Return True if detected_version >= required_version.

    Both strings are in YYYY.MM or YYYY.MM.PATCH format.
    Compares only the components present in `required` (prefix match).

    Examples:
        _version_satisfies("2026.02.1", "2026.02")   → True
        _version_satisfies("2026.01.0", "2026.02")   → False
        _version_satisfies("2026.03", "2026.02")     → True
    """
    detected_parts = _parse_version(detected)
    required_parts = _parse_version(required)

    # Pad detected to at least the length of required for safe comparison
    n = len(required_parts)
    detected_trimmed = detected_parts[:n] if len(detected_parts) >= n else detected_parts
    required_trimmed = required_parts[:n]

    return detected_trimmed >= required_trimmed


def detect_server_version(driver: Any) -> Optional[str]:
    """
    Query dbms.components() to detect the Neo4j server version.

    Returns a version string like "2026.02.1" or None on failure.
    """
    if driver is None:
        return None
    try:
        records, _, _ = driver.execute_query(
            "CALL dbms.components() YIELD name, versions WHERE name = 'Neo4j Kernel' "
            "RETURN versions[0] AS version",
            database_="system",
        )
        if records:
            raw = str(records[0]["version"])
            # Strip any suffix like "-enterprise" or "-aura"
            version = raw.split("-")[0].strip()
            return version
    except Exception:
        # Some editions / Aura may not expose dbms.components in system db;
        # fall back to neo4j db
        try:
            records, _, _ = driver.execute_query(
                "CALL dbms.components() YIELD name, versions WHERE name = 'Neo4j Kernel' "
                "RETURN versions[0] AS version",
            )
            if records:
                raw = str(records[0]["version"])
                version = raw.split("-")[0].strip()
                return version
        except Exception:
            pass
    return None


def _validate_min_version_format(v: str) -> bool:
    """Return True if v matches YYYY.MM or YYYY.MM.PATCH pattern."""
    return bool(_MIN_VERSION_RE.match(v))


# ---------------------------------------------------------------------------
# Neo4j driver setup
# ---------------------------------------------------------------------------


def _load_integration_env(path: Optional[Path] = None) -> dict[str, str]:
    """
    Load an integration.env file (KEY=VALUE lines, # comments ignored).

    Searches in order: explicit path, ./integration.env, tests/integration.env,
    skill-generation-validation-tools/integration.env.

    Returns an empty dict if no file is found.
    """
    candidates: list[Path] = []
    if path:
        candidates.append(path)
    candidates += [
        Path("integration.env"),
        _HERE.parent / "integration.env",
        _REPO_ROOT / "integration.env",
    ]
    for p in candidates:
        if p.exists():
            env: dict[str, str] = {}
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()
            return env
    return {}


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


def _build_domain_drivers(
    dataset_schemas: dict[str, dict[str, Any]],
    integration_env: dict[str, str],
    fallback_password: Optional[str] = None,
) -> dict[str, Any]:
    """
    Create per-domain Neo4j drivers from dataset YAML connection info.

    Password resolution order per domain:
    1. integration.env key  {DOMAIN}_PASSWORD  (e.g. COMPANIES_PASSWORD)
    2. Env var              NEO4J_{DOMAIN}_PASSWORD
    3. Same as username     (demo.neo4jlabs.com pattern: user == password)
    4. fallback_password    (from --neo4j-password CLI arg)

    Returns a dict mapping domain name → driver (or None if neo4j not installed).
    """
    try:
        import neo4j  # type: ignore
    except ImportError:
        return {}

    drivers: dict[str, Any] = {}
    for domain, dataset in dataset_schemas.items():
        connection = dataset.get("connection", {})
        uri = connection.get("uri") or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        username = connection.get("username") or os.environ.get("NEO4J_USERNAME", "neo4j")

        domain_key = domain.upper()
        password = (
            integration_env.get(f"{domain_key}_PASSWORD")
            or os.environ.get(f"NEO4J_{domain_key}_PASSWORD")
            or username  # demo.neo4jlabs.com convention: password == username
            or fallback_password
            or "neo4j"
        )

        try:
            drivers[domain] = neo4j.GraphDatabase.driver(uri, auth=(username, password))
        except Exception as exc:
            print(f"WARNING: could not create driver for domain '{domain}': {exc}", file=sys.stderr)

    return drivers


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
    schema_text: Optional[str] = None,
    value_hints: Optional[str] = None,
    server_version: Optional[str] = None,
) -> TestCaseResult:
    """
    Run a single test case end-to-end.

    Dry-run mode skips Claude invocation and Neo4j execution; validates only
    that the TestCase struct loaded correctly and returns a synthetic PASS.

    When server_version is provided (or auto-detected), cases with min_version
    greater than the detected version are recorded as SKIPPED rather than executed.
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

    # Version gate: skip case if min_version requirement is not met
    if tc.min_version and server_version:
        if not _version_satisfies(server_version, tc.min_version):
            skip_reason = (
                f"Server version {server_version!r} < min_version {tc.min_version!r}"
            )
            return TestCaseResult(
                case_id=tc.id,
                question=tc.question,
                difficulty=tc.difficulty,
                tags=tc.tags,
                verdict=SKIPPED,
                failed_gate=None,
                warned_gate=None,
                generated_cypher="",
                metrics={},
                gate_details=[],
                error=None,
                duration_s=round(time.monotonic() - t0, 3),
                skip_reason=skip_reason,
            )

    # Step 1: invoke Claude Code headless
    prompt = _build_claude_prompt(tc, schema_text=schema_text, value_hints=value_hints)
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


def _run_case_buffered(
    tc: TestCase,
    skill_name: str,
    driver: Any,
    *,
    idx: int,
    total: int,
    dry_run: bool,
    claude_timeout_s: int,
    schema_text: Optional[str],
    value_hints: Optional[str],
    verbose: bool,
    server_version: Optional[str] = None,
) -> tuple["TestCaseResult", list[str]]:
    """Run a single case and return (result, log_lines) for atomic printing."""
    log_lines: list[str] = []
    if verbose:
        log_lines.append(
            f"[{idx}/{total}] {tc.id} ({tc.difficulty}) — {tc.question[:60]}..."
        )
    result = run_case(
        tc, skill_name, driver,
        dry_run=dry_run,
        claude_timeout_s=claude_timeout_s,
        schema_text=schema_text,
        value_hints=value_hints,
        server_version=server_version,
    )
    if verbose:
        gate_info = ""
        if result.failed_gate:
            gate_info = f" [GATE {result.failed_gate}]"
        elif result.warned_gate:
            gate_info = f" [GATE {result.warned_gate}]"
        symbol = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗", "SKIPPED": "—"}.get(result.verdict, "?")
        skip_info = f" ({result.skip_reason})" if result.skip_reason else ""
        log_lines.append(f"  {symbol} {result.verdict}{gate_info}{skip_info}")
    return result, log_lines


def run_all(
    cases: list[TestCase],
    skill_name: str,
    driver: Any,
    *,
    dry_run: bool = False,
    claude_timeout_s: int = 120,
    verbose: bool = False,
    cases_path: Optional[Path] = None,
    schema_dir: Optional[Path] = None,
    workers: int = 1,
    integration_env: Optional[dict[str, str]] = None,
    fallback_password: Optional[str] = None,
    neo4j_version: Optional[str] = None,
) -> RunReport:
    """
    Run all test cases and return an aggregate RunReport.

    Schema injection priority:
    1. Primary: dataset: sections in YAML case files (co-located schema)
    2. Override: external JSON/YAML files in schema_dir (for shared/externalized schema)

    Driver selection per case:
    - If the domain has a dataset: connection section, a domain-specific driver is used.
    - Falls back to the shared `driver` arg for domains without connection info.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"

    # Pre-load schema texts per domain (avoid reloading on every case)
    # Primary source: dataset: sections in YAML case files (co-located schema)
    # Override source: external JSON/YAML files in schema_dir (for shared/externalized schema)
    schema_cache: dict[str, Optional[str]] = {}

    # Value hints cache: domain → formatted sample/enum/range data for prompt injection
    value_hints_cache: dict[str, Optional[str]] = {}

    # Per-domain drivers (each domain may connect to a different Neo4j instance/user)
    domain_drivers: dict[str, Any] = {}

    if cases_path:
        dataset_schemas = load_dataset_schemas(cases_path)
        for domain, dataset in dataset_schemas.items():
            schema_cache[domain] = _format_dataset_schema(dataset)
            value_hints_cache[domain] = _collect_value_hints(dataset)
            if verbose:
                hint_note = " (with value hints)" if value_hints_cache[domain] else ""
                print(f"[schema] Loaded dataset schema for '{domain}' from YAML{hint_note}", flush=True)

        # Build per-domain drivers from connection info in dataset YAML
        if not dry_run:
            domain_drivers = _build_domain_drivers(
                dataset_schemas,
                integration_env or {},
                fallback_password=fallback_password,
            )
            for domain, d in domain_drivers.items():
                if verbose:
                    ds = dataset_schemas[domain]
                    uri = ds.get("connection", {}).get("uri", "default")
                    user = ds.get("connection", {}).get("username", "default")
                    print(f"[driver] Domain '{domain}' → {uri} as {user}", flush=True)

    if schema_dir:
        unique_domains = {tc.domain for tc in cases}
        for domain in unique_domains:
            schema_text = _load_domain_schema(domain, schema_dir)
            if schema_text:
                schema_cache[domain] = schema_text  # Override with external schema
                if verbose:
                    print(f"[schema] Override schema for '{domain}' from {schema_dir}", flush=True)

    # Warn about domains with no schema
    warned_domains: set[str] = set()
    for tc in cases:
        if tc.domain not in warned_domains and (
            tc.domain not in schema_cache or not schema_cache.get(tc.domain)
        ):
            print(
                f"WARNING: No schema found for domain '{tc.domain}' — "
                "add a dataset: section to the YAML file or use --schema-dir.",
                file=sys.stderr,
                flush=True,
            )
            warned_domains.add(tc.domain)

    # Version detection: use provided flag value, or auto-detect from DB
    server_version: Optional[str] = neo4j_version
    has_version_gated_cases = any(tc.min_version for tc in cases)
    if has_version_gated_cases and not dry_run and server_version is None:
        detect_driver = driver or next(iter(domain_drivers.values()), None)
        if detect_driver:
            server_version = detect_server_version(detect_driver)
            if verbose:
                if server_version:
                    print(f"[version] Auto-detected server version: {server_version}", flush=True)
                else:
                    print(
                        "[version] WARNING: Could not auto-detect server version; "
                        "version-gated cases will NOT be skipped.",
                        flush=True,
                    )

    results: list[TestCaseResult] = []
    passed = warned = failed = skipped = 0
    n_workers = max(1, min(workers, len(cases)))

    if n_workers == 1:
        # Serial execution
        for i, tc in enumerate(cases, 1):
            schema_text = schema_cache.get(tc.domain)
            value_hints = value_hints_cache.get(tc.domain)
            tc_driver = domain_drivers.get(tc.domain, driver)
            result, log_lines = _run_case_buffered(
                tc, skill_name, tc_driver,
                idx=i, total=len(cases),
                dry_run=dry_run,
                claude_timeout_s=claude_timeout_s,
                schema_text=schema_text,
                value_hints=value_hints,
                verbose=verbose,
                server_version=server_version,
            )
            for line in log_lines:
                print(line, flush=True)
            results.append(result)
            if result.verdict == PASS:
                passed += 1
            elif result.verdict == WARN:
                warned += 1
            elif result.verdict == SKIPPED:
                skipped += 1
            else:
                failed += 1
    else:
        # Parallel execution: submit all, collect as completed, print atomically
        if verbose:
            print(f"[parallel] Running {len(cases)} cases across {n_workers} workers", flush=True)
        # Map future → submission index for result ordering
        future_to_idx: dict[concurrent.futures.Future, int] = {}
        idx_to_result: dict[int, TestCaseResult] = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
            for i, tc in enumerate(cases, 1):
                schema_text = schema_cache.get(tc.domain)
                value_hints = value_hints_cache.get(tc.domain)
                tc_driver = domain_drivers.get(tc.domain, driver)
                future = executor.submit(
                    _run_case_buffered,
                    tc, skill_name, tc_driver,
                    idx=i, total=len(cases),
                    dry_run=dry_run,
                    claude_timeout_s=claude_timeout_s,
                    schema_text=schema_text,
                    value_hints=value_hints,
                    verbose=verbose,
                    server_version=server_version,
                )
                future_to_idx[future] = i

            for future in concurrent.futures.as_completed(future_to_idx):
                i = future_to_idx[future]
                try:
                    result, log_lines = future.result()
                except Exception as exc:
                    # Shouldn't reach here — _run_case_buffered is exception-safe
                    log_lines = [f"[worker error on case {i}] {exc}"]
                    result = None  # type: ignore

                with _print_lock:
                    for line in log_lines:
                        print(line, flush=True)

                if result is not None:
                    idx_to_result[i] = result
                    if result.verdict == PASS:
                        passed += 1
                    elif result.verdict == WARN:
                        warned += 1
                    elif result.verdict == SKIPPED:
                        skipped += 1
                    else:
                        failed += 1

        # Restore submission order for the report
        results = [idx_to_result[i] for i in sorted(idx_to_result)]

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
        skipped=skipped,
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
        "skip_reason": r.skip_reason,
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
            "skipped": report.skipped,
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

        if tc.min_version is not None and not _validate_min_version_format(tc.min_version):
            errors.append(
                f"{prefix} min_version {tc.min_version!r} must be in YYYY.MM or YYYY.MM.PATCH format "
                "(e.g. '2026.02' or '2026.02.1')"
            )

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
        "--schema-dir",
        default=None,
        help=(
            "Optional path to a directory of external schema JSON/YAML files ({domain}.json or {domain}-schema.json). "
            "Overrides the dataset: section in YAML files. "
            "Use when schema needs to be shared across multiple test files."
        ),
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-case progress to stdout",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        metavar="N",
        help=(
            "Number of parallel workers for Claude invocations (default: 1 = serial). "
            "Each worker runs an independent claude subprocess. "
            "Per-domain Neo4j drivers are created from dataset YAML connection info."
        ),
    )
    parser.add_argument(
        "--integration-env",
        default=None,
        help=(
            "Path to an integration.env file with per-domain passwords "
            "(format: DOMAIN_PASSWORD=secret). "
            "Searched automatically in ./integration.env and tests/integration.env if not set."
        ),
    )
    parser.add_argument(
        "--neo4j-version",
        default=None,
        metavar="VERSION",
        help=(
            "Neo4j server version to use for min_version filtering (e.g. '2026.01', '2026.02'). "
            "When omitted, version is auto-detected via dbms.components() if any test case has min_version set. "
            "Format: YYYY.MM or YYYY.MM.PATCH."
        ),
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

    # Load integration credentials (per-domain passwords)
    integ_env_path = Path(args.integration_env) if getattr(args, "integration_env", None) else None
    integration_env = _load_integration_env(integ_env_path)

    # Set up fallback Neo4j driver (used for domains without dataset: connection info)
    driver = _get_driver(args.neo4j_uri, args.neo4j_username, args.neo4j_password)

    # External schema override directory (optional — schema lives in YAML files by default)
    schema_dir: Optional[Path] = None
    if getattr(args, "schema_dir", None):
        schema_dir = Path(args.schema_dir)

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
        cases_path=cases_path,
        schema_dir=schema_dir,
        workers=args.workers,
        integration_env=integration_env,
        fallback_password=args.neo4j_password,
        neo4j_version=getattr(args, "neo4j_version", None),
    )

    # Print summary
    skipped_note = f", {report.skipped} SKIPPED" if report.skipped else ""
    print(
        f"\nResults: {report.passed}/{report.total} PASS, "
        f"{report.warned} WARN, {report.failed} FAIL{skipped_note}",
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
