# Neo4j Privilege Reference

Full GRANT / DENY / REVOKE syntax for all privilege types.
All commands execute against the **system** database.

---

## General Syntax

```
{GRANT | DENY} [IMMUTABLE] <privilege>
  ON { GRAPH[S] {* | name[,...]} | DATABASE[S] {* | name[,...]} | HOME GRAPH | DBMS }
  [<entity>]
  TO <role>[,...]

REVOKE [IMMUTABLE] [GRANT | DENY] <privilege>
  ON { GRAPH[S] ... | DATABASE[S] ... | DBMS }
  [<entity>]
  FROM <role>[,...]
```

`IMMUTABLE` — privilege cannot be revoked by non-admin users; only `admin` can remove.

---

## Graph Privileges

### Entity scope

| Entity | Meaning |
|---|---|
| `NODES Label` | Nodes with label (can list: `NODES Person, Company`) |
| `RELATIONSHIPS Type` | Relationships of type |
| `ELEMENTS Label` | Both nodes and relationships |
| `FOR (n:Label) WHERE n.prop = val` | Pattern-matched nodes (read only) |
| *(omit)* | Defaults to `ELEMENTS *` |

### Read privileges

```cypher
GRANT TRAVERSE  ON GRAPH mydb NODES Person TO role;          -- can see node, not properties
GRANT READ {*}  ON GRAPH mydb NODES Person TO role;          -- read all properties
GRANT READ {name, email} ON GRAPH mydb NODES Person TO role; -- read specific properties
GRANT MATCH {*} ON GRAPH mydb NODES Person TO role;          -- TRAVERSE + READ combined
GRANT MATCH {*} ON GRAPH mydb ELEMENTS * TO role;            -- all nodes + rels
```

### Write privileges

```cypher
GRANT WRITE     ON GRAPH mydb TO role;              -- all writes (shorthand)
GRANT CREATE    ON GRAPH mydb NODES Person TO role; -- create Person nodes
GRANT SET PROPERTY {name} ON GRAPH mydb NODES Person TO role;
GRANT MERGE     ON GRAPH mydb NODES Person TO role; -- MERGE statement
GRANT DELETE    ON GRAPH mydb NODES Person TO role;
GRANT SET LABEL Person ON GRAPH mydb TO role;
GRANT REMOVE LABEL Person ON GRAPH mydb TO role;
GRANT CREATE    ON GRAPH mydb RELATIONSHIPS KNOWS TO role;
GRANT DELETE    ON GRAPH mydb RELATIONSHIPS KNOWS TO role;
```

### Property-based (sub-graph) read

```cypher
-- Pattern in FOR clause must have exactly one property condition
GRANT MATCH {*} ON GRAPH mydb
  FOR (n:Document) WHERE n.visibility = 'public'
  TO reader;

DENY MATCH {*} ON GRAPH mydb
  FOR (n) WHERE n.classification <> 'UNCLASSIFIED'
  TO regularUsers;

GRANT READ { address } ON GRAPH *
  FOR (n:Email|Website) WHERE n.domain = 'example.com'
  TO regularUsers;
```

---

## Database Privileges

```cypher
GRANT ACCESS          ON DATABASE mydb TO role;   -- required for any db connection
GRANT START           ON DATABASE mydb TO role;
GRANT STOP            ON DATABASE mydb TO role;
GRANT CREATE INDEX    ON DATABASE mydb TO role;
GRANT DROP INDEX      ON DATABASE mydb TO role;
GRANT SHOW INDEX      ON DATABASE mydb TO role;
GRANT INDEX           ON DATABASE mydb TO role;   -- CREATE + DROP + SHOW INDEX
GRANT CREATE CONSTRAINT ON DATABASE mydb TO role;
GRANT DROP CONSTRAINT   ON DATABASE mydb TO role;
GRANT SHOW CONSTRAINT   ON DATABASE mydb TO role;
GRANT CONSTRAINT        ON DATABASE mydb TO role; -- CREATE + DROP + SHOW CONSTRAINT
GRANT CREATE NEW ELEMENT TYPES ON DATABASE mydb TO role;  -- new labels/types/props
GRANT NAME MANAGEMENT   ON DATABASE mydb TO role; -- all element type management
GRANT ALL ON DATABASE mydb TO role;               -- all database privileges
GRANT ALL ON DATABASE * TO role;                  -- all databases
```

