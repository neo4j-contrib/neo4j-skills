# Scripts in Skills

Skills can ship executable scripts alongside `SKILL.md`. This document covers when to do it, how to do it safely, and what a good Neo4j script looks like.

---

## When to include scripts

Include a `scripts/` directory when:

- The operation involves multiple sequential steps that the agent would otherwise improvise inconsistently
- The invocation requires exact parameter handling (types, optionals, env loading)
- The operation is repeatable and the same command should work identically every time
- The script can be inspected by the user before execution

Do **not** include scripts for:
- One-liner operations (`cypher-shell -u … -p … "RETURN 1"`) — put them inline in the skill body
- Operations so destructive they should always be composed by the agent on demand with user input

---

## Security model

Scripts are **not auto-executed**. The skill body controls when the agent invokes them. The pattern:

1. Agent reads the relevant script (or the skill body describes it)
2. For write/schema/destructive operations: agent shows the command + estimated impact
3. User confirms
4. Agent executes

This means the script file itself is not a security risk — it's a template. The skill body is where confirmation gates live. See `AGENTS.md §Security and Write Operations` for the gate rules.

---

## Directory structure

```
neo4j-my-skill/
├── SKILL.md
├── scripts/
│   ├── check_schema.py       # read-only, no gate needed
│   ├── run_migration.py      # write/schema — gate required in SKILL.md
│   └── wait_for_indexes.py   # polling helper
└── references/
    └── REFERENCE.md
```

Scripts must be referenced explicitly from `SKILL.md`. Unreferenced scripts have <10% discovery rate.

---

## Parameter documentation

Every script exposed to the agent must have a parameter table in the skill body:

```markdown
| Parameter | Type | Description | Required | Default |
|---|---|---|---|---|
| `NEO4J_URI` | env | Bolt URI of the database | Yes | — |
| `NEO4J_USERNAME` | env | Database username | Yes | `neo4j` |
| `NEO4J_PASSWORD` | env | Database password | Yes | — |
| `--database` | arg | Target database name | No | `neo4j` |
| `--limit` | arg | Max rows to return | No | `25` |
```

Use `env` for env-var parameters (loaded from `.env` automatically), `arg` for CLI arguments.

---

## Cross-platform invocation

Always show both Bash and PowerShell when a script ships in the skill body:

```markdown
**Bash / macOS / Linux:**
```bash
python3 scripts/run_migration.py --database neo4j
```

**Windows (PowerShell):**
```powershell
python scripts\run_migration.py --database neo4j
```
```

---

## Neo4j script examples

### Python — run a read query and print results

`scripts/run_cypher.py` — general-purpose read-only query runner. Used by diagnostic and health-check skills.

```python
#!/usr/bin/env python3
"""Run a Cypher query against Neo4j and print results as a table."""

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # dotenv optional; rely on env vars being set

try:
    from neo4j import GraphDatabase
except ImportError:
    sys.exit("neo4j package not found — run: pip install neo4j")


def main():
    parser = argparse.ArgumentParser(description="Run a Cypher query")
    parser.add_argument("query", help="Cypher query to execute")
    parser.add_argument("--database", default="neo4j", help="Target database (default: neo4j)")
    parser.add_argument("--limit", type=int, default=25, help="Max rows (default: 25)")
    args = parser.parse_args()

    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")

    if not uri or not password:
        sys.exit("ERROR: NEO4J_URI and NEO4J_PASSWORD must be set in .env or environment")

    query = args.query
    if "LIMIT" not in query.upper():
        query = f"{query.rstrip()} LIMIT {args.limit}"

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        records, summary, _ = driver.execute_query(
            query,
            database_=args.database,
        )

    if not records:
        print("(no results)")
        return

    keys = records[0].keys()
    col_width = max(len(k) for k in keys)
    header = " | ".join(k.ljust(col_width) for k in keys)
    print(header)
    print("-" * len(header))
    for record in records:
        print(" | ".join(str(record[k]).ljust(col_width) for k in keys))

    print(f"\n{len(records)} row(s)  —  {summary.result_available_after}ms")


if __name__ == "__main__":
    main()
```

**Skill body invocation block:**

