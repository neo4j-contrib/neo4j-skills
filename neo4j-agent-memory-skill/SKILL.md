---
name: neo4j-agent-memory
description: Authoritative reference for the neo4j-agent-memory Python package — a graph-native memory system for AI agents built on Neo4j — and for the hosted service (NAMS) at memory.neo4jlabs.com. Use this skill whenever the user mentions neo4j-agent-memory, agent memory with Neo4j, context graphs, the POLE+O model, MemoryClient/MemorySettings, the memory MCP server, or any of the framework integrations (LangChain, PydanticAI, CrewAI, AWS Strands, Google ADK, Microsoft Agent Framework, OpenAI Agents, LlamaIndex). Also use when the user mentions the hosted service at memory.neo4jlabs.com, NAMS, the Neo4j Agent Memory Service, the `nams_` API key prefix, or the hosted MCP endpoint. Also use when writing documentation, blog posts, tutorials, PRDs, or code samples for the project, when comparing agent memory approaches, or when positioning graph-native memory against vector-only approaches — even if the user doesn't explicitly name the package.
---

# neo4j-agent-memory

Authoritative reference for the `neo4j-agent-memory` Python package — a Neo4j Labs project that gives AI agents three distinct memory layers (short-term, long-term, reasoning) in a single knowledge graph.

> ⚠️ **Verify authoritative state before writing.** Version numbers, extras, tool counts, and API surface change between releases. The values in this skill reflect a specific point in time. Before publishing anything version-sensitive, confirm against **PyPI** (`https://pypi.org/project/neo4j-agent-memory/`) and the **GitHub README** (`https://github.com/neo4j-labs/agent-memory`). PyPI is the authoritative source for version numbers — never infer.

## Project at a Glance

| Field | Value |
|-------|-------|
| Package | `neo4j-agent-memory` |
| PyPI | https://pypi.org/project/neo4j-agent-memory/ |
| GitHub | https://github.com/neo4j-labs/agent-memory |
| Canonical docs | https://neo4j.com/labs/agent-memory/ |
| Hosted service | https://memory.neo4jlabs.com (NAMS — early-access, not yet documented on official project pages) |
| Hosted MCP endpoint | https://memory.neo4jlabs.com/mcp (SSE, bearer auth) |
| License | Apache-2.0 |
| Python | 3.10+ |
| Neo4j | 5.20+ (required for vector indexes) |
| Status | Experimental (Neo4j Labs, community-supported) |
| Current version (at time of writing) | **0.1.1** — **always verify PyPI before citing** |

## What It Is (One Sentence)

A graph-native memory system for AI agents that stores conversations, builds knowledge graphs, and records agent reasoning — all as connected nodes in a single Neo4j database.

## Consumption Models

`neo4j-agent-memory` ships in two consumption models. They are the same underlying project — the differences are how you run it, how you authenticate, and what's managed for you.

| Option | What It Is | When to Choose |
|--------|------------|----------------|
| **Self-hosted library** | `pip install neo4j-agent-memory` + your own Neo4j (local / Docker / Aura). Full Python API, local MCP server, and framework integrations run in your process. | Dev, on-prem data, custom extraction pipelines, full control, bringing your own embeddings / LLMs. |
| **Hosted (NAMS)** | Managed service at `https://memory.neo4jlabs.com`. Per-workspace isolated Neo4j Aura database, REST API, remote MCP endpoint, web console. | Zero-infra trials, sharing memory across agents / machines, demos, teams that don't want to run Neo4j. |

> ⚠️ **NAMS is reachable but not yet referenced in the GitHub README or `neo4j.com/labs/agent-memory/`.** Treat it as early-access / soft-launched. Do not assert SLAs, pricing, or GA status in published content. See the **Hosted Service (NAMS)** section below for details.

## The Three Memory Types

The defining architectural feature. Every piece of content describing the project should lead with this trinity.

