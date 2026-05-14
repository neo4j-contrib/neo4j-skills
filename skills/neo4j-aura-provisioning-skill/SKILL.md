---
name: neo4j-aura-provisioning-skill
description: Provisions and manages Neo4j Aura instances via CLI (aura-cli v1.7+) or REST API.
  Use when creating, pausing, resuming, resizing, or deleting AuraDB Free/Professional/Business Critical/VDC
  instances; downloading credentials; scripting CI/CD pipelines; polling async status; or using the
  Terraform neo4j/neo4j-aura provider. Covers auth setup (client credentials OAuth2), credential
  lifecycle (download once — never recoverable), instance type selection, region codes, and Python
  provisioning scripts. Does NOT handle Cypher queries — use neo4j-cypher-skill.
  Does NOT cover Graph Data Science algorithms — use neo4j-gds-skill or neo4j-aura-graph-analytics-skill.
  Does NOT cover neo4j-admin/cypher-shell — use neo4j-cli-tools-skill.
version: 1.0.0
allowed-tools: Bash WebFetch
---

## When to Use
- Creating an Aura instance (CLI, REST API, Python, Terraform)
- Pausing, resuming, resizing, or deleting an instance
- Downloading initial credentials from creation response
- Polling instance status: `creating` → `running`
- Setting up CI/CD provisioning or teardown pipelines
- Choosing instance tier (Free vs Professional vs Business Critical vs VDC)

## When NOT to Use
- **Cypher queries against running DB** → `neo4j-cypher-skill`
- **GDS algorithms on Aura** → `neo4j-gds-skill` (Pro with plugin) or `neo4j-aura-graph-analytics-skill` (serverless)
- **neo4j-admin / cypher-shell** → `neo4j-cli-tools-skill`
- **Application driver setup** → use a language driver skill (python, javascript, java, go, dotnet)

---

## Instance Tier Decision Table

| Tier | API type code | Memory | GDS | Replicas | Use when |
|---|---|---|---|---|---|
| AuraDB Free | `free-db` | 1 GB | ❌ | ❌ | Dev/demo; ≤200k nodes/400k rels |
| AuraDB Professional | `professional-db` | 2–64 GB | plugin available | ❌ | Production workloads |
| AuraDB Business Critical | `business-critical` | 4–384 GB | plugin available | ✅ | HA, multi-AZ, SLA |
| AuraDB VDC | `enterprise-db` | custom | ✅ | ✅ | Dedicated infra, compliance |
| AuraDS Professional | `professional-ds` | 2–64 GB | ✅ built-in | ❌ | Data science / GDS |
| AuraDS Enterprise | `enterprise-ds` | custom | ✅ | ✅ | Enterprise GDS |

**AuraDB Free limits**: 200k nodes, 400k rels; auto-pauses after 72 h inactivity; deleted if paused >30 days; no resize.

---

## Auth Setup

### CLI (aura-cli v1.7+)

Install (binary, not pip):
```bash
# macOS
curl -L https://github.com/neo4j/aura-cli/releases/latest/download/aura-cli-darwin-amd64.tar.gz | tar xz
sudo mv aura-cli /usr/local/bin/
aura-cli -v          # verify
```

Add credentials (from console.neo4j.io → Account Settings → API Credentials):
```bash
aura-cli credential add \
  --name "my-creds" \
  --client-id "$AURA_CLIENT_ID" \
  --client-secret "$AURA_CLIENT_SECRET"
aura-cli credential use --name "my-creds"
```

Verify:
```bash
aura-cli instance list --output table
```

### REST API — Get Bearer Token

Token endpoint: `POST https://api.neo4j.io/oauth/token`
Token expires: **3600 s (1 h)**. On 403 → refresh token.

```bash
TOKEN=$(curl -s --request POST 'https://api.neo4j.io/oauth/token' \
  --user "${AURA_CLIENT_ID}:${AURA_CLIENT_SECRET}" \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=client_credentials' \
  | jq -r '.access_token')
echo "Token: ${TOKEN:0:20}..."
```

Use in all subsequent calls: `--header "Authorization: Bearer $TOKEN"`

---

## Step 1 — List Tenants (Projects)

