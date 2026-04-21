# Stage 2 — provision
# Provision a running Neo4j database and save credentials to .env.

## Local DB path — handle DB_TARGET first

Check `progress.md` for `DB_TARGET` **before** doing anything Aura-related:

- `aura-free` or `aura-pro` → proceed to Aura REST API section below
- `local-docker` → start Neo4j container and write `.env` (see below) → skip Aura section
- `local-desktop` → ask user to start Neo4j Desktop → write `.env` → skip Aura section
- `existing` → user provided credentials → write `.env` → skip everything

### DB_TARGET=local-docker — Docker provisioning flow

**In HITL mode**: ask the user for a password (or suggest `password123` as default).
**In autonomous mode**: use `password123` as the default password.

```bash
# 1. Check Docker is available
docker --version 2>/dev/null || { echo "Docker not found — please install Docker Desktop"; exit 1; }

# 2. Start Neo4j — with persistent data volume so data survives container restarts
#    Remove any leftover container with the same name first
PASS="password123"   # change this if the user provided a different password
docker rm -f neo4j-dev 2>/dev/null || true
docker run -d \
  --name neo4j-dev \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH="neo4j/${PASS}" \
  -e NEO4J_ACCEPT_LICENSE_AGREEMENT=yes \
  -v "$(pwd)/neo4j-data:/data" \
  neo4j:enterprise
echo "✓ Container started (data persisted to $HOME/neo4j-dev/data) — waiting for Bolt..."
```

> **Why `-v $(pwd)/neo4j-data:/data`?** Without a volume, all data is lost when the
> container is removed. With it, `docker rm neo4j-dev && docker run ...` keeps your graph.

```python
# 3. Wait for Neo4j to accept connections (save as /tmp/wait_neo4j.py — temp file, not in project)
from neo4j import GraphDatabase
import time, sys

for attempt in range(18):  # up to 90s
    try:
        d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password123"))
        d.verify_connectivity()
        d.close()
        print(f"✓ Neo4j ready after {attempt * 5}s")
        sys.exit(0)
    except Exception as e:
        print(f"  [{attempt+1}/18] not ready yet ({type(e).__name__}), retrying in 5s...")
        time.sleep(5)
print("Neo4j did not start in time"); sys.exit(1)
```

```bash
.venv/bin/python3 /tmp/wait_neo4j.py
```

```bash
# 4. Write .env
cat > .env << 'EOF'
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password123
NEO4J_DATABASE=neo4j
EOF
echo "✓ .env written"
```

On Completion for local-docker — write to progress.md:
```markdown
### 2-provision
status: done
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_DATABASE=neo4j
CONTAINER_NAME=neo4j-dev
```

### DB_TARGET=local-desktop — Neo4j Desktop flow

Tell the user:
> "Please open Neo4j Desktop and start your local database. Once it's running, share the
> password you set and confirm it's on the default port (bolt://localhost:7687)."

Once confirmed, write `.env`:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password user provided>
NEO4J_DATABASE=neo4j
```

On Completion for local-desktop — write to progress.md:
```markdown
### 2-provision
status: done
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_DATABASE=neo4j
```

---

## Aura REST API

Use these three endpoints directly — no extra tooling needed. For all other operations
(list, delete, pause, resume, update), fetch the live OpenAPI spec at runtime:
`GET https://api.neo4j.io/openapi.json` or browse `https://neo4j.com/docs/aura/platform/api/specification/`

### Step P-1 — Collect Aura API credentials

`aura.env` holds account-level API credentials (reusable across instances).
`.env` holds per-instance DB connection details (written later in P3).
They must be kept separate so writing `.env` never overwrites the API key.

Check in order:
1. `aura.env` exists → load it with Python (see Step P0) → proceed
2. Environment variables `CLIENT_ID` / `CLIENT_SECRET` (or `AURA_CLIENT_ID` / `AURA_CLIENT_SECRET`) already set → proceed
3. Neither found → **ask the user**:

> "To provision an Aura database I need your Aura API credentials.
> Please go to https://console.neo4j.io → Account Settings → API credentials,
> create a new client, and paste the **Client ID** and **Client Secret** here."

