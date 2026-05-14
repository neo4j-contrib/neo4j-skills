#!/usr/bin/env python3
"""Invoke an Aura Agent with a natural language query.

Usage:
  python3 scripts/invoke_agent.py --org-id ORG --project-id PROJ --agent-id AGENT "your question"
  python3 scripts/invoke_agent.py --agent-id AGENT "your question" --raw
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

try:
    import requests
except ImportError:
    sys.exit("requests not found — run: pip install requests")

BASE = "https://api.neo4j.io"
V2 = f"{BASE}/v2beta1"


def get_token() -> str:
    client_id = os.environ.get("AURA_CLIENT_ID")
    client_secret = os.environ.get("AURA_CLIENT_SECRET")
    if not client_id or not client_secret:
        sys.exit("ERROR: AURA_CLIENT_ID and AURA_CLIENT_SECRET must be set in .env or environment")
    r = requests.post(
        f"{BASE}/oauth/token",
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
    )
    r.raise_for_status()
    return r.json()["access_token"]


def main():
    parser = argparse.ArgumentParser(description="Invoke an Aura Agent")
    parser.add_argument("--org-id", default=os.environ.get("AURA_ORG_ID"))
    parser.add_argument("--project-id", default=os.environ.get("AURA_PROJECT_ID"))
    parser.add_argument("--agent-id", default=os.environ.get("AURA_AGENT_ID"))
    parser.add_argument("query", help="Natural language query to send to the agent")
    parser.add_argument("--raw", action="store_true", help="Print full JSON response (includes reasoning chain)")
    args = parser.parse_args()

    for field in ("org_id", "project_id", "agent_id"):
        if not getattr(args, field):
            flag = f"--{field.replace('_', '-')}"
            env = f"AURA_{field.upper()}"
            sys.exit(f"ERROR: {flag} required (or set {env} in .env)")

    token = get_token()
    url = f"{V2}/organizations/{args.org_id}/projects/{args.project_id}/agents/{args.agent_id}/invoke"

    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"input": args.query},
    )
    r.raise_for_status()
    response = r.json()

    if args.raw:
        print(json.dumps(response, indent=2))
        return

    data = response if isinstance(response, (list, str)) else response.get("data", response)

    if data.get("type") == "error":
        err = data.get("error", {})
        sys.exit(f"Agent error ({err.get('status_code', '?')}): {err.get('message', 'unknown error')}")

    for block in data.get("content", []):
        if block.get("type") == "text":
            print(block["text"])

    usage = data.get("usage", {})
    if usage:
        total = usage.get("total_tokens", "?")
        req = usage.get("request_tokens", "?")
        resp = usage.get("response_tokens", "?")
        print(f"\n[tokens — request: {req}, response: {resp}, total: {total}]")


if __name__ == "__main__":
    main()
