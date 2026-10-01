"""Deterministic policy guard for write actions.

The guard checks every proposed write tool call against the policy *and* the
evidence already in the conversation. A refund is allowed only if the agent has
actually looked up the transaction (and its dispute, if any) and the facts it
saw permit the refund. The model can't talk its way past this layer.

This module is pure Python with no tau2 or LLM imports, so it is fast to unit
test and easy to reuse in a production service (see docs/adr/0003).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

REFUND_LIMIT_USD = 500.00
REFUND_WINDOW_DAYS = 180
BLOCKING_DISPUTE_STATUSES = {"open", "under_review"}
WRITE_TOOLS = {"issue_refund", "submit_dispute_evidence"}

_AFFIRMATIVE = re.compile(
    r"\b(yes|yep|yeah|confirm(ed)?|go ahead|please do|do it|that'?s right|correct)\b",
    re.IGNORECASE,
)


@dataclass
class Evidence:
    """Facts the agent has observed from tool results in this conversation."""

    today: date
    authenticated_merchant_id: str | None = None
    transactions: dict[str, dict[str, Any]] = field(default_factory=dict)
    disputes: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_user_message: str = ""


@dataclass
class Violation:
    rule: str
    message: str

    def __str__(self) -> str:
        return f"[{self.rule}] {self.message}"


@dataclass
class GuardResult:
    violations: list[Violation] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return not self.violations


def check_tool_call(name: str, arguments: dict[str, Any], ev: Evidence) -> GuardResult:
    """Return the policy violations for one proposed tool call (empty if allowed)."""
    if name not in WRITE_TOOLS:
        return GuardResult()
    v: list[Violation] = []
    _check_confirmation(ev, v)
    if ev.authenticated_merchant_id is None:
        v.append(Violation("AUTH", "Authenticate the merchant before taking any action."))
    if name == "issue_refund":
        _check_refund(arguments, ev, v)
    elif name == "submit_dispute_evidence":
        _check_dispute_evidence(arguments, ev, v)
    return GuardResult(v)


def _check_confirmation(ev: Evidence, v: list[Violation]) -> None:
    if not _AFFIRMATIVE.search(ev.last_user_message or ""):
        v.append(
            Violation(
                "CONFIRM",
                "State the exact action and get an explicit 'yes' from the merchant first.",
            )
        )


def _owned_transaction(txn_id: str, ev: Evidence, v: list[Violation]) -> dict[str, Any] | None:
    txn = ev.transactions.get(txn_id)
    if txn is None:
        v.append(Violation("EVIDENCE", f"Look up transaction {txn_id} before acting on it."))
        return None
    if ev.authenticated_merchant_id and txn.get("merchant_id") != ev.authenticated_merchant_id:
        v.append(Violation("OWNERSHIP", f"Transaction {txn_id} belongs to another merchant."))
    return txn


def _check_refund(args: dict[str, Any], ev: Evidence, v: list[Violation]) -> None:
    txn_id = str(args.get("transaction_id", ""))
    txn = _owned_transaction(txn_id, ev, v)
    if txn is None:
        return
    amount = float(args.get("amount", 0) or 0)

    if txn.get("status") not in ("settled", "partially_refunded"):
        v.append(
            Violation("STATUS", f"Only settled charges can be refunded ({txn.get('status')}).")
        )

    dispute_id = txn.get("dispute_id")
    if dispute_id:
        dispute = ev.disputes.get(dispute_id)
        if dispute is None:
            v.append(Violation("EVIDENCE", f"Check linked dispute {dispute_id} before refunding."))
        elif dispute.get("status") in BLOCKING_DISPUTE_STATUSES:
            v.append(
                Violation(
                    "DISPUTE",
                    f"Dispute {dispute_id} is {dispute.get('status')}; no refund. "
                    "Offer to respond to the dispute instead.",
                )
            )

    created = _parse_date(txn.get("created_date"))
    if created and created < ev.today - timedelta(days=REFUND_WINDOW_DAYS):
        v.append(Violation("WINDOW", "Charge is older than 180 days; transfer to a specialist."))

    if amount > REFUND_LIMIT_USD:
        v.append(Violation("LIMIT", "Refunds over $500.00 need a specialist; transfer instead."))

    refunded = sum(float(r.get("amount", 0)) for r in txn.get("refunds", []) or [])
    refundable = round(float(txn.get("amount", 0)) - refunded, 2)
    if amount > refundable:
        v.append(Violation("BALANCE", f"Only ${refundable:.2f} is refundable on {txn_id}."))


def _check_dispute_evidence(args: dict[str, Any], ev: Evidence, v: list[Violation]) -> None:
    dispute_id = str(args.get("dispute_id", ""))
    dispute = ev.disputes.get(dispute_id)
    if dispute is None:
        v.append(Violation("EVIDENCE", f"Look up dispute {dispute_id} before acting on it."))
        return
    _owned_transaction(str(dispute.get("transaction_id", "")), ev, v)
    if dispute.get("status") != "open":
        v.append(
            Violation("DISPUTE", f"Dispute {dispute_id} is {dispute.get('status')}, not open.")
        )
    due = _parse_date(dispute.get("evidence_due_date"))
    if due and ev.today > due:
        v.append(
            Violation("DEADLINE", f"Evidence was due {due.isoformat()}; it can't be submitted.")
        )


def _parse_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
