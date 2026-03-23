# skill-generation-validation-tools

Test harness, schema generator, and analysis tooling for the **neo4j-cypher-authoring-skill**.

Validates that the skill produces correct, executable Cypher by submitting questions to Claude Code with the skill loaded, extracting the generated query, and running it against a real Neo4j database through a four-gate validation pipeline.

---

## Quick Start

```bash
# Validate all YAML test cases (syntax check — no DB, no Claude)
make dry-run

# Run a specific domain
make test-companies
make test-ucfraud

# Run all domains sequentially
make test-all

# Analyze the latest results
make analyze
```

All harness runs require:
- `ANTHROPIC_API_KEY` set in the environment
- A running Neo4j instance for the target domain (see domain table below)

---

## Architecture

```
skill-generation-validation-tools/
├── tests/
│   ├── cases/          # YAML test case files (one per domain)
│   ├── schemas/        # Pre-captured schema JSON files
│   ├── results/        # JSON + Markdown reports from harness runs
│   └── harness/
│       ├── runner.py   # Main test executor — submits to Claude, validates, reports
│       ├── validator.py  # Four-gate validation pipeline
│       ├── generator.py  # Schema-guided test case stub generator
│       ├── reporter.py   # JSON → Markdown report renderer
│       └── exporter.py   # Export validated cases as training JSONL
└── scripts/
    ├── extract-references.py       # Regenerates L3 reference files from Neo4j asciidoc
    ├── extract-changelog.py        # Extracts Cypher changelog from docs
    ├── analyze-results.py          # Cross-run analysis and trend reporting
    ├── test-extract-references.py  # Unit tests for the extractor
    └── to_jsonl.py                 # Convert YAML cases to JSONL format
```

---

## Validation Pipeline (Four Gates)

Every generated query passes through four gates in sequence. A query FAILs on the first gate that rejects it.

### Gate 1 — Syntax Pre-Check
Static regex checks before any DB execution:
- Query must begin with `CYPHER 25` pragma
- No GQL-only clauses: `\bLET\b`, `\bFINISH\b`, `\bFILTER\b`, `\bNEXT\b` (when not a relationship type like `[:NEXT]`), `\bINSERT\b`
- No deprecated operators: `!=` → use `<>`, `==` → use `=`

### Gate 2 — Execution Check
Runs the query against a real Neo4j database:
- **Read queries**: executed directly; validates row count ≥ `min_results`
- **Write queries**: executed inside a rolled-back write transaction (no data persisted)
- **`CALL IN TRANSACTIONS` queries**: executed via implicit transaction (auto-commit required by Neo4j)
- **Read-only databases**: write cases are `SKIPPED` (not FAIL)

### Gate 3 — Row Count Check
Validates `actual_rows >= min_results` (from the test case definition). Catches queries that run but return nothing useful.

### Gate 4 — Performance Check
Runs `PROFILE` and compares against baselines (captured when test cases were authored):
- `max_db_hits` — total DB hits across the query plan
- `max_allocated_memory_bytes` — total allocated memory
- `max_runtime_ms` — wall-clock execution time

Any threshold exceeded → WARN (not FAIL, since perf varies by environment).

---

## Test Case YAML Format

Each YAML file covers one domain (database). Structure:

```yaml
database:
  uri: neo4j+s://demo.neo4jlabs.com:7687
  username: companies
  password: companies          # optional — falls back to NEO4J_PASSWORD env
  database: companies
  neo4j_version: "2026.01"    # used to gate version-specific features in prompts
  cypher_version: "25"
  read_only: true              # SKIP write cases instead of FAIL
  gds: true                    # GDS library available
  capabilities: [apoc, apoc-extended, genai]  # optional plugins available

dataset:
  name: companies
  description: |
    <description injected into the Claude prompt as schema context>
  schema:
    nodes:
      - label: Organization
        properties: [name, country, founded, employees, revenue]
        notes: "..."
    relationships:
      - type: HAS_SUBSIDIARY
        from: Organization
        to: Organization
    indexes:
      - name: entity
        type: FULLTEXT
        labels: [Organization]
        properties: [name]
        note: "..."

cases:
  - id: companies-basic-001
    question: "List all organizations and their founding year"
    difficulty: basic           # basic | intermediate | advanced | complex | expert
    tags: [match, label]
    is_write_query: false
    min_results: 1
    max_db_hits: 5000
    max_allocated_memory_bytes: 1000000
    max_runtime_ms: 500.0
    notes: "Optional per-case guidance injected into the prompt"
```

