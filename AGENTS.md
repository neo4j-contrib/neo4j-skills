# How to Write Good Agent Skills

A practical guide to writing high-quality `SKILL.md` files and agent instruction files (`AGENTS.md` / `CLAUDE.md`), synthesizing lessons from the Agent Skills open standard, Claude Code documentation, OpenAI Codex guides, real-world skill reviews, and experience building this repository.

---

## Table of Contents

1. [The Two Layers: Skills vs Context Files](#1-the-two-layers-skills-vs-context-files)
2. [The SKILL.md Spec (agentskills.io)](#2-the-skillmd-spec-agentskillsio)
3. [The Description Field — The Routing Signal](#3-the-description-field--the-routing-signal)
4. [Body Patterns That Work](#4-body-patterns-that-work)
5. [Anti-Patterns to Avoid](#5-anti-patterns-to-avoid)
6. [Writing CLAUDE.md / AGENTS.md Context Files](#6-writing-claudemd--agentsmd-context-files)
7. [Discovery and Progressive Disclosure](#7-discovery-and-progressive-disclosure)
8. [Security, Credentials, and Write Operations](#8-security-credentials-and-write-operations)
9. [Validation and Linting](#9-validation-and-linting)
10. [Checklist](#10-checklist)

---

## 1. The Two Layers: Skills vs Context Files

| Layer | File | When loaded | Purpose |
|---|---|---|---|
| **Context** | `CLAUDE.md` / `AGENTS.md` | Every session, always | Facts, rules, conventions that apply to all work in this project |
| **Skill** | `SKILL.md` | On demand, when relevant | Playbooks for specific tasks — loaded only when the task matches |

**Rule**: If it's a multi-step procedure, it belongs in a skill, not `CLAUDE.md`. If it's a fact the agent needs in every session (build command, test runner, naming convention), it belongs in `CLAUDE.md`.

### Tooling differences

| Tool | Reads | File location |
|---|---|---|
| Claude Code | `CLAUDE.md` | `./CLAUDE.md`, `./.claude/CLAUDE.md`, `~/.claude/CLAUDE.md` |
| OpenAI Codex | `AGENTS.md` | `~/.codex/AGENTS.md`, repo root → subdirs (closer overrides) |
| Both | Skills via `SKILL.md` | `.claude/skills/<name>/SKILL.md` or per the agentskills.io spec |

If your repo uses `AGENTS.md` for Codex and you also use Claude Code, create a `CLAUDE.md` that imports it:
```markdown
@AGENTS.md

## Claude Code specifics
Use plan mode for changes under `src/billing/`.
```

---

## 2. The SKILL.md Spec (agentskills.io)

The [Agent Skills open standard](https://agentskills.io/specification) defines the `SKILL.md` format. It is supported by Claude Code, OpenAI Codex, and other agents.

### Directory structure

```
skill-name/
├── SKILL.md          # Required — metadata + instructions
├── references/       # Optional — detailed docs loaded on demand
├── scripts/          # Optional — executable code
└── assets/           # Optional — templates, data files
```

### Frontmatter fields

```yaml
---
name: my-skill-name           # Required. Must match parent directory name.
description: >-               # Required. 80–1024 chars (Claude Code linter enforces 80 min).
  What it does and when to use it. Include keywords. End with "Does NOT handle X — use Y."
compatibility: Claude Code    # Optional. Max 500 chars. Only if env requirements exist.
license: Apache-2.0           # Optional.
allowed-tools: Bash WebFetch  # Optional. Pre-approved tools (space-separated).
version: 1.0.0                # Optional (Claude Code extension, not in base spec).
status: draft                 # Optional (Claude Code extension).
---
```

### Hard rules

- `name` must exactly match the parent directory name (linters fail on mismatch)
- `name`: lowercase letters, numbers, hyphens only; no consecutive hyphens; no leading/trailing hyphen; max 64 chars
- `description`: 80–1024 characters; must be non-empty
- `compatibility`: max 500 characters if provided
- No unknown top-level frontmatter fields (linters reject them)
- **YAML inline format only**: use `description: First line text\n  continuation lines` — never use `description: >` (block scalar). Block scalars cause the raw `>` character to be read as the description value by many parsers.

---

## 3. The Description Field — The Routing Signal

The `description` is the single most important field. Agents use it as their primary routing signal — they scan all available skill descriptions to decide which skill to load. Get this wrong and the skill never triggers (or triggers on the wrong tasks).

### Anatomy of a good description

```
[What it does] + [When to use it — positive triggers] + [Does NOT handle X — use Y-skill instead]
```

**Example (good)**:
```yaml
description: Comprehensive guide to the Neo4j Go Driver v6 — covering driver lifecycle,
  ExecuteQuery, managed and explicit transactions, error handling, and data type mapping.
  Use when writing Go code that connects to Neo4j, setting up NewDriver() or ExecuteQuery()
  in Go, or debugging session/transaction patterns. Also triggers on neo4j-go-driver,
  SessionConfig, ManagedTransaction, or any Neo4j Bolt connection work in Go.
  Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
  Does NOT cover driver migration — use neo4j-migration-skill.
```

**Example (poor)**:
```yaml
description: Helps with the Neo4j Go driver.
```

### Positive triggers

Pack the description with:
- The canonical product name and version: `Neo4j Go Driver v6`, `graphdatascience v1.21`
- Common entry-point symbols: `NewDriver`, `ExecuteQuery`, `GraphDataScience`, `gds.pageRank`
- Natural-language task phrases: `"Use when writing Go code that connects to Neo4j"`
- Synonyms users might write: both `GDS` and `Graph Data Science`

### Negative triggers — the gold standard

Always include explicit exclusions. Name the sibling skill, not just the category:

```
Does NOT handle Cypher query authoring — use neo4j-cypher-skill.
Does NOT cover Aura Graph Analytics serverless sessions — use neo4j-aura-graph-analytics-skill.
```

Never write a bare "Don't" without naming where to go instead. A bundle with 15+ skills especially needs tight routing; the agent must know which skill handles each boundary case without ambiguity.

The MongoDB `mongodb-natural-language-querying` pattern is the gold standard:
> "Does NOT handle Atlas Search ($search operator) — use search-and-ai for those. Does NOT analyze or optimize queries — use mongodb-query-optimizer for that."

### When NOT to Use sections

Repeat the negative triggers in the skill body too, in a `## When NOT to Use` section near the top. The description routing and the body guidance reinforce each other:

```markdown
## When NOT to Use

- **Writing or optimizing Cypher queries** → use `neo4j-cypher-skill`
- **GDS plugin on Aura Pro or self-managed Neo4j** → use `neo4j-gds-skill`
- **Snowflake Graph Analytics** → use `neo4j-snowflake-graph-analytics-skill`
```

---

## 4. Body Patterns That Work

Evidence-backed patterns (source: Augment Code research + this repo's experience):

### Pattern 1: When to Use / When NOT to Use (at the top)

Always open the skill body with both sections. This short-circuits the agent from reading the whole skill before deciding it's the wrong one. Keep it to 4–6 bullets each.

### Pattern 2: Procedural numbered workflows (+25% correctness, +20% completeness)

For operational skills (deploy, import, provision, connect), use strict numbered steps. Each step should have:
- A clear action
- A code block
- A branch condition: "if X → continue; if Y → stop and report"

```markdown
## Step 1 — Verify GDS is available

```cypher
RETURN gds.version() AS gds_version
```

If this fails with `Unknown function 'gds.version'`, GDS is not installed. Stop and inform the user.

## Step 2 — Estimate memory before projecting
...
```

This makes skills deterministic — the agent cannot skip or reorder steps.

### Pattern 3: Decision tables (+25% best-practice adherence)

When multiple valid approaches exist, force the choice upfront with a decision table rather than describing all approaches in prose:

```markdown
| Question | Approach |
|---|---|
| Aura Pro or self-managed Neo4j? | Use GDS plugin (`neo4j-gds-skill`) |
| Aura Business Critical or VDC? | Use Aura Graph Analytics (this skill) |
| Non-Neo4j data source (Pandas, Spark)? | Use standalone AGA session |
| Need real-time graph traversal from app code? | Use the Neo4j driver + Cypher |
```

Also useful as a routing tree at the top of skills that cover multiple sub-cases.

### Pattern 4: Real code examples from production (+20% code reuse)

Include 3–10 line snippets that represent the idiomatic pattern — not toy examples. Agents copy patterns they see. If you show `gds.run_cypher()` in the right context once, the agent will use it correctly everywhere.

Bad (toy):
```python
gds.pageRank.stream(G)
```

Good (production-idiomatic):
```python
gds = sessions.get_or_create(
    session_name="prod-analysis",
    memory=memory,
    db_connection=DbmsConnectionInfo.from_env(),
    ttl=timedelta(hours=4),
)
gds.verify_connectivity()
```

### Pattern 5: Pair every "Don't" with a "Do"

Never list prohibitions without solutions. `Documentation with 15+ sequential warnings without solutions caused over-exploration and incomplete work` (Augment Code research):

```
❌  Don't instantiate HTTP clients directly.
✅  Don't instantiate HTTP clients directly — use the shared apiClient from lib/http 
    (includes retry middleware and auth headers).
```

### Pattern 6: Structured output templates

For review or analysis skills, prescribe the exact markdown the agent must produce. This prevents freeform responses that don't match the expected format:

```markdown
## Output format

### Compliant
- [item]

### Issues Found
#### [Issue Title] — Severity: HIGH / MEDIUM / LOW
- **Current**: what the code does
- **Problem**: why it's wrong
- **Fix**: specific recommendation with code snippet
```

### Pattern 7: Inter-skill delegation

When a task requires a prerequisite from a sibling skill, name the delegation explicitly:

```markdown
If the GDS plugin is not available (gds.version() fails), stop. 
For Aura BC/VDC deployments, delegate to `neo4j-aura-graph-analytics-skill`.
```

DuckDB skills show the gold standard:
> "If not found, delegate to `/duckdb-skills:install-duckdb` and then continue."

### Pattern 8: Provenance labels for derived advice

When giving recommendations that are opinion or field experience rather than documented fact, label them:

- `[official]` — directly from docs
- `[derived]` — follows from documented behavior
- `[field]` — community heuristic (add a disclaimer)

This is especially important for algorithm selection advice (GDS, query optimization) where many recommendations are experience-based.

### Pattern 9: Token-cost awareness

For skills that execute queries or return large results via MCP, add explicit guards:

```markdown
Before running any traversal query:
1. Run `EXPLAIN` or a `COUNT(*)` first
2. Warn if no `LIMIT` on a pattern that could match millions of nodes
3. Default to `LIMIT 25` on exploratory queries
4. Warn before returning result sets that would consume >1K tokens
```

### Pattern 10: Checklist at the end

Close operational skills with a checklist. Agents use checklists to self-verify before reporting completion:

```markdown
## Checklist
- [ ] GDS version confirmed (`gds.version()` returns a result)
- [ ] Memory estimated before projecting large graphs
- [ ] Named graph dropped after use (`G.drop()`)
- [ ] `randomSeed` set for reproducible embeddings
- [ ] Results written back before session deletion (AGA)
```

---

## 5. Anti-Patterns to Avoid

### Overexploration trap

**Excessive architecture overviews**: Detailed "why" explanations (event bus topology, decision rationale, historical context) push agents into reading dozens of documentation files unnecessarily. Focus on "what" and "how". Keep "why" in commit messages and PR descriptions.

**Too many warnings without solutions**: 30–50 "don't" rules cause agents to verify solutions against every warning, loading irrelevant context and taking 2x longer. Cap prohibition lists; pair every one with a concrete alternative.

### Premature patterns

Don't document patterns that don't exist yet in your codebase. If you write a WebSocket pattern alongside a REST+polling implementation, the agent may follow the documented pattern and generate inconsistent code.

### Context sprawl

A focused `AGENTS.md` sitting atop 500K characters of surrounding documentation won't help — the agent reads all of it. Fix the documentation environment by consolidating and removing orphan docs.

### YAML block scalars in frontmatter

Never use `description: >` (block scalar form). Most SKILL.md parsers read the `>` character itself as the description value, producing a 1-character description that fails validation. Use inline format:

```yaml
# Wrong:
description: >
  This skill handles...

# Right:
description: This skill handles complex cases including foo,
  bar, and baz. Use when the user asks about X or Y.
```

### Orphan documentation

From Augment Code research on discovery rates:
- `AGENTS.md` at root: **100%** discovery — the only reliable location
- Files directly referenced from it: **90%+**
- `README.md` in working directory: **80%+**  
- Nested READMEs in subdirectories: **40%**
- Orphan `_docs/` files: **<10%**

Everything important must live in `AGENTS.md` / `CLAUDE.md` or be directly referenced from it.

### Splitting without referencing

If you split content into separate files, reference them explicitly from `SKILL.md`. An unreferenced `references/REFERENCE.md` will be discovered much less reliably than a referenced one.

---

## 6. Writing CLAUDE.md / AGENTS.md Context Files

Context files (not skills) are loaded on every session. They should be short, specific, and factual.

### What belongs here

- Build and test commands: `npm test`, `python3 scripts/lint_skills.py`
- Naming conventions: skill directories must match `name` frontmatter
- Architectural decisions agents would otherwise get wrong
- "Always do X" rules that apply to every task in this repo
- Pointers to relevant sibling skills (max 10–15 references per file)

### What does NOT belong here

- Multi-step procedures → move to a skill
- Content only relevant to one subdirectory → use path-scoped rules (`.claude/rules/`)
- Information derivable from reading the code → skip it
- Historical context or rationale → belongs in commit messages

### Size and structure

**Target under 200 lines** for the main file. Longer files consume more context and reduce adherence. Use markdown headers and bullets. Claude reads structure the same way humans do.

Specificity wins:
```
✅  "Run `python3 scripts/lint_skills.py` before committing new skills"
❌  "Always lint skills before committing"
```

### Scoping for large projects

Use path-scoped rules for instructions that only apply to certain files:

```markdown
---
paths:
  - "neo4j-*-skill/SKILL.md"
---
# Skill authoring rules
- description must be 80–1024 chars
- name must match parent directory
```

### OpenAI Codex file precedence

Codex builds an instruction chain from multiple files:
1. `~/.codex/AGENTS.override.md` — global override
2. `~/.codex/AGENTS.md` — global baseline
3. Repo root `AGENTS.md` → walking toward current directory (closer = higher priority)
4. Files concatenate; combined size must stay under 32 KiB (configurable via `project_doc_max_bytes`)

Use `AGENTS.override.md` for temporary changes without modifying the base file.

### Verify which files are loading

Claude Code: run `/memory` to see all CLAUDE.md and rules files active in the current session.

Codex: run `codex --ask-for-approval never "Summarize current instructions."` to verify the instruction chain.

---

## 7. Discovery and Progressive Disclosure

The agentskills.io spec and Claude Code both implement progressive disclosure:

| Stage | Loaded | Size target |
|---|---|---|
| Skill listing | `name` + `description` (~100 tokens per skill) | 80–1024 chars |
| Skill activation | Full `SKILL.md` body | <500 lines / <5000 tokens |
| Deep reference | `references/*.md`, `scripts/` (on demand) | Any size |

**Design for this**: Keep `SKILL.md` under 500 lines. Move algorithm tables, full API references, and large code examples to `references/REFERENCE.md`. Reference them explicitly so the agent knows to fetch them:

```markdown
For the complete algorithm parameter reference, see [references/algorithms.md](references/algorithms.md).
```

Claude Code-specific: the `description` + `when_to_use` text is capped at 1,536 characters in the skill listing. Front-load the key use case — the first sentence of `description` is the most important.

For skills with many siblings, descriptions are shortened to fit the context budget (1% of context window, minimum 8,000 chars total). Trim descriptions if the budget causes clipping.

---

## 8. Security, Credentials, and Write Operations

### Credential handling

- Write credentials to `.env`, never to shell profiles
- Verify `.env` is in `.gitignore` before continuing in any skill that handles credentials
- Use `AuraAPICredentials.from_env()` / `DbmsConnectionInfo.from_env()` patterns — never hardcode
- Never print credential values in conversation output

### Write operation gates

Any skill that executes writes via MCP tools (`write-cypher`, `git push`, etc.) should:

1. Show the query or command and estimated affected rows/files before executing
2. Require explicit user confirmation for destructive operations (`DELETE`, `DETACH DELETE`, force-push)
3. Never auto-run `CALL IN TRANSACTIONS` or batch writes without approval

Use `disable-model-invocation: true` on deploy, commit, and write-back skills to prevent the agent from triggering them without explicit user intent.

---

## 9. Validation and Linting

### agentskills.io validator

```bash
skills-ref validate ./my-skill
```

### Claude Code skills lint script (this repo)

```bash
python3 scripts/lint_skills.py
```

Checks: `name` matches directory, `description` is 80–1024 chars, no unknown frontmatter fields.

All 21 skills in this repo must pass before committing.

### Manual checks before committing a new skill

- `name` exactly matches parent directory
- `description` is inline (not block scalar `>`)
- `description` includes both positive triggers AND negative triggers with named sibling skills
- `## When to Use` and `## When NOT to Use` sections present in body
- No step in procedural workflows can be skipped (each step has a "continue/stop" branch)
- Code examples are production-idiomatic, not toy snippets
- Write operations require explicit user confirmation
- `SKILL.md` is under 500 lines (move overflow to `references/`)

---

## 10. Checklist

For each new skill:

- [ ] **Directory name** matches `name` frontmatter exactly
- [ ] **Description** 80–1024 chars, inline YAML, no block scalar
- [ ] **Description** has positive triggers (product name, symbols, task phrases)
- [ ] **Description** ends with `Does NOT handle X — use Y-skill`
- [ ] **When to Use / When NOT to Use** in skill body, near the top
- [ ] **Decision table or routing tree** if skill covers multiple sub-cases
- [ ] **Numbered procedural steps** with branch conditions for operational skills
- [ ] **Real code examples** — idiomatic, not toy; from actual API/SDK docs
- [ ] **Every prohibition paired with an alternative**
- [ ] **Checklist at the end** for self-verification
- [ ] **Write operations gated** behind explicit confirmation
- [ ] **Credentials** handled via env vars; `.env` in `.gitignore`
- [ ] **Sibling skill delegation** explicit when prerequisites come from another skill
- [ ] **Large reference material** moved to `references/` and linked from `SKILL.md`
- [ ] **Linter passes**: `python3 scripts/lint_skills.py`

---

## Sources

- [Agent Skills open standard](https://agentskills.io/specification)
- [Augment Code: How to write good AGENTS.md files](https://www.augmentcode.com/blog/how-to-write-good-agents-dot-md-files)
- [Claude Code: Memory (CLAUDE.md guide)](https://code.claude.com/docs/en/memory)
- [Claude Code: Skills documentation](https://code.claude.com/docs/en/skills)
- [OpenAI Codex: AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md)
- [OpenAI Codex: Skills](https://developers.openai.com/codex/skills)
- [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) — real-world skill reviews (Neon, ClickHouse, DuckDB, MongoDB)
- [skills-learnings.md](skills-learnings.md) — lessons from reviewing the above