Once received, save to `aura.env` (never `.env`):
```bash
cat > aura.env << EOF
CLIENT_ID=<value>
CLIENT_SECRET=<value>
# Strongly recommended for users with multiple organisations or projects —
# without these the API picks the first org/project alphabetically which may be wrong.
# Find them at console.neo4j.io → your project → Settings.
# PROJECT_ID=<project/tenant id>
# ORGANIZATION_ID=<organisation id>
EOF
# aura.env is already in .gitignore from the prerequisites stage
```

The console generates keys named `CLIENT_ID` / `CLIENT_SECRET`. Both that form and `AURA_CLIENT_ID` / `AURA_CLIENT_SECRET` are accepted.

### Steps P0–P3 — Provision via Python script

**Run the entire provision flow as a single Python script.** Environment variables set in
one Bash tool call are lost in the next call, so do not split this across multiple commands.

```python
#!/usr/bin/env python3
"""
provision_aura.py — run this script to provision an Aura instance.
Reads aura.env, creates the instance, polls until running, writes .env.
Idempotent: exits immediately if already provisioned or in progress.
"""
import atexit, fcntl, json, os, pathlib, sys, time, urllib.request, urllib.error

# ── Idempotency guards — acquired before any network call ────────────────────
_env_path  = pathlib.Path(".env")
_lock_path = pathlib.Path(".provision.lock")

# Guard 1: already done
if _env_path.exists() and "NEO4J_URI=neo4j" in _env_path.read_text():
    print("✓ .env already exists with valid URI — skipping (DB already running)")
    sys.exit(0)

# Guard 2: atomic exclusive file lock — immune to TOCTOU races
_lock_fh = _lock_path.open("a")   # "a" so it always exists
try:
    fcntl.flock(_lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print("✓ Provisioning already in progress (lock held) — skipping")
    sys.exit(0)

_lock_fh.write(f"{os.getpid()}\n"); _lock_fh.flush()
atexit.register(lambda: (_lock_path.unlink(missing_ok=True)))
print(f"  Lock acquired (PID {os.getpid()})")

from dotenv import dotenv_values

# ── Load aura.env ────────────────────────────────────────────────────────────
env = dotenv_values("aura.env")

CLIENT_ID     = env.get("CLIENT_ID") or env.get("AURA_CLIENT_ID")
CLIENT_SECRET = env.get("CLIENT_SECRET") or env.get("AURA_CLIENT_SECRET")
PROJECT_ID    = env.get("PROJECT_ID")      # optional — skip discovery if set
ORG_ID        = env.get("ORGANIZATION_ID") # optional — skip discovery if set

assert CLIENT_ID and CLIENT_SECRET, "CLIENT_ID / CLIENT_SECRET missing from aura.env"

def api(method, path, token=None, body=None, base="https://api.neo4j.io"):
    url = base + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} → {e.code}: {e.read().decode()}") from e

# ── Token ────────────────────────────────────────────────────────────────────
# Endpoint: /oauth/token  •  JSON body  •  NOT /oauth2/token  •  NOT form-encoded
token = api("POST", "/oauth/token", body={
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
})["access_token"]
print(f"✓ Token obtained ({token[:16]}...)")

# ── Resolve org + project (v2beta1 for correct scoping) ──────────────────────
if not ORG_ID:
    orgs = api("GET", "/v2beta1/organizations", token)["data"]
    ORG_ID = orgs[0]["id"]
    print(f"  Discovered ORGANIZATION_ID={ORG_ID}  ({orgs[0]['name']})")
else:
    print(f"  Using ORGANIZATION_ID={ORG_ID} from aura.env")

if not PROJECT_ID:
    projects = api("GET", f"/v2beta1/organizations/{ORG_ID}/projects", token)["data"]
    PROJECT_ID = projects[0]["id"]
    print(f"  Discovered PROJECT_ID={PROJECT_ID}  ({projects[0]['name']})")
else:
    print(f"  Using PROJECT_ID={PROJECT_ID} from aura.env")

# ── Read context from progress.md ─────────────────────────────────────────────
import re as _re
_progress = pathlib.Path("progress.md").read_text() if pathlib.Path("progress.md").exists() else ""

# DB_TARGET mapping:  aura-free → free-db   aura-pro → professional-db
# NOTE: free-db is GCP-only (3 regions: europe-west1, us-central1, asia-southeast1).
#       professional-db supports GCP (12), AWS (10), Azure (8).
_db_target_m = _re.search(r"^DB_TARGET=(\S+)", _progress, _re.MULTILINE)
DB_TYPE = "professional-db" if _db_target_m and "pro" in _db_target_m.group(1) else "free-db"
print(f"  DB_TYPE={DB_TYPE}  (from DB_TARGET in progress.md)")

tenant_data = api("GET", f"/v1beta5/tenants/{PROJECT_ID}", token)
# Each config: {"type", "cloud_provider", "region", "region_name", "memory", "storage"}
# region_name is human-readable, e.g. "Belgium (europe-west1)", "US East, N. Virginia (us-east-1)"
# The same (cloud_provider, region) pair appears multiple times — once per memory size.
# Deduplicate immediately using a dict keyed by (cloud_provider, region); first entry wins.
unique_configs = list({
    (c["cloud_provider"], c["region"]): c
    for c in tenant_data["data"].get("instance_configurations", [])
    if c["type"] == DB_TYPE
}.values())
print(f"  Available {DB_TYPE} regions ({len(unique_configs)}): "
      f"{[(c['cloud_provider'], c['region_name']) for c in unique_configs]}")

# ── Pick best region ───────────────────────────────────────────────────────────
# CLOUD_PROVIDER = user's explicit preference (from context stage, aura-pro only)
# REGION_HINT    = geographic area inferred from signals (never asked)
# (_re and _progress already defined above)
_cp = _re.search(r"^CLOUD_PROVIDER=(\S+)", _progress, _re.MULTILINE)
_rh = _re.search(r"^REGION_HINT=(\S+)",   _progress, _re.MULTILINE)
PREF_PROVIDER = _cp.group(1).lower() if _cp else None   # e.g. "aws"
REGION_HINT   = _rh.group(1).lower() if _rh else None   # e.g. "europe-west"

# REGION_HINT → actual Aura region identifiers (from real tenant API data)
REGION_KEYWORDS = {
    "europe-west":  ["europe-west1", "europe-west2", "eu-west-1", "eu-west-3",
                     "francecentral", "uksouth", "westeurope"],
    "europe-east":  ["europe-west3", "eu-central-1"],
    "us-east":      ["us-east-1", "us-east1", "us-east-2", "eastus"],
    "us-west":      ["us-west-2", "us-west1", "westus3"],
    "us-central":   ["us-central1"],
    "sa-east":      ["sa-east-1", "brazilsouth"],
    "ap-southeast": ["ap-southeast-1", "ap-southeast-2", "asia-southeast1",
                     "australia-southeast1"],
    "ap-northeast": ["asia-east1", "asia-east2", "koreacentral"],
    "ap-south":     ["ap-south-1", "asia-south1", "centralindia"],
}
keywords = REGION_KEYWORDS.get(REGION_HINT, []) if REGION_HINT else []

# Cheapest/lowest-latency anchor per provider (used when no hint matches)
PROVIDER_DEFAULTS = {
    "gcp":   "europe-west1",  # Belgium — original GCP region, consistently cheapest
    "aws":   "us-east-1",     # N. Virginia — cheapest AWS, most services available
    "azure": "eastus",        # Virginia — cheapest Azure
}

CLOUD_PROVIDER, REGION, REGION_NAME = None, None, ""

def _pick(pool, provider=None, kw_list=None):
    candidates = [c for c in pool if not provider or c["cloud_provider"] == provider]
    if kw_list:
        for kw in kw_list:
            for c in candidates:
                if kw in c["region"]:
                    return c
        return None
    return candidates[0] if candidates else None

# [1] User's preferred provider + closest region to geo hint
if PREF_PROVIDER and keywords:
    c = _pick(unique_configs, PREF_PROVIDER, keywords)
    if c:
        CLOUD_PROVIDER, REGION, REGION_NAME = c["cloud_provider"], c["region"], c.get("region_name","")
        print(f"  [1] provider pref + geo: {CLOUD_PROVIDER}/{REGION} ({REGION_NAME})")

# [2] User's preferred provider + cheapest default region for that provider
if not CLOUD_PROVIDER and PREF_PROVIDER:
    c = _pick(unique_configs, PREF_PROVIDER, [PROVIDER_DEFAULTS.get(PREF_PROVIDER, "")])
    if not c:
        c = _pick(unique_configs, PREF_PROVIDER)   # any region in that provider
    if c:
        CLOUD_PROVIDER, REGION, REGION_NAME = c["cloud_provider"], c["region"], c.get("region_name","")
        print(f"  [2] provider pref, default region: {CLOUD_PROVIDER}/{REGION} ({REGION_NAME})")

# [3] No provider preference — geo hint across all providers
if not CLOUD_PROVIDER and keywords:
    c = _pick(unique_configs, kw_list=keywords)
    if c:
        CLOUD_PROVIDER, REGION, REGION_NAME = c["cloud_provider"], c["region"], c.get("region_name","")
        print(f"  [3] geo hint (any provider): {CLOUD_PROVIDER}/{REGION} ({REGION_NAME})")

# [4] No hint at all — cheapest defaults (GCP europe-west1, then AWS us-east-1, then Azure eastus)
if not CLOUD_PROVIDER:
    for provider, default_region in PROVIDER_DEFAULTS.items():
        c = _pick(unique_configs, provider, [default_region])
        if c:
            CLOUD_PROVIDER, REGION, REGION_NAME = c["cloud_provider"], c["region"], c.get("region_name","")
            print(f"  [4] cheapest default: {CLOUD_PROVIDER}/{REGION} ({REGION_NAME})")
            break

# [5] Absolute fallback
if not CLOUD_PROVIDER:
    if unique_configs:
        c = unique_configs[0]
        CLOUD_PROVIDER, REGION, REGION_NAME = c["cloud_provider"], c["region"], c.get("region_name","")
        print(f"  [5] first available: {CLOUD_PROVIDER}/{REGION}")
    else:
        CLOUD_PROVIDER, REGION = "gcp", "europe-west1"
        print(f"  [5] hardcoded fallback (no tenant configs): {CLOUD_PROVIDER}/{REGION}")

# ── Create instance ────────────────────────────────────────────────────────────
try:
    result = api("POST", "/v1beta5/instances", token, body={
        "name": "myapp-db",
        "tenant_id": PROJECT_ID,
        "cloud_provider": CLOUD_PROVIDER,
        "region": REGION,
        "type": DB_TYPE,
        "memory": "1GB",
    })["data"]
    INSTANCE_ID = result["id"]
    PASSWORD     = result["password"]   # shown only once — captured here
    print(f"✓ Instance created: {INSTANCE_ID} ({CLOUD_PROVIDER}/{REGION})")
except RuntimeError as e:
    if "quota" not in str(e).lower() and "limit" not in str(e).lower():
        raise
    # Free quota exceeded — fall back to a Pro trial instance (also free for new accounts)
    print(f"  Free quota exceeded. Falling back to professional-db trial instance...")
    pro_configs = [c for c in available if c["type"] == "professional-db"]
    if pro_configs:
        CLOUD_PROVIDER = pro_configs[0]["cloud_provider"]
        REGION         = pro_configs[0]["region"]
    result = api("POST", "/v1beta5/instances", token, body={
        "name": "myapp-db",
        "tenant_id": PROJECT_ID,
        "cloud_provider": CLOUD_PROVIDER,
        "region": REGION,
        "type": "professional-db",
        "memory": "1GB",
    })["data"]
    INSTANCE_ID = result["id"]
    PASSWORD     = result["password"]
    print(f"✓ Pro trial instance created: {INSTANCE_ID}")

# ── Poll until running ────────────────────────────────────────────────────────
CONNECTION = ""
for i in range(1, 25):
    status_data = api("GET", f"/v1beta5/instances/{INSTANCE_ID}", token)["data"]
    status = status_data.get("status", "")
    CONNECTION = status_data.get("connection_url", "")
    print(f"  [{i}/24] {status}")
    if status == "running":
        break
    time.sleep(15)
else:
    raise RuntimeError("Instance did not reach 'running' after 6 minutes")

# ── Wait for Bolt to accept connections ──────────────────────────────────────
# Aura reports "running" before the Bolt port is actually ready.
# Verify connectivity with retries before writing .env.
try:
    from neo4j import GraphDatabase as _GDB
    _connected = False
    for _attempt in range(12):   # up to 2 min
        try:
            _d = _GDB.driver(CONNECTION, auth=("neo4j", PASSWORD))
            _d.verify_connectivity()
            _d.close()
            _connected = True
            print(f"  Bolt ready after {(_attempt) * 10}s")
            break
        except Exception as _e:
            print(f"  [{_attempt+1}/12] Bolt not ready yet ({type(_e).__name__}), waiting 10s...")
            time.sleep(10)
    if not _connected:
        raise RuntimeError("Bolt port never became ready after 2 minutes")
except ImportError:
    # neo4j driver not installed yet — skip connectivity check, add a 30s safety buffer
    print("  neo4j driver not available for connectivity check — sleeping 30s as safety buffer")
    time.sleep(30)

# ── Write .env ────────────────────────────────────────────────────────────────
pathlib.Path(".env").write_text(
    f"NEO4J_URI={CONNECTION}\n"
    f"NEO4J_USERNAME=neo4j\n"
    f"NEO4J_PASSWORD={PASSWORD}\n"
    f"NEO4J_DATABASE=neo4j\n"
)
print(f"✓ .env written  URI={CONNECTION}")
print(f"✓ DONE — instance {INSTANCE_ID} is running")
```

