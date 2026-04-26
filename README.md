# Neo4j Agent Skills

A collection of [Agent Skills](https://agentskills.io/specification) designed to help AI agents work effectively with Neo4j graph databases.

## Installation

### Using npx skills (Recommended)

```bash
# Install all Neo4j skills
npx skills add neo4j-contrib/neo4j-skills

# Or install individual skills
npx skills add neo4j-contrib/neo4j-skills/neo4j-cypher-skill
npx skills add neo4j-contrib/neo4j-skills/neo4j-migration-skill
npx skills add neo4j-contrib/neo4j-skills/neo4j-cli-tools-skill
npx skills add neo4j-contrib/neo4j-skills/neo4j-getting-started-skill
```

The skills package will automatically detect your AI agent (Claude Code, Cursor, Cline, etc.) and install the skills in the appropriate location.

### Manual Installation

#### For Claude Code:
```bash
git clone https://github.com/neo4j-contrib/neo4j-skills.git

ln -s $(pwd)/neo4j-skills/neo4j-cypher-skill ~/.claude/skills/
ln -s $(pwd)/neo4j-skills/neo4j-migration-skill ~/.claude/skills/
ln -s $(pwd)/neo4j-skills/neo4j-cli-tools-skill ~/.claude/skills/
ln -s $(pwd)/neo4j-skills/neo4j-getting-started-skill ~/.claude/skills/
```

#### For other agents:
Point your AI agent to this repository or add the skill directories to your agent's skills path. Most agents support the [Agent Skills specification](https://agentskills.io/specification).

## Available Skills

### neo4j-cypher-skill

Generates, optimizes, and validates Cypher 25 queries for Neo4j 2025.x and 2026.x.

**Use this skill when:**
- Writing or optimizing Cypher queries (reads, writes, subqueries, batch, LOAD CSV)
- Using vector/fulltext search, quantified path patterns, or `CALL IN TRANSACTIONS`
- Reviewing EXPLAIN/PROFILE plans or recovering from query errors

Includes schema-first inspection, parameterized output, 50+ anti-pattern checks, and version gates for 2026.x features. Requires Neo4j >= 2025.01.

### neo4j-getting-started-skill

Guides an agent from zero to a running Neo4j application across 8 stages: prerequisites → provision → model → load → explore → query → build. Works interactively or fully autonomously.

**Use this skill when:** starting a new Neo4j project, provisioning Aura or Docker, or building an end-to-end graph application.

### neo4j-cli-tools-skill

Guidance for Neo4j CLI tools: neo4j-admin, cypher-shell, aura-cli, and neo4j-mcp.

**Use this skill when:** configuring databases via command line, running admin tasks, managing Aura instances, or setting up the Neo4j MCP server.

### neo4j-migration-skill

Assists with upgrading Neo4j drivers (.NET, Go, Java, JavaScript, Python) to new major versions.

## What are Agent Skills?

Agent Skills are a standardized format for providing AI agents with domain-specific knowledge and capabilities. They enable agents to perform specialized tasks more effectively by bundling:

- **Instructions** - Step-by-step guidance for accomplishing specific tasks
- **References** - Detailed documentation that agents can access when needed
- **Scripts** - Executable code for automation

Skills follow a progressive disclosure pattern, loading only what's needed to minimize context usage while maximizing effectiveness. For the complete specification, visit [agentskills.io/specification](https://agentskills.io/specification).

## Contributing

Contributions are welcome! Please feel free to submit pull requests with new skills or improvements to existing ones.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
