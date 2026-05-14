# Aura Agent Authoring Guide

Best practices for system prompts, tool names, tool descriptions, and parameter descriptions.
The agent's LLM reads all of these at inference time to decide which tool to call and how to answer.
Quality here determines routing accuracy and answer quality.

---

## System Prompt

### Purpose
Defines the agent's identity, scope, and behavior constraints. Supplements — does not replace — tool descriptions.

### Rules

**Role sentence** — one sentence: domain + expertise level.
```
✅ "You are a specialist assistant for commercial contract analysis using a knowledge graph."
❌ "You are a helpful AI assistant."
```

**Supported use cases** — bullet list of what it can answer. Keeps LLM from fabricating capabilities.
```
✅ "You can: look up agreements by party or type, find similar clause language, identify contracts expiring within a date range."
❌ (omitting this — LLM will guess its own scope)
```

**Explicit boundaries** — state what it cannot do; do not rely on tool absence alone.
```
✅ "You cannot modify data, generate contract drafts, or access documents outside the knowledge graph."
❌ (omitting this — LLM may attempt tasks outside its tools)
```

**Tool preference order** — tell it which tool to try first for specific lookups. Without this, LLM defaults to Text2Cypher for everything.
```
✅ "For lookups by a known ID or property value, prefer CypherTemplate tools over the Text2Cypher tool."
```

**Uncertainty handling** — tell it to say so when it cannot answer. Prevents hallucination.
```
✅ "If you cannot find an answer using the available tools, say so explicitly. Do not guess."
```

**Output format** — specify structure when the use case demands it.
```
✅ "Always include the source node ID or property in your answer so users can verify."
✅ "For comparisons across multiple items, use a table."
```

**Citation rule** — tell it to reference graph data, not LLM knowledge.
```
✅ "Base all answers on data retrieved from tools. Do not use your training knowledge about the domain."
```

**Explain mode** — when the user asks to explain an answer, the agent should go beyond restating results. Include this block in your system prompt:
```
✅ "If the user asks you to explain your answer:
    1. Describe how you determined the result — which tool you used, which nodes or relationships were traversed, and why.
    2. Suggest ways the user could ask a more precise or targeted question to get better results.
    3. If a CypherTemplate tool would answer this question more reliably than Text2Cypher, propose the template — include the Cypher query, parameter names, and data types.
    4. If a change to the data model (new property, index, or relationship type) would make this query faster or more accurate, describe it."
```

This pattern surfaces agent reasoning and turns every answer into an opportunity to improve the tools and data model over time.

**Signals inventory** — include a signals section in the prompt for each key label and relationship type relevant to the use cases. Without it, the agent sees node labels and properties but must infer their semantic meaning, valid values, and routing logic from the schema alone. A signals inventory makes that knowledge explicit.

Each signal entry should state:
- **What** the signal measures (semantic meaning)
- **Where** it lives in the graph (label, relationship pattern, property)
- **Valid values** (critical for filtering — especially low-cardinality properties)
- **When to use it** (which question types or ranking/filtering scenarios call for it)

Generate this section during Step 5 using the use case discussion and `schema.json`. For every label or relationship that appears in a tool or in the user's questions, write a signal block.

**Template**:
```
## <Domain> Signals

**<Signal Name>** — `(<StartLabel>)-[r:<REL_TYPE>]->(<EndLabel>)` (or `(<Label>)` for node properties)
- Property: `r.<propertyName>` (or `n.<propertyName>`)
- Values: `'value1'` | `'value2'` | `'value3'`
- When to use: <question types or ranking/filtering scenarios>
```

**Example** — recruiting domain:
```
## Candidate Quality Signals

**Skill Proficiency** — `(Person)-[hs:HAS_SKILL]->(Skill)`
- Property: `hs.proficiencyLevel`
- Values: `'expert'` | `'advanced'` | `'intermediate'` | `'beginner'`
- When to use: Ranking candidates, assessing readiness, computing skill depth scores

**Employment Status** — `(Person)`
- Property: `n.status`
- Values: `'active'` | `'inactive'` | `'pending'`
- When to use: Filtering to current employees or open candidates only
```

Rules:
- Include only labels/relationships that appear in the agent's tools or the user's stated questions — do not enumerate the entire schema
- Always include valid values for low-cardinality properties (copy from `schema.json → values`)
- If a property has `has_fulltext_index: true`, note that in the "When to use" line: "Supports full-text search"
- Keep each block to 4–6 lines; signal sections longer than ~300 words start to dilute the prompt budget

### Anti-Patterns

| Anti-pattern | Problem |
|---|---|
| "Answer any question about the graph" | No scope → LLM uses Text2Cypher for everything |
| Prompt that restates tool descriptions | Redundant tokens; contradictions if they diverge |
| No uncertainty clause | LLM fabricates answers when tools return nothing |
| Very long prompt (>500 words) | Dilutes the constraints; LLM ignores later rules |

---

## Tool Names

**Format**: `Verb + specific object`. Max ~5 words.

| ✅ Good | ❌ Bad | Why |
|---|---|---|
| `Get Agreement by ID` | `Agreement Lookup` | No verb → ambiguous trigger |
| `Find Agreements Expiring This Year` | `Date Filter` | Too vague |
| `Count Agreements by Type` | `Aggregation Tool` | Doesn't say what it aggregates |
| `Find Similar Clause Text` | `Semantic Search` | No domain context |
| `Summarize Graph Statistics` | `Text2Cypher Tool` | Never name a tool after its mechanism |

Do NOT include the word "Tool" in a name — redundant and wastes the LLM's routing signal.

---

