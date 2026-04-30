---
name: neo4j-security-skill
description: Programmatic security management in Neo4j — RBAC/ABAC, user lifecycle (CREATE/ALTER/DROP USER),
  role lifecycle (CREATE/GRANT ROLE/DROP ROLE), privilege grants and denies (GRANT/DENY/REVOKE on graph,
  database, DBMS), property-level access control, sub-graph access control, SHOW PRIVILEGES inspection,
  and auth provider config reference (LDAP, OIDC/SSO). Use when an agent needs to manage users, roles,
  or privileges programmatically via Cypher on the system database. Does NOT handle Cypher query writing
  — use neo4j-cypher-skill. Does NOT handle cluster ops or backups — use neo4j-cli-tools-skill.
  Property-level security and ABAC require Enterprise Edition.
allowed-tools: Bash WebFetch
version: 1.0.0
---

## When to Use
- Creating, altering, suspending, or dropping users
- Creating roles, granting/revoking role membership
- Granting/denying/revoking graph, database, or DBMS privileges
- Inspecting current privileges (`SHOW PRIVILEGES`)
- Implementing property-level access control (read/write per property)
- Setting up ABAC rules against OIDC claims
- Referencing LDAP/SSO auth provider configuration

## When NOT to Use
- **Writing Cypher queries against application data** → `neo4j-cypher-skill`
- **Cluster ops, backups, server config** → `neo4j-cli-tools-skill`
- **Driver connection setup** → `neo4j-driver-*-skill`

---

## MCP Write Gate — MANDATORY

Before executing ANY of the following, show the planned command and wait for explicit confirmation:
- `CREATE USER` / `ALTER USER` / `DROP USER`
- `CREATE ROLE` / `DROP ROLE`
- `GRANT` / `DENY` / `REVOKE` (any privilege)
- `CREATE AUTH RULE` / `DROP AUTH RULE`

Never auto-execute privilege changes. Show exact Cypher, annotate impact, get "yes".

---

## Execution Context

All security Cypher runs against the **system** database:
```cypher
// Neo4j auto-routes CREATE/ALTER/SHOW USER|ROLE|PRIVILEGE to system
// If using cypher-shell: cypher-shell -d system
// If using driver: use database="system"
```

---

## 1. User Management

### Create user
```cypher
CREATE USER alice SET PASSWORD 'secret' CHANGE NOT REQUIRED;
// CHANGE REQUIRED (default): forces password change on first login
// CHANGE NOT REQUIRED: password valid immediately
// SET STATUS ACTIVE (default) | SUSPENDED
```

### Parameterised password (preferred in scripts)
```cypher
CREATE USER $username SET PASSWORD $password CHANGE NOT REQUIRED;
```

### Alter user
```cypher
ALTER USER alice SET PASSWORD $newPw CHANGE NOT REQUIRED;
ALTER USER alice SET STATUS SUSPENDED;          -- lock account
ALTER USER alice SET STATUS ACTIVE;             -- unlock
ALTER USER alice SET HOME DATABASE mydb;        -- default db on connect
ALTER USER alice IF EXISTS SET PASSWORD $pw;    -- safe if missing
```

### Show users
```cypher
SHOW USERS YIELD username, roles, passwordChangeRequired, suspended, homeDatabase
WHERE suspended = false
RETURN username, roles ORDER BY username;
```

### Drop user
```cypher
DROP USER alice IF EXISTS;
```

---

## 2. Role Management

### Create / drop role
```cypher
CREATE ROLE analyst;
CREATE ROLE analyst IF NOT EXISTS;
DROP ROLE analyst IF EXISTS;
```

### Assign / remove roles
```cypher
GRANT ROLE analyst TO alice;
GRANT ROLE analyst, writer TO alice, bob;   -- bulk
REVOKE ROLE analyst FROM alice;
```

### Inspect roles
```cypher
SHOW ROLES YIELD role, member ORDER BY role;
SHOW ROLE analyst PRIVILEGES AS COMMANDS;   -- returns runnable GRANT commands
SHOW POPULATED ROLES YIELD role;            -- only roles with members
```

---

## 3. Privilege Decision Table

