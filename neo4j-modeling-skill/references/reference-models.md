# Reference Model Catalog

32 pre-built Neo4j property graph schemas across 6 industries. Load any model by ID with the injector script:

```bash
python3 <skill-dir>/scripts/inject.py <model-id>
```

Run `python3 <skill-dir>/scripts/inject.py --list` for the live catalog with node and relationship counts.

## Financial Services (13)

| ID | Name | Nodes | Rels |
|---|---|---|---|
| `transaction-base-model` | Transaction & Account Base Model | 19 | 24 |
| `fraud-event-sequence` | Fraud Event Sequence Model | 13 | 26 |
| `regulatory-dependency-mapping` | Regulatory Dependency Mapping | 2 | 3 |
| `mutual-fund-dependency` | Mutual Fund Dependency Analytics | 3 | 2 |
| `deposit-analysis` | Deposit Analysis | 3 | 3 |
| `account-takeover-fraud` | Account Takeover Fraud | 19 | 35 |
| `automated-facial-recognition` | Automated Facial Recognition | 1 | 0 |
| `synthetic-identity-fraud` | Synthetic Identity Fraud | 4 | 4 |
| `transaction-fraud-ring` | Transaction Fraud Ring | 2 | 2 |
| `transaction-monitoring` | Transaction Monitoring | 8 | 10 |
| `transaction-fraud-detection` | Transaction Fraud Detection (IEEE-CIS) | 6 | 5 |
| `customer-churn` | Graph-Aware Finance Churn Prediction | 4 | 4 |
| `ubo-company-ownership` | Ultimate Beneficial Owner (UBO) & Company Ownership | 5 | 5 |

## Insurance (2)

| ID | Name | Nodes | Rels |
|---|---|---|---|
| `claims-fraud` | Insurance Claims Fraud | 4 | 5 |
| `quote-fraud` | Insurance Quote Fraud | 1 | 1 |

## Healthcare & Life Sciences (7)

| ID | Name | Nodes | Rels |
|---|---|---|---|
| `patient-journey` | Patient Journey | 8 | 8 |
| `patent-intelligence` | Patent Intelligence | 12 | 13 |
| `publication-intelligence` | Publication Intelligence | 10 | 13 |
| `pipeline-intelligence` | Pharma Pipeline Intelligence | 7 | 11 |
| `drug-safety` | Drug Safety & Pharmacovigilance (FAERS) | 6 | 10 |
| `single-omics` | Single-omics Data Integration | 10 | 14 |
| `multi-omics` | Multi-omics Data Integration | 12 | 19 |

## Manufacturing (4)

| ID | Name | Nodes | Rels |
|---|---|---|---|
| `ev-route-planning` | Electric Vehicle Route Planning | 3 | 3 |
| `configurable-bom` | Configurable Bill of Materials | 4 | 9 |
| `engineering-traceability` | Engineering Traceability | 4 | 4 |
| `process-monitoring-cpa` | Process Monitoring & Critical Path Analysis | 3 | 6 |

## Cybersecurity (3)

| ID | Name | Nodes | Rels |
|---|---|---|---|
| `vulnerability-prioritization` | Vulnerability Prioritization & Exposure Management | 8 | 7 |
| `attack-path-analysis` | Attack Path Analysis | 6 | 6 |
| `software-supply-chain-security` | Software Supply Chain Security (SBOM) | 5 | 5 |

## Industry Agnostic (3)

| ID | Name | Nodes | Rels |
|---|---|---|---|
| `entity-resolution` | Entity Resolution | 1 | 1 |
| `it-service-graph` | IT Service Graph | 7 | 8 |
| `iam-effective-access` | Identity & Access Management (Effective Access Analysis) | 5 | 7 |

## Keyword Quick Reference

| Keyword | Model ID |
|---|---|
| banking, transactions, KYC, base model | `transaction-base-model` |
| fraud event sequence | `fraud-event-sequence` |
| regulatory, compliance | `regulatory-dependency-mapping` |
| mutual fund, investment | `mutual-fund-dependency` |
| deposit | `deposit-analysis` |
| account takeover, ATO | `account-takeover-fraud` |
| facial recognition, biometric | `automated-facial-recognition` |
| synthetic identity | `synthetic-identity-fraud` |
| fraud ring, circular payments | `transaction-fraud-ring` |
| transaction monitoring, AML | `transaction-monitoring` |
| IEEE-CIS, fraud detection ML | `transaction-fraud-detection` |
| customer churn, retention | `customer-churn` |
| UBO, beneficial owner, 6AMLD | `ubo-company-ownership` |
| insurance claims, crash for cash | `claims-fraud` |
| insurance quote, ghost broker | `quote-fraud` |
| patient journey, healthcare, OMOP | `patient-journey` |
| patent, IP intelligence | `patent-intelligence` |
| publication, KOL | `publication-intelligence` |
| pharma pipeline, clinical trials | `pipeline-intelligence` |
| drug safety, pharmacovigilance, FAERS | `drug-safety` |
| single-omics, genomics | `single-omics` |
| multi-omics | `multi-omics` |
| EV, route planning | `ev-route-planning` |
| BOM, bill of materials, CBOM | `configurable-bom` |
| traceability, requirements, test cases | `engineering-traceability` |
| process monitoring, critical path | `process-monitoring-cpa` |
| vulnerability, CVE, VPEM | `vulnerability-prioritization` |
| attack path, lateral movement | `attack-path-analysis` |
| SBOM, software supply chain | `software-supply-chain-security` |
| entity resolution, record linkage | `entity-resolution` |
| CMDB, IT service graph, infrastructure | `it-service-graph` |
| IAM, RBAC, effective access | `iam-effective-access` |

## Notes

- All reference models include curated positions and colours — do not re-layout automatically.
- Some models include `constraints`, `indexes`, or `notes` fields in their JSON.
- Source: https://neo4j.com/developer/industry-use-cases/
