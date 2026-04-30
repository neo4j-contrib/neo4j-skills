# neo4j-admin Reference

CLI for Neo4j database administration. Installed with Neo4j in `bin/`.

```bash
neo4j-admin --version
neo4j-admin [OPTIONS] [COMMAND]
```

**Global options**: `--help`, `--version`, `--verbose`, `--expand-commands`

## Command Categories

### DBMS Commands (`dbms`)

```bash
# Set default admin when no roles exist
neo4j-admin dbms set-default-admin <username>

# Set initial password for the neo4j user
neo4j-admin dbms set-initial-password MySecureP@ssw0rd

# Remove cluster state to enable rebinding
neo4j-admin dbms unbind-system-db
```

### Server Commands (`server`)

```bash
# Memory recommendations based on system resources
neo4j-admin server memory-recommendation
# Output: server.memory.heap.initial_size, max_size, pagecache.size

# Generate diagnostic archive for support
neo4j-admin server report [--to=<path>] [--list] [--filter=<classifier>]

# Accept license
neo4j-admin server license --accept-commercial
neo4j-admin server license --accept-evaluation
```

### Database Commands (`database`)

```bash
# Backup
neo4j-admin database backup <database-name> --to-path=<backup-directory>
neo4j-admin database backup neo4j --to-path=/backups/$(date +%Y%m%d)
# Options: --type=full|differential, --keep-failed, --verbose

# Restore (database must be stopped first)
neo4j-admin database restore <database-name> --from-path=<backup-directory>
neo4j-admin database restore neo4j --from-path=/backups/20260216

# Dump
neo4j-admin database dump <database-name> --to-path=<dump-file>
neo4j-admin database dump mydb --to-path=/exports/mydb.dump

# Load
neo4j-admin database load <database-name> --from-path=<dump-file>
neo4j-admin database load newdb --from-path=/exports/mydb.dump --overwrite-destination=true

# CSV import into new database
neo4j-admin database import \
  --nodes=Person=persons.csv \
  --relationships=KNOWS=knows.csv \
  --database=socialnetwork \
  --delimiter=","
# Options: --nodes=<Label>=<file>, --relationships=<TYPE>=<file>,
#          --delimiter, --array-delimiter, --skip-duplicate-nodes, --skip-bad-relationships

# Consistency check
neo4j-admin database check <database-name> [--report-dir=<path>] [--verbose]
neo4j-admin database check neo4j --verbose

# Copy
neo4j-admin database copy production staging

# Migrate to current Neo4j version format
neo4j-admin database migrate <database-name>
neo4j-admin database migrate legacydb --force-btree-indexes-to-range
```

## Configuration

**Priority** (highest to lowest): `--additional-config` flag → command-specific config → `neo4j-admin.conf` → `neo4j.conf`

```bash
# Pass additional config via file
neo4j-admin database backup mydb --to-path=/backups @/path/to/options.conf
```

**Environment variables:**
- `NEO4J_CONF` — path to conf directory
- `NEO4J_DEBUG` — enable debug output
- `NEO4J_HOME` — installation directory
- `HEAP_SIZE` — JVM max heap (e.g. `4g`)
- `JAVA_OPTS` — custom JVM settings (overrides HEAP_SIZE)

## Common Workflows

```bash
# Initial setup
neo4j-admin dbms set-initial-password MySecurePassword
neo4j-admin server memory-recommendation

# Backup and restore
neo4j-admin database backup neo4j --to-path=/backups/full
neo4j-admin database backup neo4j --to-path=/backups/diff --type=differential
neo4j stop
neo4j-admin database restore neo4j --from-path=/backups/full
neo4j start

# Data migration
neo4j-admin database dump production --to-path=/exports/prod.dump
neo4j-admin database load production-copy --from-path=/exports/prod.dump
neo4j-admin database check production-copy

# CSV import
neo4j-admin database import \
  --nodes=User=users.csv \
  --nodes=Product=products.csv \
  --relationships=PURCHASED=purchases.csv \
  --database=ecommerce \
  --skip-bad-relationships
```

## Exit Codes

- `0` — success
- Non-zero — error

## Best Practices

- Run as the system user that owns the Neo4j installation
- Stop DB before restore operations
- Verify backups with `check` command
- Use absolute paths for backup/dump locations
- Test migration and import in development first
- Use `--verbose` for debugging progress

## Troubleshooting

```bash
# Permission denied — run as neo4j user
sudo -u neo4j neo4j-admin database backup mydb --to-path=/backups

# Stop DB before restore
neo4j stop
neo4j-admin database restore mydb --from-path=/backup
neo4j start

# Increase heap for large imports
HEAP_SIZE=4g neo4j-admin database import --nodes=large.csv --database=bigdb

# Config not found
NEO4J_CONF=/path/to/conf neo4j-admin database backup mydb --to-path=/backup
```

## Resources

- [neo4j-admin documentation](https://neo4j.com/docs/operations-manual/current/neo4j-admin-neo4j-cli/)
- [Database Backup Documentation](https://neo4j.com/docs/operations-manual/current/backup-restore/)