| Goal | Command |
|---|---|
| Allow db connection | `GRANT ACCESS ON DATABASE mydb TO analyst` |
| Read all graph data | `GRANT MATCH {*} ON GRAPH mydb ELEMENTS * TO analyst` |
| Read specific label | `GRANT MATCH {*} ON GRAPH mydb NODES Person TO analyst` |
| Read specific rel type | `GRANT MATCH {*} ON GRAPH mydb RELATIONSHIPS KNOWS TO analyst` |
| Read one property | `GRANT READ {email} ON GRAPH mydb NODES Person TO analyst` |
| Traverse but hide properties | `GRANT TRAVERSE ON GRAPH mydb NODES Person TO analyst` |
| Write (create/set) | `GRANT WRITE ON GRAPH mydb TO writer` |
| Create nodes only | `GRANT CREATE ON GRAPH mydb NODES Person TO writer` |
| Delete nodes only | `GRANT DELETE ON GRAPH mydb NODES Person TO writer` |
| Execute procedure | `GRANT EXECUTE PROCEDURE apoc.* TO analyst` |
| Execute function | `GRANT EXECUTE USER DEFINED FUNCTION apoc.* TO analyst` |
| All on one db | `GRANT ALL ON DATABASE mydb TO dba` |
| Full DBMS admin | `GRANT ALL ON DBMS TO dba` |
| Manage users | `GRANT USER MANAGEMENT ON DBMS TO secadmin` |
| Manage roles | `GRANT ROLE MANAGEMENT ON DBMS TO secadmin` |
| Schema changes | `GRANT CREATE ELEMENT TYPES ON DATABASE mydb TO schemaadmin` |

### DENY overrides GRANT
```cypher
// Analyst can read Person but NOT the ssn property
GRANT MATCH {*} ON GRAPH mydb NODES Person TO analyst;
DENY  READ {ssn} ON GRAPH mydb NODES Person TO analyst;
```

### REVOKE removes a specific grant or deny
```cypher
REVOKE GRANT READ {email} ON GRAPH mydb NODES Person FROM analyst;
REVOKE DENY  READ {ssn}   ON GRAPH mydb NODES Person FROM analyst;
REVOKE MATCH {*} ON GRAPH mydb NODES Person FROM analyst;  -- removes both grant+deny
```

---

## 4. Common Role Patterns

### Read-only analyst
```cypher
CREATE ROLE analyst IF NOT EXISTS;
GRANT ACCESS            ON DATABASE mydb TO analyst;
GRANT MATCH {*}         ON GRAPH mydb ELEMENTS * TO analyst;
GRANT EXECUTE PROCEDURE apoc.* TO analyst;
```

### Write role (no admin)
```cypher
CREATE ROLE writer IF NOT EXISTS;
GRANT ACCESS  ON DATABASE mydb TO writer;
GRANT MATCH {*} ON GRAPH mydb ELEMENTS * TO writer;
GRANT WRITE   ON GRAPH mydb TO writer;
```

### Read-only on specific labels only
```cypher
CREATE ROLE limited_reader IF NOT EXISTS;
GRANT ACCESS    ON DATABASE mydb TO limited_reader;
GRANT TRAVERSE  ON GRAPH mydb ELEMENTS * TO limited_reader;      -- can traverse
GRANT MATCH {*} ON GRAPH mydb NODES Person TO limited_reader;    -- Person props visible
GRANT MATCH {*} ON GRAPH mydb NODES Company TO limited_reader;   -- Company props visible
// Other labels: traversable but properties invisible
```

### DBA role (full admin)
```cypher
CREATE ROLE dba IF NOT EXISTS;
GRANT ALL ON DBMS     TO dba;
GRANT ALL ON DATABASE * TO dba;
```

---

## 5. Property-Level Access Control (Enterprise)

Restrict read access to individual properties:
```cypher
// Grant read on all Person props, then deny sensitive ones
GRANT MATCH {*}   ON GRAPH mydb NODES Person TO analyst;
DENY  READ {ssn, dateOfBirth} ON GRAPH mydb NODES Person TO analyst;
```

Property-based pattern matching (sub-graph access):
```cypher
// Only see Person nodes where classification = 'public'
GRANT MATCH {*} ON GRAPH mydb
  FOR (n:Person) WHERE n.classification = 'public'
  TO analyst;

// Block access to classified nodes
DENY MATCH {*} ON GRAPH mydb
  FOR (n) WHERE n.classification <> 'UNCLASSIFIED'
  TO regularUsers;
```

**Constraints:**
- `FOR` pattern applies to read privileges only — not write
- Each property-based privilege restricted by a single property
- Performance overhead scales with number of rules; `TRAVERSE` rules cost more than `READ`
- Ensure the property used for rules cannot be modified by the restricted role

---

## 6. ABAC — Attribute-Based Access Control (Enterprise + OIDC)

ABAC grants roles dynamically from JWT/OIDC claims rather than explicit `GRANT ROLE ... TO user`.

### Prerequisites
```
# neo4j.conf
dbms.security.abac.authorization_providers=<oidc-provider-alias>
```