```markdown
## Step 1 — Verify connectivity

```bash
python3 scripts/run_cypher.py "RETURN 1 AS ok"
```
```powershell
python scripts\run_cypher.py "RETURN 1 AS ok"
```

Expected output: `ok | 1`. If this fails with a ServiceUnavailable error, check NEO4J_URI and network access. **Stop and report to the user.**
```

---

### JavaScript — run a read query

`scripts/run_cypher.js` — same purpose, for Node.js environments or projects that already have a `package.json`.

```javascript
#!/usr/bin/env node
/**
 * Run a Cypher query against Neo4j and print results.
 * Usage: node scripts/run_cypher.js "MATCH (n) RETURN count(n) AS total" [--database neo4j] [--limit 25]
 */

const neo4j = require('neo4j-driver');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Load .env if present
const envPath = path.resolve(__dirname, '..', '.env');
if (fs.existsSync(envPath)) {
  fs.readFileSync(envPath, 'utf-8').split('\n').forEach(line => {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#')) {
      const idx = trimmed.indexOf('=');
      if (idx !== -1) {
        const key = trimmed.slice(0, idx).trim();
        const val = trimmed.slice(idx + 1).trim().replace(/(^['"]|['"]$)/g, '');
        if (process.env[key] === undefined) process.env[key] = val;
      }
    }
  });
}

async function main() {
  const args = process.argv.slice(2);
  const query = args[0];
  if (!query) { console.error('Usage: run_cypher.js "<query>" [--database <db>] [--limit <n>]'); process.exit(1); }

  const dbIdx = args.indexOf('--database');
  const database = dbIdx !== -1 ? args[dbIdx + 1] : 'neo4j';
  const limitIdx = args.indexOf('--limit');
  const limit = limitIdx !== -1 ? parseInt(args[limitIdx + 1]) : 25;

  const uri      = process.env.NEO4J_URI;
  const user     = process.env.NEO4J_USERNAME || 'neo4j';
  const password = process.env.NEO4J_PASSWORD;

  if (!uri || !password) {
    console.error('ERROR: NEO4J_URI and NEO4J_PASSWORD must be set in .env or environment');
    process.exit(1);
  }

  const finalQuery = /LIMIT/i.test(query) ? query : `${query.trimEnd()} LIMIT ${limit}`;
  const driver = neo4j.driver(uri, neo4j.auth.basic(user, password));

  try {
    const { records } = await driver.executeQuery(finalQuery, {}, { database });
    if (!records.length) { console.log('(no results)'); return; }

    const keys = records[0].keys;
    const rows = records.map(r => keys.map(k => String(r.get(k))));
    const widths = keys.map((k, i) => Math.max(k.length, ...rows.map(r => r[i].length)));

    console.log(keys.map((k, i) => k.padEnd(widths[i])).join(' | '));
    console.log(widths.map(w => '-'.repeat(w)).join('-+-'));
    rows.forEach(row => console.log(row.map((v, i) => v.padEnd(widths[i])).join(' | ')));
    console.log(`\n${records.length} row(s)`);
  } finally {
    await driver.close();
  }
}

main().catch(err => { console.error('ERROR:', err.message); process.exit(1); });
```

**Dependencies:** `npm install neo4j-driver` (or add to the skill's `package.json`).

---

## Invocation gates in SKILL.md

Read-only scripts — no gate required:

```markdown
Run the schema check:
```bash
python3 scripts/check_schema.py
```
```

Write/schema/destructive scripts — always gate:

```markdown
The following command will create a uniqueness constraint on `:User(email)`.
**Show this command to the user and wait for explicit confirmation before running it.**

```bash
python3 scripts/run_migration.py --constraint "CREATE CONSTRAINT user_email_unique FOR (u:User) REQUIRE u.email IS UNIQUE"
```

If the command fails with `ConstraintAlreadyExists`, the constraint is already in place — continue.
If it fails with any other error, stop and report the exact error message.
```

---

## What to put in scripts/ vs inline in SKILL.md

| Put in `scripts/` | Put inline in skill body |
|---|---|
| Multi-step logic with error handling | Single-statement Cypher examples |
| Operations with complex parameter handling | `cypher-shell` one-liners |
| Reusable utilities (wait_for_indexes, health check) | curl/HTTP API examples |
| Operations where exact reproducibility matters | Driver code snippets for illustration |
