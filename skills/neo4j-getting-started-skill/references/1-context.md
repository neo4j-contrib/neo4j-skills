# Stage 1 — context
# Collect the user's domain, use-case, goals, and preferences.

## Autonomous mode detection — do this FIRST

Before asking anything, attempt to extract all 6 context variables from the initial prompt. Look for: domain, use-case, experience level, database target, data source, and app type — either as explicit key=value pairs or inferred from natural language.

**The autonomous/HITL decision is based solely on whether all 6 variables are present — never on phrasing like "guide me", "help me", or "walk me through".** Those phrases describe intent, not preference for interactive vs automated execution.

**If all 6 variables can be extracted → AUTONOMOUS MODE.**
- Extract and record them immediately (no questions needed)
- Record `MODE=autonomous` in progress.md alongside the other variables
- Never pause for approval at any HITL checkpoint in any stage
- Proceed through all 8 stages without stopping

**If any variable is missing → HITL MODE.**
- Ask all missing questions in one combined message (see below)
- Record `MODE=hitl` in progress.md

## What to ask (HITL mode only)

Combine into one conversational message — not a form dump. If any value is already known from context, skip that question.

```
Hi! To get you up and running with Neo4j, I need a few things:

1. What's your domain or industry?
   (e.g. social network, e-commerce, finance, healthcare, logistics, media, legal, IoT, or describe your own)

2. What's the specific use-case?
   Be as concrete as possible — e.g. "product recommendations", "fraud ring detection",
   "GraphRAG over internal documents", "supply chain visibility"

3. Your experience with Neo4j?
   beginner / intermediate / advanced

4. Where to run the database?
   A) Aura Free — easiest, 14-day trial, no credit card needed  ← default for beginners
   B) Aura Pro / Enterprise — I have or will create an account
   C) Local Docker — I have Docker installed
   D) Neo4j Desktop — GUI, already installed
   E) I already have a running database

   If they choose Aura Pro (B), ask as a follow-up:
   "Any cloud provider preference? (GCP / AWS / Azure — or leave blank and I'll pick the closest region to you)"
   Skip this follow-up for Aura Free (GCP only) and local options.

5. What data do you have?
   A) Start with a pre-built demo dataset — fastest path to first insight
   B) Generate synthetic data to match my use-case
   C) I have CSV files to import
   D) I have a relational database (PostgreSQL / MySQL / other)
   E) I have documents to build a knowledge graph / GraphRAG pipeline
      (txt, md, pdf — will be ingested via SimpleKGPipeline into data/)

   DATA_SOURCE inference rules:
   - If the user mentions having files, documents, PDFs, contracts, papers → documents
   - If files already exist in data/ → documents (even if user didn't say so)
   - Only use synthetic if the user has NO data and explicitly wants generated examples

6. What do you want to build?
   A) Python notebook (Jupyter / VS Code)
   B) Streamlit dashboard
   C) FastAPI backend
   D) GraphRAG pipeline (LLM + graph retrieval)
   E) Just queries + visual exploration
   F) MCP server integration for an agent (Claude Desktop / Claude Code)
```

## Defaults (apply when user says "just get started" or is a beginner)

```
DB_TARGET    = aura-free
DATA_SOURCE  = demo  (offer Movies as the default demo)
APP_TYPE     = notebook
LANGUAGE     = python
EXPERIENCE   = beginner
```

## Variables to store

```
DOMAIN          = <domain/industry>
USE_CASE        = <specific use-case description>
EXPERIENCE      = beginner | intermediate | advanced
DB_TARGET       = aura-free | aura-pro | local-docker | local-desktop | existing
DATA_SOURCE     = demo | synthetic | csv | relational | documents
APP_TYPE        = notebook | streamlit | fastapi | graphrag | explore-only | mcp
LANGUAGE        = python  (v1 only; javascript in phase 2)
CLOUD_PROVIDER  = gcp | aws | azure | (omit if no preference)
REGION_HINT     = <geographic hint inferred from user context — see below>
```

