# cypher-shell Reference

Cypher REPL and scripting tool against Neo4j via Bolt protocol.

## Installation

Bundled with Neo4j in the `bin/` directory. Standalone:

```bash
brew install cypher-shell   # macOS
cypher-shell --version
```

Download: https://neo4j.com/deployment-center/

**Requires Java 21.** Network access to Neo4j Bolt port (default 7687).

## Basic Syntax

```bash
cypher-shell [OPTIONS] [cypher-statement]
```

## Connection Options

```bash
cypher-shell -a neo4j://localhost:7687 -u neo4j -p password
```

- `-a ADDRESS` / `--uri` — URI (default: `neo4j://localhost:7687`); env: `NEO4J_ADDRESS` or `NEO4J_URI`
- `-u USERNAME` — env: `NEO4J_USERNAME`
- `-p PASSWORD` — env: `NEO4J_PASSWORD`
- `-d DATABASE` — env: `NEO4J_DATABASE`
- `--encryption {true,false,default}` — `default` deduces from URI scheme
- `--impersonate IMPERSONATE` — user to impersonate
- `--access-mode {read,write}` — default: `write`

Environment variables:
```bash
export NEO4J_URI=neo4j://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=MySecurePassword
export NEO4J_DATABASE=mydb
cypher-shell
```

## Interactive Mode

```bash
cypher-shell -a neo4j://localhost:7687 -u neo4j -p password
```

**Commands:**
- `:help` — available commands
- `:exit` — exit shell
- `:param <name> => <value>` — set query parameter
- `:params` — list parameters
- `:begin` / `:commit` / `:rollback` — explicit transaction
- `:source <file>` — execute from file
- `:use <database>` — switch database
- `:access-mode read|write` — switch access mode

**History**: up/down arrows; stored in `~/.neo4j/.cypher_shell_history`

**Auto-completion** (Neo4j 5+):
```bash
cypher-shell --enable-autocompletions   # Tab triggers completions
```

**Multi-line queries:**
```cypher
neo4j@neo4j> MATCH (n:Person)
... WHERE n.age > 25
... RETURN n.name, n.age;
```

## Scripting Mode

```bash
cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n);"
cypher-shell -u neo4j -p password -f queries.cypher
cat queries.cypher | cypher-shell -u neo4j -p password
echo "MATCH (n:Person) RETURN n.name LIMIT 5;" | cypher-shell -u neo4j -p password
```

**Error handling:**
```bash
cypher-shell -f script.cypher --fail-fast      # exit on first error (default)
cypher-shell -f script.cypher --fail-at-end    # continue; report all errors at end
```

## Output Formats

- `--format auto` — tabular in interactive, plain in scripting (default)
- `--format verbose` — tabular with statistics
- `--format plain` — minimal formatting

```bash
cypher-shell --format verbose -u neo4j -p password "MATCH (n) RETURN n LIMIT 3;"
cypher-shell --format plain -u neo4j -p password "MATCH (n:Person) RETURN n.name;"
```

Options (verbose only):
- `--sample-rows SAMPLE-ROWS` — rows sampled for table width (default: 1000)
- `--wrap {true,false}` — wrap column values (default: true)

## Parameters

```bash
cypher-shell -P '{name: "Alice", minAge: 25}'
cypher-shell -P '{name: "Alice"}' -P '{minAge: 25}'
cypher-shell -P '{duration: duration({seconds: 3600})}'
```

Interactive:
```cypher
neo4j@neo4j> :param name => "Alice"
neo4j@neo4j> :param minAge => 25
neo4j@neo4j> :params
```

## Transaction Management

Each statement executes in its own transaction by default.

Explicit transactions (interactive):
```cypher
neo4j@neo4j> :begin
neo4j@neo4j# CREATE (n:Person {name: "Alice"});
neo4j@neo4j# CREATE (m:Person {name: "Bob"});
neo4j@neo4j# :commit
```

## Advanced Options

```bash
cypher-shell --log /var/log/cypher-shell.log   # log to file
cypher-shell --log                              # log to stderr
cypher-shell --change-password                 # prompts for current + new passwords
cypher-shell --notifications                   # enable procedure/query notifications
cypher-shell --idle-timeout 30m               # auto-close after inactivity (format: 1h30m)
cypher-shell --error-format {gql,legacy,stacktrace}
cypher-shell --non-interactive -f script.cypher  # force non-interactive (Windows)
```

## Common Use Cases

```bash
# Database exploration
cypher-shell -u neo4j -p password "CALL db.labels();"
cypher-shell -u neo4j -p password "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count;"
cypher-shell -u neo4j -p password "CALL db.schema.visualization();"

# Export to CSV-like format
cypher-shell --format plain -u neo4j -p password \
  "MATCH (p:Person) RETURN p.name, p.age;" > people.csv

# CI/CD connectivity check
if cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1;" > /dev/null 2>&1; then
  exit 0
else
  exit 1
fi

# Parameterized query
cypher-shell -P '{minAge: 30}' \
  "MATCH (p:Person) WHERE p.age >= \$minAge RETURN p.name, p.age;"

# Read-only mode
cypher-shell --access-mode read -u neo4j -p password
```

## Keyboard Shortcuts

- `Ctrl+A/E` — beginning/end of line
- `Ctrl+U/K` — clear line / delete to end
- `Ctrl+C` — cancel query
- `Up/Down` — history navigation
- `Ctrl+R` — reverse search
- `Tab` — auto-completion (if enabled)

## Environment Variables

- `NEO4J_URI` / `NEO4J_ADDRESS`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
- `NEO4J_CYPHER_SHELL_HISTORY` — history file path

## Troubleshooting

**Java version error**: install Java 21 (`brew install openjdk@21`), set `JAVA_HOME`.

**Connection refused** (`Unable to connect to localhost:7687`): check Neo4j is running (`neo4j status`), Bolt port is correct, firewall allows connection.

**Authentication failed**: reset with `neo4j-admin dbms set-initial-password newpassword`

**SSL/TLS errors**: `cypher-shell --encryption false -a neo4j://localhost:7687` for local dev.

## Best Practices

- Use environment variables for credentials in scripts
- Enable auto-completion for interactive work (Neo4j 5+)
- Use parameters — prevents Cypher injection
- Use explicit transactions for multi-statement operations
- Use `--fail-at-end` for data migration scripts
- Use `--log` for error logging in production scripts

## Additional Resources

- [Cypher Shell Documentation](https://neo4j.com/docs/operations-manual/current/cypher-shell/)
- [Neo4j Deployment Center](https://neo4j.com/deployment-center/)