| Memory Type | Stores | Color Convention |
|-------------|--------|------------------|
| **Short-Term** | Conversation messages, session history, sequential message chains, metadata-filtered search, LLM-powered summaries | Green (`#B2F2BB` / `#2F9E44`) |
| **Long-Term** | Entities (people, places, orgs), preferences, facts, and the relationships between them — built automatically from conversations via the POLE+O model | Orange/Yellow (`#FFEC99` / `#F08C00`) |
| **Reasoning** | Decision traces, tool call provenance, thought-action-outcome chains — so the agent can learn from its own past reasoning patterns | Purple (`#D0BFFF` / `#9C36B5`) |

**Reasoning memory is the primary competitive differentiator.** Most competing systems cover short-term and long-term but treat reasoning as an afterthought or omit it entirely. Lead with this when positioning.

## The POLE+O Model

Long-term memory uses the POLE+O entity framework — the canonical entity classification for this project:

- **P**erson
- **O**rganization
- **L**ocation
- **E**vent
- **+O** Object (anything that doesn't fit the core four — products, concepts, projects, etc.)

When diagramming the data model, use ellipses for entity nodes and labeled arrows (UPPER_SNAKE_CASE) for relationships, consistent with Neo4j Browser conventions.

## Installation

Core install plus extras. The extras pattern is `pip install neo4j-agent-memory[<extra>]`.

```bash
pip install neo4j-agent-memory                  # Core
pip install neo4j-agent-memory[openai]          # + OpenAI embeddings
pip install neo4j-agent-memory[mcp]             # + MCP server
pip install neo4j-agent-memory[langchain]       # + LangChain
pip install neo4j-agent-memory[all]             # Everything
```

**Full extras list** (subject to change — verify PyPI): `all`, `anthropic`, `aws`, `bedrock`, `cli`, `crewai`, `extraction`, `full`, `fuzzy`, `gliner`, `google`, `google-adk`, `langchain`, `llamaindex`, `mcp`, `microsoft-agent`, `observability`, `openai`, `openai-agents`, `opentelemetry`, `opik`, `pydantic-ai`, `sentence-transformers`, `spacy`, `strands`, `vertex-ai`.

## Python API (Quickstart)

Canonical import pattern and basic usage. This is the shape to reproduce in tutorials and examples.

```python
import asyncio
from neo4j_agent_memory import MemoryClient, MemorySettings

async def main():
    settings = MemorySettings(
        neo4j={"uri": "bolt://localhost:7687", "password": "your-password"}
    )

    async with MemoryClient(settings) as memory:
        # Short-term: store a conversation message
        await memory.short_term.add_message(
            session_id="user-123",
            role="user",
            content="Hi, I'm John and I love Italian food!"
        )

        # Long-term: build the knowledge graph
        await memory.long_term.add_entity("John", "PERSON")
        await memory.long_term.add_preference(
            category="food",
            preference="Loves Italian cuisine"
        )

        # Get combined context for an LLM prompt
        context = await memory.get_context(
            "What restaurant should I recommend?",
            session_id="user-123"
        )
        print(context)

asyncio.run(main())
```

**Note the async context manager pattern** (`async with MemoryClient(settings) as memory:`) — this is the canonical form.

## MCP Server

Exposes memory as tools for MCP-compatible AI assistants (Claude Desktop, Claude Code, Cursor, VS Code Copilot).

### Invocation

The authoritative one-liner (no install needed):

```bash
uvx "neo4j-agent-memory[mcp]" mcp serve --password <neo4j-password>
```

Install-local alternative:

```bash
neo4j-agent-memory mcp serve --password <pw>
```

### Transports and Profiles

```bash
# stdio (default — Claude Desktop, Claude Code)
neo4j-agent-memory mcp serve --password <pw>

# SSE (network deployment)
neo4j-agent-memory mcp serve --transport sse --port 8080 --password <pw>

# Core profile — fewer tools, less context overhead
neo4j-agent-memory mcp serve --profile core --password <pw>

# Session continuity across conversations
neo4j-agent-memory mcp serve \
  --session-strategy per_day \
  --user-id alice \
  --password <pw>
```

### Tool Profiles

| Profile | Tools | Contents |
|---------|-------|----------|
| **core** | 6 | `memory_search`, `memory_get_context`, `memory_store_message`, `memory_add_entity`, `memory_add_preference`, `memory_add_fact` |
| **extended** (default) | 16 | Core + conversation history, entity details, graph export, relationship creation, reasoning traces, observations, read-only Cypher |

As of v0.1.1, `memory_add_fact` accepts a `metadata` parameter, bringing it to parity with `memory_add_entity`.

### Claude Code Registration

```bash
claude mcp add neo4j-agent-memory -- \
  uvx "neo4j-agent-memory[mcp]" mcp serve --password <neo4j-password>
```

### Claude Desktop Config

```json
{
  "mcpServers": {
    "neo4j-agent-memory": {
      "command": "uvx",
      "args": ["neo4j-agent-memory[mcp]", "mcp", "serve", "--password", "your-password"],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

> For the **hosted** MCP endpoint at `memory.neo4jlabs.com/mcp`, see the **Hosted Service (NAMS)** section below — it uses SSE transport and bearer-token auth, not a local `uvx` invocation.

## Hosted Service (NAMS)

**NAMS** — Neo4j Agent Memory Service — is the managed deployment of `neo4j-agent-memory` at `https://memory.neo4jlabs.com`. It bundles the REST API, the MCP server, a web console, and per-workspace Neo4j Aura databases.

> ⚠️ **Verify against the live service before citing.** NAMS is not documented on the GitHub README or `neo4j.com/labs/agent-memory/`. Endpoint shapes, tool counts, auth flows, and limits can change without a release note. Before publishing anything NAMS-specific, re-check the live site and the OpenAPI spec at `/openapi.json`.

### Surface

- **Base URL:** `https://memory.neo4jlabs.com`
- **Web console:** root URL — workspace management, memory browsing, entity visualization
- **REST API:** `https://memory.neo4jlabs.com/v1/` — OpenAPI spec at `/openapi.json`; covers conversations, entities, observations, reasoning traces, and read-only Cypher
- **MCP endpoint:** `https://memory.neo4jlabs.com/mcp` — SSE transport, exposes the hosted tool set, bearer-token auth

### Auth

- **API keys**, prefixed `nams_`, created and rotated from the web console — used as a bearer token for REST and MCP
- **Auth0 OAuth2 (PKCE)** + scoped JWTs for interactive user flows

Don't mix these with the self-hosted library's `--password` Neo4j credential — they serve different sides of the stack.

### Storage Model

Each workspace is backed by an **isolated Neo4j Aura database**, provisioned on demand. Bring-your-own-Neo4j is supported as an alternative, configured per workspace.

### Rate Limits

Usage counters are tracked per API key / workspace. Exact limits are not publicly documented — check the console or re-verify against the service before committing customers to numbers.

### Claude Code Registration (Hosted MCP)

```bash
claude mcp add --transport sse neo4j-agent-memory-hosted \
  https://memory.neo4jlabs.com/mcp \
  --header "Authorization: Bearer <nams_api_key>"
```

### Claude Desktop Config (Hosted MCP)

```json
{
  "mcpServers": {
    "neo4j-agent-memory-hosted": {
      "url": "https://memory.neo4jlabs.com/mcp",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer nams_..."
      }
    }
  }
}
```

## Framework Integrations

All integrations live under `neo4j_agent_memory.integrations.<framework>`. Install the matching extra.

| Framework | Install Extra | Import |
|-----------|---------------|--------|
| LangChain | `[langchain]` | `from neo4j_agent_memory.integrations.langchain import Neo4jAgentMemory` |
| Pydantic AI | `[pydantic-ai]` | `from neo4j_agent_memory.integrations.pydantic_ai import MemoryDependency` |
| Google ADK | `[google-adk]` | `from neo4j_agent_memory.integrations.google_adk import Neo4jMemoryService` |
| AWS Strands | `[strands]` | `from neo4j_agent_memory.integrations.strands import context_graph_tools` |
| CrewAI | `[crewai]` | `from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory` |
| LlamaIndex | `[llamaindex]` | `from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory` |
| OpenAI Agents | `[openai-agents]` | `from neo4j_agent_memory.integrations.openai_agents import ...` |
| Microsoft Agent Framework | `[microsoft-agent]` | `from neo4j_agent_memory.integrations.microsoft_agent import Neo4jMicrosoftMemory` |

## Entity Extraction Pipeline

Multi-stage extraction (cost/quality tradeoff from fastest → most accurate):

1. **spaCy** — fast statistical NER, cheapest, broad but imprecise coverage
2. **GLiNER** — zero-shot entity extraction with typed schemas; `GLiREL` for relationships
3. **LLM fallback** — most accurate, most expensive; used when structure is rich or ambiguous

**Enrichment** is a separate background stage: Wikipedia and Diffbot can hydrate extracted entities with additional context.

**Deduplication** (v0.1.1+) auto-merges duplicate facts and preferences using subject/predicate matching plus embedding similarity (threshold ~0.95), and updates confidence rather than creating new nodes. Tuned via `DeduplicationConfig`.

Configuration objects to know: `ExtractionConfig`, `DeduplicationConfig`, `MemoryIntegration`, `SessionStrategy`.

## Positioning Language

These phrasings are load-bearing. Use them verbatim when possible.

### Core Taglines

- **"Graph handles understanding; vector handles similarity."**
- **"Vector stores give you recall. The graph gives you understanding."**
- **"Three memory types, one knowledge graph."**

### Category Framing

- Anchor to the Foundation Capital **"AI's Trillion-Dollar Opportunity: Context Graphs"** thesis when the forum warrants it.
- `neo4j-agent-memory` is positioned as **the complete implementation** of the context graph category — it covers all three memory layers, not just two.
- The context graph coexists with domain data in the **same Neo4j instance** (not a bolted-on external system). This is a key conceptual/visual point for architecture diagrams.

### Do Say

- "graph-native memory"
- "context graph"
- "three distinct memory layers"
- "reasoning traces as first-class graph nodes"
- "learn from past reasoning"
- "build knowledge graphs automatically from conversations"
- "Neo4j Labs project" / "experimental" / "community-supported"

### Don't Say

- **Don't name specific competitors** (Mem0, Zep, Letta, Cognee, Supermemory) in published content. Reframe comparisons around capabilities, not product names.
- Don't call it "production-ready" (it's a Labs project — see the `neo4j-labs-brand` skill for the full voice guide).
- Don't say "officially supported" or imply SLAs.

