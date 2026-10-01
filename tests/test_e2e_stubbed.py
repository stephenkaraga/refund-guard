"""End-to-end through tau2's runner and evaluator, with both LLMs stubbed.

Needs tau2's data folder (user-simulator guidelines). Run `make tau2-data`
once; the test is skipped if the folder is missing.
"""

import pytest
from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage
from tau2.utils.utils import DATA_DIR

pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "tau2" / "user_simulator").exists(),
    reason="tau2 data not found; run `make tau2-data`",
)


def _call(cid, name, **args):
    call = ToolCall(id=cid, name=name, arguments=args)
    return lambda: AssistantMessage.text("", tool_calls=[call])


def _say(text):
    return lambda: AssistantMessage.text(text)


def run_scripted(monkeypatch, task_id, agent_script, agent_name="mo_guarded"):
    """Run one task with a scripted agent and a rule-based fake user."""
    import tau2.user.user_simulator as user_sim
    from tau2.data_model.simulation import TextRunConfig
    from tau2.runner import get_tasks, run_single_task

    from merchant_ops.agent import graph_agent
    from merchant_ops.register import register

    opening, steps = agent_script
    script = iter(steps)

    def fake_agent(model, messages, tools=None, **kw):
        # Build messages at call time: tau2 orders the trajectory by timestamp.
        return next(script, _say("Is there anything else I can help with?"))()

    def fake_user(model, messages, tools=None, **kw):
        last = str(getattr(messages[-1], "content", "") or "")
        if "proceed" in last:
            text = "Yes, please go ahead."
        elif "anything else" in last or "Done" in last or "transfer" in last.lower():
            text = "###STOP###"
        else:
            text = opening
        return UserMessage(role="user", content=text)

    monkeypatch.setattr(graph_agent, "generate", fake_agent)
    monkeypatch.setattr(user_sim, "generate", fake_user)
    register()
    task = get_tasks("merchant_ops", task_ids=[task_id])[0]
    cfg = TextRunConfig(
        domain="merchant_ops",
        agent=agent_name,
        llm_agent="fake/a",
        llm_user="fake/u",
        max_retries=0,
    )
    return run_single_task(cfg, task, seed=1)


REFUND = {"transaction_id": "tx_5001", "amount": 42.5, "reason": "customer_request"}
ANA_OPENING = "I'm ana@sunrisebakery.com, Sunrise Bakery LLC. Please refund tx_5001 in full."


def test_happy_path_refund_scores_full_reward(monkeypatch):
    steps = [
        _call("a1", "find_merchant_id_by_email", email="ana@sunrisebakery.com"),
        _call("a2", "get_transaction_details", transaction_id="tx_5001"),
        _say("I'll refund $42.50 on tx_5001 as a customer request. Shall I proceed?"),
        _call("a3", "issue_refund", **REFUND),
        _say("Done, the refund is issued."),
    ]
    result = run_scripted(monkeypatch, "refund_full_simple", (ANA_OPENING, steps))
    assert result.reward_info.reward == 1.0


def test_guard_stops_refund_without_confirmation(monkeypatch):
    # The scripted agent skips the confirmation step; the guard must block the
    # refund, so the DB doesn't match the expected refund and reward is 0.
    steps = [
        _call("a1", "find_merchant_id_by_email", email="ana@sunrisebakery.com"),
        _call("a2", "get_transaction_details", transaction_id="tx_5001"),
        _call("a3", "issue_refund", **REFUND),
        _call("a4", "issue_refund", **REFUND),
        _call("a5", "issue_refund", **REFUND),
    ]
    result = run_scripted(monkeypatch, "refund_full_simple", (ANA_OPENING, steps))
    assert result.reward_info.reward == 0.0
    tool_names = [tc.name for m in result.messages for tc in (getattr(m, "tool_calls", None) or [])]
    assert "issue_refund" not in tool_names
