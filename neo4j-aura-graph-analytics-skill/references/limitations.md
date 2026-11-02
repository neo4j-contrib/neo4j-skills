# AGA vs Embedded GDS — Feature Comparison

| Feature | AGA (serverless) | GDS plugin (embedded) |
|---|---|---|
| Topological link prediction | ✅ Client 2.0+ (attached sessions) | ✅ |
| ML model persistence across sessions | ❌ Session-local only | ✅ Persistent in model catalog |
| Cypher API (`CALL gds.*`) | ✅ Sessions attached to AuraDB Pro / BC / VDC only (not Free); no HITS, Topological Sort, Triangles listing | ✅ |
| Non-Neo4j data sources | ✅ Pandas, Spark, Arrow | ❌ |
| Aura BC / VDC | ✅ | ❌ |
| Aura Pro | ✅ | ✅ (Graph Analytics plugin, Professional only) |
| AuraDB Free | ✅ max `m_2GB`, 1 concurrent session, TTL max 30 min, unbilled | ❌ |
| Billing | Per session-minute, 10-minute minimum per session (Free and Pro Trial unbilled) | Included in AuraDB |
| DB performance isolation | ✅ Full isolation | ❌ Shares DB resources |

## SessionMemory Tiers

`m_2GB`, `m_4GB`, `m_8GB`, `m_16GB`, `m_24GB`, `m_32GB`, `m_48GB`, `m_64GB`, `m_96GB`, `m_128GB`, `m_192GB`, `m_256GB`, `m_384GB`, `m_512GB` — `SessionMemory.all_values()` lists them

Caps per AuraDB tier:

| AuraDB tier | Max session memory | Max concurrent sessions | Max session lifetime |
|---|---|---|---|
| Free | 2 GB | 1 | 4 hours (TTL default and max 30 min) |
| Pro Trial | 8 GB | 3 | 1 day |
| Professional / Business Critical | 128 GB | 100 | 7 days |
| Virtual Dedicated Cloud | 512 GB | 100 | 7 days |

## AlgorithmCategory Values

`CENTRALITY`, `COMMUNITY_DETECTION`, `SIMILARITY`, `PATH_FINDING`, `NODE_EMBEDDING`

## Available Cloud Locations

```python
print(sessions.available_cloud_locations())
```

Common: `CloudLocation("gcp", "europe-west1")`, `CloudLocation("gcp", "us-east1")`, `CloudLocation("aws", "us-east-1")`