## Common Corrections to Watch For

When editing or reviewing content about this project, check for:

1. **Outdated version numbers** — anyone writing "v0.1.0" today may be working from stale notes; verify PyPI.
2. **Wrong canonical docs URL** — it's `neo4j.com/labs/agent-memory`, not a Vercel preview URL.
3. **Inferred API surface** — if code samples weren't run, flag them; prefer patterns from the GitHub README or official examples.
4. **Missing "Labs" framing** — experimental/community-supported should be clear.
5. **Conflating with other Neo4j MCP servers** — there are several (`mcp-neo4j-cypher`, `mcp-neo4j-memory` — the old knowledge graph memory server, etc.). `neo4j-agent-memory`'s MCP server is distinct and ships as part of the package under the `[mcp]` extra.
6. **Confusing NAMS with the self-hosted library** — same underlying project, different consumption models. Connection strings, auth, and tool sets differ: self-hosted uses a local `uvx` invocation and a Neo4j `--password`; NAMS uses an SSE MCP URL and a `nams_`-prefixed bearer token. Don't mix them.
7. **Over-promising NAMS availability** — the hosted service is not yet referenced in the GitHub README or `neo4j.com/labs/agent-memory/`. Avoid "officially supported," SLAs, pricing claims, or "production-ready" framing. Treat it as early-access.