Write this to `scripts/provision_aura.py`. Do **not** run it directly here — use the recommended flow below with background launch + log file.

---

## Aura CLI Quick Reference

### Installation
```bash
# macOS
brew install neo4j/tap/aura-cli   # if homebrew tap exists
# or: download binary from https://github.com/neo4j/aura-cli/releases/latest
sudo mv aura-cli /usr/local/bin/ && chmod +x /usr/local/bin/aura-cli

# Verify
aura-cli --version
```

### Credential setup
```bash
# Generate Client ID + Secret at https://console.neo4j.io → Account Settings → API credentials
aura-cli credential add \
  --name "default" \
  --client-id $AURA_CLIENT_ID \
  --client-secret $AURA_CLIENT_SECRET
```

### Instance lifecycle
```bash
# Create Free instance (512MB, GCP)
aura-cli instance create \
  --name "myapp-db" \
  --cloud-provider gcp \
  --region europe-west1 \
  --type free-db \
  --output json

# Create Pro instance (1GB, AWS)
aura-cli instance create \
  --name "myapp-prod" \
  --cloud-provider aws \
  --region us-east-1 \
  --type professional-db \
  --memory 1 \
  --output json

# List instances
aura-cli instance list --output json

# Get single instance status (check for "running")
aura-cli instance get <INSTANCE_ID> --output json

# Pause / resume (cost saving)
aura-cli instance pause <INSTANCE_ID>
aura-cli instance resume <INSTANCE_ID>

# Delete
aura-cli instance delete <INSTANCE_ID>
```