CLI:
```bash
aura-cli tenants list --output table
# Copy TENANT_ID for create operations
```

REST:
```bash
curl -s https://api.neo4j.io/v1/tenants \
  -H "Authorization: Bearer $TOKEN" | jq '.data[] | {id, name}'
```

---

## Step 2 — Create Instance

CRITICAL: **Capture output immediately.** Initial password shown ONCE — never retrievable again.
If lost: delete and recreate. Store `aura-creds.json` before doing anything else.

### CLI

```bash
aura-cli instance create \
  --name "my-instance" \
  --cloud-provider gcp \
  --region europe-west1 \
  --type professional-db \
  --tenant-id "$TENANT_ID" \
  --output json | tee aura-creds.json

# Extract for .env
INSTANCE_ID=$(jq -r '.id' aura-creds.json)
PASSWORD=$(jq -r '.password' aura-creds.json)
```

### REST API (full create)

```bash
RESPONSE=$(curl -s -X POST https://api.neo4j.io/v1/instances \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":           "my-instance",
    "cloud_provider": "gcp",
    "region":         "europe-west1",
    "type":           "professional-db",
    "tenant_id":      "'"$TENANT_ID"'",
    "memory":         "4GB",
    "version":        "5"
  }')
echo "$RESPONSE" | tee aura-creds.json
INSTANCE_ID=$(echo "$RESPONSE" | jq -r '.data.id')
PASSWORD=$(echo "$RESPONSE"   | jq -r '.data.password')
```

Instance create request body fields:

| Field | Required | Values |
|---|---|---|
| `name` | ✅ | any string |
| `cloud_provider` | ✅ | `gcp` `aws` `azure` |
| `region` | ✅ | see region table |
| `type` | ✅ | see tier table |
| `tenant_id` | ✅ | from tenant list |
| `memory` | ✗ | `1GB` `2GB` `4GB` `8GB` … `384GB` |
| `version` | ✗ | `5` (default) |

---

## Step 3 — Poll Until RUNNING (CRITICAL — All Ops Are Async)

ALL lifecycle operations (create, pause, resume, resize) are async. Do NOT attempt connection or next operation until status = `running` (or `paused` for pause op).

```bash
poll_status() {
  local INSTANCE_ID=$1 TARGET=$2 MAX_WAIT=${3:-600}
  local ELAPSED=0 STATUS
  echo "Polling for status=$TARGET (max ${MAX_WAIT}s)..."
  while [ $ELAPSED -lt $MAX_WAIT ]; do
    STATUS=$(aura-cli instance get --instance-id "$INSTANCE_ID" --output json \
             | jq -r '.status' 2>/dev/null)
    echo "  [${ELAPSED}s] status=$STATUS"
    [ "$STATUS" = "$TARGET" ] && echo "Ready." && return 0
    [ "$STATUS" = "destroying" ] && echo "ERROR: instance is being destroyed" && return 1
    sleep 10; ELAPSED=$((ELAPSED + 10))
  done
  echo "TIMEOUT after ${MAX_WAIT}s — last status: $STATUS" && return 1
}

poll_status "$INSTANCE_ID" "running" 600
```

REST equivalent:
```bash
while true; do
  STATUS=$(curl -s "https://api.neo4j.io/v1/instances/$INSTANCE_ID" \
    -H "Authorization: Bearer $TOKEN" | jq -r '.data.status')
  [ "$STATUS" = "running" ] && break
  sleep 10
done
```

Status lifecycle:
```
creating → running → pausing → paused → resuming → running
                  ↘ destroying → (gone)
```

---

## Step 4 — Write .env and Verify

```bash
CONNECTION_URI="neo4j+s://${INSTANCE_ID}.databases.neo4j.io"

cat > .env <<EOF
NEO4J_URI=${CONNECTION_URI}
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=${PASSWORD}
NEO4J_DATABASE=neo4j
AURA_INSTANCE_ID=${INSTANCE_ID}
EOF

# Ensure .env never committed
grep -q '^\.env$' .gitignore 2>/dev/null || echo '.env' >> .gitignore

# Verify connectivity
cypher-shell -a "$CONNECTION_URI" -u neo4j -p "$PASSWORD" "RETURN 'connected' AS status"
```

