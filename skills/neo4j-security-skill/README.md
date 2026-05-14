# neo4j-security-skill

Skill for programmatic security management in Neo4j — users, roles, privileges, and auth configuration.

**Covers:**
- **User management**: `CREATE USER`, `ALTER USER` (password, status, home database), `DROP USER`, `SHOW USERS`
- **Role management**: `CREATE ROLE`, `GRANT ROLE`, `REVOKE ROLE`, `DROP ROLE`, `SHOW ROLES`
- **Privilege grants**: GRANT/DENY/REVOKE for graph, database, and DBMS privileges
- **Property-level access control**: `GRANT READ {prop}`, `DENY READ {prop}` per label/type (Enterprise)
- **Sub-graph access control**: `FOR (n:Label) WHERE n.prop = val` pattern restrictions (Enterprise)
- **ABAC**: `CREATE AUTH RULE` with OIDC claim conditions → dynamic role assignment (Enterprise)
- **SHOW PRIVILEGES**: inspection patterns including `AS COMMANDS` for audit/export
- **Auth provider config reference**: native, LDAP, OIDC/SSO (operational config — not Cypher)

**Edition requirements:**
- Basic RBAC: Community and Enterprise
- Property-level, sub-graph, ABAC, LDAP, SSO: Enterprise only

**Not covered:**
- Writing application Cypher queries → `neo4j-cypher-skill`
- Cluster ops, backups, neo4j-admin → `neo4j-cli-tools-skill`
- Driver connection and session management → `neo4j-driver-*-skill`

**References:**
- [privilege-reference.md](references/privilege-reference.md) — full GRANT/DENY/REVOKE syntax for all privilege types

**Install:**
```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-security-skill
```

Or paste this link into your coding assistant:
https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-security-skill
