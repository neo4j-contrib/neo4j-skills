---
name: neo4j-cli-tools-skill
description: Use when working with Neo4j command-line tools — neo4j-cli (modern unified
  CLI — Cypher via Bolt, schema inspection, Aura management, Docker containers, credential
  management, agent skill catalog install; install with curl -sSfL https://neo4j.sh/install.sh | bash),
  neo4j-admin (backup, restore, import, memory sizing), cypher-shell (ad-hoc queries,
  scripting, CI/CD), or neo4j-mcp (quick MCP server install).
  Does NOT cover Cypher query authoring — use neo4j-cypher-skill.
  Does NOT cover driver upgrades — use neo4j-migration-skill.
  Does NOT cover full MCP editor configuration — use neo4j-mcp-skill.
  Does NOT cover the relate embedded engine (relatedb.ai) — use the relate skill; choice guide in neo4j-getting-started-skill.
allowed-tools: WebFetch, Bash
version: 1.0.18
---

# Neo4j CLI Tools skill

## When to Use

- Cypher queries, schema inspection, Aura, Docker, credentials, agent skills → `neo4j-cli` (**preferred**)
- Admin tasks: backup, restore, import, memory sizing → `neo4j-admin`
- Ad-hoc queries, scripting, CI/CD (Java required) → `cypher-shell`
- MCP server install → `neo4j-mcp`
- Offline fixtures / local embedded graph, Neo4j↔local copy → `relate pull` / `relate push` (see [relate](#6-relate-embedded-engine-third-party))

## When NOT to Use

- **Writing or optimizing Cypher queries** → `neo4j-cypher-skill`
- **Upgrading Neo4j drivers or migrating Cypher syntax** → `neo4j-migration-skill`
- **Starting a new Neo4j project from scratch** → `neo4j-getting-started-skill`

## Available CLI Tools

### 1. neo4j-cli

Modern unified CLI. Bolt-native Cypher, schema inspection, Aura management, local Docker, credential storage, agent skill catalog install. Single binary — no Java required.

**Install:**
```bash
curl -sSfL https://neo4j.sh/install.sh | bash   # recommended
brew install neo4j-labs/tap/neo4j-cli            # Homebrew
pip install neo4j-cli / pipx install neo4j-cli   # PyPI
npm i -g @neo4j-labs/cli                         # npm
```

**Self-update:** `neo4j-cli update` (also refreshes installed skills automatically)

**Key subcommands:**

| Subcommand | Purpose |
|---|---|
| `neo4j-cli query [cypher]` | Run Cypher via Bolt — auto-rewrites HTTP URIs |
| `neo4j-cli query :schema` | Inspect labels, rel types, indexes, constraints |
| `neo4j-cli query :embed [text]` | Compute embedding vector standalone |
| `neo4j-cli aura instance ...` | Provision and manage Aura instances |
| `neo4j-cli aura agent ...` | Manage Aura Agents (list/get/create/invoke) |
| `neo4j-cli docker create/start/stop/delete` | Manage local Neo4j Docker containers |
| `neo4j-cli credential aura-client ...` | Store Aura API credentials |
| `neo4j-cli credential dbms ...` | Store Neo4j connection profiles (URI + auth) |
| `neo4j-cli credential embed ...` | Store embedding provider credentials |
| `neo4j-cli skill install [skill-name]` | Install self-skill or any catalog skill |
| `neo4j-cli skill list / check / remove` | Manage installed agent skills |
| `neo4j-cli update` | Self-update binary + refresh installed skills |

**Key patterns:**
```bash
# Schema-first workflow: always inspect schema before writing Cypher
neo4j-cli query :schema --format toon

# Run Cypher (bolt URIs auto-rewritten; HTTP URIs rewritten to Bolt)
neo4j-cli query "MATCH (n:Person) RETURN n.name LIMIT 5" \
  --uri neo4j+s://xxx.databases.neo4j.io --username neo4j --password $PASS

# Inline embedding parameter (text → vector; $q bound to []float32)
neo4j-cli query "MATCH (c) SEARCH c IN (VECTOR INDEX chunk_embedding FOR \$q LIMIT 5) SCORE AS score RETURN c.text, score" \
  --param q:embed="graph database performance"

# Store a connection profile, then query without flags
neo4j-cli credential dbms add --name prod \
  --uri neo4j+s://xxx.databases.neo4j.io --username neo4j --password $PASS
neo4j-cli query --credential prod "MATCH (n) RETURN count(n)"

# Local Docker: persistent or ephemeral
neo4j-cli docker create --name dev --wait --rw
neo4j-cli query --credential dev 'RETURN 1 AS n'
neo4j-cli docker create --name tmp --ephemeral --env-out-file /tmp/n.env --wait --rw
neo4j-cli query --env /tmp/n.env 'RETURN 1 AS n'

# Install skills from catalog (neo4j/agent-skills)
neo4j-cli skill install                          # self-skill into all detected agents
neo4j-cli skill install neo4j-cypher-skill       # one catalog skill, all agents
neo4j-cli skill install --all                    # self-skill + every catalog skill
neo4j-cli skill install --agent claude-code      # scope to one agent
neo4j-cli skill check                            # detect drift after upgrades
```

**Agent output:** Always use `--format toon` — ~40% fewer tokens than JSON. Set as default: `neo4j-cli config set format toon`.

**Write gate:** Write operations require `--rw` under agent harnesses. Do NOT add it preemptively — if a command fails with "this command writes; pass --rw to allow it", surface the error and ask the user once.

**Async operations:** `instance create/resize/destroy` and `docker create` accept `--wait` to block until terminal state.

**Credentials precedence:** flag > OS env (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`) > `.env` walk-up > stored credential. OS env vars are **ignored by default** — read only when `accept-env-vars` is enabled (`neo4j-cli config set accept-env-vars true --rw` or `NEO4J_CLI_ACCEPT_ENV_VARS=1`); otherwise a stored credential is used silently. Prefer `--uri/--username/--password`, `--env <file>` or `--credential <name>`.

**Supported agents:** Claude Code, Cursor, Windsurf, Copilot, Gemini CLI, Antigravity CLI, Cline, Codex, OpenCode, Junie, and more. Antigravity: skills land in `~/.gemini/antigravity/skills`.

Full reference: `neo4j-cli skill install` keeps an always-in-sync skill in your agent.

---

### 2. neo4j-admin

Included with Neo4j. Backup, restore, dump/load, CSV import, memory sizing, password reset. Run as Neo4j system user.

Reference: [neo4j-admin-reference.md](references/neo4j-admin-reference.md)

### 3. cypher-shell

Interactive Cypher REPL. Requires Java 21. Included with Neo4j. Use for ad-hoc queries, file-based batch scripting, CI/CD pipelines.

Reference: [cypher-shell-reference.md](references/cypher-shell-reference.md)

### 4. aura-cli

Legacy Aura cloud CLI. **Prefer `neo4j-cli aura` for new work** — covers all aura-cli operations plus credential storage, Docker, and agent skills.

Reference: [aura-cli-reference.md](references/aura-cli-reference.md)

### 5. neo4j-mcp

MCP server for AI agent integration. For full install + editor config → use `neo4j-mcp-skill` (covers Claude Code, Desktop, Cursor, Windsurf, VS Code, Kiro, stdio vs HTTP transport, troubleshooting).

```bash
pip install neo4j-mcp-server && neo4j-mcp-server -v   # PyPI: command is neo4j-mcp-server
brew install neo4j-mcp && neo4j-mcp -v                 # Homebrew: command is neo4j-mcp
```

Server 2.0.0 (2026-10-28) accepts only `NEO4J_MCP_*` env vars and unprefixed flags (`--uri`, `--database`); STDIO requires `NEO4J_MCP_DATABASE`. See [CHANGELOG](https://github.com/neo4j/mcp/blob/main/CHANGELOG.md).

Reference: [neo4j-mcp-reference.md](references/neo4j-mcp-reference.md)

### 6. Relate by Neo4j (embedded engine)

Embedded in-memory Cypher graph database, single binary. A Neo4j product; but not a replacement for a Neo4j server. Single process, one writer, graph must fit in RAM, no RBAC/clustering.

| Situation | Use |
|---|---|
| Production, concurrent writers, larger-than-RAM, HA, RBAC, GDS, Aura | Neo4j (this skill's other tools) |
| Offline test fixtures, sandbox analytics, single-agent local memory, edge/WASM | relate |

Full matrix: `neo4j-getting-started-skill` → `references/choose-engine.md`.

```bash
curl -sSfL https://relatedb.ai/install.sh | bash   # CLI
npx skills add https://relatedb.ai --skill relate  # relate skill; --skill required (else installs all six)
# Neo4j/Aura slice → local file (needs neo4j.env: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
relate pull --from neo4j.env --query 'MATCH (p:Person)-[r]-() RETURN p, r LIMIT 500' --database ./slice.rl
# local file → Neo4j/Aura: dry-run first, confirm with user before the real push
relate push --to neo4j.env --database ./slice.rl --dry-run
```

`pull` skips VECTOR/FULLTEXT indexes; destination must be empty. relate CLI, Cypher-on-relate, vector, geospatial → delegate to the relate skill. Docs for agents: https://relatedb.ai/llms.txt · https://relatedb.ai/skill.md

## Backup and Recovery

### Edition gate

Online backup requires **Enterprise Edition**. Community Edition users must use dump/load only (database must be offline).

### Backup (Enterprise — database stays online)

```bash
# Database name is positional (last); there is no --database option
# Full online backup — database stays online during backup
neo4j-admin database backup --to-path=/backups/ --type=FULL neo4j

# Differential backup — only changes since last backup in the chain (faster)
neo4j-admin database backup --to-path=/backups/ --type=DIFF neo4j

# Backup to cloud storage (S3, GCS, or Azure)
neo4j-admin database backup --to-path=s3://my-bucket/neo4j-backups/ neo4j
```

`--type` = `FULL` / `DIFF` / `AUTO` (default `AUTO`: full if no chain exists). `--compress` defaults to `true`. Each run writes a `<db>-<timestamp>.backup` artifact file into `--to-path`.

### Restore (Enterprise)

**AGENT GATE — destructive operation**: Before running restore, show the user the exact command and target database name, and wait for explicit confirmation. A restore overwrites the existing database.

```bash
# Database name is positional; allowed only when --from-path is a single artifact
# Replace existing DB: stop it first (STOP DATABASE neo4j on system)
neo4j-admin database restore \
  --from-path=/backups/neo4j-2026-01-15T10-00-00.backup \
  --overwrite-destination=true \
  neo4j

# Restore to a new database name (non-destructive path), then CREATE DATABASE neo4jrestored on system
neo4j-admin database restore \
  --from-path=/backups/neo4j-2026-01-15T10-00-00.backup \
  neo4jrestored
```

### Dump / Load (all editions — database must be offline)

Use for migrations, dev/test data transfers, and Community Edition backups.

```bash
# Dump — database must be stopped (dump of a running DB fails); writes /exports/neo4j.dump
neo4j-admin database dump --to-path=/exports/ neo4j

# Load — --from-path is a DIRECTORY; looks for <database>.dump; database name positional
neo4j-admin database load \
  --from-path=/exports/ \
  --overwrite-destination=true \
  neo4j
```

**AGENT GATE — destructive operation**: Before running load with `--overwrite-destination=true`, confirm target database name and path with the user.

### Key flags

| Flag | Notes |
|---|---|
| `--compress` | Compress backup artifact (default `true`) |
| `--type=FULL\|DIFF\|AUTO` | Backup type; default `AUTO` |
| `--to-path` | Directory: local path or `s3://`, `gs://`, `azb://` |
| `--overwrite-destination=true` | Required if target database already exists; target must be stopped |
| `--restore-until` | Restore chain up to a transaction ID or UTC timestamp |

### Point-in-time restore strategy

- **Full backup**: weekly (e.g. every Sunday)
- **Differential backup**: daily (captures only changes since last full)
- **Naming**: neo4j-admin names artifacts `<db>-<timestamp>.backup`; keep one chain per `--to-path` directory
- **Restore sequence**: ONE restore. Pointing `--from-path` at a differential artifact replays the whole chain (full + differentials up to it). Never run separate overwrite restores per artifact — each replaces the DB.

```bash
# Restore Sunday full + Monday + Tuesday differentials: point at Tuesday's artifact
neo4j-admin database restore \
  --from-path=/backups/neo4j-2026-01-21T02-00-00.backup \
  --overwrite-destination=true neo4j

# Point-in-time: stop replay at a UTC timestamp (or transaction ID: --restore-until=123)
neo4j-admin database restore \
  --from-path=/backups/neo4j-2026-01-21T02-00-00.backup \
  --restore-until="2026-01-21 01:30:00" \
  --overwrite-destination=true neo4j
```

---

## Environment Variables (neo4j-admin / cypher-shell)

- `NEO4J_URI` / `NEO4J_ADDRESS` — connection URI
- `NEO4J_USERNAME` / `NEO4J_PASSWORD` / `NEO4J_DATABASE`
- `NEO4J_CONF` — path to neo4j.conf directory
- `NEO4J_HOME` — Neo4j installation directory

Precedence: flags > env vars > config files. neo4j-cli uses its own credential store — see `neo4j-cli credential dbms`.

## Resources

- [Neo4j Operations Manual](https://neo4j.com/docs/operations-manual/current/)
- [Cypher Shell Documentation](https://neo4j.com/docs/operations-manual/current/cypher-shell/)
- [Aura CLI GitHub](https://github.com/neo4j/aura-cli)
- [Neo4j MCP Documentation](https://neo4j.com/docs/mcp/current/)
- [Neo4j Developer Portal](https://neo4j.com/developer/)

---

## Checklist

- [ ] Correct tool selected: neo4j-cli (preferred) / neo4j-admin / cypher-shell / neo4j-mcp / relate (embedded only)
- [ ] If using neo4j-cli: `neo4j-cli skill install` run after install or upgrade (keeps skill in sync)
- [ ] Credentials via env or `credential dbms`; not hardcoded
- [ ] Using `--format toon` for agent-facing neo4j-cli output
- [ ] Destructive ops confirmed before execution
- [ ] Post-op verify: connect + `SHOW INDEXES` + count
- [ ] Backup taken before restore or schema change