---

## Step 5 — Lifecycle Operations

All operations require instance in the correct state. Wrong-state ops return 4xx error.

### Pause
Required state: `running`
```bash
aura-cli instance pause --instance-id "$INSTANCE_ID"
poll_status "$INSTANCE_ID" "paused" 600
```

### Resume
Required state: `paused`
```bash
aura-cli instance resume --instance-id "$INSTANCE_ID"
poll_status "$INSTANCE_ID" "running" 900   # resume can take longer
```

### Resize (Professional+ only — NOT Free)
Required state: `running`; instance remains available during resize.
```bash
# REST only — CLI resize not available in v1.7
curl -s -X PATCH "https://api.neo4j.io/v1/instances/$INSTANCE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"memory": "8GB"}'
poll_status "$INSTANCE_ID" "running" 600
# Cannot reduce below current usage level
```

### Delete
IRREVERSIBLE. Export snapshots first if data needed.
```bash
aura-cli instance delete --instance-id "$INSTANCE_ID"
# No poll needed — immediate
```

REST:
```bash
curl -s -X DELETE "https://api.neo4j.io/v1/instances/$INSTANCE_ID" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Python CI/CD Provisioning Script

```python
import os, time, requests

CLIENT_ID     = os.environ["AURA_CLIENT_ID"]
CLIENT_SECRET = os.environ["AURA_CLIENT_SECRET"]
BASE          = "https://api.neo4j.io/v1"

def get_token() -> str:
    r = requests.post(
        "https://api.neo4j.io/oauth/token",
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
    )
    r.raise_for_status()
    return r.json()["access_token"]

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def create_instance(token: str, tenant_id: str, **kwargs) -> dict:
    payload = {"tenant_id": tenant_id, "version": "5", **kwargs}
    r = requests.post(f"{BASE}/instances", headers=auth_headers(token), json=payload)
    r.raise_for_status()
    return r.json()["data"]   # contains id, password, connection_url

def poll_status(token: str, instance_id: str, target: str, timeout: int = 600) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{BASE}/instances/{instance_id}", headers=auth_headers(token))
        r.raise_for_status()
        status = r.json()["data"]["status"]
        print(f"  status={status}")
        if status == target:
            return
        if status == "destroying":
            raise RuntimeError("Instance destroyed unexpectedly")
        time.sleep(10)
    raise TimeoutError(f"Instance {instance_id} did not reach '{target}' in {timeout}s")

# --- usage ---
token    = get_token()
instance = create_instance(
    token,
    tenant_id = os.environ["AURA_TENANT_ID"],
    name           = "ci-test-instance",
    cloud_provider = "aws",
    region         = "us-east-1",
    type           = "professional-db",
    memory         = "2GB",
)
# SAVE CREDENTIALS IMMEDIATELY — password never retrievable again
print(f"ID:       {instance['id']}")
print(f"URI:      neo4j+s://{instance['id']}.databases.neo4j.io")
print(f"Password: {instance['password']}")   # log to secure vault NOW

poll_status(token, instance["id"], "running", timeout=600)
print("Instance ready.")
```

---

## Region Codes

### AWS
| Region code | Location |
|---|---|
| `us-east-1` | N. Virginia |
| `us-east-2` | Ohio |
| `us-west-2` | Oregon |
| `eu-west-1` | Ireland |
| `eu-west-3` | Paris |
| `eu-central-1` | Frankfurt |
| `ap-southeast-1` | Singapore |
| `ap-southeast-2` | Sydney |
| `ap-south-1` | Mumbai |
| `sa-east-1` | São Paulo |

### GCP
| Region code | Location |
|---|---|
| `europe-west1` | Belgium |
| `europe-west3` | Frankfurt |
| `europe-west4` | Netherlands |
| `us-central1` | Iowa |
| `us-east1` | S. Carolina |
| `us-east4` | N. Virginia |
| `asia-east1` | Taiwan |
| `asia-northeast1` | Tokyo |
| `asia-southeast1` | Singapore |
| `australia-southeast1` | Sydney |

### Azure
| Region code | Location |
|---|---|
| `eastus` | E. US |
| `eastus2` | E. US 2 |
| `westeurope` | Netherlands |
| `northeurope` | Ireland |
| `uksouth` | London |
| `southeastasia` | Singapore |
| `brazilsouth` | Brazil |
| `koreacentral` | Korea |

Enterprise tiers (Business Critical, VDC) add 20+ additional regions per provider. Check console for full list.
Free tier: GCP only; limited subset of regions.

---

## Terraform Provider

```hcl
terraform {
  required_providers {
    aura = {
      source  = "neo4j/neo4j-aura"
    }
  }
}

