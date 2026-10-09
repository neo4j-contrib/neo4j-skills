# Evaluation Dataset Guide

How to generate an Aura Agent evaluation dataset (JSON) that can be imported in the Aura console
(Agent → Evaluation). Source: https://neo4j.com/docs/aura/aura-agent/#agent-evaluation

## Platform facts

- Dataset = project-level asset, **max 50 questions**.
- Questions become **permanently read-only once saved**; no version history. Get it right before import.
- Per question: `query_number` (1-based), `query_text`, `expected_answer`, optional `expected_tool_calls`.
- Metrics: accuracy, relevance, grounding (0–1), tool trajectory (Jaccard of expected vs actual tool calls), latency. Scores < 0.8 are flagged.
- **Never invent tool calls.** Tool names, types and parameter names must come from the agent's actual definition (`manage_agent.py get`, or the console export).

## File format

```json
{
  "dataset_name": "<agent-name>-eval",
  "description": "<what is covered, which tools>",
  "questions": [
    {
      "query_number": 1,
      "query_text": "...",
      "expected_answer": "...",
      "expected_tool_calls": [
        {"tool_name": "<exact tool name>", "tool_type": "cypher_template", "tool_input": {"<param>": "<value>"}}
      ]
    }
  ]
}
```

### tool_type mapping (agent config `type` → dataset `tool_type`)

| Agent tool `type` | `tool_type` | `tool_input` |
|---|---|---|
| `cypherTemplate` | `cypher_template` | Template parameter names → values. Include all required params; `is_optional` params may be omitted (include when the question implies them, e.g. a limit); `is_list` params take a JSON array, e.g. `{"contract_id": [12, 15]}` |
| `text2cypher` | `text2cypher` | `{"query": "<natural-language question the agent would pass>"}` |
| `similaritySearch` | `similarity_search` | `{"query": "<search text>"}`. The exported config declares no input parameters and the docs give no example, so `query` is an assumption — confirm against a real invocation's reasoning chain (`invoke_agent.py --raw`) |

Zero-result and schema questions: still list the tool the agent should call (usually `text2cypher`).
Multi-tool questions: list calls in the order the agent should make them.

## Inputs required (do not generate from description alone)

1. Agent definition: `uv run python3 scripts/manage_agent.py get --agent-id "$AURA_AGENT_ID" > agent.json`
2. `schema.json` (Step 4) for labels, properties, relationships, low-cardinality values.
3. **Ground truth from the database.** Expected answers MUST come from running Cypher against the graph
   (via `neo4j` driver using `.env`, or an available Neo4j MCP tool) — never from model guesses.
   Record the Cypher used for each question in a side file (`eval_dataset.provenance.json`), not in the dataset.

## Question budget (total ≤ 50)

Default allocation; scale down proportionally if the agent has few tools. Always keep the total ≤ 50.

| # | Category | Default count |
|---|---|---|
| 1 | Core Factual | 8 |
| 2 | Per-tool probing | 3 per non-Text2Cypher tool (cap total at 15; if >5 tools, prioritise tools by likely usage) |
| 3 | Semantic search | 4 (2 exact-match, 2 paraphrased) — skip entirely if no `similaritySearch` tool |
| 4 | Multi-tool composition | 6 |
| 5 | Text2Cypher stress | 5.1:4, 5.2:3, 5.3:3, 5.4:3, 5.5:3 = 16 |

Reallocate unused slots (e.g. no similarity tool → +4 to Category 1/4). Tell the user the final per-category counts.

## Category definitions

### Category 1 — Core Factual
Answerable from the tools; cover aggregate lookups, counts, filters, comparisons, and compound logic.
Include at least one each of: count, aggregate (sum/avg/max/min), filter on a property, comparison
(A vs B / greater than), compound **AND**, **NOT** / exclusion. Anchor on real values from `schema.json`.
Expected tool: whichever tool the agent *should* choose (template if one fits, else text2cypher).