## Related Projects in the Ecosystem

Mentions of these are frequent; recognize them and use the correct names.

| Project | What It Is |
|---------|------------|
| **create-context-graph** | CLI scaffolder (`uvx create-context-graph`) that generates full-stack context graph apps pre-wired with neo4j-agent-memory. Canonical docs: `create-context-graph.dev`. |
| **Lenny's Podcast Memory Explorer** | Flagship demo — 299 podcast episodes, knowledge graph, geospatial maps, Wikipedia enrichment. PydanticAI-based. Lives at `examples/lennys-memory/` in the repo. |
| **neo4j-agent-integrations** | Broader umbrella of framework integrations, many of which are packaged back into `neo4j-agent-memory` under `[<framework>]` extras. |
| **agent-memory-tck** | Technology Compliance Kit — behavioral specifications for multi-language/multi-framework interoperability (polyglot). |
| **Microsoft Learn integration** | Official Microsoft Agent Framework docs reference `neo4j-agent-memory` as the Neo4j Memory Provider. |

## Canonical Examples (from the Repo)

Point users here rather than inventing examples:

- `examples/lennys-memory` — flagship PydanticAI demo
- `examples/full-stack-chat-agent` — PydanticAI news research with NVL graph viz
- `examples/financial-services-advisor/aws-financial-services-advisor` — AWS Strands multi-agent KYC/AML with reasoning-trace audit trails
- `examples/financial-services-advisor/google-cloud-financial-advisor` — Google ADK multi-agent with Vertex AI embeddings + SSE streaming
- `examples/microsoft_agent_retail_assistant` — Microsoft Agent Framework with GDS algorithms and context providers
- `examples/domain-schemas` — 8 GLiNER2 extraction scripts
- `examples/google_cloud_integration` — progressive tutorial covering Vertex AI → ADK → MCP → `MemoryIntegration`
- `examples/google_adk_demo` — standalone ADK demo of `Neo4jMemoryService`

