#!/usr/bin/env python3
"""
validate_queries.py — batch-validate queries/queries.cypher against the live DB.

Run from the project work directory (where .env lives):
    python3 "${CLAUDE_SKILL_DIR}/scripts/validate_queries.py"

Substitutes $param placeholders (comment defaults like `// $minAge = 30` first,
then built-in defaults), runs all queries, and prints a pass/fail table.
Exit 0 only when the stage-6 gate holds: ≥5 queries, ≥2 traversal queries
(`->` or `<-` anywhere in the query), ≥3 queries returning ≥1 row.
Exit 1 if the gate fails; exit 2 on setup errors (no file, no connection).
"""
import os
import re
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # fall back to env vars already set

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j package not installed. Run: pip install neo4j", file=sys.stderr)
    sys.exit(2)

# ── Read sample_id from progress.md (written by 4-load) ─────────────────────
def _read_sample_id() -> str:
    progress = Path("progress.md")
    if progress.exists():
        m = re.search(r"^sample_id=(.+)$", progress.read_text(), re.MULTILINE)
        if m:
            val = m.group(1).strip().strip('"').strip("'")
            if val:
                return val
    # Fallback: first row of primary node CSV
    for csv_path in sorted(Path("data").glob("*.csv")) if Path("data").exists() else []:
        try:
            import csv as _csv
            with open(csv_path) as f:
                row = next(_csv.DictReader(f), None)
                if row:
                    for key in ("id", "ID", next(iter(row))):
                        if key in row:
                            return row[key]
        except Exception:
            pass
    return "p1"

SAMPLE_ID = _read_sample_id()

# ── Locate queries file ───────────────────────────────────────────────────────
candidates = [Path("queries/queries.cypher"), Path("queries.cypher")]
queries_file = next((p for p in candidates if p.exists()), None)
if not queries_file:
    print("ERROR: queries/queries.cypher not found", file=sys.stderr)
    sys.exit(2)

# ── Parse queries (split on ; , skip comment-only segments) ──────────────────
text = queries_file.read_text()
segments = text.split(";")
queries = []
for seg in segments:
    content_lines = [
        ln for ln in seg.splitlines()
        if ln.strip() and not ln.strip().startswith("//")
    ]
    if content_lines:
        queries.append(seg.strip())

if not queries:
    print("ERROR: no queries found in", queries_file, file=sys.stderr)
    sys.exit(2)

# ── Connect ────────────────────────────────────────────────────────────────────
uri      = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
user     = os.environ.get("NEO4J_USERNAME", "neo4j")
password = os.environ.get("NEO4J_PASSWORD", "")
database = os.environ.get("NEO4J_DATABASE", "neo4j")

if not password:
    print("ERROR: NEO4J_PASSWORD not set. Source .env or set the variable.", file=sys.stderr)
    sys.exit(2)

driver = GraphDatabase.driver(uri, auth=(user, password))
try:
    driver.verify_connectivity()
except Exception as e:
    print(f"ERROR: cannot connect to {uri}: {e}", file=sys.stderr)
    sys.exit(2)

# ── Run each query ─────────────────────────────────────────────────────────────
PARAM_DEFAULTS = {
    r"\$id\b":          f"'{SAMPLE_ID}'",
    r"\$\w*[Ii]d\b":    f"'{SAMPLE_ID}'",  # personId, userId, nodeId etc.
    r"\$limit\b":       "10",
    r"\$threshold\b":   "0",
    r"\$searchTerm\b":  "'test'",
    r"\$embedding\b":   "[]",
    r"\$\w+":           "'test'",   # fallback for any remaining $param
}

COMMENT_DEFAULT = re.compile(r"^\s*//\s*\$(\w+)\s*=\s*(.+?)\s*(?:←.*)?$", re.MULTILINE)

def _cypher_literal(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1].replace("\\", "\\\\").replace("'", "\\'")
        return f"'{inner}'"
    return value  # numbers, booleans, lists — used as written

def substitute_params(q: str) -> tuple[str, list[str]]:
    # 1) comment defaults declared in the query: // $name = value
    for name, value in COMMENT_DEFAULT.findall(q):
        q = re.sub(rf"\${name}\b", lambda _m, v=_cypher_literal(value): v, q)
    # 2) built-in defaults; track params that fall through to 'test'
    guessed = []
    for pattern, default in PARAM_DEFAULTS.items():
        if pattern == r"\$\w+":
            guessed = re.findall(r"\$(\w+)", "\n".join(
                ln for ln in q.splitlines() if not ln.strip().startswith("//")))
        q = re.sub(pattern, lambda _m, d=default: d, q)
    return q, guessed

passed = 0
results = []

def _is_traversal(q: str) -> bool:
    body = "\n".join(ln for ln in q.splitlines() if not ln.strip().startswith("//"))
    return "->" in body or "<-" in body

for i, raw_query in enumerate(queries, 1):
    test_query, guessed = substitute_params(raw_query)
    if guessed:
        print(f"WARN Q{i}: no default for ${', $'.join(guessed)} — guessed 'test'; "
              f"add a `// $name = value` comment", file=sys.stderr)
    # extract first non-comment line for display
    label = next(
        (ln.strip() for ln in raw_query.splitlines()
         if ln.strip() and not ln.strip().startswith("//")),
        "(empty)"
    )[:70]
    try:
        records, _, _ = driver.execute_query(test_query, database_=database)
        row_count = len(records)
        results.append((i, True,  row_count, label, _is_traversal(raw_query)))
        passed += 1
    except Exception as e:
        results.append((i, False, str(e)[:80], label, _is_traversal(raw_query)))

driver.close()

# ── Report ─────────────────────────────────────────────────────────────────────
print(f"\nQuery validation — {queries_file}")
print(f"{'Q':<4} {'Status':<8} {'Rows/Error':<12}  Query")
print("-" * 80)
for qnum, ok, detail, label, _ in results:
    icon   = "✓" if ok else "✗"
    detail_str = str(detail)
    print(f"Q{qnum:<3} {icon:<8} {detail_str:<12}  {label}")

traversals = sum(1 for r in results if r[4])
with_rows  = sum(1 for r in results if r[1] and r[2] > 0)
print(f"\n{passed}/{len(queries)} executed  |  {with_rows} returned rows  |  "
      f"{traversals} traversal queries detected")

problems = []
if len(queries) < 5:
    problems.append(f"need ≥5 queries (have {len(queries)})")
if traversals < 2:
    problems.append(f"need ≥2 traversal queries (have {traversals})")
if with_rows < 3:
    problems.append(f"need ≥3 queries returning ≥1 row (have {with_rows})")
if problems:
    print("FAIL: " + "; ".join(problems) + ". Fix queries before proceeding.")
    sys.exit(1)
print("PASS" + (f" ({len(queries) - passed} query error(s) — fix them)" if passed < len(queries) else ""))
sys.exit(0)
