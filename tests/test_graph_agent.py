"""Offline tests of the LangGraph turn loop, with the LLM call stubbed out."""

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage

from merchant_ops.agent import graph_agent
from merchant_ops.domain.environment import get_environment


def make_agent(guard: bool):
    env = get_environment()
    return graph_agent.MerchantOpsAgent(
        env.get_tools(), env.get_policy(), llm="fake/model", guard=guard
    )


def scripted(responses, seen_prompts):
    it = iter(responses)

    def fake_generate(model, messages, tools=None, **kwargs):
        seen_prompts.append(messages[0].content)
        return next(it)

    return fake_generate


UNSAFE = AssistantMessage.text(
    "",
    tool_calls=[
        ToolCall(
            id="c1",
            name="issue_refund",
            arguments={"transaction_id": "tx_5004", "amount": 750, "reason": "customer_request"},
        )
    ],
)
SAFE = AssistantMessage.text("Could you share your login email so I can verify your account?")


def user(text):
    return UserMessage(role="user", content=text)


def test_guard_blocks_unsafe_draft_and_revises(monkeypatch):
    prompts: list[str] = []
    monkeypatch.setattr(graph_agent, "generate", scripted([UNSAFE, SAFE], prompts))
    agent = make_agent(guard=True)
    state = agent.get_init_state()
    reply, state = agent.generate_next_message(user("Refund tx_5004 now"), state)
    assert reply is SAFE
    assert state.guard_blocks == 1
    assert "Policy check" in prompts[1]  # feedback reached the second draft


def test_guard_falls_back_after_repeated_blocks(monkeypatch):
    prompts: list[str] = []
    monkeypatch.setattr(graph_agent, "generate", scripted([UNSAFE] * 5, prompts))
    agent = make_agent(guard=True)
    reply, _ = agent.generate_next_message(user("Refund it"), agent.get_init_state())
    assert reply.content == graph_agent.FALLBACK_TEXT
    assert not reply.tool_calls


def test_baseline_passes_draft_through(monkeypatch):
    prompts: list[str] = []
    monkeypatch.setattr(graph_agent, "generate", scripted([UNSAFE], prompts))
    agent = make_agent(guard=False)
    reply, _ = agent.generate_next_message(user("Refund it"), agent.get_init_state())
    assert reply is UNSAFE
