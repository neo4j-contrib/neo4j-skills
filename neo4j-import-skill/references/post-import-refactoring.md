# Post-Import Refactoring Patterns

Use after Data Importer or basic LOAD CSV to reshape imported data.

## 1. Verify Property Types First

```cypher
// Node property types (requires APOC)
CALL apoc.meta.nodeTypeProperties()
YIELD nodeType, propertyName, propertyTypes
RETURN nodeType, propertyName, propertyTypes
ORDER BY nodeType, propertyName;

// Relationship property types (requires APOC)
CALL apoc.meta.relTypeProperties()
YIELD relType, propertyName, propertyTypes
RETURN relType, propertyName, propertyTypes;
```

Without APOC: extract a sample and inspect values manually.

Neo4j Browser displays dates as strings — use `n.born.year` to confirm a property is a date, not a string.

## 2. String → List (split delimited field)

Data Importer stores multi-value fields as strings like `"USA|Germany|France"`.
Convert to `StringArray`:

```cypher
MATCH (m:Movie)
CALL (m) {
  SET m.countries = split(coalesce(m.countries, ''), '|'),
      m.languages = split(coalesce(m.languages, ''), '|')
} IN TRANSACTIONS OF 10000 ROWS ON ERROR CONTINUE;
```

`coalesce(m.countries, '')` → returns `''` if null; `split('', '|')` → `['']` — filter afterward if needed:

```cypher
SET m.countries = [x IN split(coalesce(m.countries, ''), '|') WHERE x <> '']
```

Check source data for separator (`|`, `,`, `;` are common). Never assume `,` — conflicts with CSV delimiter.

## 3. Add Labels Based on Relationships

Add specific labels for targeted lookups.

```cypher
// Add Actor label to Person nodes with ACTED_IN relationship
MATCH (p:Person)-[:ACTED_IN]->()
SET p:Actor;

// Add Director label to Person nodes with DIRECTED relationship
MATCH (p:Person)-[:DIRECTED]->()
SET p:Director;
```

After adding, verify:
```cypher
MATCH (n:Actor) RETURN count(n);
MATCH (n:Director) RETURN count(n);
```

## 4. Extract Nodes from String/List Property

Convert a property that holds category values into proper nodes + relationships.

### Step 1: Create constraint for new node type
```cypher
CREATE CONSTRAINT genre_name IF NOT EXISTS
FOR (g:Genre) REQUIRE g.name IS UNIQUE;
```

### Step 2: UNWIND list → MERGE nodes + relationships
```cypher
MATCH (m:Movie)
WHERE m.genres IS NOT NULL
CALL (m) {
  UNWIND m.genres AS genreName
  MERGE (g:Genre {name: genreName})
  MERGE (m)-[:IN_GENRE]->(g)
} IN TRANSACTIONS OF 10000 ROWS ON ERROR CONTINUE;
```

### Step 3: Remove the now-redundant property
```cypher
MATCH (m:Movie) WHERE m.genres IS NOT NULL
CALL (m) { REMOVE m.genres }
IN TRANSACTIONS OF 10000 ROWS ON ERROR CONTINUE;
```

### Step 4: Verify schema
```cypher
CALL db.schema.visualization();
```

## 5. String → Date/Datetime

```cypher
MATCH (p:Person)
WHERE p.born IS NOT NULL
CALL (p) {
  SET p.born = date(p.born)
} IN TRANSACTIONS OF 10000 ROWS ON ERROR CONTINUE;
```

Ensure source string is ISO format (`YYYY-MM-DD`). For other formats, transform in the SET clause:
```cypher
SET p.born = date({year: toInteger(left(p.born, 4)),
                   month: toInteger(substring(p.born, 5, 2)),
                   day: toInteger(right(p.born, 2))})
```

## 6. Validate Foreign Keys Before Creating Relationships

Detect missing referenced nodes before bulk relationship creation (prevents silent skips):

```cypher
// Check for order rows where the customer doesn't exist yet
LOAD CSV WITH HEADERS FROM 'file:///orders.csv' AS row
WITH row.customer_id AS custId
WHERE NOT EXISTS { MATCH (c:Customer {customerID: custId}) }
RETURN DISTINCT custId AS missingCustomer
LIMIT 25;
```

Any results → import missing nodes first, then create relationships.

## 7. Self-Referencing Relationship (two-pass)

Node must exist before relationship can reference it — even when both ends share a label.

```cypher
// Pass 1: Import Employee nodes (already done)

// Pass 2: Create REPORTS_TO from same file
LOAD CSV WITH HEADERS FROM 'file:///employees.csv' AS row
WHERE row.reports_to IS NOT NULL
CALL (row) {
  MATCH (e:Employee {employeeID: toIntegerOrNull(row.employee_id)})
  MATCH (m:Employee {employeeID: toIntegerOrNull(row.reports_to)})
  MERGE (e)-[:REPORTS_TO]->(m)
} IN TRANSACTIONS OF 5000 ROWS ON ERROR CONTINUE REPORT STATUS AS s;
```

## Refactoring Checklist

- [ ] `apoc.meta.nodeTypeProperties()` run — types confirmed match data model
- [ ] Delimited string properties split into lists (`split()` + `coalesce()`)
- [ ] Additional labels added (`SET n:NewLabel`) for query-targeted nodes
- [ ] Constraint created for new node type BEFORE extracting nodes
- [ ] Properties extracted to nodes via `UNWIND` + `MERGE`
- [ ] Source property removed after node extraction
- [ ] Self-referencing rels created in second pass (all nodes loaded first)
- [ ] FK validation run before any relationship creation pass
- [ ] Schema confirmed with `CALL db.schema.visualization()`
