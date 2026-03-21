# Cypher Skill Test Report — `run-20260321T104138`

**Skill**: `neo4j-cypher-authoring-skill`  
**Started**: 2026-03-21 10:41:38 UTC  
**Completed**: 2026-03-21 10:44:46 UTC  

## Overall Results

| Metric | Value |
|--------|-------|
| Total cases | 27 |
| PASS | 7 |
| WARN | 0 |
| FAIL | 20 |
| Pass rate | 25.9% |

## Per-Difficulty Pass Rates

| Difficulty | Total | PASS | WARN | FAIL | Pass Rate |
|------------|------:|-----:|-----:|-----:|----------:|
| Basic | 6 | 4 | 0 | 2 | 66.7% |
| Intermediate | 6 | 1 | 0 | 5 | 16.7% |
| Advanced | 6 | 2 | 0 | 4 | 33.3% |
| Complex | 4 | 0 | 0 | 4 | 0.0% |
| Expert | 5 | 0 | 0 | 5 | 0.0% |

## DB-Hits Summary (per Difficulty)

Only cases that completed Gate 4 (PROFILE) are included.

| Difficulty | n | Min | Median | Max |
|------------|--:|----:|-------:|----:|
| — | — | — | — | — |

## Test Case Results

| ID | Difficulty | Verdict | Gate | DB Hits | Duration (s) | Question |
|----|------------|---------|-----:|--------:|-------------:|----------|
| `ucf-basic-001` | basic | PASS | — | — | 6.3 | How many transactions are recorded in the system in total? |
| `ucf-basic-002` | basic | **FAIL** | 2 | — | 5.3 | Which active accounts have the highest balances? Show the a… |
| `ucf-basic-003` | basic | PASS | — | — | 4.0 | What types of transactions does the system support? |
| `ucf-basic-004` | basic | **FAIL** | 2 | — | 5.2 | Show me the customers who have been flagged for fraud. Who … |
| `ucf-basic-005` | basic | PASS | — | — | 3.2 | What are the largest transactions in the system? Show the t… |
| `ucf-basic-006` | basic | PASS | — | — | 8.1 | How many accounts of each type (savings, checking, etc.) ar… |
| `ucf-intermediate-001` | intermediate | **FAIL** | 2 | — | 7.6 | Which accounts are sending the most money? Show the total a… |
| `ucf-intermediate-002` | intermediate | **FAIL** | 2 | — | 6.3 | Show me which customers own which accounts, including the a… |
| `ucf-intermediate-003` | intermediate | **FAIL** | 2 | — | 7.5 | What does transaction activity look like across 2025? Break… |
| `ucf-intermediate-004` | intermediate | **FAIL** | 2 | — | 6.1 | Which accounts appear to be linked to each other through sh… |
| `ucf-intermediate-005` | intermediate | **FAIL** | 2 | — | 4.5 | Are there customers using more than one email address? Show… |
| `ucf-intermediate-006` | intermediate | PASS | — | — | 8.2 | What is the average, highest, and total number of transacti… |
| `ucf-advanced-001` | advanced | **FAIL** | 1 | — | 5.7 | Which accounts are indirectly linked to each other through … |
| `ucf-advanced-002` | advanced | **FAIL** | 2 | — | 4.6 | What is the shortest chain of linked accounts connecting a … |
| `ucf-advanced-003` | advanced | PASS | — | — | 5.8 | Which customers sit at the center of the most financial con… |
| `ucf-advanced-004` | advanced | **FAIL** | 2 | — | 3.3 | Which accounts have been particularly active — sending more… |
| `ucf-advanced-005` | advanced | PASS | — | — | 5.8 | Which transactions are unusually large compared to other tr… |
| `ucf-advanced-006` | advanced | **FAIL** | 2 | — | 10.1 | Look up customers with the surname 'Hoffman'. Are any of th… |
| `ucf-complex-001` | complex | **FAIL** | 1 | — | 7.3 | Find pairs of accounts that share personal details where at… |
| `ucf-complex-002` | complex | **FAIL** | 2 | — | 7.2 | Which accounts received unusually large sums of money withi… |
| `ucf-complex-003` | complex | **FAIL** | 2 | — | 6.6 | Are there customers in the same fraud network cluster who a… |
| `ucf-complex-004` | complex | **FAIL** | 2 | — | 4.6 | For money transfer transactions, can you trace the flow of … |
| `ucf-expert-001` | expert | **FAIL** | 2 | — | 5.7 | Find all customers named Michael. Are any of them flagged f… |
| `ucf-expert-002` | expert | **FAIL** | 1 | — | 17.7 | Among the most influential accounts in our network, which p… |
| `ucf-expert-003` | expert | **FAIL** | 2 | — | 5.2 | Are there active accounts sending money through multiple in… |
| `ucf-expert-004` | expert | **FAIL** | 2 | — | 5.4 | Mark all customers who belong to the same network cluster a… |
| `ucf-expert-005` | expert | **FAIL** | 2 | — | 20.9 | Search for customers with the surname 'Poole' and trace how… |

