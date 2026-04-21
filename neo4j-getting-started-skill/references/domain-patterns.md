# Domain Patterns Reference

Pre-built graph model templates for common domains. Use as starting point, adapt to user's specific use-case.

---

## Social Network

**Use-cases**: Friend recommendations, community detection, influence analysis, feed ranking

### Model
```
(Person {id, name, email, joinedAt})
(Post {id, content, createdAt, likes})
(Hashtag {name})
(Community {id, name})

(Person)-[:FOLLOWS]->(Person)
(Person)-[:POSTED]->(Post)
(Post)-[:TAGGED]->(Hashtag)
(Person)-[:MEMBER_OF]->(Community)
(Person)-[:LIKED]->(Post)
```

### DDL
```cypher
CYPHER 25
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT post_id IF NOT EXISTS FOR (p:Post) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT hashtag_name IF NOT EXISTS FOR (h:Hashtag) REQUIRE h.name IS UNIQUE;
CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name);
CREATE INDEX post_created IF NOT EXISTS FOR (p:Post) ON (p.createdAt);
```

### Key queries
```cypher
// Friends of friends (recommendations)
CYPHER 25
MATCH (me:Person {id: $userId})-[:FOLLOWS]->(friend)-[:FOLLOWS]->(fof)
WHERE NOT exists { (me)-[:FOLLOWS]->(fof) } AND me <> fof
WITH fof, count(DISTINCT friend) AS mutualFriends
ORDER BY mutualFriends DESC LIMIT 10
RETURN fof.name AS recommendation, mutualFriends;

// Top influencers (by follower count)
CYPHER 25
MATCH (p:Person)
RETURN p.name, count{(p)<-[:FOLLOWS]-()} AS followers
ORDER BY followers DESC LIMIT 20;
```

---

## E-Commerce / Retail

**Use-cases**: Product recommendations, purchase history, inventory, customer segmentation

### Model
```
(Customer {id, name, email, joinedAt, segment})
(Product {id, name, sku, price, category, stock})
(Order {id, orderedAt, total, status})
(Category {name})
(Supplier {id, name, country})

(Customer)-[:PLACED]->(Order)
(Order)-[:CONTAINS {quantity, price}]->(Product)
(Product)-[:BELONGS_TO]->(Category)
(Supplier)-[:SUPPLIES]->(Product)
(Customer)-[:VIEWED]->(Product)
(Customer)-[:WISHLISTED]->(Product)
```

### DDL
```cypher
CYPHER 25
CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT product_sku IF NOT EXISTS FOR (p:Product) REQUIRE p.sku IS UNIQUE;
CREATE CONSTRAINT order_id IF NOT EXISTS FOR (o:Order) REQUIRE o.id IS UNIQUE;
CREATE INDEX product_category IF NOT EXISTS FOR (p:Product) ON (p.category);
CREATE INDEX order_date IF NOT EXISTS FOR (o:Order) ON (o.orderedAt);
```

### Key queries
```cypher
// Co-purchased products (collaborative filtering)
CYPHER 25
MATCH (p:Product {sku: $sku})<-[:CONTAINS]-(o:Order)-[:CONTAINS]->(other:Product)
WHERE p <> other
RETURN other.name AS recommendation, count(o) AS coOrders
ORDER BY coOrders DESC LIMIT 10;

// Top customers by revenue
CYPHER 25
MATCH (c:Customer)-[:PLACED]->(o:Order)
RETURN c.name AS customer, sum(o.total) AS revenue, count(o) AS orders
ORDER BY revenue DESC LIMIT 20;
```

---

## Financial / Fraud Detection

**Use-cases**: Fraud ring detection, money laundering, transaction pattern analysis, KYC

### Model

Account-centric model (preferred for ring detection — cycles traverse Account→Transaction→Account):
```
(Account {accountId, owner, type, balance, createdAt, status})
(Transaction {txId, amount, currency, timestamp, status})

(Account)-[:PERFORMS]->(Transaction)   ← sender
(Transaction)-[:BENEFITS_TO]->(Account) ← receiver
```

Extended model (add as needed):
```
(Account)-[:USES_PHONE]->(Phone {number})
(Account)-[:USES_EMAIL]->(Email {address})
(Transaction)-[:VIA]->(Device {deviceId, ip})
```

