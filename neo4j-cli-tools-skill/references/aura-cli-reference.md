# aura-cli Reference

CLI for managing Neo4j Aura cloud resources: instances, tenants, credentials.

## Installation

**Download binary** from [releases page](https://github.com/neo4j/aura-cli/releases/latest), extract, then:

**Windows**:
```bash
move aura-cli.exe c:\windows\system32
```

**macOS/Linux**:
```bash
sudo mv aura-cli /usr/local/bin/
chmod +x /usr/local/bin/aura-cli
```

```bash
aura-cli --version
```

## Initial Setup

1. Log in to [Neo4j Console](https://console.neo4j.io/) → Account Settings → generate API credentials (Client ID + Client Secret)

```bash
aura-cli credential add \
  --name "Aura API Credentials" \
  --client-id <your-client-id> \
  --client-secret <your-client-secret>
```

Adds and sets as default credential.

## Basic Syntax

```bash
aura-cli [command] [subcommand] [flags]
```

**Global Flags**:
- `-h, --help` - help for any command
- `-v, --version` - version info
- `--output {default,json,table}` - output format
- `--auth-url <url>` - authentication URL (optional)
- `--base-url <url>` - API base URL (optional)

## Command Categories

### Credential Management (`credential`)

```bash
aura-cli credential add \
  --name "Production Credentials" \
  --client-id <client-id> \
  --client-secret <client-secret>

aura-cli credential list

aura-cli credential use "Production Credentials"

aura-cli credential remove "Old Credentials"
```

### Instance Management (`instance`)

```bash
aura-cli instance create \
  --name "production-db" \
  --type "enterprise-db" \
  --region "us-east-1" \
  --memory "8GB" \
  --cloud-provider "gcp"
```

Options: `--name`, `--type` (`enterprise-db`, `professional-db`), `--region`, `--memory`, `--cloud-provider` (`gcp`, `aws`, `azure`), `--tenant-id`

```bash
aura-cli instance list
aura-cli instance list --output table
aura-cli instance list --output json

aura-cli instance get <instance-id>
aura-cli instance get abc123def456 --output json

aura-cli instance update <instance-id> --name "new-name" --memory "16GB"

aura-cli instance pause <instance-id>    # stops billing
aura-cli instance resume <instance-id>
aura-cli instance delete <instance-id> --confirm

# Overwrite target with data from source (e.g. refresh staging from production)
aura-cli instance overwrite <target-instance-id> --source-instance-id <source-instance-id>
```

#### Snapshots
```bash
aura-cli instance snapshot list <instance-id>
aura-cli instance snapshot create <instance-id> --name "backup-2026-02-16"
aura-cli instance snapshot restore <instance-id> --snapshot-id <snapshot-id>
```

### Tenant Management (`tenant`)

```bash
aura-cli tenant list
aura-cli tenant get <tenant-id>
```

### Graph Analytics (`graph-analytics`)

```bash
aura-cli graph-analytics list
aura-cli graph-analytics get <instance-id>
```

### Customer Managed Keys (`customer-managed-key`)

```bash
aura-cli customer-managed-key list
aura-cli customer-managed-key add --key-id <key-id> --cloud-provider <provider>
```

## Configuration

Config file locations:
- **Linux/macOS**: `~/.aura-cli/config.json`
- **Windows**: `%USERPROFILE%\.aura-cli\config.json`

Environment variables:
- `AURA_CLI_AUTH_URL`, `AURA_CLI_BASE_URL`
- `AURA_CLI_CLIENT_ID`, `AURA_CLI_CLIENT_SECRET`
- `AURA_CLI_CONFIG_PATH`

## Common Workflows

### Provision New Instance

```bash
aura-cli credential add --name "Aura Credentials" --client-id $CLIENT_ID --client-secret $CLIENT_SECRET

aura-cli instance create \
  --name "my-app-db" \
  --type "enterprise-db" \
  --region "us-east-1" \
  --memory "8GB" \
  --cloud-provider "aws"

aura-cli instance get <instance-id>
```

### Backup and Restore

```bash
aura-cli instance snapshot create abc123def456 --name "pre-migration-backup"
aura-cli instance snapshot list abc123def456
aura-cli instance snapshot restore abc123def456 --snapshot-id snapshot-xyz789
```

### Cost Management

```bash
aura-cli instance pause dev-instance-id
aura-cli instance resume dev-instance-id
aura-cli instance delete old-instance-id
```

### CI/CD Integration

```bash
#!/bin/bash
INSTANCE_ID=$(aura-cli instance create \
  --name "test-$CI_BUILD_ID" \
  --type "professional-db" \
  --region "us-east-1" \
  --memory "4GB" \
  --output json | jq -r '.id')

# Run tests...

aura-cli instance delete $INSTANCE_ID
```

### Multi-Environment Management

```bash
aura-cli credential use "Production Credentials"
aura-cli instance list

aura-cli credential use "Development Credentials"
aura-cli instance list
```

### Refresh Staging from Production

```bash
aura-cli instance overwrite staging-instance-id --source-instance-id production-instance-id
```

## Output Examples

```bash
aura-cli instance list --output table
```

```
+------------------+------------------+----------+----------+---------------+
| ID               | NAME             | TYPE     | STATUS   | REGION        |
+------------------+------------------+----------+----------+---------------+
| abc123def456     | production-db    | enterprise| running  | us-east-1     |
| xyz789ghi012     | staging-db       | professional| running| eu-west-1     |
| mno345pqr678     | dev-db           | free     | paused   | us-west-2     |
+------------------+------------------+----------+----------+---------------+
```

```bash
aura-cli instance get abc123def456 --output json
```

```json
{
  "id": "abc123def456",
  "name": "production-db",
  "type": "enterprise-db",
  "status": "running",
  "region": "us-east-1",
  "memory": "8GB",
  "cloud_provider": "aws",
  "connection_url": "neo4j+s://abc123def456.databases.neo4j.io",
  "created_at": "2026-01-15T10:30:00Z",
  "tenant_id": "tenant-123"
}
```

## Scripting Examples

```bash
#!/bin/bash
aura-cli instance list --output json | jq -r '.[] | "\(.name) (\(.status)) - \(.connection_url)"'
```

```python
import subprocess, json, time

def create_instance(name, memory="4GB"):
    cmd = ["aura-cli", "instance", "create",
           "--name", name, "--type", "professional-db",
           "--region", "us-east-1", "--memory", memory, "--output", "json"]
    return json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)

def get_instance(instance_id):
    cmd = ["aura-cli", "instance", "get", instance_id, "--output", "json"]
    return json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)

instance = create_instance("test-db")
instance_id = instance["id"]

while True:
    status = get_instance(instance_id)
    if status["status"] == "running":
        print(f"Instance ready: {status['connection_url']}")
        break
    time.sleep(30)
```

## Troubleshooting

**Authentication failed**: verify credentials in Neo4j Console, re-add with `aura-cli credential add`.

**No default credential**: `aura-cli credential use "Credential Name"`

**Instance creation failed — insufficient quota**: check account quota limits and billing in Neo4j Console.

**Rate limit exceeded**: add delays between calls; use `--output json` and parse to minimize calls.

**Unable to connect to Aura API**: check internet connectivity, firewall/proxy, https://status.neo4j.io/

## Best Practices

- Never commit credentials to version control — use environment variables in CI/CD
- Use `--output json` in automation scripts
- Check exit codes (`$?`) in scripts
- Separate credentials per environment
- Pause dev/staging instances to reduce costs
- Schedule regular snapshots

## Additional Resources

- [Aura CLI GitHub Repository](https://github.com/neo4j/aura-cli)
- [Neo4j Aura Documentation](https://neo4j.com/docs/aura/)
- [Aura API Documentation](https://neo4j.com/docs/aura/aura-api/)
