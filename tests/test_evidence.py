"""Evidence extraction against real tau2 tool messages (no LLM)."""

from datetime import date

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage

from merchant_ops.agent.evidence import build_evidence
from merchant_ops.agent.guard import check_tool_call
from merchant_ops.domain.environment import get_environment

TODAY = date(2026, 10, 1)


def run_calls(env, calls):
    """Return a history of assistant tool calls followed by the env's tool messages."""
    history = []
    for i, (name, args) in enumerate(calls):
        call = ToolCall(id=f"c{i}", name=name, arguments=args)
        history.append(AssistantMessage.text("", tool_calls=[call]))
        history.append(env.get_response(call))
    return history


def test_evidence_from_real_tool_results():
    env = get_environment()
    history = run_calls(
        env,
        [
            ("find_merchant_id_by_email", {"email": "marcus@peakoutfitters.com"}),
            ("get_transaction_details", {"transaction_id": "tx_5005"}),
            ("get_dispute_details", {"dispute_id": "dp_7001"}),
        ],
    )
    history.append(UserMessage(role="user", content="Yes, refund it"))
    ev = build_evidence(history, TODAY)
    assert ev.authenticated_merchant_id == "m_1002"
    assert ev.transactions["tx_5005"]["dispute_id"] == "dp_7001"
    assert ev.disputes["dp_7001"]["status"] == "open"

    args = {"transaction_id": "tx_5005", "amount": 89.99, "reason": "customer_request"}
    result = check_tool_call("issue_refund", args, ev)
    assert {v.rule for v in result.violations} == {"DISPUTE"}


def test_failed_lookup_does_not_authenticate():
    env = get_environment()
    history = run_calls(env, [("find_merchant_id_by_email", {"email": "nobody@example.com"})])
    assert build_evidence(history, TODAY).authenticated_merchant_id is None


def test_first_authenticated_merchant_sticks():
    env = get_environment()
    history = run_calls(
        env,
        [
            ("find_merchant_id_by_email", {"email": "priya@lumenstudio.co"}),
            ("find_merchant_id_by_email", {"email": "ana@sunrisebakery.com"}),
            ("get_transaction_details", {"transaction_id": "tx_5001"}),
        ],
    )
    history.append(UserMessage(role="user", content="yes"))
    ev = build_evidence(history, TODAY)
    assert ev.authenticated_merchant_id == "m_1003"
    args = {"transaction_id": "tx_5001", "amount": 42.5, "reason": "customer_request"}
    assert "OWNERSHIP" in {v.rule for v in check_tool_call("issue_refund", args, ev).violations}
