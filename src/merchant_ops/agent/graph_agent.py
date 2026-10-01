"""LangGraph agent for tau2-bench, with an optional deterministic policy guard.

Each tau2 turn runs a small LangGraph graph:

    draft --> check --(allowed)--> END
                 |--(blocked, retries left)--> draft   (guard feedback added)
                 |--(blocked, no retries)----> fallback --> END

With guard=False the graph is draft --> END, so the baseline and guarded agents
differ only by the guard. That keeps the before/after comparison honest.
"""

from __future__ import annotations

from datetime import date
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict
from tau2.agent.base_agent import HalfDuplexAgent, ValidAgentInputMessage
from tau2.data_model.message import AssistantMessage, Message, SystemMessage
from tau2.environment.toolkit import Tool
from tau2.utils.llm_utils import generate

from merchant_ops.agent.evidence import build_evidence
from merchant_ops.agent.guard import check_tool_call

TODAY = date(2026, 10, 1)  # matches db.json "today" and the policy
DEFAULT_LLM = "anthropic/claude-sonnet-4-5"  # any LiteLLM model id works
MAX_REVISIONS = 2

SYSTEM_PROMPT = """You are a merchant support agent for a payments platform.

## Policy
{policy}

Follow the policy exactly. Use tools for facts; never guess. Make at most one tool call per turn."""

FALLBACK_TEXT = (
    "I'm not able to complete that request under our support policy. "
    "Would you like me to transfer you to a specialist?"
)


class AgentState(BaseModel):
    """Conversation state carried between tau2 turns."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    system_messages: list[SystemMessage]
    messages: list[Any]
    guard_blocks: int = 0  # how many drafts the guard rejected (reported in evals)


class TurnState(TypedDict, total=False):
    history: list[Any]
    feedback: list[str]
    revisions: int
    draft: AssistantMessage | None


class MerchantOpsAgent(HalfDuplexAgent[AgentState]):
    def __init__(
        self,
        tools: list[Tool],
        domain_policy: str,
        llm: str = DEFAULT_LLM,
        llm_args: dict | None = None,
        guard: bool = True,
    ):
        super().__init__(tools=tools, domain_policy=domain_policy)
        self.llm = llm
        self.llm_args = llm_args or {}
        self.guard = guard
        self._graph = self._build_graph()

    # ---------- tau2 interface ----------

    def get_init_state(self, message_history: list[Message] | None = None) -> AgentState:
        system = SystemMessage(
            role="system", content=SYSTEM_PROMPT.format(policy=self.domain_policy)
        )
        return AgentState(system_messages=[system], messages=list(message_history or []))

    def generate_next_message(
        self, message: ValidAgentInputMessage, state: AgentState
    ) -> tuple[AssistantMessage, AgentState]:
        state.messages.append(message)
        out = self._graph.invoke({"history": state.messages, "feedback": [], "revisions": 0})
        state.guard_blocks += out.get("revisions", 0)
        response = out["draft"]
        state.messages.append(response)
        return response, state

    # ---------- graph ----------

    def _build_graph(self):
        g = StateGraph(TurnState)
        g.add_node("draft", self._draft)
        g.add_edge(START, "draft")
        if not self.guard:
            g.add_edge("draft", END)
            return g.compile()
        g.add_node("check", self._check)
        g.add_node("fallback", self._fallback)
        g.add_edge("draft", "check")
        g.add_conditional_edges(
            "check", self._route, {"done": END, "revise": "draft", "fallback": "fallback"}
        )
        g.add_edge("fallback", END)
        return g.compile()

    def _draft(self, s: TurnState) -> TurnState:
        content = SYSTEM_PROMPT.format(policy=self.domain_policy)
        if s.get("feedback"):
            notes = "\n".join(f"- {f}" for f in s["feedback"])
            content += (
                "\n\n## Policy check\nYour last proposed action was blocked:\n"
                f"{notes}\nChoose a compliant next step."
            )
        system = SystemMessage(role="system", content=content)
        draft = generate(
            model=self.llm,
            tools=self.tools,
            messages=[system] + s["history"],
            call_name="merchant_ops_draft",
            **self.llm_args,
        )
        return {"draft": draft}

    def _check(self, s: TurnState) -> TurnState:
        draft = s["draft"]
        if not draft or not draft.tool_calls:
            return {"feedback": []}
        ev = build_evidence(s["history"], TODAY)
        problems = [
            str(v)
            for call in draft.tool_calls
            for v in check_tool_call(call.name, call.arguments, ev).violations
        ]
        if not problems:
            return {"feedback": []}
        return {"feedback": problems, "revisions": s.get("revisions", 0) + 1}

    def _route(self, s: TurnState) -> str:
        if not s.get("feedback"):
            return "done"
        return "revise" if s.get("revisions", 0) <= MAX_REVISIONS else "fallback"

    def _fallback(self, s: TurnState) -> TurnState:
        return {"draft": AssistantMessage.text(FALLBACK_TEXT)}


def create_baseline_agent(tools, domain_policy, **kwargs) -> MerchantOpsAgent:
    return MerchantOpsAgent(
        tools,
        domain_policy,
        llm=kwargs.get("llm") or DEFAULT_LLM,
        llm_args=kwargs.get("llm_args"),
        guard=False,
    )


def create_guarded_agent(tools, domain_policy, **kwargs) -> MerchantOpsAgent:
    return MerchantOpsAgent(
        tools,
        domain_policy,
        llm=kwargs.get("llm") or DEFAULT_LLM,
        llm_args=kwargs.get("llm_args"),
        guard=True,
    )