**Why PERFORMS/BENEFITS_TO (not FROM/TO on Transaction):** The ring detection pattern
`(a)-[:PERFORMS]->()-[:BENEFITS_TO]->(b)` creates a direct Account→Account traversal path
that can be chained as variable-length paths for cycle detection. Transaction-centric
models `(tx)-[:FROM]->(a)` require more complex patterns and are harder to chain.

### DDL
```cypher
CYPHER 25
CREATE CONSTRAINT account_id IF NOT EXISTS FOR (a:Account) REQUIRE a.accountId IS UNIQUE;
CREATE CONSTRAINT transaction_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.txId IS UNIQUE;
CREATE INDEX account_status IF NOT EXISTS FOR (a:Account) ON (a.status);
CREATE INDEX transaction_timestamp IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp);
CREATE INDEX transaction_amount IF NOT EXISTS FOR (t:Transaction) ON (t.amount);
```

### Key queries
```cypher
// Transaction rings — accounts cycling funds (3–6 hops back to origin)
// This is the canonical fraud ring query; SQL cannot do this efficiently
CYPHER 25
MATCH path = (start:Account)-[:PERFORMS]->(:Transaction)-[:BENEFITS_TO*1..5]->(start)
WHERE ALL(n IN nodes(path) WHERE n:Account OR n:Transaction)
WITH start, length(path) AS ringLength, path
ORDER BY ringLength
RETURN start.accountId AS originAccount, ringLength, 
       [n IN nodes(path) WHERE n:Account | n.accountId] AS ring
LIMIT 20;

// Accounts sharing a phone number (shared identifier clusters)
CYPHER 25
MATCH (a1:Account)-[:USES_PHONE]->(p:Phone)<-[:USES_PHONE]-(a2:Account)
WHERE a1.accountId < a2.accountId
RETURN p.number AS sharedPhone, collect(a1.accountId) + collect(a2.accountId) AS accounts
ORDER BY size(accounts) DESC LIMIT 20;

// High-velocity accounts (potential smurfing)
CYPHER 25
MATCH (a:Account)-[:PERFORMS]->(t:Transaction)
WITH a, count(t) AS txCount, sum(t.amount) AS totalOut
WHERE txCount > 10
RETURN a.accountId AS account, txCount, totalOut
ORDER BY txCount DESC LIMIT 20;
```

### Synthetic data guidance (generate.py)

**Always plant explicit ring patterns** — random transactions will almost never form cycles.
Generate rings deliberately:

```python
# Plant ring patterns: A→B→C→A with ≤20% amount decay per hop (realistic fee/skimming)
rings = [
    ["acc001", "acc002", "acc003"],          # 3-hop ring
    ["acc004", "acc005", "acc006", "acc007"], # 4-hop ring
    ["acc008", "acc009", "acc010", "acc011", "acc012"],  # 5-hop ring
]
for ring in rings:
    amount = random.uniform(5000, 20000)
    for i, src in enumerate(ring):
        tgt = ring[(i + 1) % len(ring)]
        amount *= random.uniform(0.80, 0.98)  # 2–20% decay per hop
        transactions.append({
            "txId": f"ring_tx_{src}_{tgt}",
            "fromAccount": src, "toAccount": tgt,
            "amount": round(amount, 2),
            "timestamp": (datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat(),
            "status": "completed",
        })
```

---

## Knowledge Graph / RAG

**Use-cases**: Document Q&A, GraphRAG, entity extraction, knowledge base

### Model
```
(Document {id, title, url, source, publishedAt})
(Chunk {id, text, position, tokenCount})
(Entity {id, name, type})  -- Person, Organization, Location, Concept
(Topic {name})

(Document)-[:HAS_CHUNK]->(Chunk)
(Chunk)-[:MENTIONS]->(Entity)
(Entity)-[:RELATED_TO {weight}]->(Entity)
(Document)-[:ABOUT]->(Topic)
(Entity)-[:INSTANCE_OF]->(Entity)  -- e.g., Apple IS_A Company
```

