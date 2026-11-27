---
name: neo4j-aura-provisioning-skill
description: Provisions and manages Neo4j Aura instances via CLI (aura-cli v1.7+) or REST API.
  Use when creating, pausing, resuming, resizing, or deleting AuraDB Free/Professional/Business Critical/VDC
  instances; downloading credentials; scripting CI/CD pipelines; polling async status; or using the
  Terraform neo4j-labs/neo4jaura provider. Covers auth setup (client credentials OAuth2), credential
  lifecycle (download once — never recoverable), instance type selection, region codes, and Python
  provisioning scripts. Does NOT handle Cypher queries — use neo4j-cypher-skill.
  Does NOT cover Graph Data Science algorithms — use neo4j-gds-skill or neo4j-aura-graph-analytics-skill.
  Does NOT cover neo4j-admin/cypher-shell — use neo4j-cli-tools-skill.
version: 1.0.6
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
| AuraDB Professional | `professional-db` | 1–128 GB | plugin available | ❌ | Production workloads |
| AuraDB Business Critical | `business-critical` | 2 GB – 512 GB (AWS/Azure), 2 TB (GCP) | plugin available | ✅ | HA, multi-AZ, SLA |
| AuraDB VDC | `enterprise-db` | custom | ✅ | ✅ | Dedicated infra, compliance |
| AuraDS Professional | `professional-ds` | 2–64 GB | ✅ built-in | ❌ | Data science / GDS |
| AuraDS Enterprise | `enterprise-ds` | custom | ✅ | ✅ | Enterprise GDS |

Valid memory sizes per project: `GET /v1/tenants/{tenantId}` (CLI: `aura-cli tenant get <tenant-id>`).

**AuraDB Free limits**: 200k nodes, 400k rels; auto-pauses after 72 h inactivity; deleted if paused >30 days; no resize.

---

## Auth Setup

### CLI (aura-cli v1.7+)

Install (binary, not pip). Asset names carry version + OS + arch: `aura-cli_<ver>_Darwin_arm64.tar.gz`, `_Darwin_x86_64`, `_Linux_x86_64`, `_Linux_arm64`, `_Windows_x86_64.zip`. Pick from https://github.com/neo4j/aura-cli/releases:
```bash
# macOS / Linux — resolve latest version, pick OS/arch
VER=$(curl -s https://api.github.com/repos/neo4j/aura-cli/releases/latest | jq -r '.tag_name' | sed 's/^v//')
OS=$(uname -s); ARCH=$(uname -m); [ "$ARCH" = "aarch64" ] && ARCH=arm64
curl -fL "https://github.com/neo4j/aura-cli/releases/download/v${VER}/aura-cli_${VER}_${OS}_${ARCH}.tar.gz" | tar xz
sudo mv aura-cli /usr/local/bin/
aura-cli -v          # verify
```

Add credentials (from console.neo4j.io → Account Settings → API Credentials):
```bash
aura-cli credential add \
  --name "my-creds" \
  --client-id "$AURA_CLIENT_ID" \
  --client-secret "$AURA_CLIENT_SECRET"
aura-cli credential use my-creds      # name is positional
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
aura-cli tenant list --output table
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
  --memory 4GB \
  --tenant-id "$TENANT_ID" \
  --output json | tee aura-creds.json

# Extract for .env — response is wrapped in "data"
INSTANCE_ID=$(jq -r '.data.id' aura-creds.json)
PASSWORD=$(jq -r '.data.password' aura-creds.json)
[ -z "$INSTANCE_ID" ] || [ "$INSTANCE_ID" = "null" ] || [ -z "$PASSWORD" ] || [ "$PASSWORD" = "null" ] \
  && echo "STOP: id/password missing — inspect aura-creds.json; do NOT write .env"
```

`--memory` required for all types except `free-db` (CLI defaults `version` to `5`).

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
| `name` | ✅ | 1–30 chars, no leading/trailing whitespace |
| `cloud_provider` | ✅ | `gcp` `aws` `azure` |
| `region` | ✅ | see region table |
| `type` | ✅ | see tier table |
| `tenant_id` | ✅ | from tenant list |
| `memory` | ✅ | e.g. `1GB` `2GB` `4GB` `8GB` …; valid sizes per project from `GET /v1/tenants/{tenantId}` |
| `version` | ✅ | `5` (provisions latest calendar version) |

