# Neo4j Quick Reference — First-Day Patterns

## Movie Graph Demo Dataset (Standard Quick-Start)

Fastest path to a populated graph. Load via `:play movies` in Neo4j Browser or the Aura Query tool.

```cypher
// Load the movie graph (Neo4j Browser only — :play command)
:play movies
// Then click "Create" in the guide to populate the database
```

Alternatively, load programmatically:
```cypher
// Load sample movie data directly
LOAD CSV WITH HEADERS FROM 'https://data.neo4j.com/importing-cypher/movies.csv' AS row
MERGE (m:Movie {movieId: row.movieId})
SET m.title = row.title, m.year = toInteger(row.year)
```

Movie graph schema: `(Person)-[:ACTED_IN {roles}]->(Movie)`, `(Person)-[:DIRECTED]->(Movie)`

Starter queries:
```cypher
// Find all Tom Hanks movies
MATCH (p:Person {name: 'Tom Hanks'})-[:ACTED_IN]->(m:Movie)
RETURN m.title, m.year ORDER BY m.year

// Co-actors (2-hop)
MATCH (p:Person {name: 'Tom Hanks'})-[:ACTED_IN]->(m)<-[:ACTED_IN]-(costar)
RETURN costar.name, count(m) AS films ORDER BY films DESC LIMIT 10

// Recommendation: movies by actors in same film
MATCH (liked:Movie {title: 'Cast Away'})<-[:ACTED_IN]-(a)-[:ACTED_IN]->(rec:Movie)
WHERE rec <> liked
RETURN rec.title, count(a) AS score ORDER BY score DESC LIMIT 5
```

## Neo4j Browser / Aura Query Tool Commands

| Command | Effect |
|---|---|
| `:play movies` | Load movie graph walkthrough (Browser only) |
| `:server connect` | Connect to a different database |
| `:clear` | Clear result pane |
| `:schema` | Show labels, relationship types, property keys |
| `:help` | Show available commands |
| `Ctrl+Enter` / `Cmd+Enter` | Execute query |

## Cypher Quick Reference

```cypher
// Schema inspection
CALL db.schema.visualization()          // graph view of schema
CALL db.labels()                        // all node labels
CALL db.relationshipTypes()             // all rel types
SHOW INDEXES                            // all indexes + status
SHOW CONSTRAINTS                        // all constraints

// Count everything
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY cnt DESC
MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS cnt ORDER BY cnt DESC

// Sample data
MATCH (n) RETURN n LIMIT 25
MATCH (n)-[r]->(m) RETURN n,r,m LIMIT 50

// Create a node
CREATE (p:Person {name: 'Alice', age: 30})

// Create a relationship
MATCH (a:Person {name: 'Alice'}), (b:Person {name: 'Bob'})
CREATE (a)-[:KNOWS]->(b)

// Upsert (create or update)
MERGE (p:Person {name: 'Alice'})
SET p.age = 30

// Delete node and its relationships
MATCH (p:Person {name: 'Alice'})
DETACH DELETE p
```

## Common First-Day Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Querying without index | Slow queries; full node scan | Add `CREATE INDEX` on frequently filtered property before loading data |
| Using `CREATE` instead of `MERGE` on re-import | Duplicate nodes | Use `MERGE (n:Label {id: row.id})` for idempotent imports |
| Keeping FK columns as node properties | Graph has no traversable connections | Map FK columns to relationships |
| Storing NULL as empty string `""` | Properties pollute queries | Use `CASE WHEN ... IS NOT NULL` to omit; Neo4j silently skips actual nulls |
| No constraint before bulk import | Duplicates on load, constraint creation then fails | `CREATE CONSTRAINT ... REQUIRE x IS UNIQUE` before first LOAD CSV |
| `neo4j://` URI for Aura | TLS error / connection refused | Use `neo4j+s://` for all Aura connections |
| Global `pip install` on Python 3.12+ | "externally-managed-environment" error | Always use `.venv`: `python3 -m venv .venv && .venv/bin/pip install ...` |
| Forgetting to save credentials file | Can't retrieve password later | Download credentials file at instance creation — no password reset available |
| Running large queries without LIMIT | Browser/Query tool hangs | Always add `LIMIT 25` when exploring unknown graph |

## Aura Quick-Start Checklist (First-Time)

1. Go to https://console.neo4j.io → create account → Create Instance
2. Select tier (Free for learning, Professional for production)
3. Download credentials file immediately — password shown only once
4. Wait for status to change from "Creating" to "Running" (~2-5 min)
5. Open instance → Import (Data Importer) or Query tool
6. Verify connectivity: `RETURN 'connected' AS status`
7. Write credentials to `.env`:
   ```
   NEO4J_URI=neo4j+s://<id>.databases.neo4j.io
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=<password>
   NEO4J_DATABASE=neo4j
   ```
8. Add `.env` to `.gitignore`

## Northwind Demo Dataset (Relational-to-Graph Example)

Classic relational → graph migration example. CSV files at:
https://github.com/neo4j-graph-examples/northwind/tree/main/import

Schema: `(Customer)-[:PLACED]->(Order)-[:CONTAINS {quantity,unitPrice}]->(Product)-[:IN_CATEGORY]->(Category)`, `(Supplier)-[:SUPPLIES]->(Product)`, `(Employee)-[:PROCESSED]->(Order)`, `(Employee)-[:REPORTS_TO]->(Employee)`

See `neo4j-migration-skill` for full relational-to-graph import patterns.
