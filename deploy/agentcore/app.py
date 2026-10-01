"""Bedrock AgentCore Runtime entrypoint (stub).

Runs the same MerchantOpsAgent the benchmark measures, behind AgentCore's
HTTP contract. Locally, `python deploy/agentcore/app.py` serves on :8080.

What is stubbed vs. production (see deploy/agentcore/README.md):
- Tools run in-process against the mock DB. In production they become
  AgentCore Gateway targets over the real payments API.
- Conversation state lives in a dict. In production it lives in AgentCore Memory.
- The guard runs in the agent. In production, also mirror the write rules in
  AgentCore Policy (Cedar) so the gateway enforces them even if the agent is bypassed.
"""

from __future__ import annotations

from typing import Any

from bedrock_agentcore import BedrockAgentCoreApp
from tau2.data_model.message import UserMessage

from merchant_ops.agent.graph_agent import DEFAULT_LLM, MerchantOpsAgent
from merchant_ops.domain.environment import get_environment

MAX_TOOL_STEPS = 8

app = BedrockAgentCoreApp()
_env = get_environment()
_agent = MerchantOpsAgent(_env.get_tools(), _env.get_policy(), llm=DEFAULT_LLM, guard=True)
_sessions: dict[str, Any] = {}  # TODO: replace with AgentCore Memory


@app.entrypoint
def invoke(payload: dict) -> dict:
    session_id = str(payload.get("session_id", "default"))
    text = payload.get("message")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("payload.message must be a non-empty string")

    state = _sessions.get(session_id) or _agent.get_init_state()
    message: Any = UserMessage(role="user", content=text)

    # Let the agent call tools until it produces a reply for the merchant.
    for _ in range(MAX_TOOL_STEPS):
        reply, state = _agent.generate_next_message(message, state)
        if not reply.tool_calls:
            break
        call = reply.tool_calls[0]
        message = _env.get_response(call)  # TODO: route through AgentCore Gateway
    _sessions[session_id] = state
    return {"reply": reply.content, "guard_blocks": state.guard_blocks}


if __name__ == "__main__":
    app.run()
