# First-pass testing proposal for Neo4j Agent Skills

## Current state

The repository currently has useful conventions, but no repo-wide test framework.

What exists:

- `AGENTS.md` defines expected `SKILL.md` frontmatter rules and says to run `python3 scripts/lint_skills.py` before every commit.
- `evals/dataset.json` contains skill-routing scenarios with prompts, expected skills, and expected output patterns.
- `neo4j-getting-started-skill/scripts/validate_queries.py` validates generated Cypher query files against a live Neo4j database for that one skill workflow.
- `neo4j-getting-started-skill/AGENTS.md` describes a richer persona test harness, but the referenced `tests/harness/*` and `tests/personas/*` files are not present in this repository.

What is missing:

- No top-level `scripts/lint_skills.py`, despite being referenced by `AGENTS.md`.
- No top-level `tests/` directory.
- No `.github/workflows/` CI configuration.
- No repo-wide validation that every skill has valid frontmatter, local Markdown links, or safe content.
- No convention for executable Cypher examples in skills.
- No CI job that runs examples against Neo4j.

Conclusion: testing is currently mostly aspirational. The repo has the right direction in its contributor guidance and eval dataset, but the blocking, repeatable checks are not implemented yet.

## Goal

Treat skills as productized instructions. Add cheap, boring, CI-friendly tests that catch malformed skills and broken executable examples before adding complex agent-behavior evaluation.

The first pass should be small enough that maintainers accept it and future skill authors can use it without asking for help.

## Non-goals

- Full agent-behavior scoring.
- Running every Markdown code block.
- Complex natural-language grading.
- Multi-version Neo4j test matrix.
- Large fixture datasets.
- Perfect coverage.
- Validating external services such as OpenAI, Aura, GDS SaaS, Kafka, or Spark.

## Proposed first pass

### 1. Add static skill linting

Add `scripts/lint_skills.py`.

Initial checks:

- Every `neo4j-*-skill/` directory has `SKILL.md`.
- `SKILL.md` has YAML-style frontmatter bounded by `---`.
- Required fields exist: `name`, `description`.
- `name` exactly matches parent directory name.
- Skill names are unique.
- `name` format matches the existing `AGENTS.md` rule: lowercase letters, numbers, hyphens, no leading or trailing hyphen, no consecutive hyphens, max 64 chars.
- `description` length is 80-1024 characters.
- `compatibility` is at most 500 characters if present.
- No unknown top-level frontmatter fields beyond the fields currently used by skills: `name`, `description`, `compatibility`, `allowed-tools`, `version`, `status`.
- Markdown links to local files resolve.
- `SKILL.md` stays within the line budget. The current skills are within 500 lines, so first pass can fail over-budget files.
- Obvious secrets are not committed.

Secret scanning should stay conservative to avoid noisy false positives:

- Fail on OpenAI-style keys, GitHub tokens, AWS access key IDs, private key blocks, and obvious `password=...` examples with real-looking values.
- Ignore documented placeholder values such as `$openaiKey`, `<password>`, `NEO4J_PASSWORD`, and `your-api-key`.

Implementation notes:

- Prefer Python standard library for the first pass. A tiny frontmatter parser is enough if we only need simple scalar fields and continuation lines.
- If YAML parsing becomes brittle, add `pyyaml` later with a small `requirements-dev.txt` or `pyproject.toml`.
- Output one line per failure with file path and reason.
- Exit non-zero on hard failures.

### 2. Add explicit executable Cypher examples

Add `scripts/extract_cypher_examples.py`.

Keep `SKILL.md` clean. Do not add testing metadata to the skill prose. Instead, use a dedicated manifest per skill to identify which Cypher examples are executable.

Example manifest:

```json
{
  "skill": "neo4j-vector-index-skill/SKILL.md",
  "examples": [
    {
      "name": "basic-count",
      "heading": "Pre-flight — Determine Version",
      "cypherBlock": 1
    }
  ]
}
```

Supported manifest metadata in the first pass:

- `name`: stable identifier for reports.
- `heading`: nearest Markdown heading that contains the target block.
- `cypherBlock`: one-based Cypher block number under that heading.
- `setup`: relative path to a setup Cypher file.
- `minVersion`: minimum Neo4j version for the example.
- `parameters`: parameter map passed when executing the query.

Skill examples stay normal:

````markdown
```cypher
CYPHER 25
MATCH (d:Document)
  SEARCH d IN (
    VECTOR INDEX document_embedding
    FOR [0.1, 0.2, 0.3]
    WHERE d.lang = 'en'
    LIMIT 5
  ) SCORE AS score
RETURN d.id, score
```
````

Non-testable examples are simply omitted from the manifest.

Extractor output should include:

- source file path
- block number
- example name
- setup path
- minimum version
- query text

The output can be JSON so both local scripts and pytest can consume it.

### 3. Run manifest-selected Cypher examples against Neo4j

Add `tests/test_cypher_examples.py`.

First-pass behavior:

- Discover examples from the selected manifest via `scripts/extract_cypher_examples.py`.
- Start a disposable Neo4j instance if `NEO4J_TEST_URI` is not set.
- Reuse an externally provided instance when `NEO4J_TEST_URI`, `NEO4J_TEST_USERNAME`, and `NEO4J_TEST_PASSWORD` are set.
- Wait until Bolt is available.
- For each example:
  - clear the test database or recreate it where supported
  - run the optional setup file
  - run the example query
  - fail if setup or query errors
- Skip examples where `minVersion` is greater than the Neo4j instance version.

Keep state isolation simple at first:

- Use one database named `neo4j` unless multi-database setup is confirmed.
- Before each example, run `MATCH (n) DETACH DELETE n` and drop user-created indexes/constraints discovered by `SHOW INDEXES` and `SHOW CONSTRAINTS`.
- If index/constraint cleanup becomes flaky, switch to per-example database recreation in a later pass.

Failure output must include:

- skill file
- example name
- Markdown block number
- setup file used
- Neo4j version
- error message
- query text

### 4. Add a small number of high-value examples to manifests

Do not add every Cypher block immediately. Start with examples intended to be copied by users and easy to fixture.

Suggested first examples:

- `neo4j-cypher-skill`: basic schema-safe read query with a tiny setup graph.
- `neo4j-vector-index-skill`: run the pre-flight version query and one vector query example against a tiny fixture graph.
- `neo4j-import-skill`: minimal `LOAD CSV` or `UNWIND` ingestion pattern that does not depend on external URLs.
- `neo4j-modeling-skill`: create a uniqueness constraint and MERGE a small graph.
- `neo4j-driver-python-skill`: do not execute driver code in this first pass; keep it for later language-specific tests.

For vector examples, prefer `LIST<FLOAT>` fixtures in first-pass tests so Community Edition-compatible testing remains possible. Native `VECTOR` storage and block-format behavior should be tested later in a targeted Enterprise/Aura-compatible job.

### 5. Add optional golden agent-skill evals

Add `scripts/run_golden_evals.py` plus a small manifest for high-value skill behavior checks.

First-pass behavior:

- Keep eval prompts and pattern checks in a per-skill manifest, for example `neo4j-vector-index-skill/tests/golden-evals.json`.
- Run against an OpenAI-compatible chat-completions API only when local API configuration is present.
- Require `SKILL_EVAL_MODEL` plus `SKILL_EVAL_API_KEY` or `OPENAI_API_KEY`; optionally support `SKILL_EVAL_API_BASE`.
- Load local API settings from ignored `.config/skill-evals.env`; keep `.config/skill-evals.env.example` tracked.
- In CI, validate the manifest structure but skip live model calls unless credentials are explicitly provided.
- Check output with conservative required and forbidden regex patterns rather than free-form LLM judging.

The first vector evals should cover:

- Creating a vector index with explicit `vector.dimensions`.
- Using `db.index.vector.queryNodes()` for Neo4j 2025.x.
- Using SEARCH with simple in-index filters and explaining the AND-only limitation.
- Using `ai.text.embed()` instead of deprecated `genai.vector.encode()`.

### 6. Add CI

Add `.github/workflows/validate-skills.yml` if maintainers are comfortable adding GitHub Actions to this repository.

Jobs:

1. `lint-skills`
   - Python version: current stable 3.x.
   - Run `python3 tests/test_lint_skills.py`.
   - Applies to every skill in the repository.
   - Blocking.

2. `test-vector-skill`
   - Requires Docker.
   - Install Python test dependencies.
   - Extract examples from `neo4j-vector-index-skill/tests/cypher-examples.json`.
   - Start Neo4j through the vector skill test harness when no external `NEO4J_TEST_URI` is provided.
   - Run `pytest tests/test_vector_skill.py`.
   - Validate the vector golden-eval manifest and skip live model calls unless local API credentials are available.
   - Acts as the first skill-specific executable example job. Future skills should add their own manifest and test job without changing the repo-wide linting contract.

If maintainers are cautious about CI cost, start with `lint-skills` blocking and make skill-specific example jobs manual or non-blocking for the first PR.

## Dependencies

Keep dependencies minimal:

- Python 3.10+
- `neo4j` Python driver
- `pytest`

Optional later:

- `pyyaml` for richer frontmatter parsing.
- `testcontainers` if Docker lifecycle management via subprocess becomes too noisy.

## Recommended branch and PR slicing

Avoid one large framework PR. Submit focused PRs:

1. Static linter only.
2. Cypher extractor plus a few manifest-selected examples, without Neo4j execution.
3. Neo4j-backed pytest harness.
4. CI workflow wiring.
5. Optional agent eval fixtures.

This lets maintainers accept useful pieces even if they want changes to the Docker or CI approach.

## Acceptance criteria for first implemented PR set

The first testing pass is done when:

- `python3 scripts/lint_skills.py` validates every `SKILL.md`.
- Manifest-selected Cypher examples are discovered with path, block number, name, setup, parameters, and minVersion metadata.
- At least one high-value skill has Cypher examples that run against a real Neo4j instance.
- Non-testable Cypher examples are left alone.
- CI separates repo-wide static validation from skill-specific executable example and optional golden-eval tests.
- Failures point directly to the skill file and block that needs fixing.
- The documented workflow is short enough for future skill authors to follow.

## Open questions before implementation

- Which Neo4j Docker image should be the default for CI: latest stable calendar release, `2026.01`, or a project-maintained matrix variable?
- Should the first CI workflow be blocking for both lint and Neo4j-backed tests, or should Neo4j-backed tests start non-blocking?
- Should the 500-line limit allow an explicit exception flag for unusually complex skills, or always fail?
- Should local link validation inspect only Markdown links, or also parse inline path references such as `references/foo.md`?
- Should the first Neo4j-backed tests target only Community Edition-compatible examples?

## Proposed first implementation after this proposal

Start with PR 1: static linter only.

Why:

- It resolves the current `AGENTS.md` mismatch by adding the referenced `scripts/lint_skills.py`.
- It is cheap to run locally and in CI.
- It catches malformed skills before introducing Docker complexity.
- It creates the foundation for later executable example tests.

Suggested PR 1 contents:

- `scripts/lint_skills.py`
- `tests/test_lint_skills.py`
- `README.md` or `AGENTS.md` update with the exact command
- optional `.github/workflows/validate-skills.yml` running only the linter
