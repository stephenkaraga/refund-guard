from datetime import date

from merchant_ops.agent.guard import Evidence, check_tool_call

TODAY = date(2026, 10, 1)


def txn(**kw):
    base = {
        "transaction_id": "tx_1",
        "merchant_id": "m_1",
        "amount": 100.0,
        "status": "settled",
        "created_date": "2026-09-20",
        "refunds": [],
        "dispute_id": None,
    }
    return base | kw


def evidence(t=None, disputes=None, user="yes, please go ahead", merchant="m_1"):
    t = t or txn()
    return Evidence(
        today=TODAY,
        authenticated_merchant_id=merchant,
        transactions={t["transaction_id"]: t},
        disputes=disputes or {},
        last_user_message=user,
    )


def rules(name, args, ev):
    return {v.rule for v in check_tool_call(name, args, ev).violations}


def refund(amount=50.0, txn_id="tx_1"):
    return {"transaction_id": txn_id, "amount": amount, "reason": "customer_request"}


def test_valid_refund_is_allowed():
    assert check_tool_call("issue_refund", refund(), evidence()).allowed


def test_read_tools_are_never_blocked():
    ev = Evidence(today=TODAY)
    assert check_tool_call("get_transaction_details", {"transaction_id": "x"}, ev).allowed


def test_requires_explicit_confirmation():
    assert "CONFIRM" in rules("issue_refund", refund(), evidence(user="how much can I refund?"))


def test_requires_authentication():
    assert "AUTH" in rules("issue_refund", refund(), evidence(merchant=None))


def test_requires_transaction_lookup():
    assert "EVIDENCE" in rules("issue_refund", refund(txn_id="tx_unseen"), evidence())


def test_blocks_other_merchants_transaction():
    assert "OWNERSHIP" in rules("issue_refund", refund(), evidence(merchant="m_2"))


def test_blocks_refund_over_limit():
    ev = evidence(txn(amount=750.0))
    assert "LIMIT" in rules("issue_refund", refund(600.0), ev)


def test_blocks_refund_over_remaining_balance():
    t = txn(status="partially_refunded", refunds=[{"amount": 20.0}])
    assert "BALANCE" in rules("issue_refund", refund(90.0), evidence(t))
    assert check_tool_call("issue_refund", refund(80.0), evidence(t)).allowed


def test_blocks_refund_older_than_window():
    assert "WINDOW" in rules("issue_refund", refund(), evidence(txn(created_date="2026-03-01")))


def test_blocks_refund_with_open_dispute():
    t = txn(dispute_id="dp_1")
    disputes = {"dp_1": {"dispute_id": "dp_1", "transaction_id": "tx_1", "status": "open"}}
    assert "DISPUTE" in rules("issue_refund", refund(), evidence(t, disputes))


def test_requires_dispute_lookup_before_refund():
    assert "EVIDENCE" in rules("issue_refund", refund(), evidence(txn(dispute_id="dp_1")))


def test_dispute_evidence_after_deadline_is_blocked():
    disputes = {
        "dp_1": {
            "dispute_id": "dp_1",
            "transaction_id": "tx_1",
            "status": "open",
            "evidence_due_date": "2026-09-28",
        }
    }
    args = {"dispute_id": "dp_1", "evidence_type": "proof_of_delivery"}
    assert "DEADLINE" in rules("submit_dispute_evidence", args, evidence(disputes=disputes))


def test_dispute_evidence_before_deadline_is_allowed():
    disputes = {
        "dp_1": {
            "dispute_id": "dp_1",
            "transaction_id": "tx_1",
            "status": "open",
            "evidence_due_date": "2026-10-10",
        }
    }
    args = {"dispute_id": "dp_1", "evidence_type": "customer_authorized"}
    assert check_tool_call("submit_dispute_evidence", args, evidence(disputes=disputes)).allowed