### Category 2 — Per-tool probing
For **each distinct tool except Text2Cypher** (Text2Cypher is covered by Category 5), write three questions
shaped by that tool's config (name, description, template, parameters, `data_type`, valid values):
1. **Nail it** — a question the tool should answer perfectly: a real parameter value, in the tool's described scope.
2. **Edge case** — exploits a *hypothesised* limit: `top_k` cut-off (ask for "all"/more results than `top_k`), 
   parameter at boundary (entity with zero matches, many matches, special chars, case/spelling variance,
   low-cardinality value not exactly matching), hard-coded `LIMIT`, directionality, or null properties.
3. **Structural gap** — exploits a gap *confirmed by reading the config*: e.g. template doesn't return a
   property the user asks for, can't filter by a property that exists in the schema, only matches one
   relationship direction, no parameter for a requested filter. The expected answer reflects the
   correct truth (agent should fall back to Text2Cypher if available, or say it cannot).
   Read the template Cypher itself for gaps. Typical ones: a `LIMIT` applied before a later `MATCH`/aggregation (fewer rows than the limit); an inner `MATCH` on a related node (e.g. a required `Country` link) that silently drops entities lacking it; fulltext/fuzzy name matching returning near-matches; a similarity tool whose `top_k` caps results; `post_processing_cypher` that only returns some properties. Verify the gap by running the template's Cypher.
   State the gap you verified in the provenance file. If no gap exists for a tool, replace with a second edge case.

### Category 3 — Semantic search
Only for `similaritySearch` tools. Look up real text from the indexed node property first.
- **Exact-match retrieval** (2 by default): query uses wording copied/near-copied from a stored passage; expected answer names that node/passage.
- **Paraphrased / conceptual** (2 by default): same meaning, no shared keywords; expected answer is the node a human would judge relevant. Verify by running the vector search yourself when possible.
Write expected answers around entities/facts that must appear, not exact wording.

### Category 4 — Multi-tool composition
Each question needs **2–4 tool calls chained** (output of one feeds another, or results from different tools are merged):
e.g. similarity search → cypher template on the hit → text2cypher aggregation. `expected_tool_calls` has 2–4 entries in order.
Do not create a multi-tool question unless the agent's tools genuinely cannot answer it in one call.

### Category 5 — Text2Cypher stress (all use `text2cypher` expected tool; `tool_input.query` is the question text unless a clearer paraphrase is natural)
- **5.1** 2–3 hop traversals, filters, basic aggregation (`count`, `collect`, `avg`).
- **5.2** `WITH` pipelines / `OPTIONAL MATCH` / compound constraints (e.g. "entities with X but without Y, ordered by count").
- **5.3** Shortest path and variable-length traversals (`shortestPath`, `[*1..4]`); pick endpoints verified to be connected, state hop count.
- **5.4** Questions that **must return zero records** (hallucination test): plausible entity that does not exist, valid entity + non-existent relationship, real label with impossible filter value. Expected answer: states that no results were found / the data does not contain it — never an invented answer. Verify zero rows in the DB.
- **5.5** Knowledge-graph **schema** questions: node labels, relationship types, properties of a label, which labels connect via which relationship. Expected answer from `schema.json`.

## Writing expected answers

- Concrete, complete, and self-contained (include the numbers/names returned by the ground-truth query).
- For lists > 10 items, state the count and the first items/top-N the question asks for (ask questions with bounded answers).
- For zero-result questions: "No X found …", not "I don't know".
- No Cypher in the answer. Don't embed unstable values (timestamps, "today").

## Workflow

1. Gather inputs (agent JSON, `schema.json`); list tools with name/type/params.
2. Propose the category plan with counts; confirm with the user if the tool set is unusual.
3. For each question: draft → run ground-truth Cypher → write expected answer + tool calls.
4. Write `eval_dataset.json` (+ `eval_dataset.provenance.json` with Cypher and rationale per question).
5. Validate: `uv run python3 scripts/validate_eval_dataset.py eval_dataset.json --agent agent.json`
6. Show category counts and a sample to the user. Tell them to import in console: Agent → Evaluation → datasets
   (remember questions are read-only after save).