---

## Step 3 — Poll Until RUNNING (CRITICAL — All Ops Are Async)

ALL lifecycle operations (create, pause, resume, resize, delete) are async. Do NOT attempt connection or next operation until status = `running` (or `paused` for pause op).

```bash
poll_status() {
  local INSTANCE_ID=$1 TARGET=$2 MAX_WAIT=${3:-600}
  local ELAPSED=0 STATUS
  echo "Polling for status=$TARGET (max ${MAX_WAIT}s)..."
  while [ $ELAPSED -lt $MAX_WAIT ]; do
    STATUS=$(aura-cli instance get "$INSTANCE_ID" --output json \
             | jq -r '.data.status')
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
aura-cli instance pause "$INSTANCE_ID"
poll_status "$INSTANCE_ID" "paused" 600
```

### Resume
Required state: `paused`
```bash
aura-cli instance resume "$INSTANCE_ID"
poll_status "$INSTANCE_ID" "running" 900   # resume can take longer
```

### Resize (Professional+ only — NOT Free)
Required state: `running`; instance remains available during resize.
```bash
aura-cli instance update "$INSTANCE_ID" --memory "8GB"
# or REST:
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
aura-cli instance delete "$INSTANCE_ID"
# Async — API returns 202; deletion completes in the background
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
| `europe-west4` | Netherlands (VDC only) |
| `us-central1` | Iowa |
| `us-east1` | S. Carolina |
| `us-east4` | N. Virginia (VDC only) |
| `asia-east1` | Taiwan |
| `asia-northeast1` | Tokyo (VDC only) |
| `asia-southeast1` | Singapore |
| `australia-southeast1` | Sydney |

### Azure
| Region code | Location |
|---|---|
| `eastus` | E. US |
| `eastus2` | E. US 2 (VDC only) |
| `westeurope` | Netherlands |
| `northeurope` | Ireland (VDC only) |
| `uksouth` | London |
| `southeastasia` | Singapore (VDC only) |
| `brazilsouth` | Brazil |
| `koreacentral` | Korea |

Professional and Business Critical share the same region list (12 AWS, 8 Azure, 12 GCP); only VDC and AuraDS Enterprise have the longer lists. "VDC only" rows are not available on Professional/BC. Full per-tier lists: https://neo4j.com/docs/aura/managing-instances/regions/
Free tier: GCP only; limited subset of regions.

---

## Terraform Provider

```hcl
terraform {
  required_providers {
    neo4jaura = {
      source  = "neo4j-labs/neo4jaura"
    }
  }
}

provider "neo4jaura" {
  client_id     = var.aura_client_id       # or AURA_CLIENT_ID env var
  client_secret = var.aura_client_secret   # or AURA_CLIENT_SECRET env var
}

resource "neo4jaura_instance" "db" {
  name           = "prod-db"
  type           = "professional-db"
  cloud_provider = "gcp"
  region         = "europe-west1"
  memory         = "4GB"
  project_id     = var.aura_project_id   # Terraform uses project_id (REST API: tenant_id)
}

output "neo4j_uri" {
  value     = neo4jaura_instance.db.connection_url
  sensitive = false
}
output "neo4j_password" {
  value     = neo4jaura_instance.db.password
  sensitive = true
}
```

After `terraform apply`: poll status before marking infra ready — Terraform resource creation returns when API call completes, not when DB is `running`.

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `403 Forbidden` after working | Token expired (1 h TTL) | Re-run `get_token()` |
| `400` on create | Invalid body (missing required field, bad name/memory/region) | Fix body; required: name, type, tenant_id, cloud_provider, region, memory, version |
| `405` on create | Instance limit reached | Delete/pause unused instances or raise limit |
| `409 Conflict` on pause/resume/resize/delete | Another operation in progress on the instance | Poll status; retry when op finishes |
| Region not found | Tier doesn't support that region | Use `Free` tier on GCP only; Pro/BC on all 3 clouds |
| Credentials lost after create | Password only returned at create time | Delete + recreate — no reset exists |
| `429 Too Many Requests` | Rate limit hit (25 req/min Free, 125 req/min Pro+) | Add `time.sleep(2)` between polling calls |
| `instance list` returns empty | Wrong credential active | `aura-cli credential use <name>` |

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