### Regions by cloud provider
| Provider | Available Regions |
|----------|------------------|
| GCP | us-central1, us-east1, europe-west1, europe-west3, asia-east1, asia-southeast1 |
| AWS | us-east-1, us-west-2, eu-west-1, eu-central-1, ap-southeast-1 |
| Azure | eastus, westeurope, southeastasia |

### Poll for running status (bash)
```bash
INSTANCE_ID="<id>"
for i in $(seq 1 24); do
  STATUS=$(aura-cli instance get $INSTANCE_ID --output json | \
           python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))")
  echo "[$i/24] Status: $STATUS"
  [ "$STATUS" = "running" ] && { echo "Instance ready"; break; }
  sleep 15
done
```

---

## Docker Quick Reference

```bash
# Basic (ephemeral — data lost on container remove)
docker run -d \
  --name neo4j-dev \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  -e NEO4J_ACCEPT_LICENSE_AGREEMENT=yes \
  neo4j:enterprise

# Recommended — persistent data volume
docker run -d \
  --name neo4j-dev \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  -e NEO4J_ACCEPT_LICENSE_AGREEMENT=yes \
  -v $(pwd)/neo4j-data:/data \
  neo4j:enterprise

# With plugins (APOC + GDS)
docker run -d \
  --name neo4j-dev \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  -e NEO4J_ACCEPT_LICENSE_AGREEMENT=yes \
  -e NEO4J_PLUGINS='["apoc","graph-data-science"]' \
  neo4j:enterprise

# Persistent data volume
docker run -d \
  --name neo4j-dev \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  -e NEO4J_ACCEPT_LICENSE_AGREEMENT=yes \
  -v $HOME/neo4j/data:/data \
  neo4j:enterprise

# Check logs
docker logs neo4j-dev -f

# Stop / remove
docker stop neo4j-dev && docker rm neo4j-dev
```

