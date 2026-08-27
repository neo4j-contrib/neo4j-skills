---
name: neo4j-hol-guard-skill
description: Protect local AI coding-agent Neo4j mutation workflows with HOL Guard before tools execute. Use when a supported local agent harness can run neo4j-cli, neo4j-admin, cypher-shell, MCP, migrations, or other state-changing Neo4j tools and the user wants an additional pre-execution approval boundary. Does NOT replace Neo4j authentication, RBAC, native write gates, backups, or product-specific validation — use the relevant Neo4j skill for the actual database workflow.
allowed-tools: Bash WebFetch
version: 1.0.0
---

# HOL Guard for Neo4j agent workflows

## When to Use
- Supported local coding-agent harness can execute state-changing Neo4j tools
- User wants an additional local pre-execution approval boundary
- Workflow includes CLI, MCP, migration, schema, import, Aura, or administration mutations

## When NOT to Use
- **Write or optimize Cypher** → `neo4j-cypher-skill`
- **Neo4j CLI/admin syntax** → `neo4j-cli-tools-skill`
- **Users, roles, privileges, RBAC, ABAC** → `neo4j-security-skill`
- **Neo4j MCP setup** → `neo4j-mcp-skill`
- **No supported local agent harness is present** → use Neo4j native controls only; do not claim Guard coverage

## Entry criteria
- State-changing Neo4j workflow identified
- Neo4j target, credentials, permissions, backups, and native confirmation requirements understood
- Local agent host can install the `hol-guard` CLI

## Step 1 — Install and inspect HOL Guard

Probe the actual runtime CLI rather than relying on a platform-specific executable lookup:

```bash
hol-guard --version
```

If that command is unavailable and `pipx` is available:

```bash
pipx install hol-guard
```

Inspect local state:

```bash
hol-guard status
hol-guard detect --json
```

Use the exact supported harness identifier returned by `hol-guard detect --json`. Never maintain a separate harness list in this skill.

## Step 2 — Protect the detected harness

```bash
hol-guard bootstrap
hol-guard install <harness>
hol-guard run <harness> --dry-run
hol-guard run <harness>
hol-guard status
hol-guard doctor <harness> --json
```

Stop if detection, bootstrap, install, dry-run, run, status, or harness-specific doctor fails or cannot prove the expected protection state. Do not fall back to an unprotected agent session just to complete the mutation.

Do not claim protection until current Guard status and doctor output prove the detected harness is configured successfully.

## Step 3 — Handle Guard decisions

If Guard blocks, queues, or requires review:

```bash
hol-guard approvals
hol-guard receipts
hol-guard diff <harness>
```

Never auto-approve. Show the affected command/scope and let the user decide.

Guard deny, review-required, malformed, unavailable, timeout, or error states stop the protected mutation path. Do not retry the same mutation outside Guard.

## Step 4 — Execute the Neo4j workflow normally

Delegate product behavior to the existing Neo4j skill:

| Workflow | Delegate to |
|---|---|
| Cypher authoring/query behavior | `neo4j-cypher-skill` |
| `neo4j-cli`, `neo4j-admin`, `cypher-shell`, Aura CLI | `neo4j-cli-tools-skill` |
| Users, roles, privileges, auth | `neo4j-security-skill` |
| MCP install/configuration | `neo4j-mcp-skill` |
| Schema design | `neo4j-modeling-skill` |

Keep Neo4j-native controls authoritative:
- Keep least-privilege credentials and RBAC/ABAC rules
- Keep native `--rw`/confirmation gates and explicit destructive-operation confirmation
- Keep backups, transactions, migration review, tests, and post-operation verification
- Never put database credentials into prompts, Guard receipts, or logs

HOL Guard protects the supported local agent harness. It does not run inside Neo4j, replace server authorization, or validate arbitrary Cypher/API payloads as Neo4j-aware policy.

## Outputs
- Supported local agent harness protected by HOL Guard or workflow stopped with exact failure
- Neo4j mutation executed only through the existing product-specific safety flow
- Native Neo4j verification completed after any mutation

## Checklist
- [ ] `hol-guard detect --json` returned the harness used
- [ ] `hol-guard run <harness> --dry-run` inspected before activation
- [ ] `hol-guard status` confirms installed protection
- [ ] `hol-guard doctor <harness> --json` confirms the detected harness is healthy
- [ ] Guard deny/review/error state not bypassed
- [ ] Neo4j native authentication and authorization remain authoritative
- [ ] Destructive Neo4j operations received required explicit confirmation
- [ ] Credentials excluded from prompts, receipts, and logs
- [ ] Product-specific Neo4j verification completed