### Difficulty Tiers

| Tier | Description |
|---|---|
| `basic` | Single MATCH + RETURN on one label; no aggregation |
| `intermediate` | Two or more hops; simple aggregation (count, avg, sum) |
| `advanced` | QPE, SEARCH/fulltext, CALL subquery, complex WHERE |
| `complex` | Multi-hop QPE with `{m,n}`, CALL IN TRANSACTIONS, vector + graph combination |
| `expert` | Multi-step analytics, GDS algorithms, APOC, or highly constrained graph traversals |

---

## Domain Reference

| Domain | URI | Version | Local/Remote | Write? | Capabilities |
|---|---|---|---|---|---|
| companies | demo.neo4jlabs.com | 2026.01 | remote | SKIP | apoc, apoc-extended, genai, gds |
| recommendations | demo.neo4jlabs.com | 2026.01 | remote | SKIP | apoc, apoc-extended, genai, gds |
| goodreads | demo.neo4jlabs.com | 2026.01 | remote | SKIP | apoc, apoc-extended, genai, gds |
| stackoverflow | demo.neo4jlabs.com | 2026.01 | remote | SKIP | apoc, apoc-extended, genai, gds |
| legalcontracts | demo.neo4jlabs.com | 2026.01 | remote | SKIP | apoc, apoc-extended, genai, gds |
| retail | demo.neo4jlabs.com | 2026.01 | remote | SKIP | apoc, apoc-extended, genai, gds |
| ucnetwork | demo.neo4jlabs.com | 2026.01 | remote | SKIP | apoc, apoc-extended, genai, gds |
| ucfraud | localhost:7687 | 2026.02.1 | local | YES | apoc, apoc-extended, genai, gds |
| northwind | localhost:7687 | 2026.02 | local | YES | apoc, apoc-extended, genai, gds |
| twitter | localhost:7687 | 2026.02 | local | YES | apoc, apoc-extended, genai, gds |

**Note**: demo.neo4jlabs.com runs Neo4j 2026.01.x — the `SEARCH` clause (vector index) is **not available** there (GA in 2026.02.1+). Local instances run 2026.02.x and support SEARCH.

---

## Make Targets

```
make dry-run          Validate all YAML test cases (no DB, no Claude)
make smoke            Smoke-test validator, reporter, and analyzer (no DB)
make test-extract     Run reference extraction unit tests
make test-companies   Run companies domain
make test-ucfraud     Run ucfraud domain (local, writeable, 2026.02.1)
make test-northwind   Run northwind domain (local)
make test-twitter     Run twitter domain (local)
make test-goodreads   Run goodreads domain
make test-stackoverflow Run stackoverflow domain
make test-legalcontracts Run legalcontracts domain
make test-retail      Run retail domain
make test-ucnetwork   Run ucnetwork domain
make test-recommendations Run recommendations domain
make test-all         Run companies + recommendations + ucfraud sequentially
make test-basic       Run only basic-difficulty cases across all domains
make test-expert      Run only expert-difficulty cases across all domains
make analyze          Analyze latest results in tests/results/
make report-latest    Re-render Markdown reports from 3 most recent JSON files
```

**Tuning options** (pass as `make` variables):
```bash
make test-companies WORKERS=4    # parallel Claude invocations (default: 5)
make test-ucfraud TIMEOUT=240    # Claude invocation timeout in seconds (default: 180)
```

---

## Schema Generator

`tests/harness/generator.py` connects to a Neo4j database, inspects its schema, and uses Claude to generate test case stubs. Stubs are written to `tests/cases/{domain}-generated.yml` for human review before promotion to the main case file.

