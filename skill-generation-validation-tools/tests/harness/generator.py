#!/usr/bin/env python3
"""
generator.py — Question generator for the neo4j-cypher-authoring-skill test harness.

Connects to a Neo4j database, inspects the schema, samples property values,
infers property semantics, calls the Claude API to generate questions at four
difficulty tiers, auto-executes candidate Cypher to capture PROFILE baselines,
applies tolerance multipliers, and writes YAML test stubs for human review.

Output is written to tests/cases/{domain}-generated.yml — NOT tests/cases/{domain}.yml.
Human promotion required before the stubs are used by the runner.

Usage:
    uv run python3 tests/harness/generator.py \\
        --domain companies \\
        --database companies \\
        --output-dir tests/cases/ \\
        [--counts 5 5 3 2] \\
        [--neo4j-uri neo4j+s://demo.neo4jlabs.com:7687] \\
        [--neo4j-username companies] \\
        [--neo4j-password companies] \\
        [--dry-run]

Environment variables (override with CLI flags):
    NEO4J_URI       — Neo4j connection URI (default: bolt://localhost:7687)
    NEO4J_USERNAME  — Neo4j username (default: neo4j)
    NEO4J_PASSWORD  — Neo4j password (default: neo4j)
    ANTHROPIC_API_KEY — Required for Claude API calls
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_HERE))

# ---------------------------------------------------------------------------
# YAML output helpers (stdlib only — no ruamel needed for generation)
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
# Model ID mapping (mirrors runner.py)
# ---------------------------------------------------------------------------

_MODEL_MAP: dict[str, str] = {
    "sonnet": "claude-sonnet-4-6",
    "opus":   "claude-opus-4-5",
    "haiku":  "claude-haiku-4-5",
}
_DEFAULT_MODEL_ID = "claude-sonnet-4-6"


def resolve_model_id(model_short: Optional[str]) -> str:
    """Resolve short model name to full model ID; pass-through full IDs unchanged."""
    if model_short is None:
        return _DEFAULT_MODEL_ID
    return _MODEL_MAP.get(model_short, model_short)


# ---------------------------------------------------------------------------
# Neo4j driver
# ---------------------------------------------------------------------------


def _get_driver(
    uri: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Any:
    """Create and return a neo4j driver; exits on ImportError."""
    try:
        import neo4j  # type: ignore
    except ImportError:
        print(
            "ERROR: neo4j package not installed. Install with: uv add neo4j",
            file=sys.stderr,
        )
        sys.exit(1)

    uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    username = username or os.environ.get("NEO4J_USERNAME", "neo4j")
    password = password or os.environ.get("NEO4J_PASSWORD", "neo4j")
    return neo4j.GraphDatabase.driver(uri, auth=(username, password))


# ---------------------------------------------------------------------------
# Schema inspection
# ---------------------------------------------------------------------------


def detect_capabilities(driver: Any, database: str) -> dict[str, Any]:
    """
    Detect optional plugins by counting procedures with known prefixes.

    Returns a dict with:
        capabilities: list[str]  — e.g. ['gds', 'apoc', 'apoc-extended', 'genai']
    """
    _CHECKS = [
        ("gds", "gds."),
        ("apoc", "apoc."),
        ("genai", "ai."),
    ]
    capabilities: list[str] = []
    for key, prefix in _CHECKS:
        try:
            records, _, _ = driver.execute_query(
                "SHOW PROCEDURES YIELD name WHERE name STARTS WITH $prefix RETURN count(*) AS cnt",
                prefix=prefix,
                database_=database,
            )
            cnt = int(records[0]["cnt"]) if records else 0
            if cnt > 0:
                capabilities.append(key)
                # If apoc procedures > ~400 it's likely apoc-extended too
                if key == "apoc" and cnt > 400:
                    capabilities.append("apoc-extended")
        except Exception as exc:
            print(f"  WARNING: capability detection for '{prefix}' failed: {exc}", file=sys.stderr)
    return {"capabilities": capabilities}


def inspect_schema(driver: Any, database: str) -> dict[str, Any]:
    """
    Inspect the Neo4j schema: node labels, relationship types, property keys,
    index information, and optional plugin capabilities.

    Returns a dict with:
        labels: list of node label strings
        relationship_types: list of relationship type strings
        indexes: list of index info dicts (name, type, state, labelsOrTypes, properties)
        node_properties: {label: [property_name, ...]}
        rel_properties: {rel_type: [property_name, ...]}
        gds: bool
        capabilities: list[str]
    """
    schema: dict[str, Any] = {
        "labels": [],
        "relationship_types": [],
        "indexes": [],
        "node_properties": {},
        "rel_properties": {},
        "capabilities": [],
    }

    # Labels
    records, _, _ = driver.execute_query(
        "CALL db.labels() YIELD label RETURN label ORDER BY label",
        database_=database,
    )
    schema["labels"] = [r["label"] for r in records]

    # Relationship types
    records, _, _ = driver.execute_query(
        "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType",
        database_=database,
    )
    schema["relationship_types"] = [r["relationshipType"] for r in records]

    # Indexes (SHOW INDEXES returns name, type, state, labelsOrTypes, properties)
    try:
        records, _, _ = driver.execute_query(
            "SHOW INDEXES YIELD name, type, state, labelsOrTypes, properties "
            "RETURN name, type, state, labelsOrTypes, properties ORDER BY name",
            database_=database,
        )
        schema["indexes"] = [
            {
                "name": r["name"],
                "type": r["type"],
                "state": r["state"],
                "labelsOrTypes": list(r["labelsOrTypes"] or []),
                "properties": list(r["properties"] or []),
            }
            for r in records
        ]
    except Exception as exc:
        print(f"  WARNING: SHOW INDEXES failed ({exc}); skipping index inspection", file=sys.stderr)

    # Node properties per label (via schema procedure if available, else skip)
    for label in schema["labels"]:
        try:
            records, _, _ = driver.execute_query(
                f"MATCH (n:`{label}`) "
                "WITH keys(n) AS props UNWIND props AS prop "
                "RETURN DISTINCT prop ORDER BY prop LIMIT 50",
                database_=database,
            )
            schema["node_properties"][label] = [r["prop"] for r in records]
        except Exception:
            schema["node_properties"][label] = []

    # Relationship properties per type
    for rel_type in schema["relationship_types"]:
        try:
            records, _, _ = driver.execute_query(
                f"MATCH ()-[r:`{rel_type}`]->() "
                "WITH keys(r) AS props UNWIND props AS prop "
                "RETURN DISTINCT prop ORDER BY prop LIMIT 20",
                database_=database,
            )
            schema["rel_properties"][rel_type] = [r["prop"] for r in records]
        except Exception:
            schema["rel_properties"][rel_type] = []

    # Detect optional plugins (GDS, APOC, GenAI)
    caps = detect_capabilities(driver, database)
    schema["capabilities"] = caps["capabilities"]

    return schema


# ---------------------------------------------------------------------------
# Property sampling using COLLECT subquery (Cypher 25)
# ---------------------------------------------------------------------------


def sample_property_values(
    driver: Any,
    database: str,
    label: str,
    prop: str,
    limit: int = 100,
) -> list[Any]:
    """
    Sample up to `limit` distinct values for `prop` on nodes with `label`.

    Uses COLLECT { MATCH ... RETURN DISTINCT ... LIMIT N } subquery form
    as required by the PRD (not collect()[..N]).
    """
    cypher = (
        f"CYPHER 25 "
        f"MATCH (n:`{label}`) WHERE n.`{prop}` IS NOT NULL "
        f"WITH COLLECT {{ MATCH (m:`{label}`) WHERE m.`{prop}` IS NOT NULL "
        f"RETURN DISTINCT m.`{prop}` LIMIT {limit} }} AS samples "
        f"RETURN samples LIMIT 1"
    )
    try:
        records, _, _ = driver.execute_query(cypher, database_=database)
        if records:
            return list(records[0]["samples"])
    except Exception as exc:
        print(
            f"  WARNING: property sampling failed for {label}.{prop}: {exc}",
            file=sys.stderr,
        )
    return []


def count_non_null(
    driver: Any,
    database: str,
    label: str,
    prop: str,
) -> int:
    """Count the number of nodes that have a non-null value for `prop`."""
    cypher = (
        f"CYPHER 25 "
        f"MATCH (n:`{label}`) WHERE n.`{prop}` IS NOT NULL "
        f"RETURN count(n) AS cnt"
    )
    try:
        records, _, _ = driver.execute_query(cypher, database_=database)
        if records:
            return int(records[0]["cnt"])
    except Exception:
        pass
    return 0


# ---------------------------------------------------------------------------
# Property semantics inference
# ---------------------------------------------------------------------------

# UUID pattern: 8-4-4-4-12 hex characters separated by dashes
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Long text pattern: more than 100 characters suggests freetext
_FREETEXT_MIN_LEN = 100


def infer_semantic(
    prop: str,
    samples: list[Any],
    non_null_count: int,
    total_node_count: int,
) -> str:
    """
    Infer the semantic category of a property from its name, sample values,
    and population density.

    Returns one of: uuid | range | enum | score | freetext | sparse | unknown
    """
    # Sparseness check runs first: applies even when sampling returns no values
    if non_null_count == 0:
        return "sparse"
    if total_node_count > 0 and non_null_count / total_node_count < 0.10:
        return "sparse"

    if not samples:
        return "unknown"

    # Check for UUID pattern
    str_samples = [s for s in samples if isinstance(s, str)]
    if str_samples and all(_UUID_RE.match(s) for s in str_samples[:10]):
        return "uuid"

    # Check for freetext: long string values
    if str_samples and any(len(s) > _FREETEXT_MIN_LEN for s in str_samples):
        return "freetext"

    # Check for score: float in [-1, 1] or [0, 1] range
    num_samples = [s for s in samples if isinstance(s, (int, float))]
    if num_samples:
        min_v = min(num_samples)
        max_v = max(num_samples)
        if min_v >= -1.0 and max_v <= 1.0:
            return "score"

    # Check for range: numeric values with high cardinality suggest continuous range
    if num_samples and len(set(num_samples)) > 20:
        return "range"

    # Check by property name heuristics before falling back to enum
    # (name is a stronger signal than low-cardinality samples for well-named properties)
    prop_lower = prop.lower()
    if any(kw in prop_lower for kw in ("uuid", "guid")):
        return "uuid"
    if any(kw in prop_lower for kw in ("score", "rating", "weight", "similarity", "sentiment")):
        return "score"
    if any(kw in prop_lower for kw in ("description", "text", "body", "content", "summary", "bio")):
        return "freetext"
    if any(kw in prop_lower for kw in ("date", "time", "year", "month", "age", "count", "num", "total")):
        return "range"

    # Check for enum: low-cardinality string or numeric values
    if len(samples) <= 30 and len(set(str(s) for s in samples)) <= 30:
        return "enum"

    # Remaining name-based heuristics
    if any(kw in prop_lower for kw in ("id", "key")):
        return "uuid"
    if any(kw in prop_lower for kw in ("type", "status", "category", "kind", "role", "gender")):
        return "enum"

    return "unknown"


# ---------------------------------------------------------------------------
# Schema context builder (for Claude prompt)
# ---------------------------------------------------------------------------


def build_schema_context(
    schema: dict[str, Any],
    property_samples: dict[str, dict[str, Any]],
) -> str:
    """
    Build a compact schema context string for the Claude prompt.

    Format:
        Labels: A, B, C
        Relationships: REL_A, REL_B
        Indexes: name (TYPE on Label.prop) [state]
        Node properties:
          Label: prop1 (enum), prop2 (range), ...
    """
    lines: list[str] = []

    labels = schema.get("labels", [])
    rel_types = schema.get("relationship_types", [])
    indexes = schema.get("indexes", [])

    lines.append(f"Labels: {', '.join(labels)}")
    lines.append(f"Relationships: {', '.join(rel_types)}")

    if indexes:
        lines.append("Indexes (ONLINE only):")
        for idx in indexes:
            if idx.get("state") == "ONLINE":
                lots = ", ".join(idx.get("labelsOrTypes") or [])
                props = ", ".join(idx.get("properties") or [])
                lines.append(f"  {idx['name']} ({idx['type']} on {lots}.{props})")

    lines.append("Node properties:")
    for label in labels:
        props_info = []
        for prop, info in property_samples.get(label, {}).items():
            sem = info.get("inferred_semantic", "unknown")
            props_info.append(f"{prop} ({sem})")
        if props_info:
            lines.append(f"  {label}: {', '.join(props_info)}")

    # Optional plugin capabilities (unified list: gds, apoc, apoc-extended, genai, ...)
    caps = schema.get("capabilities", [])
    if caps:
        lines.append(f"capabilities: [{', '.join(caps)}]  (optional plugins available — gds.* usable if 'gds' listed; apoc.* if 'apoc' listed)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Baseline metrics capture via PROFILE
# ---------------------------------------------------------------------------


def _profile_query(
    driver: Any,
    database: str,
    cypher: str,
) -> dict[str, Any]:
    """
    Execute a query with PROFILE and return observed metrics.

    Returns dict with: observed_count, observed_db_hits, observed_memory_bytes,
    observed_runtime_ms. Returns None for unavailable metrics.
    """
    # Import validator for profile extraction
    try:
        from validator import extract_profile_metrics  # type: ignore
    except ImportError:
        from tests.harness.validator import extract_profile_metrics  # type: ignore

    profile_cypher = "PROFILE " + cypher
    if cypher.lstrip().upper().startswith("CYPHER"):
        # Preserve the CYPHER pragma
        lines = cypher.strip().splitlines()
        profile_cypher = lines[0] + "\nPROFILE " + "\n".join(lines[1:]).lstrip()

    result: dict[str, Any] = {
        "observed_count": None,
        "observed_db_hits": None,
        "observed_memory_bytes": None,
        "observed_runtime_ms": None,
    }

    try:
        t0 = time.monotonic()
        records, summary, _ = driver.execute_query(profile_cypher, database_=database)
        elapsed_ms = (time.monotonic() - t0) * 1000.0

        result["observed_count"] = len(records)

        plan = getattr(summary, "profile", None)
        metrics = extract_profile_metrics(plan)
        result["observed_db_hits"] = metrics.get("totalDbHits")
        result["observed_memory_bytes"] = metrics.get("totalAllocatedMemory")
        elapsed = metrics.get("elapsedTimeMs")
        result["observed_runtime_ms"] = round(elapsed if elapsed is not None else elapsed_ms, 2)

    except Exception as exc:
        print(f"  WARNING: PROFILE failed for candidate query: {exc}", file=sys.stderr)

    return result


# ---------------------------------------------------------------------------
# Claude API — question + candidate Cypher generation
# ---------------------------------------------------------------------------

_DIFFICULTY_DESCRIPTIONS = {
    "basic": (
        "Simple MATCH + RETURN or MATCH + WHERE + RETURN on a single node label. "
        "No aggregation, no path traversal, no subqueries. "
        "Example: Find all Organization nodes, return their name and country."
    ),
    "intermediate": (
        "Two or more hops of relationship traversal, or simple aggregation (count, avg, sum). "
        "May use WITH to pipeline. One label per side of the relationship. "
        "Example: Find how many articles mention each organization; return top 10 by count."
    ),
    "advanced": (
        "Quantified path expressions (QPE), SEARCH clause (vector/fulltext), "
        "or CALL subquery. May use complex WHERE filters, UNWIND, or COLLECT subquery. "
        "Example: For each org, collect the titles of all articles mentioning it using QPE traversal."
    ),
    "complex": (
        "Multi-hop QPE with quantifiers {m,n}, CALL IN TRANSACTIONS batching, "
        "OPTIONAL CALL, or combination of vector search + graph traversal. "
        "Example: Find all organizations reachable within 2 hops of a given org via HAS_SUBSIDIARY, "
        "then retrieve the top 5 most recent articles mentioning any of them."
    ),
}

_SYSTEM_PROMPT = """\
You are an expert Neo4j Cypher 25 query author. Your task is to generate test
questions and valid Cypher queries for a given database schema and difficulty level.

