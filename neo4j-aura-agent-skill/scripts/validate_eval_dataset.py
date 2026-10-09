#!/usr/bin/env python3
"""Validate an Aura Agent evaluation dataset JSON.

Usage: validate_eval_dataset.py eval_dataset.json [--agent agent.json]

With --agent (output of `manage_agent.py get`, or the console JSON export) every expected tool call
is checked against the agent's real tools: name, type, and cypherTemplate parameters
(required ones present, no unknown ones, `is_list` params given as arrays; `is_optional` may be omitted).
"""

import argparse
import json
import sys

MAX_QUESTIONS = 50
TYPE_MAP = {
    "cypherTemplate": "cypher_template",
    "text2cypher": "text2cypher",
    "similaritySearch": "similarity_search",
}


def agent_tools(path: str) -> dict:
    with open(path) as f:
        data = json.load(f)
    data = data.get("data", data) if isinstance(data, dict) else data
    tools = {}
    for t in data.get("tools", []):
        plist = t.get("config", {}).get("parameters", [])
        tools[t.get("name")] = {
            "type": TYPE_MAP.get(t.get("type"), t.get("type")),
            "params": {p["name"] for p in plist},
            "required": {p["name"] for p in plist if not p.get("is_optional")},
            "lists": {p["name"] for p in plist if p.get("is_list")},
        }
    return tools


def validate(ds: dict, tools: dict | None) -> list[str]:
    errs = []
    for k in ("dataset_name", "description", "questions"):
        if k not in ds:
            errs.append(f"missing top-level key: {k}")
    qs = ds.get("questions", [])
    if not qs:
        errs.append("no questions")
    if len(qs) > MAX_QUESTIONS:
        errs.append(f"{len(qs)} questions exceeds max {MAX_QUESTIONS}")
    seen_text = set()
    for i, q in enumerate(qs, 1):
        p = f"Q{i}"
        if q.get("query_number") != i:
            errs.append(f"{p}: query_number should be {i}, got {q.get('query_number')}")
        for k in ("query_text", "expected_answer"):
            if not isinstance(q.get(k), str) or not q[k].strip():
                errs.append(f"{p}: missing/empty {k}")
        text = (q.get("query_text") or "").strip().lower()
        if text in seen_text:
            errs.append(f"{p}: duplicate query_text")
        seen_text.add(text)
        for j, c in enumerate(q.get("expected_tool_calls", []), 1):
            cp = f"{p} call {j}"
            for k in ("tool_name", "tool_type", "tool_input"):
                if k not in c:
                    errs.append(f"{cp}: missing {k}")
            if tools is None or c.get("tool_name") is None:
                continue
            t = tools.get(c["tool_name"])
            if t is None:
                errs.append(f"{cp}: tool '{c['tool_name']}' not in agent (have: {sorted(tools)})")
                continue
            if c.get("tool_type") != t["type"]:
                errs.append(f"{cp}: tool_type '{c.get('tool_type')}' should be '{t['type']}'")
            inp = c.get("tool_input", {})
            if t["type"] == "cypher_template":
                missing = t["required"] - set(inp)
                unknown = set(inp) - t["params"]
                if missing:
                    errs.append(f"{cp}: missing required params {sorted(missing)}")
                if unknown:
                    errs.append(f"{cp}: unknown params {sorted(unknown)} (template has {sorted(t['params'])})")
                for n in t["lists"] & set(inp):
                    if not isinstance(inp[n], list):
                        errs.append(f"{cp}: param '{n}' is_list, value must be a JSON array")
            if t["type"] in ("text2cypher", "similarity_search") and "query" not in inp:
                errs.append(f"{cp}: tool_input should contain 'query'")
    return errs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset")
    ap.add_argument("--agent", help="agent definition JSON to check tool calls against")
    args = ap.parse_args()
    with open(args.dataset) as f:
        ds = json.load(f)
    errs = validate(ds, agent_tools(args.agent) if args.agent else None)
    if errs:
        print("\n".join(f"ERROR: {e}" for e in errs))
        sys.exit(1)
    print(f"OK: {len(ds['questions'])} questions" + (" (tool calls checked against agent)" if args.agent else ""))


if __name__ == "__main__":
    main()