### Create auth rule
```cypher
CREATE AUTH RULE salesRule
  SET CONDITION abac.oidc.user_attribute('department') = 'sales';

GRANT ROLE analyst TO AUTH RULE salesRule;
```

### Compound conditions
```cypher
CREATE OR REPLACE AUTH RULE seniorRule
  SET CONDITION abac.oidc.user_attribute('department') = 'engineering'
    AND abac.oidc.user_attribute('level') >= 5;

GRANT ROLE senior_engineer TO AUTH RULE seniorRule;
```

### Manage auth rules
```cypher
SHOW AUTH RULES YIELD ruleName, condition, roles;
ALTER AUTH RULE salesRule SET ENABLED false;     -- disable without dropping
RENAME AUTH RULE salesRule TO salesDeptRule;
DROP AUTH RULE salesDeptRule;
REVOKE ROLE analyst FROM AUTH RULE salesRule;
```

**Notes:**
- Missing claims evaluate to NULL → rule condition false → role not granted
- Rules apply immediately to existing sessions when claims are already loaded
- ABAC works only with OIDC providers (not native or LDAP)

---

## 7. SHOW PRIVILEGES Patterns

```cypher
// All privileges in the system
SHOW PRIVILEGES YIELD *;

// Privileges for a specific user (as runnable commands)
SHOW USER alice PRIVILEGES AS COMMANDS;

// Privileges for a specific role
SHOW ROLE analyst PRIVILEGES YIELD privilege, action, resource, graph, segment;

// Find who has access to a database
SHOW PRIVILEGES YIELD *
WHERE graph = 'mydb'
RETURN role, action, resource, segment ORDER BY role;

// Find all DENY rules
SHOW PRIVILEGES YIELD *
WHERE access = 'DENIED'
RETURN role, action, resource, segment;
```

---

## 8. Built-in Roles (do not drop)

| Role | Scope |
|---|---|
| `admin` | Full DBMS + all databases |
| `architect` | Schema changes + write on all databases |
| `publisher` | Write on all databases |
| `editor` | Write excluding schema changes |
| `reader` | Read-only on all databases |
| `public` | All users implicitly; default home database access |

Assign built-in roles: `GRANT ROLE reader TO alice;`

---

## 9. Auth Provider Config Reference (operational — not Cypher)

### Native (default)
```
dbms.security.auth_enabled=true
dbms.security.auth_max_failed_attempts=3    # lockout threshold
```

### LDAP
```
dbms.security.auth_provider=ldap
dbms.security.ldap.host=ldap://ldap.example.com
dbms.security.ldap.authentication.mechanism=simple
dbms.security.ldap.authentication.user_dn_template=uid={0},ou=users,dc=example,dc=com
dbms.security.ldap.authorization.group_membership_attributes=memberOf
dbms.security.ldap.authorization.group_to_role_mapping=\
  "cn=analysts,ou=groups,dc=example,dc=com" = analyst;\
  "cn=admins,ou=groups,dc=example,dc=com"   = admin
```

### OIDC / SSO (Okta, Auth0, Entra ID)
```
dbms.security.oidc.<alias>.display_name=Okta
dbms.security.oidc.<alias>.auth_flow=pkce
dbms.security.oidc.<alias>.well_known_discovery_uri=https://example.okta.com/.well-known/openid-configuration
dbms.security.oidc.<alias>.audience=neo4j
dbms.security.oidc.<alias>.claims.username=email
dbms.security.oidc.<alias>.claims.groups=groups
dbms.security.oidc.<alias>.authorization.group_to_role_mapping=\
  "neo4j-analysts" = analyst;\
  "neo4j-admins"   = admin
```

Config changes require **server restart**. Roles referenced in mappings must exist in Neo4j (native or created via Cypher).

---

## Checklist — New Role Setup

- [ ] Determine required operations: read / write / admin
- [ ] Identify target database(s) and graph scope (all labels vs specific)
- [ ] Identify any properties that must be hidden (→ DENY READ)
- [ ] Create role: `CREATE ROLE ... IF NOT EXISTS`
- [ ] Grant ACCESS on database
- [ ] Grant MATCH / TRAVERSE / WRITE as needed
- [ ] Apply DENY for restricted properties
- [ ] Run `SHOW ROLE ... PRIVILEGES AS COMMANDS` to verify
- [ ] Assign to users: `GRANT ROLE ... TO ...`
- [ ] Test with `SHOW USER ... PRIVILEGES AS COMMANDS`

Full privilege syntax → [references/privilege-reference.md](references/privilege-reference.md)