provider "aura" {
  client_id     = var.aura_client_id       # or AURA_CLIENT_ID env var
  client_secret = var.aura_client_secret   # or AURA_CLIENT_SECRET env var
}

resource "aura_instance" "db" {
  name           = "prod-db"
  type           = "professional-db"
  cloud_provider = "gcp"
  region         = "europe-west1"
  memory         = "4GB"
  tenant_id      = var.aura_tenant_id
}

output "neo4j_uri" {
  value     = "neo4j+s://${aura_instance.db.id}.databases.neo4j.io"
  sensitive = false
}
output "neo4j_password" {
  value     = aura_instance.db.password
  sensitive = true
}
```

After `terraform apply`: poll status before marking infra ready — Terraform resource creation returns when API call completes, not when DB is `running`.

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `403 Forbidden` after working | Token expired (1 h TTL) | Re-run `get_token()` |
| `409 Conflict` on create | Name already exists in tenant | Change name or delete existing |
| `422` on pause | Instance not `running` | Check status; wait for ongoing op to finish |
| `422` on resume | Instance not `paused` | Check status |
| `422` on resize | Below current usage | Reduce data first; can't shrink below usage |
| Region not found | Tier doesn't support that region | Use `Free` tier on GCP only; Pro/BC on all 3 clouds |
| Credentials lost after create | Password only returned at create time | Delete + recreate — no reset exists |
| `429 Too Many Requests` | Rate limit hit (25 req/min Free, 125 req/min Pro+) | Add `time.sleep(2)` between polling calls |
| `instance list` returns empty | Wrong credential active | `aura-cli credential use --name <name>` |

---

## API Rate Limits

| Tier | Requests/minute |
|---|---|
| Free / Pro Trial (no billing) | 25 |
| Pro with billing, BC, VDC | 125 |

Poll interval: ≥10 s to stay within limits on Free; 5 s safe on Pro+.
On `Retry-After` header in 5xx response: wait that many seconds before retry.

---

## Security Rules

- Write initial credentials to `.env`; verify `.env` in `.gitignore` before proceeding
- Never print `PASSWORD` in CI logs — write to secrets vault (AWS Secrets Manager, GitHub secret, Vault)
- Use `from_env()` / `os.environ` — never hardcode credentials
- If `.env` absent: `python-dotenv` `load_dotenv()` auto-loads; do NOT prompt user unless loading fails

---

## WebFetch — Current Docs

| Need | URL |
|---|---|
| REST API spec (OpenAPI) | `https://neo4j.com/docs/aura/platform/api/specification/` |
| CLI reference | `https://neo4j.com/docs/aura/aura-cli/` |
| Region list | `https://neo4j.com/docs/aura/managing-instances/regions/` |
| Auth details | `https://neo4j.com/docs/aura/api/authentication/` |
| Instance actions | `https://neo4j.com/docs/aura/managing-instances/instance-actions/` |

---

## Checklist
- [ ] `.env` created with URI/user/password; `.env` in `.gitignore`
- [ ] Initial credentials saved to secure storage immediately after create
- [ ] `poll_status` called after create — do NOT connect before status = `running`
- [ ] `poll_status` called after pause/resume
- [ ] Correct tier selected (Free for dev, Pro+ for production, BC for HA)
- [ ] Region confirmed available for chosen tier and cloud provider
- [ ] Tenant ID provided for all create/list operations (required in multi-tenant orgs)
- [ ] Token refreshed if > 1 h old (or 403 received)
- [ ] Delete confirmed by user — data loss is permanent, no recovery