## Failure Analysis

### FAIL (20 cases)

#### Gate 1 (3 case(s))

**`ucf-advanced-001`** — Which accounts are indirectly linked to each other through chains of shared personal details? I want to see account pairs that are connected through two to four intermediate links.

> **Gate 1 FAIL**: Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '-': expected '(' (line 2, column 47 (offset: 56))
"EXPLAIN MATCH (a1:Account)-[:HAS_DETAIL]-{2,4}-(a2:Account)"
                                               ^} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}

```cypher
CYPHER 25
MATCH (a1:Account)-[:HAS_DETAIL]-{2,4}-(a2:Account)
WHERE elementId(a1) < elementId(a2)
RETURN DISTINCT a1.id AS account1, a2.id AS account2
```

**`ucf-complex-001`** — Find pairs of accounts that share personal details where at least one account belongs to a customer flagged for fraud. Who owns these accounts?

> **Gate 1 FAIL**: Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input 'WHERE': expected 'ORDER BY', 'CALL', 'CREATE', 'LOAD CSV', 'DELETE', 'DETACH', 'FILTER', 'FINISH', 'FOREACH', 'IN', 'INSERT', 'LET', 'LIMIT', 'MATCH', 'MERGE', 'NEXT', 'NODETACH', 'OFFSET', 'OPTIONAL', 'REMOVE', 'RETURN', 'SET', 'SKIP', 'UNION', 'UNWIND', 'USE', 'WITH' or <EOF> (line 10, column 1 (offset: 460))
"WHERE size(sharedDetails) > 0"
 ^} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}

```cypher
CYPHER 25
MATCH (c1:Customer)-[:HAS_ACCOUNT]->(a1:Account),
      (c2:Customer)-[:HAS_ACCOUNT]->(a2:Account)
WHERE elementId(a1) < elementId(a2)
  AND (c1.fraudFlag = true OR c2.fraudFlag = true)
CALL (a1, a2) {
  MATCH (a1)-[:HAS_PHONE|HAS_EMAIL|HAS_ADDRESS]->(shared)<-[:HAS_PHONE|HAS_EMAIL|HAS_ADDRESS]-(a2)
  RETURN collect(DISTINCT labels(shared)[0] + ': ' + coalesce(shared.value, shared.address, toString(elementId(shared)))) AS sharedDetails
}
WHERE size(sharedDetails) > 0
... (9 more lines)
```

**`ucf-expert-002`** — Among the most influential accounts in our network, which pairs are most directly connected through shared identity links? Show the tightest connections first.