---

## Connectivity Verification

### cypher-shell
```bash
cypher-shell -a "neo4j+s://xxxxx.databases.neo4j.io" \
             -u neo4j -p "<password>" \
             "RETURN 'connected' AS status"
```

### Python
```python
from neo4j import GraphDatabase
driver = GraphDatabase.driver(
    "neo4j+s://xxxxx.databases.neo4j.io",
    auth=("neo4j", "<password>")
)
driver.verify_connectivity()
print("Connected")
driver.close()
```

### Node.js
```javascript
const neo4j = require('neo4j-driver');
const driver = neo4j.driver(
  'neo4j+s://xxxxx.databases.neo4j.io',
  neo4j.auth.basic('neo4j', '<password>')
);
await driver.verifyConnectivity();
console.log('Connected');
await driver.close();
```

---

## Neo4j Query API (HTTP — no driver required)

Useful for connectivity checks and scripting when no driver is installed:

```bash
# Aura: host is the bolt URI without the scheme
HOST="xxxxx.databases.neo4j.io"
curl -s -X POST "https://${HOST}/db/neo4j/query/v2" \
  -H "Content-Type: application/json" \
  -u "neo4j:<password>" \
  -d '{"statement": "MATCH (n) RETURN count(n) AS total"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d)"

# Local Docker
curl -s -X POST "http://localhost:7474/db/neo4j/query/v2" \
  -H "Content-Type: application/json" \
  -u "neo4j:password123" \
  -d '{"statement": "RETURN 1"}'
```

