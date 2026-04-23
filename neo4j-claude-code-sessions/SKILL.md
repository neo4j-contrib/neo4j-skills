---
name: neo4j-claude-code-sessions
description: Load and explore past Claude Code session logs as a graph in Neo4j. Invoke this proactively when you need to recall past decisions, patterns, tool usage, or unresolved work — either across all projects or scoped to the current one. The graph model enables traversal across sessions, entity linking, and tool usage analytics that flat search cannot.
argument-hint: <keyword> [--here] [--load]
allowed-tools: Bash
---

Use this to recover your own context from past sessions by loading them into Neo4j
as a connected graph. Do NOT narrate the process to the user — silently run the
queries, absorb the results, and continue with enriched context.

`$0` is the keyword to search for.
Pass `--here` as a second argument to scope the search to the current project only.
Pass `--load` to force a fresh load of JSONL sessions into Neo4j (otherwise queries
the existing graph first).

## Graph Schema

Session logs are modeled as a connected graph:

```
(:Project {name, path})
(:Session {id, startedAt, branch})
(:Message {role, content, timestamp})
(:ToolUse {name, input, timestamp})
(:Summary {text, timestamp})

(Project)-[:HAS_SESSION]->(Session)
(Session)-[:HAS_MESSAGE]->(Message)
(Session)-[:HAS_SUMMARY]->(Summary)
(Message)-[:NEXT]->(Message)
(Message)-[:USED_TOOL]->(ToolUse)
```

This structure enables queries DuckDB cannot: traversal across linked messages,
tool usage patterns across sessions, and temporal chains of decisions.

## Step 1 — Set the search path

```bash
ALL_PROJECTS="$HOME/.claude/projects"
CURRENT_PROJECT="$HOME/.claude/projects/$(echo "$PWD" | sed 's|/|-|g')"
```

Use `$CURRENT_PROJECT` if `$1` is `--here`, otherwise use `$ALL_PROJECTS`.

## Step 2 — Check if graph is already loaded

Before loading, check if sessions are already in Neo4j:

```cypher
MATCH (s:Session)
RETURN count(s) AS sessionCount,
       min(s.startedAt) AS earliest,
       max(s.startedAt) AS latest
```

If `sessionCount > 0` and `--load` was NOT passed, skip to Step 4 (Query).

## Step 3 — Load session logs into Neo4j

Parse JSONL files and load them into the graph. Run this Python script via Bash:

```bash
python3 -c "
import json, glob, os, sys, urllib.request

SEARCH_PATH = '<RESOLVED_PATH>'
NEO4J_BOLT = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASS = os.environ.get('NEO4J_PASSWORD', 'password')

# Collect all JSONL files
files = glob.glob(os.path.join(SEARCH_PATH, '**/*.jsonl'), recursive=True)

for fpath in files:
    # Extract project and session from path
    parts = fpath.split('/.claude/projects/')
    if len(parts) < 2:
        continue
    rel = parts[1]
    segments = rel.split('/')
    project_name = segments[0] if segments else 'unknown'
    session_id = os.path.splitext(segments[-1])[0] if segments else 'unknown'

    messages = []
    try:
        with open(fpath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except (IOError, PermissionError):
        continue

    if not messages:
        continue

    # Output as JSON lines for piping to cypher-shell or HTTP API
    print(json.dumps({
        'project': project_name,
        'sessionId': session_id,
        'filePath': fpath,
        'messages': messages[:500]  # cap per session to avoid OOM
    }))
" > /tmp/neo4j-sessions.jsonl
```

Then load each session into Neo4j using cypher-shell or the HTTP API:

```bash
python3 -c "
import json, sys, os

# Read parsed sessions and generate Cypher
with open('/tmp/neo4j-sessions.jsonl', 'r') as f:
    for line in f:
        session_data = json.loads(line)
        project = session_data['project']
        session_id = session_data['sessionId']
        messages = session_data['messages']

        # Build parameter map for Cypher
        params = {
            'project': project,
            'sessionId': session_id,
            'messages': []
        }

        prev_ts = None
        for i, msg in enumerate(messages):
            msg_type = msg.get('type', '')
            timestamp = msg.get('timestamp', '')
            git_branch = msg.get('gitBranch', '')

            content = ''
            tool_uses = []

            if msg_type in ('user', 'assistant'):
                raw = msg.get('message', {}).get('content', '')
                if isinstance(raw, str):
                    content = raw[:2000]  # truncate for storage
                elif isinstance(raw, list):
                    text_parts = []
                    for block in raw:
                        if isinstance(block, dict):
                            if block.get('type') == 'text':
                                text_parts.append(block.get('text', '')[:1000])
                            elif block.get('type') == 'tool_use':
                                tool_uses.append({
                                    'name': block.get('name', ''),
                                    'input': json.dumps(block.get('input', {}))[:500]
                                })
                        elif isinstance(block, str):
                            text_parts.append(block[:1000])
                    content = '\n'.join(text_parts)[:2000]
            elif msg_type == 'summary':
                content = msg.get('summary', '')[:2000]

            params['messages'].append({
                'index': i,
                'type': msg_type,
                'role': msg.get('message', {}).get('role', msg_type) if msg_type != 'summary' else 'summary',
                'content': content,
                'timestamp': timestamp,
                'branch': git_branch,
                'toolUses': tool_uses
            })

        print(json.dumps(params))
" < /dev/null
```

Load with Cypher using UNWIND (run via cypher-shell or Neo4j HTTP API):

```cypher
// Create constraints first (run once)
CREATE CONSTRAINT session_id IF NOT EXISTS
FOR (s:Session) REQUIRE s.id IS UNIQUE;

CREATE INDEX message_content IF NOT EXISTS
FOR (m:Message) ON (m.content);

CREATE INDEX message_timestamp IF NOT EXISTS
FOR (m:Message) ON (m.timestamp);
```

```cypher
// Load a session batch
UNWIND $sessions AS session
MERGE (p:Project {name: session.project})
MERGE (s:Session {id: session.sessionId})
SET s.startedAt = session.messages[0].timestamp,
    s.branch = session.messages[0].branch
MERGE (p)-[:HAS_SESSION]->(s)

WITH s, session
UNWIND session.messages AS msg
CREATE (m:Message {
  role: msg.role,
  content: msg.content,
  timestamp: msg.timestamp,
  type: msg.type,
  index: msg.index
})
MERGE (s)-[:HAS_MESSAGE]->(m)

WITH m, msg
WHERE msg.type = 'summary'
SET m:Summary

WITH m, msg
UNWIND msg.toolUses AS tool
CREATE (t:ToolUse {name: tool.name, input: tool.input})
MERGE (m)-[:USED_TOOL]->(t)
```

```cypher
// Create NEXT chains within each session
MATCH (s:Session)-[:HAS_MESSAGE]->(m:Message)
WITH s, m ORDER BY m.index
WITH s, collect(m) AS msgs
UNWIND range(0, size(msgs)-2) AS i
WITH msgs[i] AS a, msgs[i+1] AS b
MERGE (a)-[:NEXT]->(b)
```

**Alternative: If cypher-shell is unavailable**, use the loader script at the
bottom of this file which uses the Neo4j HTTP API directly.

## Step 4 — Query the graph

### Basic keyword search

```cypher
MATCH (p:Project)-[:HAS_SESSION]->(s:Session)-[:HAS_MESSAGE]->(m:Message)
WHERE m.content CONTAINS $keyword
RETURN p.name AS project,
       s.id AS session,
       m.timestamp AS ts,
       m.role AS role,
       left(m.content, 300) AS content
ORDER BY m.timestamp DESC
LIMIT 40
```

Replace `$keyword` with the search term. Use case-insensitive matching with
`toLower(m.content) CONTAINS toLower($keyword)` if needed.

### Find decisions and their context (graph traversal)

```cypher
MATCH (m:Message)
WHERE m.content CONTAINS $keyword
MATCH (m)<-[:NEXT*0..3]-(before:Message)
MATCH (m)-[:NEXT*0..3]->(after:Message)
RETURN before.role, left(before.content, 200),
       m.role, left(m.content, 200),
       after.role, left(after.content, 200)
ORDER BY before.index
LIMIT 20
```