Rules:
- Every query MUST begin with CYPHER 25 on the first line.
- Use QPE syntax (-[:REL]*-> or -[:REL]{m,n}->) instead of deprecated [:REL*].
- Use SHORTEST N instead of shortestPath() / allShortestPaths().
- Use elementId() instead of deprecated id().
- Use COLLECT { MATCH ... RETURN DISTINCT ... LIMIT N } for sampling (not collect()[..N]).
- Use CALL (x) { ... } scope clause instead of importing WITH inside CALL.
- Do NOT use GQL-only clauses: LET, FINISH, FILTER, NEXT, INSERT.
- Queries must be executable and return non-empty results on the given database.
- Return ONLY the JSON object described below — no markdown, no explanation.

Output format (JSON):
{
  "cases": [
    {
      "question": "Natural language question the query answers",
      "cypher": "CYPHER 25\\nMATCH ...",
      "is_write_query": false,
      "tags": ["match", "label"]
    }
  ]
}
"""


def _build_generation_prompt(
    schema_context: str,
    database: str,
    difficulty: str,
    count: int,
) -> str:
    desc = _DIFFICULTY_DESCRIPTIONS.get(difficulty, "")
    return (
        f"Database: {database}\n\n"
        f"Schema:\n{schema_context}\n\n"
        f"Generate exactly {count} test case(s) at difficulty: {difficulty}\n\n"
        f"Difficulty description: {desc}\n\n"
        f"Return a JSON object with a 'cases' array containing {count} entries.\n"
        f"Each entry needs: question (string), cypher (string starting with CYPHER 25), "
        f"is_write_query (bool, usually false), tags (list of strings)."
    )


def _invoke_claude_for_generation(
    prompt: str,
    *,
    timeout_s: int = 120,
    model_id: str = _DEFAULT_MODEL_ID,
) -> tuple[str, Optional[str]]:
    """
    Invoke Claude Code headless in print mode to generate test cases.

    model_id is the full Anthropic model ID (e.g. 'claude-sonnet-4-6').
    Use resolve_model_id() to convert a short name before calling.

    Returns (response_text, error_message).
    """
    cmd = ["claude", "--model", model_id, "--print", "--output-format", "text"]
    full_prompt = _SYSTEM_PROMPT + "\n\n---\n\n" + prompt

    try:
        result = subprocess.run(
            cmd,
            input=full_prompt,
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
        return "", "claude CLI not found — ensure 'claude' is on PATH and ANTHROPIC_API_KEY is set"
    except Exception as exc:
        return "", f"Unexpected error: {exc}"


def _parse_generation_response(response_text: str) -> list[dict[str, Any]]:
    """
    Parse Claude's JSON response and extract the 'cases' array.

    Handles cases where Claude wraps JSON in markdown code blocks.
    """
    # Strip markdown code blocks if present
    stripped = response_text.strip()
    json_match = re.search(r"```(?:json)?\s*\n(.*?)```", stripped, re.DOTALL)
    if json_match:
        stripped = json_match.group(1).strip()

    # Also try to find raw JSON object
    json_obj_match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if json_obj_match:
        stripped = json_obj_match.group(0)

    try:
        data = json.loads(stripped)
        return data.get("cases", [])
    except json.JSONDecodeError as exc:
        print(f"  WARNING: Failed to parse generation response as JSON: {exc}", file=sys.stderr)
        print(f"  Response text (first 500 chars): {response_text[:500]}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# YAML stub builder
# ---------------------------------------------------------------------------


def _build_case_id(domain: str, difficulty: str, index: int) -> str:
    """Build a test case ID like 'companies-basic-001'."""
    return f"{domain}-{difficulty}-{index:03d}"


def _compute_thresholds(observed: dict[str, Any]) -> dict[str, Any]:
    """
    Compute threshold values from observed baseline metrics.

    Tolerance multipliers:
        max_db_hits         = observed_db_hits × 3
        max_allocated_memory_bytes = observed_memory_bytes × 3
        max_runtime_ms      = observed_runtime_ms × 5  (CI timing sensitive)

    Returns a dict of threshold keys; None for any metric not observed.
    """
    thresholds: dict[str, Any] = {}

    db_hits = observed.get("observed_db_hits")
    if db_hits is not None:
        thresholds["max_db_hits"] = int(db_hits * 3)

    memory = observed.get("observed_memory_bytes")
    if memory is not None:
        thresholds["max_allocated_memory_bytes"] = int(memory * 3)

    runtime = observed.get("observed_runtime_ms")
    if runtime is not None:
        thresholds["max_runtime_ms"] = round(runtime * 5, 1)

    return thresholds


def _build_yaml_stub(
    case_id: str,
    question: str,
    cypher: str,
    difficulty: str,
    tags: list[str],
    is_write_query: bool,
    database: str,
    domain: str,
    observed: dict[str, Any],
    thresholds: dict[str, Any],
    property_semantics: dict[str, dict[str, str]],  # {label: {prop: semantic}}
) -> dict[str, Any]:
    """
    Build a single YAML test stub dict with all required fields.

    Inferred semantics are included as a top-level comment field for human review.
    """
    stub: dict[str, Any] = {
        "id": case_id,
        "question": question,
        "database": database,
        "domain": domain,
        "difficulty": difficulty,
        "tags": tags,
        "is_write_query": is_write_query,
        # Baseline observed metrics (captured by running candidate Cypher with PROFILE)
        "observed_count": observed.get("observed_count"),
        "observed_db_hits": observed.get("observed_db_hits"),
        "observed_memory_bytes": observed.get("observed_memory_bytes"),
        "observed_runtime_ms": observed.get("observed_runtime_ms"),
        # Tolerance-multiplied thresholds (pre-populated for human review/adjustment)
        "min_results": max(1, int(observed.get("observed_count") or 0)),
        **thresholds,
        # Candidate Cypher (auto-generated, requires human review before promotion)
        "candidate_cypher": cypher,
    }

    # Include inferred semantics as a structured field for human reviewers
    if property_semantics:
        semantics_flat = {}
        for label, props in property_semantics.items():
            for prop, sem in props.items():
                semantics_flat[f"{label}.{prop}"] = sem
        stub["inferred_semantics"] = semantics_flat

    return stub


# ---------------------------------------------------------------------------
# Main generation pipeline
# ---------------------------------------------------------------------------


def generate(
    domain: str,
    database: str,
    output_dir: Path,
    *,
    counts: Optional[dict[str, int]] = None,
    driver: Any,
    dry_run: bool = False,
    claude_timeout_s: int = 120,
    verbose: bool = False,
    model_id: str = _DEFAULT_MODEL_ID,
) -> Path:
    """
    Full generation pipeline:
      1. Inspect schema
      2. Sample property values + infer semantics
      3. For each difficulty tier, call Claude to generate questions + Cypher
      4. Execute candidate Cypher with PROFILE to capture baselines
      5. Write YAML stubs to {output_dir}/{domain}-generated.yml

    Returns the path to the written output file.
    """
    if counts is None:
        counts = {"basic": 5, "intermediate": 5, "advanced": 3, "complex": 2}

    output_path = output_dir / f"{domain}-generated.yml"

    print(f"[generator] Inspecting schema on database '{database}'...", flush=True)
    schema = inspect_schema(driver, database)

    if verbose:
        print(f"  Labels:         {schema['labels']}")
        print(f"  Rel types:      {schema['relationship_types']}")
        print(f"  ONLINE indexes: {sum(1 for i in schema['indexes'] if i.get('state') == 'ONLINE')}")
        print(f"  Capabilities:   {schema['capabilities']}")

    # Sample property values and infer semantics
    print("[generator] Sampling property values...", flush=True)
    property_samples: dict[str, dict[str, Any]] = {}  # {label: {prop: {samples, non_null_count, inferred_semantic}}}
    property_semantics: dict[str, dict[str, str]] = {}  # {label: {prop: semantic}}

    for label in schema["labels"]:
        props = schema["node_properties"].get(label, [])
        if not props:
            continue

        # Count total nodes for this label
        try:
            records, _, _ = driver.execute_query(
                f"CYPHER 25 MATCH (n:`{label}`) RETURN count(n) AS cnt",
                database_=database,
            )
            total_count = int(records[0]["cnt"]) if records else 0
        except Exception:
            total_count = 0

        property_samples[label] = {}
        property_semantics[label] = {}

        for prop in props:
            samples = sample_property_values(driver, database, label, prop, limit=100)
            non_null = count_non_null(driver, database, label, prop)
            semantic = infer_semantic(prop, samples, non_null, total_count)

            property_samples[label][prop] = {
                "samples": samples[:5],  # keep only 5 representative samples in output
                "non_null_count": non_null,
                "inferred_semantic": semantic,
            }
            property_semantics[label][prop] = semantic

            if verbose:
                print(f"  {label}.{prop}: {semantic} ({non_null} non-null, {len(samples)} samples)")

    # Build schema context for Claude
    schema_context = build_schema_context(schema, property_samples)

    if dry_run:
        print(f"[generator] DRY RUN — schema context built ({len(schema_context)} chars)")
        print("[generator] Would generate the following cases:")
        for difficulty, count in counts.items():
            print(f"  {difficulty}: {count} case(s)")
        print(f"[generator] Would write to: {output_path}")
        return output_path

    # Generate questions per difficulty tier
    all_stubs: list[dict[str, Any]] = []
    difficulty_counters: dict[str, int] = {d: 0 for d in counts}

    for difficulty, count in counts.items():
        if count <= 0:
            continue

        print(f"[generator] Generating {count} {difficulty} question(s) via Claude...", flush=True)
        prompt = _build_generation_prompt(schema_context, database, difficulty, count)
        response_text, error = _invoke_claude_for_generation(
            prompt, timeout_s=claude_timeout_s, model_id=model_id
        )

        if error:
            print(f"  WARNING: Claude generation failed for {difficulty}: {error}", file=sys.stderr)
            continue

        cases = _parse_generation_response(response_text)
        if not cases:
            print(f"  WARNING: No valid cases parsed from Claude response for {difficulty}", file=sys.stderr)
            continue

        for raw_case in cases:
            question = str(raw_case.get("question", ""))
            cypher = str(raw_case.get("cypher", ""))
            is_write_query = bool(raw_case.get("is_write_query", False))
            tags = list(raw_case.get("tags", []))

            if not question or not cypher:
                print(f"  WARNING: Skipping case with missing question or cypher", file=sys.stderr)
                continue

            difficulty_counters[difficulty] += 1
            case_id = _build_case_id(domain, difficulty, difficulty_counters[difficulty])

            print(f"  [{case_id}] Profiling: {question[:60]}...", flush=True)

            # Execute candidate Cypher with PROFILE to capture baselines
            observed = _profile_query(driver, database, cypher)
            thresholds = _compute_thresholds(observed)

            if verbose:
                print(
                    f"    count={observed.get('observed_count')}, "
                    f"dbHits={observed.get('observed_db_hits')}, "
                    f"memory={observed.get('observed_memory_bytes')}, "
                    f"runtime={observed.get('observed_runtime_ms')}ms"
                )

            stub = _build_yaml_stub(
                case_id=case_id,
                question=question,
                cypher=cypher,
                difficulty=difficulty,
                tags=tags,
                is_write_query=is_write_query,
                database=database,
                domain=domain,
                observed=observed,
                thresholds=thresholds,
                property_semantics=property_semantics,
            )
            all_stubs.append(stub)

    if not all_stubs:
        print("WARNING: No stubs generated — nothing to write.", file=sys.stderr)
        return output_path

    # Write YAML output
    output_dir.mkdir(parents=True, exist_ok=True)

    output_data = {
        "# GENERATED FILE — requires human review before promotion to {domain}.yml": None,
        "# Run generator.py again to refresh stubs from latest schema+Claude output": None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "database": database,
        "total_generated": len(all_stubs),
        "cases": all_stubs,
    }

    # Write with comments preamble manually since YAML comments aren't native
    with open(output_path, "w") as f:
        f.write(f"# GENERATED FILE — requires human review before promotion to {domain}.yml\n")
        f.write(f"# Run generator.py again to refresh stubs from latest schema+Claude output\n")
        f.write(f"# Generated: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"#\n")
        f.write(f"# HOW TO PROMOTE:\n")
        f.write(f"#   1. Review each case: verify question is sensible and cypher is correct\n")
        f.write(f"#   2. Check observed_count >= 1 (non-empty results)\n")
        f.write(f"#   3. Copy verified cases to tests/cases/{domain}.yml\n")
        f.write(f"#   4. Remove candidate_cypher, observed_*, inferred_semantics fields\n")
        f.write(f"#      (those are for review only — runner uses generated_cypher from Claude)\n")
        f.write(f"\n")
        yaml.dump(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "domain": domain,
                "database": database,
                "total_generated": len(all_stubs),
                "cases": all_stubs,
            },
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )

    print(f"[generator] Written {len(all_stubs)} stub(s) to: {output_path}", flush=True)
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Cypher test case stubs for the neo4j-cypher-authoring-skill harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--domain",
        required=True,
        help="Domain name used for case IDs and output filename (e.g. 'companies')",
    )
    parser.add_argument(
        "--database",
        default=None,
        help="Neo4j database name (default: same as --domain)",
    )
    parser.add_argument(
        "--output-dir",
        default="tests/cases",
        help="Directory to write the generated YAML file (default: tests/cases/)",
    )
    parser.add_argument(
        "--counts",
        nargs=4,
        type=int,
        metavar=("BASIC", "INTERMEDIATE", "ADVANCED", "COMPLEX"),
        default=[5, 5, 3, 2],
        help="Number of cases to generate per difficulty tier (default: 5 5 3 2)",
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
        help="Timeout in seconds for each Claude API call (default: 120)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect schema and print plan without calling Claude or writing output",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed progress including per-property semantics",
    )
    parser.add_argument(
        "--model",
        default=None,
        metavar="MODEL",
        help=(
            "Claude model to use for question generation. "
            "Short names: sonnet (default), haiku, opus. "
            "Or pass a full model ID (e.g. 'claude-sonnet-4-6'). "
            "Default: claude-sonnet-4-6."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    _require_yaml()

    args = _parse_args(argv)
    domain = args.domain
    database = args.database or domain
    output_dir = Path(args.output_dir)
    counts_list = args.counts  # [basic, intermediate, advanced, complex]
    counts = {
        "basic": counts_list[0],
        "intermediate": counts_list[1],
        "advanced": counts_list[2],
        "complex": counts_list[3],
    }

    model_id = resolve_model_id(getattr(args, "model", None))

    print(f"[generator] domain={domain} database={database}", flush=True)
    print(f"[generator] counts={counts}", flush=True)
    print(f"[generator] output_dir={output_dir}", flush=True)
    print(f"[generator] model={model_id}", flush=True)

    driver = _get_driver(args.neo4j_uri, args.neo4j_username, args.neo4j_password)

    try:
        output_path = generate(
            domain=domain,
            database=database,
            output_dir=output_dir,
            counts=counts,
            driver=driver,
            dry_run=args.dry_run,
            claude_timeout_s=args.timeout,
            verbose=args.verbose,
            model_id=model_id,
        )
        print(f"[generator] Done: {output_path}", flush=True)
        return 0
    except KeyboardInterrupt:
        print("\n[generator] Interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    finally:
        try:
            driver.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
