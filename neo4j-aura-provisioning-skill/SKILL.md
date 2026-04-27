---
name: neo4j-aura-provisioning-skill
description: >
  Use when programmatically creating, pausing, resuming, resizing, or deleting Neo4j
  Aura instances: Aura CLI (aura-cli), Aura REST API, or scripted provisioning in
  CI/CD pipelines. Also covers downloading credentials, listing tenants, and managing
  instance lifecycles. Does NOT cover Cypher queries or application code — use
  neo4j-cypher-skill or driver skills. Does NOT cover general CLI tools
  (neo4j-admin, cypher-shell) — use neo4j-cli-tools-skill.
status: draft
version: 0.1.0
allowed-tools: Bash, WebFetch
---

# Neo4j Aura Provisioning Skill

> **Status: Draft / WIP** — Content is a placeholder. Reference files and Aura API details to be added.
> Fetch current API reference: https://neo4j.com/docs/aura/platform/api/specification/

## When to Use

- Creating a Neo4j Aura instance programmatically (CLI, API, Python script)
- Managing instance lifecycle: pause, resume, resize, delete
- Downloading credentials and `.env` files from the Aura Console or API
- Listing tenants and instances in a CI/CD pipeline
- Provisioning Aura for automated testing environments

## When NOT to Use

- **Cypher queries against a running database** → use `neo4j-cypher-skill`
- **Application driver setup** → use a driver skill (python, javascript, java, etc.)
- **neo4j-admin / cypher-shell / CLI tools** → use `neo4j-cli-tools-skill`

---

## Setup

```bash
pip install aura-cli       # Python CLI
aura-cli auth login        # opens browser for OAuth; saves token to ~/.aura/credentials
```

Or use environment variables for headless/CI:
```bash
export AURA_CLIENT_ID=<client-id>
export AURA_CLIENT_SECRET=<client-secret>
```

---

## Core CLI Commands (Step-by-Step)

**Step 1 — List tenants:**
```bash
aura-cli tenants list
```

**Step 2 — Create instance (capture output immediately):**
```bash
# Add --format json to capture credentials programmatically
aura-cli instances create \
  --name "my-instance" \
  --region us-east-1 \
  --cloud-provider aws \
  --type free-db \
  --tenant-id <tenant-id> \
  --format json | tee aura-creds.json
# Initial password is shown ONCE here. Save aura-creds.json immediately.
# If lost: you must delete and recreate the instance — there is no password reset.
```

**Step 3 — Wait for RUNNING status (with timeout):**
```bash
for i in $(seq 1 60); do
  STATUS=$(aura-cli instances get --instance-id <id> --format json | jq -r '.status')
  echo "Attempt $i: $STATUS"
  [ "$STATUS" = "running" ] && break
  [ $i -eq 60 ] && echo "TIMEOUT: instance did not start after 10 min" && exit 1
  sleep 10
done
```

**Step 4 — Write .env:**
```bash
cat <<EOF > .env
NEO4J_URI=neo4j+s://<instance-id>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password>
NEO4J_DATABASE=neo4j
EOF
grep -q '.env' .gitignore || echo '.env' >> .gitignore
```

**Step 5 — Verify connectivity:**
```bash
source .env
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
  "RETURN 'connected' AS status"
```

---

## Aura Free Limitations

If provisioning a `free-db` instance, be aware:
- Max 200,000 nodes and 400,000 relationships
- No GDS (Graph Data Science) — suggest `neo4j-gds-skill` only for Pro/Enterprise
- No read replicas or clustering
- Instance pauses after 3 days of inactivity (auto-resumes on connection)

---

## Checklist

- [ ] `.env` created with credentials and added to `.gitignore`
- [ ] Instance status is `running` before attempting connection
- [ ] Credentials printed/displayed only once at creation — save them immediately
- [ ] `aura-cli auth login` or `AURA_CLIENT_ID`/`AURA_CLIENT_SECRET` env vars configured
- [ ] Tenant ID specified for all operations (required in multi-tenant accounts)

---

## Fetching Current Docs

```
https://neo4j.com/docs/llms.txt     ← full documentation index (includes Aura API spec)
https://neo4j.com/docs/aura/platform/api/specification/  ← live Aura REST API spec
```

## References

- [Aura Docs](https://neo4j.com/docs/aura/)
- [Aura CLI Docs](https://neo4j.com/docs/aura/aura-cli/)
- [Aura REST API Specification](https://neo4j.com/docs/aura/platform/api/specification/)
- [Aura CLI GitHub](https://github.com/neo4j/aura-cli)
- [GraphAcademy: AuraDB Fundamentals](https://graphacademy.neo4j.com/courses/aura-fundamentals/)