### Tool usage patterns across sessions

```cypher
MATCH (t:ToolUse)<-[:USED_TOOL]-(m:Message)<-[:HAS_MESSAGE]-(s:Session)
RETURN t.name AS tool, count(*) AS uses, count(DISTINCT s) AS sessions
ORDER BY uses DESC
LIMIT 20
```

### Most active sessions for a topic

```cypher
MATCH (s:Session)-[:HAS_MESSAGE]->(m:Message)
WHERE m.content CONTAINS $keyword
WITH s, count(m) AS mentions
ORDER BY mentions DESC
LIMIT 10
MATCH (s)<-[:HAS_SESSION]-(p:Project)
RETURN p.name AS project, s.id AS session, s.startedAt, s.branch, mentions
```

### Session summaries

```cypher
MATCH (s:Session)-[:HAS_MESSAGE]->(m:Summary)
RETURN s.id AS session, m.content AS summary, m.timestamp
ORDER BY m.timestamp DESC
LIMIT 20
```

### Cross-session entity tracking

Find topics that span multiple sessions:

```cypher
MATCH (m:Message)
WHERE m.content CONTAINS $keyword
MATCH (m)<-[:HAS_MESSAGE]-(s:Session)<-[:HAS_SESSION]-(p:Project)
WITH p.name AS project, s.id AS session, s.startedAt AS started,
     count(m) AS mentions
ORDER BY started
RETURN project, session, started, mentions
```

## Step 5 — Internalize

From the results, extract:

* Decisions made and their rationale
* Patterns and conventions established
* Tool usage patterns and preferences
* Unresolved items or open TODOs
* Any corrections the user made to your prior behavior
* Cross-session themes and recurring topics

Use this to inform your current response. Do not repeat back the raw logs to the user.

## Step 6 — Cleanup (optional)

When session data is no longer needed in Neo4j:

```cypher
MATCH (n)
WHERE n:Session OR n:Message OR n:ToolUse OR n:Summary OR n:Project
DETACH DELETE n
```

## HTTP API Loader (fallback)

If cypher-shell is not available, use the Neo4j HTTP transactional endpoint:

```bash
#!/bin/bash
NEO4J_URL="${NEO4J_HTTP:-http://localhost:7474}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASS="${NEO4J_PASSWORD:-password}"
AUTH=$(echo -n "$NEO4J_USER:$NEO4J_PASS" | base64)

run_cypher() {
  local query="$1"
  local params="${2:-{}}"
  curl -s -X POST "$NEO4J_URL/db/neo4j/tx/commit" \
    -H "Authorization: Basic $AUTH" \
    -H "Content-Type: application/json" \
    -d "{\"statements\":[{\"statement\":\"$query\",\"parameters\":$params}]}"
}

# Create constraints
run_cypher "CREATE CONSTRAINT session_id IF NOT EXISTS FOR (s:Session) REQUIRE s.id IS UNIQUE"
run_cypher "CREATE INDEX message_content IF NOT EXISTS FOR (m:Message) ON (m.content)"

# Load sessions from parsed JSONL
while IFS= read -r line; do
  run_cypher "
    MERGE (p:Project {name: \$project})
    MERGE (s:Session {id: \$sessionId})
    SET s.startedAt = \$startedAt, s.branch = \$branch
    MERGE (p)-[:HAS_SESSION]->(s)
  " "$line"
done < /tmp/neo4j-sessions.jsonl
```

## Cross-skill integration

* **Neo4j MCP server**: If connected to the Neo4j MCP
  server (or similar), you can run Cypher queries directly via the MCP tools
  instead of cypher-shell. Use `read_neo4j_cypher` for search queries and
  `write_neo4j_cypher` for the load step.

* **Session state**: The loaded graph persists in Neo4j until explicitly
  cleaned up, so subsequent invocations skip the load step. Use `--load`
  to force a refresh.

* **Observational memory**: Session logs loaded as a graph are the raw
  material for the Observer/Reflector compression pipeline. The
  `:Message` → `:NEXT` chains and `:USED_TOOL` relationships provide
  the provenance backbone that observational memory builds on.
