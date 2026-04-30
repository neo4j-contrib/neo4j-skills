# Writing Skills for this Repository

A `SKILL.md` is an on-demand operational playbook for an autonomous coding agent — runbook with judgment, checklist with decision logic, guardrail against improvisational mistakes.

All skills live in `neo4j-*-skill/` directories. Run `python3 scripts/lint_skills.py` before every commit.

## Language Style — Write for Agents, Not Humans

Skills are read by agents that execute instructions, not humans that interpret prose. Strip every word that doesn't add information. The [Caveman compression](https://github.com/juliusbrussee/caveman) principle: remove articles, politeness, conjunctions, and explanatory padding. Keep technical content (code, commands, tables) untouched.

```
❌ You should always make sure to check the schema first before writing any queries.
✅ Check schema before writing any query.

❌ The following defaults must be applied to every query that you generate.
✅ Defaults — apply every query:

❌ Don't create a new driver per request — it is important that you create one Driver
   at startup and share it across goroutines for performance reasons.
✅ Create one Driver at startup; share across goroutines. Never create per-request.
```

Every instruction must be answerable with "done" or "not done". Terse is correct; verbose is noise that costs tokens and buries the rule.

**The 500-line budget is for content, not ceremony.** Frontmatter + When to Use/NOT + Entry + Checklist take ~40 lines. Spend the rest on actionable rules, decision tables, and code examples — not on explanatory paragraphs the agent doesn't need.

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

### Write imperatively

Commands, not explanations. See Language Style section above for examples.

### Open with When to Use / When NOT to Use

Always first two sections. Short-circuits agent before it reads the body:

````markdown
## When to Use
- Running GDS algorithms on Aura BC or VDC

## When NOT to Use
- **Aura Pro with GDS plugin** → use `neo4j-gds-skill`
- **Writing Cypher queries** → use `neo4j-cypher-skill`
````

### Entry criteria (operational skills only)

State prerequisites before execution begins:

```markdown
## Entry criteria
- Feature request or bug report present
- Files to modify identified
- Existing tests passing
```

### Specify artifacts explicitly

State exact outputs — agent improvises format without this:

```markdown
## Outputs
- Modified `SKILL.md` with inline description
- Lint output confirming all checks pass
```

### Handle uncertainty explicitly

Missing info before starting (not command failure):

```markdown
If required context missing: state what's missing, ask for minimum input. Do NOT guess.
```

### Narrow Bridge vs Open Field

- **Narrow Bridge** (migrations, schema changes, bulk writes): exact sequential commands, every branch explicit. No room for improvisation.
- **Open Field** (code review, refactoring, analysis): goals + constraints only; let agent find the path. Over-specifying produces brittle skills.

### Procedural numbered steps for operational skills

Connect/provision/import/deploy skills — numbered steps, each with code block and branch condition:

````markdown
## Step 1 — Verify GDS is available

```cypher
RETURN gds.version() AS gds_version
```

If fails with `Unknown function 'gds.version'` → GDS not installed. **Stop and inform user.**

## Step 2 — Estimate memory before projecting
````

Evidence: numbered workflows +25% correctness, +20% completeness (Augment Code).

### Decision tables when multiple approaches exist

Force choice upfront — don't describe all approaches in prose:

````markdown
| Deployment | Use |
|---|---|
| Aura Pro | `neo4j-gds-skill` (embedded plugin) |
| Aura BC / VDC | `neo4j-aura-graph-analytics-skill` (serverless) |
| Self-managed | `neo4j-gds-skill` |
````

Evidence: +25% best-practice adherence (Augment Code).

### Real code examples — idiomatic, not toy

Agents copy patterns. Show production-idiomatic usage; for transformations use diff blocks:

```diff
- const driver = neo4j.driver(uri, neo4j.auth.basic(user, password))
+ const driver = await neo4j.driver(uri, neo4j.auth.basic(user, password))
+ await driver.verifyConnectivity()
```

Evidence: +20% code reuse (Augment Code).

### Pair every prohibition with a solution

```
❌  Don't create a new driver per request.
✅  Create one Driver at startup; share across goroutines.
```

15+ unpaired warnings → agents over-explore, 2× slower (Augment Code).

### Inter-skill delegation

Name delegation in the body, not just description:

```markdown
If `gds.version()` fails → GDS unavailable. Delegate to `neo4j-aura-graph-analytics-skill`.
```

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

```markdown
Before any traversal via MCP: run EXPLAIN or COUNT(*). No LIMIT → warn. Default LIMIT 25.
```

### Plan-First for complex skills

Multi-file or non-trivial transformations:

```markdown
Before changes: list files+reasons, state before/after, identify risks. Proceed only after plan visible.
```

### Self-Healing — explicit failure paths

Every command that can fail needs a failure path:

```markdown
Run `npm test`. If fails: do NOT proceed. Revert with `git checkout .`. Report exact error.
```

### Async operations — poll explicitly

Index builds, migrations, Aura provisioning return immediately. Tell agent to poll:

```markdown
After migration: poll `SHOW INDEXES YIELD name, state WHERE state <> 'ONLINE'` every 5s
until empty. Do NOT use index until ONLINE.
```

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

### Language style applies to `references/` too

Same caveman compression rule applies to every file in `references/`. References are loaded at execution time and read in full — verbosity costs tokens just as much as in `SKILL.md`.

#### Remove — pure prose padding

| Pattern | Example | Action |
|---|---|---|
| Section intro restating the heading | "This section describes the available options for configuring…" | Delete entirely |
| Numbered step comment before self-describing command | `# 2. Create instance` before `aura-cli instance create \` | Delete |
| Hedging | "you may want to", "it is generally recommended that" | Delete or restate as imperative |
| Redundant label before single code block | `**Example**:` when there is exactly one example | Delete |
| "What is X?" overview when X is already named in the section heading | "The Model Context Protocol (MCP) is a standardized way for AI agents to…" | Delete |
| Passive voice explaining what a command does | "This command adds the credential and sets it as the default." | Delete (the command is self-documenting) |

#### Never remove — technical content

The test: *would a developer need to look this up?* If yes, it stays.

| Type | Examples |
|---|---|
| Flag / option lists | `--name`, `--type <enterprise-db\|professional-db>`, with their descriptions |
| Error trigger strings | `Error: authentication failed`, `Error: rate limit exceeded` |
| Error fix steps | The bullet list or sentence explaining how to resolve each error |
| Example output | JSON responses, table output, plain-text results from commands |
| Code blocks | Any fenced block |
| Table data rows | Any row in a markdown table |
| `key: value` reference pairs | `NEO4J_DATABASE` - target database (default: neo4j) |
| Sub-command descriptions | One-line summaries under `#### create`, `#### list` etc. when they add meaning beyond the name |
| Best Practices / Checklist items | Concrete numbered or bulleted guidance with actionable content |

**The terse rule compresses sentences. It never removes facts.**

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
