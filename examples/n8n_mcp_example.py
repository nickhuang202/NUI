#!/usr/bin/env python3
"""
n8n MCP Server - Practical Usage Examples
Demonstrates how to interact with n8n using the REST API (same calls the MCP server makes).

API Key: antigravity-mcp (expires Mar 25 2026)
n8n instance: http://172.17.9.199:5678
"""

import json
import requests

N8N_URL   = "http://172.17.9.199:5678"
API_KEY   = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiJjODRhMzg4Ni0xMDgxLTQ3YWItYjRhMC0wNTZjZTIwNmY1MDAiL"
    "CJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZWU4MjI2ZWMt"
    "MWFmYi00ZTdkLWE1MmUtNDA5ZTZlM2RmZTkyIiwiaWF0IjoxNzcxODI1Nzc1LCJ"
    "leHAiOjE3NzQ0MTEyMDB9.XSAhjiwciDg194v1zrIGpJTbX2kCQp03c672x834Aio"
)

HEADERS = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json",
}

# ──────────────────────────────────────────────
# Example 1: List all workflows
# ──────────────────────────────────────────────
def list_workflows():
    print("\n=== Example 1: List all workflows ===")
    resp = requests.get(f"{N8N_URL}/api/v1/workflows", headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    for wf in data.get("data", []):
        status = "🟢 Active" if wf["active"] else "🔴 Inactive"
        print(f"  [{status}] {wf['name']}  (id={wf['id']})")


# ──────────────────────────────────────────────
# Example 2: Get details of a specific workflow
# ──────────────────────────────────────────────
def get_workflow(workflow_id: str):
    print(f"\n=== Example 2: Inspect workflow {workflow_id} ===")
    resp = requests.get(f"{N8N_URL}/api/v1/workflows/{workflow_id}", headers=HEADERS, timeout=10)
    resp.raise_for_status()
    wf = resp.json()
    print(f"  Name   : {wf['name']}")
    print(f"  Active : {wf['active']}")
    print(f"  Nodes  : {[n['name'] for n in wf['nodes']]}")


# ──────────────────────────────────────────────
# Example 3: Activate / Deactivate a workflow
# ──────────────────────────────────────────────
def activate_workflow(workflow_id: str, activate: bool = True):
    action = "activate" if activate else "deactivate"
    print(f"\n=== Example 3: {action.capitalize()} workflow {workflow_id} ===")
    resp = requests.post(
        f"{N8N_URL}/api/v1/workflows/{workflow_id}/{action}",
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    wf = resp.json()
    print(f"  Workflow '{wf['name']}' active={wf['active']}")


# ──────────────────────────────────────────────
# Example 4: Trigger a workflow via Webhook
# ──────────────────────────────────────────────
def trigger_via_webhook(webhook_path: str, payload: dict):
    print(f"\n=== Example 4: Trigger webhook /{webhook_path} ===")
    resp = requests.post(
        f"{N8N_URL}/webhook/{webhook_path}",
        json=payload,
        timeout=10,
    )
    print(f"  HTTP {resp.status_code}: {resp.text[:200]}")


# ──────────────────────────────────────────────
# Example 5: List recent executions
# ──────────────────────────────────────────────
def list_executions(workflow_id: str = None, limit: int = 5):
    print(f"\n=== Example 5: Recent executions (limit={limit}) ===")
    params = {"limit": limit}
    if workflow_id:
        params["workflowId"] = workflow_id
    resp = requests.get(
        f"{N8N_URL}/api/v1/executions", headers=HEADERS, params=params, timeout=10
    )
    resp.raise_for_status()
    data = resp.json()
    for ex in data.get("data", []):
        print(f"  [{ex['status']}] id={ex['id']}  started={ex.get('startedAt','?')}")


# ──────────────────────────────────────────────
# Example 6: Create a new workflow via API
# ──────────────────────────────────────────────
def create_workflow(name: str):
    print(f"\n=== Example 6: Create workflow '{name}' ===")
    workflow_json = {
        "name": name,
        "nodes": [
            {
                "id": "node-1",
                "name": "Manual Trigger",
                "type": "n8n-nodes-base.manualTrigger",
                "typeVersion": 1,
                "position": [250, 300],
                "parameters": {},
            },
            {
                "id": "node-2",
                "name": "Apply Topology",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4,
                "position": [450, 300],
                "parameters": {
                    "method": "POST",
                    "url": "http://172.17.9.199:5000/api/apply_topology",
                    "sendBody": True,
                    "contentType": "json",
                    "jsonBody": json.dumps({
                        "platform": "MINIPACK3BA",
                        "config_filename": "Env_Test.materialized_JSON",
                    }),
                },
            },
        ],
        "connections": {
            "Manual Trigger": {
                "main": [[{"node": "Apply Topology", "type": "main", "index": 0}]]
            }
        },
        "settings": {"executionOrder": "v1"},
    }
    resp = requests.post(
        f"{N8N_URL}/api/v1/workflows",
        headers=HEADERS,
        json=workflow_json,
        timeout=10,
    )
    resp.raise_for_status()
    new_wf = resp.json()
    print(f"  Created! id={new_wf['id']}  name={new_wf['name']}")
    return new_wf["id"]


# ──────────────────────────────────────────────
# Run all examples
# ──────────────────────────────────────────────
if __name__ == "__main__":
    MY_WORKFLOW_ID = "1o6gsiIf9peXugRo"

    try:
        list_workflows()
    except Exception as e:
        print(f"  ERROR: {e}")

    try:
        get_workflow(MY_WORKFLOW_ID)
    except Exception as e:
        print(f"  ERROR: {e}")

    try:
        list_executions(workflow_id=MY_WORKFLOW_ID)
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\nDone! Uncomment other examples in __main__ to run them.")
    print("  - activate_workflow(MY_WORKFLOW_ID, activate=True)")
    print("  - trigger_via_webhook('your-path', {'key': 'value'})")
    print("  - create_workflow('My New Workflow')")
