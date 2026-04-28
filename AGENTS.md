# Writing Skills for this Repository

A `SKILL.md` is not a prompt, not documentation, and not a policy file. It is a **portable, on-demand operational playbook** for an autonomous coding agent — a runbook with judgment, a checklist with decision logic, a guardrail against improvisational mistakes.

When adding or editing skills in this repository, follow these rules. All skills live in `neo4j-*-skill/` directories. Run `python3 scripts/lint_skills.py` before every commit — all skills must pass.

## Six Design Principles

Every skill must satisfy all six:

| Principle | Test |
|---|---|
| **Triggerable** | Does the description clearly state when to activate? |
| **Procedural** | Do the instructions define a deterministic workflow? |
| **Scoped** | Does the skill do exactly one coherent thing? |
| **Composable** | Does it work alongside sibling skills without conflict or overlap? |
| **Verifiable** | Are outputs and success criteria explicit? |
| **Context-efficient** | Is metadata concise? Does detail load only when needed? |

---

## SKILL.md Spec (agentskills.io)

Each skill is a directory with a `SKILL.md` file at the root:

```
neo4j-my-skill/
├── SKILL.md          # Required
├── references/       # Optional — detailed docs, loaded on demand
├── scripts/          # Optional — executable code
└── assets/           # Optional — templates, data files
```

### Frontmatter

```yaml
---
name: neo4j-my-skill          # Required. Must exactly match the parent directory name.
description: What it does and when to use it. Include keywords and negative triggers.
  Does NOT handle X — use neo4j-other-skill.
compatibility: Claude Code    # Optional. Max 500 chars. Only if env requirements exist.
allowed-tools: Bash WebFetch  # Optional. Space-separated pre-approved tools.
version: 1.0.0                # Optional.
---
```

### Hard rules enforced by the linter (`scripts/lint_skills.py`)

- `name` must exactly match the parent directory name — linter hard-fails on mismatch
- `name`: lowercase letters, numbers, and hyphens only; no consecutive hyphens; no leading/trailing hyphen; max 64 chars
- `description`: **80–1024 characters** — linter hard-fails outside this range
- `compatibility`: max 500 characters if present
- No unknown top-level frontmatter fields — linter rejects them
- **Never use `description: >` (YAML block scalar)**. Parsers read the raw `>` character as the description value → 1-char string → linter fail. Use inline continuation instead:

```yaml
# WRONG — block scalar, linter fails:
description: >
  Comprehensive guide to...

# RIGHT — inline with indented continuation:
description: Comprehensive guide to the Neo4j Go Driver v6 — covering driver lifecycle,
  ExecuteQuery, managed and explicit transactions, error handling, and data type mapping.
  Use when writing Go code that connects to Neo4j. Does NOT handle Cypher — use neo4j-cypher-skill.
```

---

## The Description Field — The Routing Signal

The `description` is how the agent decides which skill to load. Get it wrong and the skill never triggers, or triggers on the wrong task.

**Anatomy**: `[what it does] + [positive triggers] + [Does NOT handle X — use Y-skill]`

### Positive triggers — pack these in

- Canonical product name and version: `Neo4j Go Driver v6`, `graphdatascience v1.21`
- Common entry-point symbols: `NewDriver`, `ExecuteQuery`, `GdsSessions`, `gds.pageRank`
- Natural-language task phrases: `"Use when writing Go code that connects to Neo4j"`
- Synonyms: both `GDS` and `Graph Data Science`; both `AGA` and `Aura Graph Analytics`

### Negative triggers — always name the sibling skill

```yaml
Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
Does NOT cover Aura Graph Analytics serverless sessions — use neo4j-aura-graph-analytics-skill.
```

Never a bare "Don't" without naming where to go instead. With 20+ skills in this repo, tight routing is critical. The MongoDB `mongodb-natural-language-querying` pattern is the gold standard:
> "Does NOT handle Atlas Search ($search operator) — use search-and-ai for those. Does NOT analyze or optimize queries — use mongodb-query-optimizer for that."

