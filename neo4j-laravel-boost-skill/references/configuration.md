# Configuration Reference — neo4j/laravel-boost

## Publish config

```bash
php artisan vendor:publish --tag=neo4j-boost-config
```

Creates `config/neo4j-boost.php`. Re-publish after upgrading:

```bash
php artisan vendor:publish --tag=neo4j-boost-config --force
```

Clear cache after changes:

```bash
php artisan config:clear
```

---

## Environment Variables

### Core connection

| Variable | Default | Description |
|---|---|---|
| `NEO4J_URI` | `bolt://localhost:7687` | Bolt URI for Neo4j instance |
| `NEO4J_USERNAME` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | (empty) | Neo4j password |
| `NEO4J_DATABASE` | `neo4j` | Target database (driver transport) |

### Transport selection

| Variable | Default | Values |
|---|---|---|
| `NEO4J_MCP_TRANSPORT` | `stdio` | `stdio`, `http`, `driver` |

### STDIO transport

| Variable | Default | Description |
|---|---|---|
| `NEO4J_MCP_STDIO_COMMAND` | `neo4j-mcp` | Path to binary (auto-installed by setup) |
| `NEO4J_MCP_VERSION` | `v1.4.0` | Binary version to download |
| `NEO4J_MCP_BINARY_PATH` | (auto) | Custom binary path override |
| `NEO4J_MCP_PLATFORM_ASSET` | (auto) | Override auto-detected platform asset name |
| `NEO4J_MCP_AUTO_INSTALL` | `false` | Auto-install binary on first use |

### HTTP transport

| Variable | Default | Description |
|---|---|---|
| `NEO4J_MCP_URL` | `http://localhost:8080/mcp` | MCP HTTP endpoint URL |
| `NEO4J_MCP_USERNAME` | falls back to `NEO4J_USERNAME` | Basic Auth username for MCP HTTP |
| `NEO4J_MCP_PASSWORD` | falls back to `NEO4J_PASSWORD` | Basic Auth password for MCP HTTP |

### Driver transport (in-process Bolt)

Uses `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE` from core connection.

| Variable | Default | Description |
|---|---|---|
| `NEO4J_SCHEMA_SAMPLE_SIZE` | `100` | Sample size for schema introspection |

### Container graph (`php artisan container:graph`)

| Variable | Default | Description |
|---|---|---|
| `NEO4J_URI` | (empty) | Bolt URI for graph export |
| `NEO4J_DEFAULT_CONNECTION_DSN` | (empty) | Fallback DSN when `NEO4J_URI` empty |
| `NEO4J_USER` | falls back to `NEO4J_USERNAME` | Username for container graph |
| `NEO4J_PASSWORD` | (empty) | Password for container graph |

---

## config/neo4j-boost.php structure

```php
return [
    'transport' => [
        'driver' => env('NEO4J_MCP_TRANSPORT', 'stdio'),

        'stdio' => [
            'command' => env('NEO4J_MCP_STDIO_COMMAND', 'neo4j-mcp'),
            'env' => [
                'NEO4J_URI'      => env('NEO4J_URI', 'bolt://localhost:7687'),
                'NEO4J_USERNAME' => env('NEO4J_USERNAME', 'neo4j'),
                'NEO4J_PASSWORD' => env('NEO4J_PASSWORD', ''),
            ],
        ],

        'http' => [
            'url'      => env('NEO4J_MCP_URL', 'http://localhost:8080/mcp'),
            'username' => env('NEO4J_MCP_USERNAME', env('NEO4J_USERNAME')),
            'password' => env('NEO4J_MCP_PASSWORD', env('NEO4J_PASSWORD')),
        ],
    ],

    'neo4j_mcp' => [
        'transport'      => env('NEO4J_MCP_TRANSPORT', 'stdio'),
        'version'        => env('NEO4J_MCP_VERSION', 'v1.4.0'),
        'binary_path'    => env('NEO4J_MCP_BINARY_PATH'),
        'platform_asset' => env('NEO4J_MCP_PLATFORM_ASSET'),
        'auto_install'   => env('NEO4J_MCP_AUTO_INSTALL', false),
    ],

    'bolt' => [
        'uri'                => env('NEO4J_URI', 'bolt://localhost:7687'),
        'username'           => env('NEO4J_USERNAME', 'neo4j'),
        'password'           => env('NEO4J_PASSWORD', ''),
        'database'           => env('NEO4J_DATABASE', 'neo4j'),
        'schema_sample_size' => (int) env('NEO4J_SCHEMA_SAMPLE_SIZE', 100),
    ],

    'container_graph' => [
        'uri'                    => env('NEO4J_URI', ''),
        'default_connection_dsn' => env('NEO4J_DEFAULT_CONNECTION_DSN', ''),
        'username'               => env('NEO4J_USER', env('NEO4J_USERNAME', 'neo4j')),
        'password'               => env('NEO4J_PASSWORD', ''),
    ],
];
```

---

## Platform support (neo4j-mcp binary)

| OS | Architecture | Archive | PHP requirement |
|---|---|---|---|
| Linux | x86_64 / amd64 | `.tar.gz` | — |
| Linux | arm64 / aarch64 | `.tar.gz` | — |
| Linux | i386 / i686 | `.tar.gz` | — |
| macOS | x86_64 / amd64 | `.tar.gz` | — |
| macOS | arm64 (Apple Silicon) | `.tar.gz` | — |
| Windows | x86_64 / amd64 | `.zip` | `ext-zip` required |
| Windows | arm64 | `.zip` | `ext-zip` required |
| Windows | i386 | `.zip` | `ext-zip` required |

Override auto-detection with `NEO4J_MCP_PLATFORM_ASSET` in `.env`.
