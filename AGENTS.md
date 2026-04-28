# Writing Skills for this Repository

When adding or editing skills in this repository, follow these rules. All skills live in `neo4j-*-skill/` directories. Run `python3 scripts/lint_skills.py` before every commit — all skills must pass.

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
#### [Title] — Severity: HIGH / MEDIUM / LOW
- **Current**: what the code does
- **Problem**: why it's wrong  
- **Fix**: specific change with code snippet
````

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
