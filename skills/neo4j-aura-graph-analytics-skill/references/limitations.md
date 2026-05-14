# AGA vs Embedded GDS — Feature Comparison

| Feature | AGA (serverless) | GDS plugin (embedded) |
|---|---|---|
| Topological link prediction | ❌ Not supported | ✅ |
| ML model persistence across sessions | ❌ Session-local only | ✅ Persistent in model catalog |
| Cypher procedures (`CALL gds.*`) | ❌ Python client only | ✅ |
| Non-Neo4j data sources | ✅ Pandas, Spark, Arrow | ❌ |
| Aura BC / VDC | ✅ | ❌ |
| Aura Pro | ❌ | ✅ |
| Billing | Per session-minute | Included in AuraDB |
| DB performance isolation | ✅ Full isolation | ❌ Shares DB resources |

## SessionMemory Tiers

`m_2GB`, `m_4GB`, `m_8GB`, `m_16GB`, `m_24GB`, `m_32GB`, `m_48GB`, `m_64GB`, `m_128GB`, `m_192GB`, `m_256GB`

## AlgorithmCategory Values

`CENTRALITY`, `COMMUNITY_DETECTION`, `SIMILARITY`, `PATH_FINDING`, `NODE_EMBEDDING`

## Available Cloud Locations

```python
print(sessions.available_cloud_locations())
```

Common: `CloudLocation("gcp", "europe-west1")`, `CloudLocation("gcp", "us-east1")`, `CloudLocation("aws", "us-east-1")`