## Tool Descriptions

The description is the primary signal the LLM uses to select a tool. It must answer three questions:
1. **When** to use this tool (trigger condition)
2. **What** it returns
3. **When NOT** to use it (prevents wrong selection when tools overlap)

### Structure

```
Use [trigger condition]. Returns [what the output contains].
Do NOT use [exclusion condition] — use [alternative tool name] instead.
```

### CypherTemplate

```
✅ "Use when the user asks for a specific agreement by its contract ID.
    Returns party names, agreement type, effective date, and expiration date.
    Do NOT use for aggregations or open-ended discovery — use the aggregation tool instead."

❌ "Runs MATCH (a:Agreement {contract_id: $contract_id}) and returns agreement data."
   (describes the Cypher, not the use case — LLM cannot route from this)
```

Rules:
- Describe the **question pattern**, not the query mechanics
- Name the key parameter in plain language ("by its contract ID", "by city name")
- If a filter parameter has a fixed set of valid values, state that in the description too: `"Valid filter values are: 'Type A', 'Type B', 'Type C'"`

### SimilaritySearch

```
✅ "Use when the user wants to find nodes whose text is semantically similar to a phrase or sentence.
    Returns the top-K most similar results ranked by embedding distance.
    Do NOT use for exact property matches — use a CypherTemplate tool for those."

❌ "Performs vector search on the excerpt_embedding index."
   (mechanism, not use case)
```

Rules:
- Say what kind of text is embedded ("full clause text", "product descriptions", "support ticket summaries")
- Make clear this is approximate/semantic, not exact
- State the exclusion: exact-match queries belong in CypherTemplate

### Text2Cypher

Text2Cypher is the most flexible tool — and the one most likely to be overused. The description must tightly bound its scope.

```
✅ "Use for open-ended discovery and aggregation: counting nodes, grouping by category,
    finding patterns not covered by other tools. Example questions: 'How many agreements
    exist per type?', 'Which organizations appear most frequently?'.
    Do NOT use for lookups by a known ID or property value — use the specific CypherTemplate
    tools for those. Do NOT use for similarity search — use the similarity search tool."

❌ "Translates natural language to Cypher."
   (says nothing about scope — LLM uses it for everything)
```

Rules:
- List 2–3 example questions it handles well — LLM uses these as routing anchors
- Always have at least two explicit exclusions naming the alternative tool
- Put this tool last in the `tools` array — LLM tries tools in order; Text2Cypher is the fallback

---

## CypherTemplate Parameter Descriptions

Parameter descriptions are shown to the LLM when it needs to fill in a parameter value from the user's message. A poor description causes wrong values or failed extractions.

### Rules

**Always state what the parameter represents:**
```
✅ "description": "The unique contract identifier, e.g. 'CUAD-001'"
❌ "description": "id"
```

**Low-cardinality properties — always list valid values:**

When `schema.json → node_props[Label][prop].low_cardinality` is `true`, copy the `values` array verbatim into the description. The LLM will normalize user input to a valid value.

```
✅ "description": "Clause type to filter by. Valid values: \"Anti-Assignment\", \"Exclusivity\", \"Governing Law\", \"IP Ownership Assignment\", \"License Grant\", \"Non-Compete\", \"Termination For Convenience\""

❌ "description": "The type of clause"
   (LLM guesses — may pass a value that matches no nodes)
```

**Date parameters — include format:**
```
✅ "description": "Effective date to filter from. Format: YYYY-MM-DD (e.g. '2023-01-01')"
❌ "description": "Start date"
```

**ID parameters — say where the user gets the value:**
```
✅ "description": "Contract ID from a prior 'Get Agreement' result or from the user's request"
❌ "description": "Contract ID"
```

**Full-text indexed properties** (`has_fulltext_index: true` in schema.json) — especially important to list valid values; the full-text index implies this property is a primary filter target.

### Anti-Patterns

| Anti-pattern | Problem |
|---|---|
| Description is the param name only (`"id"`, `"type"`) | LLM cannot extract correctly from varied user phrasing |
| No valid values on low-cardinality property | LLM invents values; Cypher returns nothing |
| Missing format on date/time param | LLM passes wrong format; Cypher fails silently |
| Description longer than 2000 chars | API truncates; valid values may be cut |

---

## Tool Ordering

The LLM considers tools in array order when multiple tools could answer a question.

Recommended order:
1. Most specific CypherTemplate tools (exact lookups)
2. Broader CypherTemplate tools (filtered searches)
3. SimilaritySearch (if present)
4. Text2Cypher (always last — catches what others can't)

```json
"tools": [
  { "type": "cypherTemplate", "name": "Get Agreement by ID", ... },
  { "type": "cypherTemplate", "name": "Get Agreements by Clause Type", ... },
  { "type": "similaritySearch", "name": "Find Similar Clause Text", ... },
  { "type": "text2cypher", "name": "Discover and Aggregate", ... }
]
```

---

## Checklist Before Creating

- [ ] System prompt has: role sentence, supported use cases, explicit boundaries, tool preference order, uncertainty clause
- [ ] System prompt is ≤500 words
- [ ] Every tool name is a verb + specific object (no "Tool" suffix)
- [ ] Every tool description answers: when to use, what it returns, when NOT to use
- [ ] Every CypherTemplate tool names at least one exclusion with an alternative
- [ ] Text2Cypher is last in the tools array
- [ ] Text2Cypher description has ≥2 explicit exclusions
- [ ] Every parameter on a low-cardinality property lists all valid values verbatim
- [ ] Date/time parameters include format string
- [ ] ID parameters say where the user obtains the value
