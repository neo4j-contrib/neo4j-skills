# Aura Monitoring and Metrics

## Accessing Metrics

Quick view: expand **Metrics** section at bottom of instance card (shows CPU, Storage, Query Rate for last 24h).
Full dashboard: instance card → "View all metrics" button, or Operations → Metrics in left menu.

## Metrics Dashboard Tabs

**Resources tab:**
- CPU Usage — min/max/avg % of CPU capacity
- Storage — % disk used
- Out of Memory Errors — count; **critical metric**, monitor closely

**Instance tab:**
- Heap — min/max/avg heap memory for query execution
- Page Cache — % time data found in memory (higher = better; low = disk reads hurting performance)
- Page Cache Evictions — times/min data swapped out; frequent spikes = page cache too small
- Bolt Connections — active Cypher transaction connections
- Garbage Collection — % time freeing memory; high = memory strain

**Database tab:**
- Store Size, Query Metrics, Transaction counts, Checkpoint/Replan stats

## External Monitoring (Prometheus)

Aura exposes a Prometheus-compatible endpoint per project:

```
https://customer-metrics-api.neo4j.io/api/v1/<project-id>/<metrics-id>/metrics
```

Authentication: OAuth2 with Client ID + Client Secret from Metrics Integration settings.
Token URL: `https://api.neo4j.io/oauth/token`

Prometheus config:
```yaml
- job_name: 'aura-metrics'
  scrape_timeout: 30s
  metrics_path: '/api/v1/<project-id>/<metrics-id>/metrics'
  scheme: 'https'
  static_configs:
    - targets: ['customer-metrics-api.neo4j.io']
  oauth2:
    client_id: '<AURA_CLIENT_ID>'
    client_secret: '<AURA_CLIENT_SECRET>'
    token_url: 'https://api.neo4j.io/oauth/token'
```

Access: project Settings → Metrics Integration.

Keep Client Secret secure — grants access to the entire organization.

## Backup and Restore

Snapshots: automatic per tier schedule (see aura-tiers.md) + on-demand manual snapshots.
Restore: creates a new instance from snapshot (does not overwrite existing instance).
Local backup: download `.dump` file from console for offline storage.

## Query Logs

Access: Operations → Query Logs.
Contains: query text, duration, plan, user.
Use for: identifying slow queries, security review of query patterns.
Security logs: separate tab — tracks auth events, role changes.
