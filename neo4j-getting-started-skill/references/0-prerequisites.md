# Stage 0 — prerequisites
# Verify and install required CLI tools before anything else.

## neo4j-mcp (official Neo4j MCP server — required)

MCP tool names exposed by this server:
- `get-schema` — introspect node labels, relationship types, property keys
- `read-cypher` — execute read-only Cypher
- `write-cypher` — execute write Cypher (disabled in read-only mode)
- `list-gds-procedures` — list available GDS procedures (only if GDS is installed)

```bash
# Check if already installed
which neo4j-mcp 2>/dev/null || ls $HOME/bin/neo4j-mcp 2>/dev/null && echo "FOUND" || echo "MISSING"
```

If missing, install (any one):
```bash
# A) Homebrew
brew install neo4j-mcp

# B) Release archive (macOS / Linux) — assets are neo4j-mcp_<Darwin|Linux>_<x86_64|arm64>.tar.gz
OS=$(uname -s)       # Darwin | Linux
ARCH=$(uname -m)     # x86_64 | arm64 | aarch64
[ "$ARCH" = "aarch64" ] && ARCH="arm64"
curl -fsSL "https://github.com/neo4j/mcp/releases/latest/download/neo4j-mcp_${OS}_${ARCH}.tar.gz" \
  | tar xz neo4j-mcp && chmod +x ./neo4j-mcp
./neo4j-mcp -v
```

Windows: download `neo4j-mcp_Windows_<x86_64|arm64>.zip` from https://github.com/neo4j/mcp/releases. PyPI alternative: `uvx neo4j-mcp-server` (then the config `command` is `uvx` with args `["neo4j-mcp-server"]`, not a binary path). Install docs: https://neo4j.com/docs/mcp/current/installation/

The binary can live in `./neo4j-mcp` (project-local) or `$HOME/bin/neo4j-mcp` (user-wide). Either works.

## aura-cli (optional — for Aura provisioning via CLI)

```bash
which aura-cli 2>/dev/null && echo "FOUND" || echo "MISSING — using Aura REST API directly (no install needed)"
```

aura-cli is **not required** — the `provision` stage uses the Aura REST API via `curl` as the primary path, which works without any binary.

## Docker (optional — for local Docker path only)

```bash
docker --version 2>/dev/null && echo "FOUND" || echo "MISSING"
```

## Python (required for app generation)

```bash
python3 --version && which python3
```

**STOP. Use ONLY `python3` — never probe `python3.10`, `python3.11`, `python3.12`, `python3.13` etc. individually. One command, one result. Any version ≥3.10 is fine.**

## Python virtual environment (required — always create)

Modern Python (3.12+, all macOS system Pythons) **forbids global `pip install`** with the "externally-managed-environment" error. A `.venv` in the working directory is required for all package installs.

```bash
python3 -m venv .venv
echo "✓ Virtual environment created at .venv"
```

All subsequent `pip install`, `python3 script.py`, `jupyter`, `streamlit`, and `uvicorn` commands must use this venv:
- Install: `.venv/bin/pip install ...`
- Run scripts: `.venv/bin/python3 script.py`
- Run app: `.venv/bin/jupyter notebook ...` / `.venv/bin/streamlit run ...` / `.venv/bin/uvicorn ...`

**Never use bare `pip install` or `python3` commands after this point — they may target the wrong (system) Python.**

## .gitignore setup (always run)

```bash
for entry in .env aura.env neo4j-mcp "mcp-*.json" .mcp.json .provision.lock neo4j-data/ .venv/; do
  grep -qxF "$entry" .gitignore 2>/dev/null || echo "$entry" >> .gitignore
done
echo "✓ .gitignore updated"
```

## Completion condition

- `neo4j-mcp` binary reachable (local or on PATH)
- `.gitignore` contains `.env`, `aura.env`, and `.venv/`
- Python ≥3.10 available
- `.venv/` created in working directory

## On Completion — write to progress.md

```markdown
### 0-prerequisites
status: done
PYTHON=<path from `which python3`>
NEO4J_MCP=<path from `which neo4j-mcp` or local path>
VENV=.venv
```