> **Gate 1 FAIL**: Syntax error: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '+': expected '-' (line 14, column 102 (offset: 343))
"MATCH path = ALL SHORTEST (a1)-[:SHARES_IDENTITY|SHARES_PII|SHARES_PHONE|SHARES_EMAIL|SHARES_ADDRESS]+->(a2)"
                                                                                                      ^} {gql_status: 42001} {gql_status_description: error: syntax error or access rule violation - invalid syntax}

```cypher
CYPHER 25
MATCH (a:Account)
WITH a, apoc.node.degree(a) AS influence
ORDER BY influence DESC
LIMIT 50

WITH collect(a) AS topAccounts

UNWIND topAccounts AS a1
UNWIND topAccounts AS a2
... (15 more lines)
```


#### Gate 2 (17 case(s))

**`ucf-basic-002`** — Which active accounts have the highest balances? Show the account number and current balance for the top 20.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (a:Account {status: 'active'})
RETURN a.accountNumber AS accountNumber, a.balance AS currentBalance
ORDER BY a.balance DESC
LIMIT 20
```

_Metrics_: elapsed=12 ms

**`ucf-basic-004`** — Show me the customers who have been flagged for fraud. Who are the most at-risk based on their network influence score?

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (c:Customer {fraudFlag: true})
RETURN c.customerId AS customerId,
       c.name AS name,
       c.networkInfluenceScore AS networkInfluenceScore,
       c.riskScore AS riskScore
ORDER BY c.networkInfluenceScore DESC
```

_Metrics_: elapsed=15 ms

**`ucf-intermediate-001`** — Which accounts are sending the most money? Show the total amount sent and number of transactions per account.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (a:Account)-[t:TRANSACTION]->(b:Account)
WITH a, sum(t.amount) AS totalSent, count(t) AS txCount
ORDER BY totalSent DESC
RETURN a.id AS account, totalSent, txCount
```

_Metrics_: elapsed=14 ms

**`ucf-intermediate-002`** — Show me which customers own which accounts, including the account balance and account type.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (c:Customer)-[:OWNS]->(a:Account)
RETURN c.name AS customer, a.accountType AS accountType, a.balance AS balance
ORDER BY c.name, a.accountType
```

_Metrics_: elapsed=16 ms

**`ucf-intermediate-003`** — What does transaction activity look like across 2025? Break down the count and total value by transaction type.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (t:Transaction)
WHERE t.date >= date('2025-01-01') AND t.date < date('2026-01-01')
WITH t.type AS transactionType,
     count(t) AS transactionCount,
     sum(t.amount) AS totalValue
RETURN transactionType,
       transactionCount,
       totalValue
ORDER BY totalValue DESC
```

_Metrics_: elapsed=20 ms

**`ucf-intermediate-004`** — Which accounts appear to be linked to each other through shared personal details? Show the pairs of linked account numbers.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (a1:Account)-[:HAS_PHONE|HAS_EMAIL|HAS_ADDRESS]->(detail)<-[:HAS_PHONE|HAS_EMAIL|HAS_ADDRESS]-(a2:Account)
WHERE elementId(a1) < elementId(a2)
RETURN DISTINCT a1.accountNumber AS account1, a2.accountNumber AS account2
```

_Metrics_: elapsed=22 ms

**`ucf-intermediate-005`** — Are there customers using more than one email address? Show those customers and how many email addresses they have on file.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (c:Customer)-[:HAS_EMAIL]->(e:Email)
WITH c, count(e) AS emailCount
WHERE emailCount > 1
RETURN c.name AS customer, emailCount
ORDER BY emailCount DESC
```

_Metrics_: elapsed=16 ms

**`ucf-advanced-002`** — What is the shortest chain of linked accounts connecting a savings account to a checking account?

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1
> **Gate 3 FAIL**: Old variable-length path syntax [:REL*]; use QPE -[:REL]*- instead

```cypher
CYPHER 25
MATCH path = SHORTEST 1 (s:Account {type: 'savings'})-[:LINKED*]->(c:Account {type: 'checking'})
RETURN [node IN nodes(path) | node.id] AS accountChain,
       length(path) AS chainLength
