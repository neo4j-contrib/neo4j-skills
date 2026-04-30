# Aura Tiers and Connection Details

## Tier Comparison

| Tier | Limits | Cloud | Backups | HA | Use case |
|---|---|---|---|---|---|
| **Free** | 200K nodes, 400K rels | GCP us-central1 only | On-demand snapshots only | No | Learning, prototyping |
| **Professional** | Flexible sizing | AWS/GCP/Azure multi-region | Daily, 7-day retention | No | Production moderate |
| **Business Critical** | Flexible sizing | AWS/GCP/Azure multi-region | Daily, 7-day retention | 99.95% SLA | Enterprise |
| **Virtual Dedicated Cloud** | Flexible sizing | Dedicated infrastructure | Hourly, 60-day retention | Yes + CMEK, VPC | Compliance/security |

Free auto-pauses after 72h inactivity. Professional/BC/VDC include 7-day free trial (extendable 7 more days).

## Connection String Format

URI pattern (all tiers):
```
NEO4J_URI=neo4j+s://<instance-id>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password from credentials file>
NEO4J_DATABASE=neo4j
AURA_INSTANCEID=<instance-id>
```

- URI uses `neo4j+s://` (TLS enforced) — never `bolt://` or `neo4j://` for Aura
- Instance ID is fixed at creation; cannot be changed
- Cloud provider and region are fixed at creation — changing either requires a new instance
- Password can be changed later via console; name and size (paid tiers) also changeable

## Fixed vs Changeable Settings

Fixed at creation (new instance required to change):
- Cloud provider (AWS, GCP, Azure)
- Region/location
- Instance ID

Changeable later:
- Instance name
- Memory and storage size (paid tiers)
- Password

## User Roles

| Role | Access |
|---|---|
| Organisation Admin | Full access to all projects, instances, billing, users |
| Project Admin | Full access within project; manage users + settings |
| Project Member | Read/write to instances; cannot manage users/settings |
| Project Viewer | Read-only; no changes |
| Metrics Reader | View metrics only; no DB changes |

Invite users: Project Settings → Users → Invite Users.

## Aura Shared Responsibility

Neo4j manages: infrastructure, DB maintenance, backups, scaling, security/encryption.
User manages: data modeling, application code, query optimization, monitoring response.