`CLOUD_PROVIDER` comes from **user preference** (asked for Aura Pro only).
`REGION_HINT` is **inferred** from geographic signals (never asked).

The provision stage combines both: user's preferred provider, closest available region within that provider using the geographic hint.

### REGION_HINT — infer, don't ask

Infer from any available signal — do not ask:
- Explicit mention: "I'm in Brazil", "our servers are in Tokyo", "EU data residency required"
- Language/locale of the conversation
- Timezone in system prompt or `date` output (e.g. `CET` → western Europe, `BRT` → Brazil)
- Initial prompt already contains a region → use it directly

Store the **geographic area** only — the provision stage maps it to the user's chosen provider:

| Signal | REGION_HINT |
|--------|------------|
| Western Europe / CET / BST / CEST | `europe-west` |
| Eastern Europe | `europe-east` |
| US East Coast / EST / EDT | `us-east` |
| US West Coast / PST / PDT | `us-west` |
| Brazil / BRT | `sa-east` |
| Singapore / SGT | `ap-southeast` |
| Japan / JST | `ap-northeast` |
| Australia / AEST / AEDT | `ap-southeast` |
| No signal | (omit — provision stage uses first available) |

The provision stage maps `REGION_HINT` + `CLOUD_PROVIDER` to an actual Aura region from the tenant's available configurations.

If `APP_TYPE=graphrag`, also collect:
```
EMBEDDING_PROVIDER = openai | cohere | ollama | other
EMBEDDING_MODEL    = <model name, e.g. text-embedding-3-small>
```

## Special cases

**DB_TARGET=existing**: ask for URI, username, password, database name.
Write to `.env` immediately, skip `provision` stage.

**DATA_SOURCE=demo**: ask which demo dataset:
- Movies — classic graph, great for beginners
- Northwind — e-commerce (orders, products, customers)
- StackOverflow — Q&A network
- Companies — corporate KG with news and embeddings
- Other — check https://github.com/neo4j-graph-examples

## Detect execution method

Detect `EXEC_METHOD` for all subsequent Cypher execution.
See `${CLAUDE_SKILL_DIR}/references/capabilities/execute-cypher.md` for details on each option.

```bash
# Priority order:
# 1. MCP (neo4j-mcp running as MCP server in this session)
# 2. cypher-shell
# 3. Query API (HTTP curl — always works)
which cypher-shell 2>/dev/null && EXEC_METHOD=cypher-shell || EXEC_METHOD=query-api
# Override to mcp if neo4j-mcp tools are available in this session
echo "EXEC_METHOD=$EXEC_METHOD"
```

Store `EXEC_METHOD` alongside the other variables. Reference only the relevant section of `${CLAUDE_SKILL_DIR}/references/capabilities/execute-cypher.md` in subsequent stages.

## On Completion — write to progress.md

```markdown
### 1-context
status: done
MODE=<autonomous|hitl>
DOMAIN=<value>
USE_CASE=<value>
EXPERIENCE=<beginner|intermediate|advanced>
DB_TARGET=<value>
DATA_SOURCE=<value>
APP_TYPE=<value>
EXEC_METHOD=<mcp|cypher-shell|query-api>
CLOUD_PROVIDER=<gcp|aws|azure — omit if no preference stated>
REGION_HINT=<e.g. europe-west, us-east, sa-east — omit if no signal>
```

Include `EMBEDDING_PROVIDER` and `EMBEDDING_MODEL` if `APP_TYPE=graphrag`.

## Completion condition

All variables known + `EXEC_METHOD` determined. Summarize before proceeding:
```
Got it — here's your plan:
  Domain:    <DOMAIN>
  Use-case:  <USE_CASE>
  Database:  <DB_TARGET>
  Data:      <DATA_SOURCE>
  Build:     <APP_TYPE>

Starting now — I'll provision your database and design a data model.
```