## Diagram Conventions (Cross-Reference)

When building diagrams for this project, combine this skill with:

- **`excalidraw` skill** — JSON format and the project's diagram management script
- **`neo4j-styleguide` skill** — Cypher code style and Neo4j brand colors
- **`neo4j-labs-brand` skill** — Labs purple (`#6366F1`), status badges, disclaimer language

Memory-type colors (use consistently across all diagrams):

```
Short-Term:  #B2F2BB fill / #2F9E44 stroke  (green)
Long-Term:   #FFEC99 fill / #F08C00 stroke  (orange/yellow)
Reasoning:   #D0BFFF fill / #9C36B5 stroke  (purple)
Neo4j/Store: #A5D8FF fill / #1971C2 stroke  (blue)
Labs accent: #6366F1 (purple, for Labs branding elements)
```

## Documentation Structure (Cross-Reference)

The canonical docs at `neo4j.com/labs/agent-memory` follow the **Diataxis** framework (see the `diataxis` skill in this project for details):

- **Tutorials** — build your first memory-enabled agent
- **How-To Guides** — entity extraction, deduplication, enrichment, integrations
- **Reference** — configuration, CLI, MCP tools, API
- **Explanation** — POLE+O model, memory types, extraction pipeline

When adding new content, place it in the right quadrant.

## Quick Authoritative-Facts Checklist

Before publishing any content about this project, verify:

- [ ] Version number is current per PyPI (not inferred from notes)
- [ ] Canonical docs link points to `neo4j.com/labs/agent-memory`
- [ ] Three memory types named correctly (short-term, long-term, reasoning)
- [ ] POLE+O model named consistently (not POLEO, not POLE-O)
- [ ] Python ≥ 3.10 and Neo4j ≥ 5.20 requirements are stated if relevant
- [ ] Labs disclaimer present for README/landing content
- [ ] No competitor names in published positioning
- [ ] Reasoning memory is called out as the differentiator
- [ ] Import paths use `neo4j_agent_memory.integrations.<framework>` (underscore, snake_case)
- [ ] If NAMS is referenced, distinguish clearly from the self-hosted library and re-verify endpoints against the live service (not yet mirrored in the README)

## Resources

- **PyPI (authoritative for version):** https://pypi.org/project/neo4j-agent-memory/
- **GitHub:** https://github.com/neo4j-labs/agent-memory
- **Canonical docs:** https://neo4j.com/labs/agent-memory/
- **CHANGELOG:** https://github.com/neo4j-labs/agent-memory/blob/main/CHANGELOG.md
- **NAMS (hosted service):** https://memory.neo4jlabs.com
- **NAMS REST API:** https://memory.neo4jlabs.com/v1/ (OpenAPI at `/openapi.json`)
- **NAMS MCP endpoint:** https://memory.neo4jlabs.com/mcp (SSE)
- **create-context-graph (scaffolder):** https://create-context-graph.dev
- **Community Forum:** https://community.neo4j.com
- **Microsoft Learn integration page:** https://learn.microsoft.com/en-us/agent-framework/integrations/neo4j-memory