```bash
uv run --project skill-generation-validation-tools python3 tests/harness/generator.py \
  --domain companies \
  --database companies \
  --neo4j-uri neo4j+s://demo.neo4jlabs.com:7687 \
  --neo4j-username companies \
  --neo4j-password companies \
  --counts 5 5 3 2 \        # basic intermediate advanced complex
  --verbose
```

The generator:
1. Inspects schema (labels, rel types, properties, ONLINE indexes)
2. **Detects capabilities** via `SHOW PROCEDURES WHERE name STARTS WITH 'gds.'` etc.
3. Samples property values and infers semantics (enum, range, uuid, freetext, score, sparse)
4. Calls Claude to generate questions + candidate Cypher per difficulty tier
5. Profiles each candidate query to capture baseline metrics (db hits, memory, runtime)
6. Writes YAML stubs with auto-computed thresholds (3× db hits, 3× memory, 5× runtime)

**Promotion workflow**: review `{domain}-generated.yml` → verify `observed_count >= 1` → copy verified cases to `{domain}.yml` → remove `candidate_cypher`, `observed_*`, `inferred_semantics` fields.

---

## Reporter

Renders JSON result files to human-readable Markdown:

```bash
uv run --project skill-generation-validation-tools python3 tests/harness/reporter.py \
  --input tests/results/companies-run-20260323.json \
  --output tests/results/companies-run-20260323.md
```

The Markdown report includes: summary stats, per-case verdict with gate that failed, timing, and db hits.

---

## Analyzer

Cross-run analysis of all JSON files in a results directory:

```bash
make analyze
# or directly:
uv run --project skill-generation-validation-tools python3 scripts/analyze-results.py \
  --input tests/results/ \
  --output tests/results/analysis-$(date +%Y%m%d).md
```

Reports pass rate trends, most common failure gates, and per-domain breakdown.

---

## Exporter

Exports validated test cases as JSONL for fine-tuning or few-shot use:

```bash
uv run --project skill-generation-validation-tools python3 tests/harness/exporter.py \
  --input tests/results/companies-run-20260323.json \
  --output training-data/companies.jsonl
```

Each JSONL record pairs the question, injected schema context, and the generated Cypher that passed all four gates.

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | Claude API access for runner and generator |
| `NEO4J_URI` | `bolt://localhost:7687` | Default Neo4j URI (overridden per-domain by YAML) |
| `NEO4J_USERNAME` | `neo4j` | Default username |
| `NEO4J_PASSWORD` | `neo4j` | Default password |

Per-domain credentials in YAML `database.password` override env vars. For demo.neo4jlabs.com, the password matches the username (e.g., `companies` / `companies`).

---

## L3 Reference Extraction

The `scripts/extract-references.py` script regenerates all L3 reference files from upstream Neo4j asciidoc sources pinned in `neo4j-cypher-authoring-skill/VERSION`:

```bash
# From repo root — requires docs-cypher/ and docs-cheat-sheet/ checkouts
uv run python3 skill-generation-validation-tools/scripts/extract-references.py \
  --docs-dir docs-cypher/ \
  --cheat-sheet docs-cheat-sheet/ \
  --output neo4j-cypher-authoring-skill/references/

# Unit tests for the extractor
make test-extract
```

Each output file is capped at **2,000 tokens** (enforced by the extractor). GQL-only clauses (`LET`, `FINISH`, `FILTER`, `NEXT`, `INSERT`) are excluded by default.

---

## Adding a New Domain

1. **Create a YAML file** `tests/cases/{domain}.yml` — use an existing file as template
2. **Add database credentials** to `integration.env` if using a local instance
3. **Add a Makefile target** — copy an existing `test-*` block and update domain/path
4. **Optionally generate stubs**: run `generator.py --domain {domain}`, review, promote
5. **Add a schema snapshot** (optional) to `tests/schemas/{domain}.json` for offline use

---

## Known Limitations

- `SEARCH` clause cases only run on local Neo4j 2026.02+ (not demo.neo4jlabs.com 2026.01)
- GDS algorithm cases require a local Neo4j instance with GDS installed
- Execution timeouts (180s) may cause false failures for complex ucnetwork queries under API load — use `WORKERS=2` for these
- The `CALL IN TRANSACTIONS` write pattern requires an implicit (auto-commit) transaction — the harness handles this automatically