ORDER BY chainLength ASC
LIMIT 1
```

_Metrics_: elapsed=16 ms

**`ucf-advanced-004`** — Which accounts have been particularly active — sending more than three transactions? Show the account number, type, and transaction count.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (a:Account)-[:HAS_TRANSACTION]->(t:Transaction)
WITH a, count(t) AS txCount
WHERE txCount > 3
RETURN a.accountNumber AS accountNumber, a.type AS type, txCount
ORDER BY txCount DESC
```

_Metrics_: elapsed=18 ms

**`ucf-advanced-006`** — Look up customers with the surname 'Hoffman'. Are any of them flagged for fraud, and how prominent are they in our customer network?

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to invoke procedure `db.index.fulltext.queryNodes`: Caused by: java.lang.IllegalArgumentException: There is no such fulltext schema index: customerFulltext} {gql_status: 52N37} {gql_status_description: error: procedure exception - procedure execution error. Execution of the procedure db.index.fulltext.queryNodes() failed.}

```cypher
CYPHER 25
CALL db.index.fulltext.queryNodes('customerFulltext', 'Hoffman') YIELD node AS customer, score
WHERE customer:Customer AND customer.lastName = 'Hoffman'
WITH customer, score
OPTIONAL MATCH (customer)-[r]-(neighbor)
WITH customer, score,
     customer.fraudFlag AS isFlagged,
     count(DISTINCT neighbor) AS networkDegree
RETURN
  customer.customerId                        AS customerId,
... (5 more lines)
```

**`ucf-complex-002`** — Which accounts received unusually large sums of money within a single month in 2025? Flag any account that received more than $10,000 in one calendar month.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (a:Account)<-[:TO]-(t:Transaction)
WHERE t.date >= date('2025-01-01') AND t.date < date('2026-01-01')
WITH a,
     date.truncate('month', t.date) AS txMonth,
     sum(t.amount) AS monthlyTotal
WHERE monthlyTotal > 10000
RETURN a.id AS account,
       txMonth.year AS year,
       txMonth.month AS month,
... (2 more lines)
```

_Metrics_: elapsed=19 ms

**`ucf-complex-003`** — Are there customers in the same fraud network cluster who are also sharing phone numbers or email addresses with each other? This could indicate coordinated activity.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (c1:Customer)-[:BELONGS_TO]->(cluster:FraudNetworkCluster)<-[:BELONGS_TO]-(c2:Customer)
WHERE elementId(c1) < elementId(c2)
WITH cluster, c1, c2
OPTIONAL MATCH (c1)-[:HAS_PHONE]->(phone:Phone)<-[:HAS_PHONE]-(c2)
OPTIONAL MATCH (c1)-[:HAS_EMAIL]->(email:Email)<-[:HAS_EMAIL]-(c2)
WITH cluster, c1, c2,
     collect(DISTINCT phone.number) AS sharedPhones,
     collect(DISTINCT email.address) AS sharedEmails
WHERE size(sharedPhones) > 0 OR size(sharedEmails) > 0
... (8 more lines)
```

_Metrics_: elapsed=34 ms

**`ucf-complex-004`** — For money transfer transactions, can you trace the flow of funds — showing which account sent money, which transaction carried it, and which account received it? Show the largest transfers first.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (sender:Account)-[out:TRANSFER]->(tx:Transaction)-[in:TRANSFER]->(receiver:Account)
RETURN sender.id AS sender_account,
       tx.id AS transaction_id,
       tx.amount AS amount,
       tx.currency AS currency,
       receiver.id AS receiver_account
