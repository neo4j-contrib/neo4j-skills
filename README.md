# Neo4j Agent Skills

A collection of [Agent Skills](https://agentskills.io/specification) designed to help AI agents work effectively with Neo4j graph databases.

## What are Agent Skills?

Agent Skills are a standardized format for providing AI agents with domain-specific knowledge and capabilities. They enable agents to perform specialized tasks more effectively by bundling:

- **Instructions** - Step-by-step guidance for accomplishing specific tasks
- **References** - Detailed documentation that agents can access when needed
- **Scripts** - Executable code for automation

Skills follow a progressive disclosure pattern, loading only what's needed to minimize context usage while maximizing effectiveness. For the complete specification, visit [agentskills.io/specification](https://agentskills.io/specification).

## Available Skills

### neo4j-cli-tools-skill

Comprehensive guidance for Neo4j command-line tools including neo4j-admin, cypher-shell, aura-cli, and neo4j-mcp.

**Use this skill when:**
- Setting up or configuring Neo4j databases via command line
- Running administrative tasks with neo4j-admin
- Executing Cypher queries from the command line
- Managing Neo4j Aura cloud instances
- Setting up the Neo4j MCP server for AI agents
- Troubleshooting Neo4j CLI tool issues

### neo4j-migration-skill

Assists with upgrading Neo4j drivers to new major versions.

**Use this skill when:**
- Upgrading Neo4j drivers (.NET, Go, Java, JavaScript, Python)

### neo4j-cypher-skill

Assists with upgrading Cypher queries to newer Neo4j versions.

**Use this skill when:**
- Migrating databases from Neo4j 4.x or 5.x to 2025.x or 2026.x
- Updating Cypher queries to a newer major Neo4j version

## Installation

### Using npx skills (Recommended)

The easiest way to install these skills is using the skills package:

```bash
# Install all Neo4j skills
npx skills add neo4j-contrib/neo4j-skills

# Or install individual skills
npx skills add neo4j-contrib/neo4j-skills/neo4j-cypher-skill
npx skills add neo4j-contrib/neo4j-skills/neo4j-migration-skill
npx skills add neo4j-contrib/neo4j-skills/neo4j-cli-tools-skill
```

The skills package will automatically detect your AI agent (Claude Code, Cursor, Cline, etc.) and install the skills in the appropriate location.

### Manual Installation

#### For Claude Code:
```bash
# Clone the repository
git clone https://github.com/neo4j-contrib/neo4j-skills.git

# Symlink or copy skills to Claude's skills directory
ln -s $(pwd)/neo4j-skills/neo4j-cypher-skill ~/.claude/skills/
ln -s $(pwd)/neo4j-skills/neo4j-migration-skill ~/.claude/skills/
ln -s $(pwd)/neo4j-skills/neo4j-cli-tools-skill ~/.claude/skills/
```

#### For other agents:
Point your AI agent to this repository or add the skill directories to your agent's skills path. Most agents support the [Agent Skills specification](https://agentskills.io/specification).

## Usage

Once installed, the skills are automatically available to your AI agent. Simply describe your Neo4j-related task, and the agent will activate the appropriate skill when needed.

## Resources

- [Using Claude Skills with Neo4j](https://towardsdatascience.com/using-claude-skills-with-neo4j/) - Learn how to leverage AI skills for Neo4j graph database operations

## Contributing

Contributions are welcome! Please feel free to submit pull requests with new skills or improvements to existing ones.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
