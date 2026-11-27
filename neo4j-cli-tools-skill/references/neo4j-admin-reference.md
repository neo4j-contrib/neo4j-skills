# neo4j-admin Reference

`neo4j-admin` is installed automatically with Neo4j in the `bin/` directory.

**Edition:** `database backup`, `database restore`, `database copy`, `backup inspect/aggregate`, `server license`, `dbms unbind-system-db` and `server unbind` are Enterprise only. Community has `database check/dump/import/info/load/migrate/upload` and `dbms set-default-admin/set-initial-password`.

```bash
neo4j-admin --version
```

## Basic Syntax

```bash
neo4j-admin [OPTIONS] [COMMAND]
```

**Global Options**:
- `--help`, `-h` - Show help message
- `--version`, `-V` - Print version information
- `--verbose` - Print additional information
- `--expand-commands` - Allow command expansion in config value evaluation

## Command Categories

### dbms

#### set-default-admin

```bash
neo4j-admin dbms set-default-admin <username>
```

#### set-initial-password

Takes effect only if run before the database is started for the first time.

```bash
neo4j-admin dbms set-initial-password <password>
```

```bash
neo4j-admin dbms set-initial-password MySecureP@ssw0rd
```

#### unbind-system-db

Enterprise only. Removes cluster state to enable rebinding to a different cluster.

```bash
neo4j-admin dbms unbind-system-db
```

### server

#### memory-recommendation

```bash
neo4j-admin server memory-recommendation
```

```
# Recommended memory settings:
server.memory.heap.initial_size=4g
server.memory.heap.max_size=4g
server.memory.pagecache.size=8g
```

#### report

Generates a diagnostic archive for Neo4j support team.

```bash
neo4j-admin server report
```

```bash
neo4j-admin server report --to-path=/tmp/reports logs config threads   # positional classifiers, or `all`
```

**Options**:
- `--to-path=<path>` - Output directory for the report archive
- `--list` - List available classifiers
- `[<classifier>...]` - Positional classifiers (e.g. `logs tx threads`, or `all`); no `--filter` option

#### license

Enterprise only.

```bash
neo4j-admin server license --accept-commercial
neo4j-admin server license --accept-evaluation
```

### database

#### backup

Enterprise only.

```bash
neo4j-admin database backup --to-path=<backup-directory> <database-name>
```

```bash
neo4j-admin database backup --to-path=/backups/$(date +%Y%m%d) neo4j
```

**Options**:
- `--to-path=<path>` - Destination directory (required); artifacts named `<db>-<timestamp>.backup`
- `--type=<type>` - Backup type: `FULL`, `DIFF` or `AUTO` (default `AUTO`)
- `--keep-failed` - Keep failed backup attempts
- `--verbose` - Print detailed progress
- `--split-archive-part-size=<size>` - Split the backup artifact into multiple parts of this size [2026.09]; config default `server.split_archive.part_size`
- `--skip-empty-diffs[=true|false]` - Differential backup with no new transactions produces no artifact [2026.08]; requires `--include-metadata=none`; default `false`

#### restore

Enterprise only. **Important**: Database must be stopped before restore with `--overwrite-destination=true`.

```bash
neo4j-admin database restore --from-path=<artifact-or-directory> [<database-name>]
```

```bash
# <database-name> allowed only when --from-path is a single artifact
neo4j-admin database restore --from-path=/backups/20260216/neo4j-2026-02-16T02-00-00.backup --overwrite-destination=true neo4j
```

A differential artifact restores its whole chain. `--restore-until=<txId | "YYYY-MM-DD HH:MM:SS">` (UTC) stops replay early.

#### dump

Database must be stopped (a running database cannot be dumped).

```bash
neo4j-admin database dump --to-path=<directory> <database-name>
```

```bash
neo4j-admin database dump --to-path=/exports mydb    # writes /exports/mydb.dump

# Split a large dump into 5 GB parts [2026.09]
neo4j-admin database dump mydb --to-path=/exports --split-archive-part-size=5G
```

**Options**:
- `--to-path=<path>` - Destination directory; file is named `<database>.dump`
- `--split-archive-part-size=<size>` - Split the dump into multiple parts of this size [2026.09]; config default `server.split_archive.part_size`

#### load

```bash
neo4j-admin database load --from-path=<directory> <database-name>
```

`load` looks for `<database-name>.dump` in `--from-path`. To load under a different name, rename the file or stream it:

```bash
neo4j-admin database load --from-path=/exports --overwrite-destination=true mydb
cat /exports/mydb.dump | neo4j-admin database load --from-stdin newdb
```

**Options**:
- `--from-path=<path>` - Directory containing `<database>.dump` (not a file path)
- `--from-stdin` - Read archive from standard input
- `--overwrite-destination` - Allow overwriting existing database

#### import

Mode `full` (all editions) or `incremental` (Enterprise) is required. No `--database` option: database is positional. Put it right after `full` — placed last, it is swallowed by `--relationships`.

```bash
neo4j-admin database import full <database-name> \
  --nodes=<node-files> \
  --relationships=<relationship-files>
```

```bash
neo4j-admin database import full socialnetwork \
  --nodes=Person=/abs/persons.csv \
  --relationships=KNOWS=/abs/knows.csv \
  --delimiter=","
```