ORDER BY tx.amount DESC
```

_Metrics_: elapsed=16 ms

**`ucf-expert-001`** — Find all customers named Michael. Are any of them flagged for fraud, and which fraud network cluster do they belong to?

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to invoke procedure `db.index.fulltext.queryNodes`: Caused by: java.lang.IllegalArgumentException: There is no such fulltext schema index: entity} {gql_status: 52N37} {gql_status_description: error: procedure exception - procedure execution error. Execution of the procedure db.index.fulltext.queryNodes() failed.}

```cypher
CYPHER 25
CALL db.index.fulltext.queryNodes('entity', 'Michael') YIELD node AS customer, score
WHERE customer:Customer
WITH customer, score
OPTIONAL MATCH (customer)-[:BELONGS_TO]->(cluster:FraudNetworkCluster)
RETURN
  customer.name AS name,
  customer.id AS customerId,
  coalesce(customer.fraudFlag, false) AS isFlaggedForFraud,
  cluster.id AS fraudClusterId,
... (3 more lines)
```

**`ucf-expert-003`** — Are there active accounts sending money through multiple intermediate accounts before reaching a destination — a pattern that could indicate layering in money laundering? Show account pairs with multiple such routing paths.

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 1
> **Gate 3 FAIL**: Old variable-length path syntax [:REL*]; use QPE -[:REL]*- instead

```cypher
CYPHER 25
MATCH (src:Account)-[:TRANSACTION*2..5]->(dst:Account)
WHERE src <> dst
  AND src.status = 'active'
  AND dst.status = 'active'
WITH src, dst, count(*) AS routingPaths
WHERE routingPaths > 1
RETURN src.id AS sourceAccount,
       dst.id AS destinationAccount,
       routingPaths
... (2 more lines)
```

_Metrics_: elapsed=15 ms

**`ucf-expert-004`** — Mark all customers who belong to the same network cluster as known fraudsters as 'suspicious due to network association'. Process them in small batches to avoid overloading the system.

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.DatabaseError.Transaction.TransactionStartFailed} {message: A query with 'CALL { ... } IN TRANSACTIONS' can only be executed in an implicit transaction, but tried to execute in an explicit transaction.} {gql_status: 25N17} {gql_status_description: error: invalid transaction state - implicit transaction required. The attempted operation requires an implicit transaction.}

```cypher
CYPHER 25
MATCH (fraudster:Customer {status: 'fraudster'})
MATCH (fraudster)-[:BELONGS_TO]->(cluster:NetworkCluster)<-[:BELONGS_TO]-(suspect:Customer)
WHERE suspect.status <> 'fraudster'
WITH collect(DISTINCT suspect) AS suspects
CALL (suspects) {
  UNWIND suspects AS suspect
  SET suspect.status = 'suspicious',
      suspect.suspicionReason = 'suspicious due to network association',
      suspect.flaggedAt = datetime()
... (1 more lines)
```

**`ucf-expert-005`** — Search for customers with the surname 'Poole' and trace how many accounts in our system are linked to their accounts — directly or through up to three degrees of shared identity.

> **Gate 2 FAIL**: Execution error: {neo4j_code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to invoke procedure `db.index.fulltext.queryNodes`: Caused by: java.lang.IllegalArgumentException: There is no such fulltext schema index: customers} {gql_status: 52N37} {gql_status_description: error: procedure exception - procedure execution error. Execution of the procedure db.index.fulltext.queryNodes() failed.}

```cypher
CYPHER 25
CALL db.index.fulltext.queryNodes('customers', 'Poole') YIELD node AS customer
MATCH (customer)-[:HAS_ACCOUNT]->(seed:Account)
MATCH (seed)-[:SHARED_IDENTITY]-{1,3}(linked:Account)
WHERE linked <> seed
RETURN customer.name                  AS customerName,
       seed.accountId                 AS seedAccount,
       count(DISTINCT linked)         AS linkedAccountCount
ORDER BY linkedAccountCount DESC
```


---

_Report generated 2026-03-21T10:44:55Z by `tests/harness/reporter.py`_
