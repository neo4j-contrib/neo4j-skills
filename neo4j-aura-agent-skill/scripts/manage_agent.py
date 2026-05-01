#!/usr/bin/env python3
"""Manage Aura Agents via the v2beta1 REST API.

Commands: list, create, get, update (PATCH), delete
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


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def agents_url(org_id: str, project_id: str, agent_id: str = "") -> str:
    base = f"{V2}/organizations/{org_id}/projects/{project_id}/agents"
    return f"{base}/{agent_id}" if agent_id else base


def unwrap(response: requests.Response):
    data = response.json()
    if isinstance(data, (list, str)):
        return data
    return data.get("data", data)


def cmd_list(args, token: str):
    r = requests.get(agents_url(args.org_id, args.project_id), headers=headers(token))
    r.raise_for_status()
    agents = unwrap(r)
    if not agents:
        print("(no agents found)")
        return
    items = agents if isinstance(agents, list) else [agents]
    for a in items:
        status = "enabled" if a.get("enabled") else "disabled"
        print(f"ID:       {a['id']}")
        print(f"Name:     {a['name']}")
        print(f"Status:   {status}")
        if a.get("endpoint_link"):
            print(f"Endpoint: {a['endpoint_link']}")
        if a.get("mcp_endpoint_link"):
            print(f"MCP:      {a['mcp_endpoint_link']}")
        tools = a.get("tools", [])
        if tools:
            print(f"Tools:    {', '.join(t.get('name', t.get('type', '?')) for t in tools)}")
        print()


def cmd_create(args, token: str):
    with open(args.config) as f:
        payload = json.load(f)
    r = requests.post(agents_url(args.org_id, args.project_id), headers=headers(token), json=payload)
    r.raise_for_status()
    data = unwrap(r)
    print(json.dumps(data, indent=2))
    agent_id = data.get("id")
    if agent_id:
        print(f"\nAgent created. Save this ID:\nAURA_AGENT_ID={agent_id}")


def cmd_get(args, token: str):
    r = requests.get(agents_url(args.org_id, args.project_id, args.agent_id), headers=headers(token))
    r.raise_for_status()
    print(json.dumps(unwrap(r), indent=2))


def cmd_update(args, token: str):
    with open(args.config) as f:
        payload = json.load(f)
    r = requests.patch(
        agents_url(args.org_id, args.project_id, args.agent_id),
        headers=headers(token),
        json=payload,
    )
    r.raise_for_status()
    print(json.dumps(unwrap(r), indent=2))


def cmd_delete(args, token: str):
    r = requests.delete(agents_url(args.org_id, args.project_id, args.agent_id), headers=headers(token))
    r.raise_for_status()
    print(f"Agent {args.agent_id} deleted (status {r.status_code})")


def main():
    parser = argparse.ArgumentParser(description="Manage Aura Agents (v2beta1)")
    parser.add_argument("--org-id", default=os.environ.get("AURA_ORG_ID"), help="Organization ID")
    parser.add_argument("--project-id", default=os.environ.get("AURA_PROJECT_ID"), help="Project ID")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all agents in project")

    p_create = sub.add_parser("create", help="Create agent from JSON config file")
    p_create.add_argument("--config", required=True, help="Path to JSON config (see assets/contract-review-agent.json)")

    p_get = sub.add_parser("get", help="Get full agent details")
    p_get.add_argument("--agent-id", default=os.environ.get("AURA_AGENT_ID"), required=False)

    p_update = sub.add_parser("update", help="Partial update (PATCH) agent")
    p_update.add_argument("--agent-id", default=os.environ.get("AURA_AGENT_ID"), required=False)
    p_update.add_argument("--config", required=True, help="Path to JSON with fields to patch")

    p_delete = sub.add_parser("delete", help="Delete agent (irreversible)")
    p_delete.add_argument("--agent-id", default=os.environ.get("AURA_AGENT_ID"), required=False)

    args = parser.parse_args()

    if not args.org_id:
        sys.exit("ERROR: --org-id required (or set AURA_ORG_ID in .env)")
    if not args.project_id:
        sys.exit("ERROR: --project-id required (or set AURA_PROJECT_ID in .env)")

    for cmd in ("get", "update", "delete"):
        if args.command == cmd and not args.agent_id:
            sys.exit(f"ERROR: --agent-id required for {cmd} (or set AURA_AGENT_ID in .env)")

    token = get_token()

    dispatch = {
        "list": cmd_list,
        "create": cmd_create,
        "get": cmd_get,
        "update": cmd_update,
        "delete": cmd_delete,
    }
    dispatch[args.command](args, token)


if __name__ == "__main__":
    main()