---

## Skill Body Structure

### Write imperatively, not explanatorily

Instructions must be commands, not explanations. Agents execute procedures; they do not reliably interpret prose intent.

```
❌  You may want to consider writing tests first.
✅  Write a failing test. Confirm the failure is for the intended reason.
```

Every instruction should be answerable with "done" or "not done" — not "I think so."

### Open with When to Use / When NOT to Use

Always the first two sections. Short-circuits the agent before it reads the whole skill body:

````markdown
## When to Use
- Running GDS algorithms on Aura BC or VDC
- Processing graph data from Pandas DataFrames or Spark

## When NOT to Use
- **Aura Pro with GDS plugin** → use `neo4j-gds-skill`
- **Writing Cypher queries** → use `neo4j-cypher-skill`
````

### Define entry criteria

State explicitly when the skill should begin executing, not just when it's relevant. Prevents the agent from starting work before prerequisites are met:

```markdown
## Entry criteria
- A feature request or bug report is present in the conversation
- The file(s) to be modified have been identified
- Existing tests (if any) are confirmed passing before changes begin
```

### Specify artifacts explicitly

Tell the agent exactly what to produce. Without this, the agent improvises output format — sometimes useful, often not:

```markdown
## Outputs
- Modified `SKILL.md` with inline description (no block scalar)
- Updated `README.md` for the skill directory
- Lint output confirming all checks pass
```

### Handle uncertainty explicitly

Distinct from failure recovery (command failed) — this is what to do when required information is *missing before starting*:

```markdown
If required context is missing before starting (e.g., no target file identified, 
connection credentials not provided):
1. State exactly what is missing
2. Explain why it is needed
3. Ask for the minimum input required to proceed
Do NOT guess. Do NOT proceed with assumptions that could cause destructive changes.
```

### Narrow Bridge vs Open Field

Calibrate instruction strictness to task risk:

- **Narrow Bridge** (high risk — migrations, schema changes, security patches, bulk writes): provide exact, sequential commands. Leave no room for agent "creativity." Every step is prescribed; every branch condition is explicit.
- **Open Field** (low risk — code review, refactoring, analysis): provide goals and constraints, then let the agent's reasoning find the implementation path. Over-specifying here produces rigid, brittle skills.

### Procedural numbered steps for operational skills

For connect, provision, import, and deploy skills — strict numbered steps, each with a code block and a branch condition. Agents cannot skip or reorder numbered steps:

````markdown
## Step 1 — Verify GDS is available

```cypher
RETURN gds.version() AS gds_version
```

If this fails with `Unknown function 'gds.version'`, GDS is not installed. **Stop and inform the user.**

## Step 2 — Estimate memory before projecting
````

Evidence: numbered workflows reduced missing wiring from 40% to 10%, +25% correctness, +20% completeness (Augment Code).

### Decision tables when multiple approaches exist

Force the choice upfront — don't describe all approaches in prose and let the agent guess:

````markdown
| Deployment | Use |
|---|---|
| Aura Pro | `neo4j-gds-skill` (embedded plugin) |
| Aura Business Critical / VDC | `neo4j-aura-graph-analytics-skill` (serverless) |
| Self-managed with GDS | `neo4j-gds-skill` |
````

Evidence: decision tables produce 25% higher best-practice adherence (Augment Code).

### Real code examples — idiomatic, not toy

Agents copy patterns they see. Show the full production-idiomatic usage, not stripped-down snippets:

```python
# Toy (bad):
gds.pageRank.stream(G)

# Idiomatic (good):
gds = sessions.get_or_create(
    session_name="prod-analysis",
    memory=memory,
    db_connection=DbmsConnectionInfo.from_env(),
    ttl=timedelta(hours=4),
)
gds.verify_connectivity()
```

Evidence: production code examples improve code reuse by 20% (Augment Code).

For transformation skills, use diff blocks to show exactly how code should change — one diff is worth more than 1,000 words of prose:

```diff
- const driver = neo4j.driver(uri, neo4j.auth.basic(user, password))
+ const driver = await neo4j.driver(uri, neo4j.auth.basic(user, password))
+ await driver.verifyConnectivity()
```

### Pair every prohibition with a solution

```
❌  Don't create a new driver per request.
✅  Don't create a new driver per request — create one Driver at startup and share it across goroutines.
```

15+ sequential warnings without paired solutions cause agents to over-explore and take 2× longer (Augment Code).

### Inter-skill delegation

Name sibling skill delegation explicitly in the body, not just the description:

````markdown
If `gds.version()` fails, GDS is not available on this deployment.
For Aura BC/VDC, delegate to `neo4j-aura-graph-analytics-skill` instead.
````

### Structured output templates for review skills

For skills that produce analysis or recommendations, prescribe exact output format:

````markdown
## Output format

### Compliant
- [item]

### Issues Found
#### [Title] — Severity: ERROR / WARNING / INFO
- **Current**: what the code does
- **Problem**: why it's wrong  
- **Fix**: specific change with code snippet
````

Use consistent severity semantics across all analysis/review skills:

| Severity | Meaning | Agent action |
|---|---|---|
| `ERROR` | Blocking — must be fixed before proceeding | Stop and report; do not continue |
| `WARNING` | Review recommended — may need attention | Report; ask user before proceeding |
| `INFO` | Informational — no action required | Surface in output; continue |

### Provenance labels for advice skills

Label recommendations to distinguish documented fact from field heuristic:

- `[official]` — stated directly in Neo4j docs
- `[derived]` — follows from documented behavior
- `[field]` — community heuristic; add a disclaimer

Use especially in GDS algorithm selection and modeling advice.

### Token-cost guards for MCP/query skills

````markdown
Before running any traversal query via MCP:
1. Run `EXPLAIN` or `COUNT(*)` first
2. Warn if no `LIMIT` on patterns that could match millions of nodes
3. Default to `LIMIT 25` on exploratory queries
````

### Plan-First for complex skills

For skills covering multi-file changes or non-trivial transformations, instruct the agent to produce a plan before touching code:

```markdown
Before making any changes:
1. List all files you will modify and why
2. State the before/after for each non-trivial change
3. Identify any risks or unknowns

Only proceed after the plan is visible in the conversation.
```

### Self-Healing — tell the agent what to do when a command fails

Every command that can fail should have an explicit failure path. Don't rely on the agent improvising:

```markdown
Run `npm test`. If tests fail:
1. Do NOT proceed
2. Revert all changes with `git checkout .`
3. Report the exact failing test and error message to the user
```

### Async operations — poll explicitly, don't assume completion

For operations that are asynchronous (index builds, schema migrations, Aura instance provisioning, GDS algorithm runs on large graphs), tell the agent to poll for completion rather than moving on:

```markdown
Run the migration. It returns immediately with an operation ID.
Call `SHOW INDEXES YIELD name, state WHERE state <> 'ONLINE'` every 5 seconds
until the result is empty. Do NOT query the index until it reports ONLINE.
```

Async operations that silently "succeed" but are still running are a common source of hard-to-debug failures. Make the wait explicit.

### Close with a checklist

Agents use checklists to self-verify before reporting done:

````markdown
## Checklist
- [ ] `gds.version()` confirmed
- [ ] Memory estimated before large projections
- [ ] Named graph dropped after use (`G.drop()`)
- [ ] Results written back before session deletion
````

---

## Progressive Disclosure

The agentskills.io spec and Claude Code both load skills in three stages:

| Stage | Content | Size target |
|---|---|---|
| Skill listing | `name` + `description` only (~100 tokens) | 80–1024 chars |
| Skill activation | Full `SKILL.md` body | **< 500 lines** |
| On demand | `references/`, `scripts/`, `assets/` | Any size |

Keep `SKILL.md` under 500 lines. Move large algorithm tables, full API references, and parameter lists to `references/REFERENCE.md` — but always link them explicitly:

````markdown
For the complete algorithm parameter reference, see [references/algorithms.md](references/algorithms.md).
````