### DDL + Vector Index
```cypher
CYPHER 25
CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;

// Vector index for semantic search on chunks
CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
  FOR (c:Chunk) ON (c.embedding)
  OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' } };

// Fulltext index for entity search
CREATE FULLTEXT INDEX entity_search IF NOT EXISTS
  FOR (e:Entity) ON EACH [e.name];
```

### Key queries
```cypher
// GraphRAG: semantic search + graph expansion
CYPHER 25
MATCH (chunk)
  SEARCH chunk IN (
    VECTOR INDEX chunk_embeddings
    FOR $embedding
    LIMIT 5
  ) SCORE AS score
MATCH (chunk)<-[:HAS_CHUNK]-(doc:Document)
OPTIONAL MATCH (chunk)-[:MENTIONS]->(e:Entity)
RETURN chunk.text AS text, doc.title AS source,
       collect(DISTINCT e.name) AS entities, score
ORDER BY score DESC;

// Entity co-occurrence network
CYPHER 25
MATCH (c:Chunk)-[:MENTIONS]->(e1:Entity), (c)-[:MENTIONS]->(e2:Entity)
WHERE e1.id < e2.id
RETURN e1.name, e2.name, count(c) AS coMentions
ORDER BY coMentions DESC LIMIT 20;
```

---

## Healthcare

**Use-cases**: Patient care pathways, drug interactions, clinical trial matching, medical knowledge graph

### Model
```
(Patient {id, age, gender, bloodType})
(Condition {icd10, name, category})
(Medication {rxnorm, name, form, strength})
(Provider {id, name, specialty, npi})
(Visit {id, date, type, notes})
(ClinicalTrial {nctId, title, phase, status})

(Patient)-[:HAS_CONDITION]->(Condition)
(Patient)-[:TAKES]->(Medication)
(Patient)-[:SEEN_BY {at: visitId}]->(Provider)
(Patient)-[:HAD_VISIT]->(Visit)
(Visit)-[:DIAGNOSED]->(Condition)
(Visit)-[:PRESCRIBED]->(Medication)
(Medication)-[:INTERACTS_WITH {severity}]->(Medication)
(Patient)-[:ELIGIBLE_FOR]->(ClinicalTrial)
```

### DDL
```cypher
CYPHER 25
CREATE CONSTRAINT patient_id IF NOT EXISTS FOR (p:Patient) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT condition_icd IF NOT EXISTS FOR (c:Condition) REQUIRE c.icd10 IS UNIQUE;
CREATE CONSTRAINT medication_rxnorm IF NOT EXISTS FOR (m:Medication) REQUIRE m.rxnorm IS UNIQUE;
CREATE INDEX visit_date IF NOT EXISTS FOR (v:Visit) ON (v.date);
```

---

## IoT / Network Monitoring

**Use-cases**: Root cause analysis, topology mapping, anomaly detection, capacity planning

### Model
```
(Device {id, name, type, ip, location, status})
(Service {id, name, version, port})
(Alert {id, severity, message, timestamp, resolved})
(Network {id, name, subnet, vlan})
(DataCenter {id, name, location})

(Device)-[:CONNECTED_TO {bandwidth, latency}]->(Device)
(Device)-[:RUNS]->(Service)
(Device)-[:MEMBER_OF]->(Network)
(Network)-[:HOSTED_IN]->(DataCenter)
(Alert)-[:TRIGGERED_ON]->(Device)
(Device)-[:DEPENDS_ON]->(Service)
```

### Key queries
```cypher
// Find blast radius (devices depending on a failing service)
CYPHER 25
MATCH path = (d:Device) (()-[:DEPENDS_ON]->()){0,5} (s:Service {id: $serviceId})
RETURN d.name AS affectedDevice, length(path) AS hops
ORDER BY hops;

// Active alerts with topology context
CYPHER 25
MATCH (a:Alert {resolved: false})-[:TRIGGERED_ON]->(d:Device)
OPTIONAL MATCH (d)-[:MEMBER_OF]->(n:Network)-[:HOSTED_IN]->(dc:DataCenter)
RETURN a.severity, a.message, d.name, n.name AS network, dc.name AS datacenter
ORDER BY a.severity DESC, a.timestamp DESC;
```
