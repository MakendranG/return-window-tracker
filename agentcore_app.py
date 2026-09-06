"""
Amazon Bedrock AgentCore Runtime entrypoint for the Return Window Tracker.

This wraps the SAME Strands agent core (agent.py: two deterministic @tools +
LLM drafting + typed structured output) as an HTTP service that AgentCore
Runtime can host. No agent logic is duplicated — this file only adapts the
input/output to the AgentCore payload contract.

Local test:
    python agentcore_app.py
    curl -X POST http://localhost:8080/invocations \
      -H "Content-Type: application/json" \
      -d '{"purchases": [ ... ]}'

Deploy: see DEPLOYMENT.md (AgentCore CLI `agentcore configure/launch`, or the
bedrock-agentcore-starter-toolkit). Requires AWS credentials with Bedrock +
AgentCore permissions.

Built With: Strands Agents SDK on Amazon Bedrock AgentCore.
"""

from __future__ import annotations

import os
from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agent import run_tracker
from generate_sample_data import build_purchases

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict[str, Any]) -> dict[str, Any]:
    """
    AgentCore entrypoint.

    Accepts a JSON payload with an optional "purchases" list. If none is
    provided, it falls back to freshly generated synthetic sample data so the
    endpoint is demoable out of the box.

    Payload:
        {
          "purchases": [ {item, store, purchase_date, return_window_days,
                          price, reason_for_potential_return}, ... ],
          "model": "<optional model id override>"
        }

    Returns the structured TrackerResult dict (digest, needs_you_count,
    auto_handled_count, items[...]).
    """
    purchases = payload.get("purchases") or build_purchases()
    model = payload.get("model") or os.environ.get("STRANDS_MODEL_ID") or None

    # state_path=None keeps the hosted endpoint stateless and repeatable.
    result = run_tracker(purchases, model=model, state_path=None)
    return result


if __name__ == "__main__":
    # Runs a local HTTP server on port 8080 with /invocations and /ping.
    app.run()