---

## URI Schemes

| Scheme | Use case |
|--------|----------|
| `neo4j+s://` | Aura (TLS required) |
| `bolt+s://` | Self-hosted with TLS |
| `bolt://` | Local development (no TLS) |
| `neo4j://` | Cluster routing, no TLS |

---

## Parallelise with offline work (saves 2–3 min)

Aura provisioning typically takes 2–4 minutes. Everything that doesn't touch the
database can be done during that wait. Only execution needs the DB to be ready.

**What can be done before the DB is running (no connection needed):**
- Stage 3: design the model, write `schema/schema.json` + `schema/schema.cypher`
- Stage 4: write `data/generate.py`, run it (pure Python → CSVs), write `data/import.py`
- Stage 6: write `queries/queries.cypher` (text only — validation runs later)

**What must wait for the DB:**
- Apply `schema/schema.cypher` (constraints + indexes)
- Run `data/import.py` (loads CSVs into Neo4j)
- Run `validate_queries.py` (executes queries against live DB)
- Stage 5: generate browser URL (needs `NEO4J_URI` from `.env`)

**Recommended flow after writing provision_aura.py:**

```bash
# Step 1 — launch provision in background with unbuffered output (never run twice, never kill)
mkdir -p scripts
PYTHONUNBUFFERED=1 python3 scripts/provision_aura.py > scripts/provision.log 2>&1 &
echo "Provision PID=$!"
sleep 3 && head -10 scripts/provision.log   # confirm it started

# Step 2 — do all offline work while DB spins up (no DB needed):
#   - read 3-model.md → design model → write schema/schema.json + schema/schema.cypher
#   - read 4-load.md  → write data/import.py
#   - read 6-query.md → write queries/queries.cypher

# Step 3 — wait for .env to appear (provision script writes it when DB is running)
until grep -q "NEO4J_URI=neo4j" .env 2>/dev/null; do sleep 10; echo "waiting for DB..."; done
echo "✓ DB ready" && tail -5 scripts/provision.log
```

**IMPORTANT — never kill or re-run the provision process:**
- `PYTHONUNBUFFERED=1` ensures output appears immediately in the log
- If the log appears empty after 5s, check `ps aux | grep provision` — if the process is running, it is working; just wait
- **Never `kill` a running provision process** — this releases the lock and allows a duplicate to start
- If `.env` already exists with a valid URI, skip provision entirely — the DB is already running

If any offline-written files need fixing after DB validation, the fix loop is short
because the structure is already correct — only execution errors need addressing.

## On Completion — write to progress.md

Write the provision script to `scripts/provision_aura.py` (not the project root).

```markdown
### 2-provision
status: done
NEO4J_URI=<value from .env>
NEO4J_USERNAME=<value from .env>
NEO4J_DATABASE=<value from .env, usually "neo4j">
INSTANCE_ID=<Aura instance ID, e.g. "f1cad593" — needed for cleanup>
files=scripts/provision_aura.py
```

## .env File Template
```
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<generated-password>
NEO4J_DATABASE=neo4j
```
