# Skill Test Harness

This directory contains repo-wide validation plus focused executable tests for the vector index skill.

## Test Layers

| Layer | Scope | Command |
|---|---|---|
| Skill lint | All tracked `neo4j-*-skill/SKILL.md` files | `python3 scripts/lint_skills.py` |
| Python tests | Lint wrapper, vector Cypher examples, golden eval manifest/runner | `python3 -m pytest tests -v` |
| Cypher examples | Manifest-selected Cypher from `neo4j-vector-index-skill/SKILL.md` | `python3 scripts/run_cypher_examples.py --manifest neo4j-vector-index-skill/tests/cypher-examples.json` |
| Golden evals | Agent response checks against `neo4j-vector-index-skill/tests/golden-evals.json` | `python3 scripts/run_golden_evals.py --manifest neo4j-vector-index-skill/tests/golden-evals.json --require-api --fail-on-advisory` |

## Setup

Install test dependencies:

```bash
python3 -m pip install -r requirements-dev.txt
```

Run all tests:

```bash
python3 -m pytest tests -v
```

The Cypher tests need either Docker or a configured Neo4j instance.

Prefer Docker for local runs. It starts a disposable container and avoids touching any existing database:

```bash
python3 scripts/run_cypher_examples.py --manifest neo4j-vector-index-skill/tests/cypher-examples.json
```

Configured `NEO4J_TEST_URI` runs are destructive. The runner drops constraints, drops indexes, and deletes nodes before each example and at the end of the run. Use only a disposable database, and opt in explicitly:

```bash
NEO4J_TEST_ALLOW_DESTRUCTIVE=1 \
NEO4J_TEST_URI=neo4j://localhost:7687 \
NEO4J_TEST_USERNAME=neo4j \
NEO4J_TEST_PASSWORD=password \
python3 scripts/run_cypher_examples.py --manifest neo4j-vector-index-skill/tests/cypher-examples.json
```

When `NEO4J_TEST_URI` is unset, the runner starts a disposable Docker container. The vector skill test suite also runs `docker.io/library/neo4j:5.26-community` and asserts the `neo4j` database uses a `record-aligned` store format.

## Golden Eval Configuration

Live golden evals are optional. They run when these values are present in the environment or in `.config/skill-evals.env`:

```bash
SKILL_EVAL_MODEL=gpt-4o-mini
OPENAI_API_KEY=...
```

Optional values:

```bash
SKILL_EVAL_JUDGE_MODEL=gpt-5.5
SKILL_EVAL_STRESS_MODEL=gpt-5.4-mini
SKILL_EVAL_API_BASE=https://api.openai.com/v1
```

Use `SKILL_EVAL_MODEL` for the model under test. Use `SKILL_EVAL_JUDGE_MODEL` for semantic judging. Prefer a stronger judge model than the tested model when criteria require interpretation rather than exact token matching.

## Adding Cypher Example Tests

Cypher examples are selected from `SKILL.md` by `neo4j-vector-index-skill/tests/cypher-examples.json`. Test metadata stays outside `SKILL.md` so the skill remains clean.

Add an entry:

```json
{
  "name": "query-vector-index-procedure",
  "heading": "Post-filter pattern (2025.x or arbitrary predicates)",
  "cypherBlock": 1,
  "setup": "examples/vector-query.setup.cypher",
  "minVersion": "5.13",
  "parameters": {
    "queryEmbedding": [0.1, 0.2, 0.3],
    "source": "docs"
  },
  "dropCypherVersionPragma": true
}
```

Guidelines:

- Select only copyable examples that should execute.
- Keep setup files minimal and local to the skill directory.
- Use `parameters` instead of hardcoding secrets or environment-specific values.
- Use `minVersion` when syntax or procedures require a specific Neo4j version.
- Use `dropCypherVersionPragma` only when testing a Cypher 25 example against an older-compatible runner path.

## Adding Golden Evals

Golden evals live in `neo4j-vector-index-skill/tests/golden-evals.json`. Each eval sends the skill and task prompt to the configured model, then evaluates the response with typed checks.

Use deterministic checks for objective requirements:

```json
{
  "type": "literal",
  "scope": "code",
  "value": "CREATE VECTOR INDEX"
}
```

Use `regex` only when a simple literal is not enough:

```json
{
  "type": "regex",
  "scope": "code",
  "pattern": "YIELD\\s+node\\s+AS\\s+c\\s*,\\s*score"
}
```

Use `llm_judge` for semantic criteria where wording can vary:

```json
{
  "type": "llm_judge",
  "blocking": false,
  "criteria": [
    {
      "id": "mentions_with_list_requirement",
      "description": "The answer says that properties filtered inside SEARCH must be declared in the vector index WITH list. Equivalent wording is acceptable."
    }
  ]
}
```

Check scopes:

| Scope | Meaning |
|---|---|
| `code` | Search fenced code blocks only |
| `prose` | Search text outside fenced code blocks |
| `any` | Search the whole response |

Blocking behavior:

- `literal` and `regex` checks are blocking by default.
- `llm_judge` checks are advisory by default.
- Set `"blocking": true` only after the judge criteria have been calibrated against real outputs.
- Run with `--fail-on-advisory` to make advisory failures return non-zero locally.
- The live golden eval pytest path uses `--fail-on-advisory`, so advisory semantic criteria gate configured live eval runs.

## Golden Eval Output

The runner can write machine-readable reports:

```bash
python3 scripts/run_golden_evals.py \
  --manifest neo4j-vector-index-skill/tests/golden-evals.json \
  --require-api \
  --fail-on-advisory \
  --repeat 3 \
  --json-output /tmp/vector-golden-summary.json \
  --jsonl-output /tmp/vector-golden-results.jsonl \
  --output-dir /tmp/vector-golden-outputs
```

Reports include model, judge model, pass/fail, advisory findings, latency, API usage, output paths, and pass@1/pass@N/pass^N summaries.