**Options**:
- `--nodes=<Label>=<file>` - Node CSV files with optional labels
- `--relationships=<TYPE>=<file>` - Relationship CSV files with types
- `--delimiter=<char>` - CSV field delimiter (default: comma)
- `--array-delimiter=<char>` - Array value delimiter (default: semicolon)
- `--skip-duplicate-nodes` - Skip duplicate node IDs
- `--skip-bad-relationships` - Skip relationships with invalid nodes
- `--target-format=backup` - Produce a backup artifact instead of a live store [2026.04]
- `--compress` - Zstd-compress output; only valid with `--target-format=backup` [2026.04]

#### check

```bash
neo4j-admin database check <database-name>
```

```bash
neo4j-admin database check neo4j --verbose
```

**Options**:
- `--report-path=<path>` - Directory (or `.report` file) for consistency report
- `--verbose` - Detailed output

#### copy

Enterprise only.

```bash
neo4j-admin database copy <source-db> <target-db>
```

```bash
neo4j-admin database copy production staging

# Produce a compressed backup-format copy [2026.04]
neo4j-admin database copy production /backups/prod-copy \
  --target-format=backup --compress
```

**Options**:
- `--target-format=backup` - Emit a backup artifact instead of a live store [2026.04]
- `--compress` - Zstd-compress output; only valid with `--target-format=backup` [2026.04]

#### backup inspect

Enterprise only.

```bash
neo4j-admin backup inspect /backups/full
```

Results ordered by append index; ties broken by time (since 2026.04).

#### migrate

```bash
neo4j-admin database migrate <database-name>
```

```bash
neo4j-admin database migrate legacydb --force-btree-indexes-to-range
```

## Configuration

Commands resolve settings in this order (highest to lowest priority):
1. `--additional-config` flag
2. Command-specific configuration files
3. `neo4j-admin.conf`
4. `neo4j.conf`

```bash
neo4j-admin database backup --to-path=/backups @/path/to/options.conf mydb
```

**Example options.conf**:
```
--verbose
--keep-failed=true
```

## Environment Variables

- `NEO4J_CONF` - Path to directory containing neo4j.conf
- `NEO4J_DEBUG` - Enable debug output (set to any value)
- `NEO4J_HOME` - Neo4j installation directory
- `HEAP_SIZE` - JVM maximum heap size (e.g., `512m`, `4g`)
- `JAVA_OPTS` - Custom JVM settings (takes precedence over HEAP_SIZE)

## Common Workflows

### Initial Setup
```bash
neo4j-admin dbms set-initial-password MySecurePassword
neo4j-admin server memory-recommendation
```

### Backup and Restore
```bash
# Enterprise; keep full + diffs in one directory (one chain)
neo4j-admin database backup --to-path=/backups/neo4j --type=FULL neo4j
neo4j-admin database backup --to-path=/backups/neo4j --type=DIFF neo4j

# Stop the database (STOP DATABASE neo4j on system), then restore the latest artifact (replays the chain)
neo4j-admin database restore --from-path=/backups/neo4j/<latest>.backup --overwrite-destination=true neo4j
```

### Data Migration
```bash
# production must be stopped; writes /exports/production.dump
neo4j-admin database dump --to-path=/exports production
cat /exports/production.dump | neo4j-admin database load --from-stdin productioncopy
neo4j-admin database check productioncopy
```

### CSV Import
```bash
neo4j-admin database import full ecommerce \
  --nodes=User=users.csv \
  --nodes=Product=products.csv \
  --relationships=PURCHASED=purchases.csv \
  --skip-bad-relationships
```

## Exit Codes

- `0` - Success
- Non-zero - Error occurred (check error message for details)

## Best Practices

1. **Always run as Neo4j user**: Execute as the system user that owns the Neo4j installation
2. **Stop database for restore**: Always stop before running restore operations
3. **Verify backups**: Use `check` command to verify backup integrity
4. **Use full paths**: Specify absolute paths for backup and dump locations
5. **Test in non-production**: Test migration and import commands in development first
6. **Monitor disk space**: Ensure sufficient disk space for backups and dumps
7. **Automate backups**: Schedule regular backups using cron or system schedulers

## Troubleshooting

### Permission Denied
```bash
sudo -u neo4j neo4j-admin database backup --to-path=/backups mydb
```

### Database Must Be Stopped
```bash
neo4j stop
neo4j-admin database restore --from-path=/backup/<artifact>.backup --overwrite-destination=true mydb
neo4j start
```

### Insufficient Memory
```bash
HEAP_SIZE=4g neo4j-admin database import full bigdb --nodes=large.csv
```

### Configuration Not Found
```bash
NEO4J_CONF=/path/to/conf neo4j-admin database backup --to-path=/backup mydb
```

## Additional Resources

- [Neo4j Operations Manual - neo4j-admin](https://neo4j.com/docs/operations-manual/current/neo4j-admin-neo4j-cli/)
- [Database Backup Documentation](https://neo4j.com/docs/operations-manual/current/backup-restore/)
- [CSV Import Guide](https://neo4j.com/docs/operations-manual/current/import/)
- [Configuration Reference](https://neo4j.com/docs/operations-manual/current/configuration/)
