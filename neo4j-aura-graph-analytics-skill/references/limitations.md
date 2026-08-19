# AGA vs Embedded GDS — Feature Comparison

| Feature | AGA (serverless) | GDS plugin (embedded) |
|---|---|---|
| Topological link prediction | ❌ Not supported | ✅ |
| ML model persistence across sessions | ❌ Session-local only | ✅ Persistent in model catalog |
| Cypher API (`CALL gds.*`) | ✅ AuraDB attached sessions only; limited vs plugin | ✅ |
| Non-Neo4j data sources | ✅ Pandas, Spark, Arrow | ❌ |
| Aura BC / VDC | ✅ | ❌ |
| Aura Pro | ❌ | ✅ |
| AuraDB Free | ✅ max `m_2GB`, 1 concurrent session, unbilled | ❌ |
| Billing | Per session-minute (Free and Pro Trial unbilled) | Included in AuraDB |
| DB performance isolation | ✅ Full isolation | ❌ Shares DB resources |

## SessionMemory Tiers

`m_2GB`, `m_4GB`, `m_8GB`, `m_16GB`, `m_24GB`, `m_32GB`, `m_48GB`, `m_64GB`, `m_96GB`, `m_128GB`, `m_192GB`, `m_256GB`, `m_384GB`, `m_512GB` — `SessionMemory.all_values()` lists them

Caps per AuraDB tier:

| AuraDB tier | Max session memory | Max concurrent sessions |
|---|---|---|
| Free | 2 GB | 1 |
| Pro Trial | 8 GB | 3 |
| Professional / Business Critical | 128 GB | 100 |
| Virtual Dedicated Cloud | 512 GB | 100 |

## AlgorithmCategory Values

`CENTRALITY`, `COMMUNITY_DETECTION`, `SIMILARITY`, `PATH_FINDING`, `NODE_EMBEDDING`

## Available Cloud Locations

```python
print(sessions.available_cloud_locations())
```

Common: `CloudLocation("gcp", "europe-west1")`, `CloudLocation("gcp", "us-east1")`, `CloudLocation("aws", "us-east-1")`