---

## DBMS Privileges

```cypher
-- User management
GRANT SHOW USER     ON DBMS TO role;
GRANT CREATE USER   ON DBMS TO role;
GRANT SET USER STATUS ON DBMS TO role;
GRANT SET PASSWORDS ON DBMS TO role;
GRANT ALTER USER    ON DBMS TO role;
GRANT DROP USER     ON DBMS TO role;
GRANT USER MANAGEMENT ON DBMS TO role;   -- all user management

-- Role management
GRANT SHOW ROLE     ON DBMS TO role;
GRANT CREATE ROLE   ON DBMS TO role;
GRANT RENAME ROLE   ON DBMS TO role;
GRANT DROP ROLE     ON DBMS TO role;
GRANT ASSIGN ROLE   ON DBMS TO role;     -- GRANT ROLE ... TO user
GRANT REMOVE ROLE   ON DBMS TO role;     -- REVOKE ROLE ... FROM user
GRANT ROLE MANAGEMENT ON DBMS TO role;  -- all role management

-- Privilege management
GRANT SHOW PRIVILEGE  ON DBMS TO role;
GRANT ASSIGN PRIVILEGE ON DBMS TO role;
GRANT REMOVE PRIVILEGE ON DBMS TO role;
GRANT PRIVILEGE MANAGEMENT ON DBMS TO role; -- all privilege management

-- Database management
GRANT CREATE DATABASE ON DBMS TO role;
GRANT DROP DATABASE   ON DBMS TO role;
GRANT ALTER DATABASE  ON DBMS TO role;
GRANT SET DATABASE ACCESS ON DBMS TO role;
GRANT DATABASE MANAGEMENT ON DBMS TO role; -- all database management

-- Procedure / function execution
GRANT EXECUTE PROCEDURE apoc.* TO role;
GRANT EXECUTE BOOSTED PROCEDURE apoc.* TO role;  -- elevated mode
GRANT EXECUTE USER DEFINED FUNCTION apoc.* TO role;
GRANT EXECUTE BOOSTED USER DEFINED FUNCTION apoc.* TO role;

-- Full DBMS admin
GRANT ALL ON DBMS TO role;
```

---

## REVOKE Variants

```cypher
-- Remove a GRANT
REVOKE GRANT MATCH {*} ON GRAPH mydb NODES Person FROM analyst;

-- Remove a DENY
REVOKE DENY READ {ssn} ON GRAPH mydb NODES Person FROM analyst;

-- Remove both GRANT and DENY at once
REVOKE MATCH {*} ON GRAPH mydb NODES Person FROM analyst;
```

In Cypher 25, REVOKE on a non-existent privilege raises an **error** (was a notification in earlier versions).

---

## SHOW PRIVILEGE Commands

```cypher
SHOW PRIVILEGES YIELD *;
SHOW PRIVILEGES YIELD * WHERE access = 'DENIED';
SHOW PRIVILEGES YIELD * WHERE graph = 'mydb' ORDER BY role;

SHOW USER alice PRIVILEGES;
SHOW USER alice PRIVILEGES AS COMMANDS;       -- returns runnable GRANT statements

SHOW ROLE analyst PRIVILEGES;
SHOW ROLE analyst PRIVILEGES AS COMMANDS;

SHOW ROLE analyst PRIVILEGES YIELD privilege, action, resource, graph, segment
WHERE action = 'read';
```

---

## Access Decision Rules

1. `DENY` always overrides `GRANT` — a user with both gets the DENY.
2. Roles are additive — user inherits union of all assigned role privileges, minus any DENY.
3. Missing `ACCESS ON DATABASE` = connection refused regardless of graph privileges.
4. Read restriction makes data **invisible** (not an error); write restriction returns an error.
5. `FOR` pattern restrictions apply at query time — every node match is filtered against the condition.

---

## Edition Notes

| Feature | Community | Enterprise |
|---|---|---|
| RBAC (users/roles/privileges) | Basic | Full |
| Sub-graph / label-based access | No | Yes |
| Property-level READ/DENY | No | Yes |
| Property-based pattern (`FOR`) | No | Yes |
| ABAC / `CREATE AUTH RULE` | No | Yes |
| LDAP integration | No | Yes |
| OIDC/SSO | No | Yes |
| `IMMUTABLE` privileges | No | Yes |