An unreferenced file in `references/` has <10% discovery rate. A referenced one has 90%+.

---

## Security and Write Operations

- Write credentials to `.env`; verify `.env` is in `.gitignore` before proceeding
- Use `from_env()` patterns — never hardcode credentials
- Never print credential values in conversation output
- **Do not prompt the user to set env vars** unless skill execution actually fails due to a missing variable — skills that use `from_env()` or load `.env` automatically do not need the user to set anything in advance
- Any skill that writes via MCP must show the query + estimated impact and require explicit user confirmation before executing `DELETE`, `DETACH DELETE`, `CALL IN TRANSACTIONS`, or bulk writes
- Use `disable-model-invocation: true` for write/deploy skills to prevent auto-triggering

---

## Anti-Patterns

**Excessive architecture overviews** — detailed "why" explanations push agents into reading irrelevant docs. Focus on "what" and "how"; keep "why" in commit messages.

**YAML block scalar `description: >`** — always inline. This burns the most time in review because linters report it as a 1-char description (hard fail) or silent wrong routing.

**Bare prohibitions without solutions** — every "Don't" needs a "Do with pointer".

**Toy code examples** — agents replicate what they see. Show idiomatic, real patterns.

**Orphan reference files** — always link from `SKILL.md`. Discovery rates: root `AGENTS.md` 100%, directly referenced files 90%+, unreferenced nested files <10%.

**Premature patterns** — don't document approaches that don't exist in the codebase yet. The agent will use them on the existing code.

**No exit criteria** — without an explicit verification checklist or done condition, agents tend to "wander": continuing to refine, second-guess, or add unrequested work. Always define when the skill is finished.

**Overlapping skills** — if two skills cover the same trigger, the agent picks unpredictably. Every skill must be composable: it should be possible to have all skills active simultaneously without them conflicting. Resolve overlaps with explicit negative triggers naming the boundary.

---

## Linter Reference

```bash
python3 scripts/lint_skills.py
```

The linter uses `git ls-files` to find tracked `SKILL.md` files and checks:

| Rule | Detail |
|---|---|
| `name` matches directory | Hard fail — most common mistake |
| `description` length | Hard fail if < 80 or > 1024 chars |
| `description` not block scalar | Detected via `>` prefix in parsed value |
| No unknown frontmatter fields | `status`, `version` are allowed extensions; anything else fails |
| `compatibility` length | Hard fail if > 500 chars |

Stage new skills with `git add` before running — the linter only sees tracked files.

---

## New Skill Checklist

- [ ] Directory name matches `name` frontmatter exactly
- [ ] Description 80–1024 chars, inline YAML, no `>`
- [ ] Description has positive triggers (product name, symbols, task phrases)
- [ ] Description ends with `Does NOT handle X — use Y-skill`
- [ ] `## When to Use` and `## When NOT to Use` near top of body
- [ ] Decision table if skill covers multiple sub-cases or deployments
- [ ] Numbered steps with branch conditions for operational workflows
- [ ] Production-idiomatic code examples (not toy snippets)
- [ ] Every prohibition paired with a concrete alternative
- [ ] Inter-skill delegation explicit in body when prerequisites are elsewhere
- [ ] Checklist at end of skill body
- [ ] Write operations gated behind explicit confirmation
- [ ] Credentials via env vars; `.env` in `.gitignore`
- [ ] `SKILL.md` under 500 lines; overflow in `references/` with explicit links
- [ ] `git add <skill-dir>` then `python3 scripts/lint_skills.py` — all pass
- [ ] `README.md` in skill directory covers what skill does, availability, install command
- [ ] **No placeholders** — no `[Insert Repo Path]`, `[TODO]`, or `[Your Value Here]` left in the skill; use relative paths or instruct the agent to discover them with `ls`/`find`
- [ ] **Dry run test** — could a junior developer with no ability to ask questions complete every step? If not, add the missing branch conditions or context
- [ ] **Self-healing** — every command that can fail has an explicit failure path (revert, report, stop)
