"""Build guard Evidence from a tau2 conversation history."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from tau2.data_model.message import (
    AssistantMessage,
    MultiToolMessage,
    ToolMessage,
    UserMessage,
)

from merchant_ops.agent.guard import Evidence


def _parse(content: str | None) -> Any:
    if content is None:
        return None
    try:
        return json.loads(content)
    except (TypeError, ValueError):
        return content


def build_evidence(messages: list[Any], today: date) -> Evidence:
    """Walk the history, pairing each tool call with its result."""
    ev = Evidence(today=today)
    pending: dict[str, tuple[str, dict]] = {}

    for msg in messages:
        if isinstance(msg, AssistantMessage) and msg.tool_calls:
            for call in msg.tool_calls:
                pending[call.id] = (call.name, call.arguments)
        elif isinstance(msg, UserMessage) and msg.content:
            ev.last_user_message = msg.content
        tool_msgs = (
            msg.tool_messages
            if isinstance(msg, MultiToolMessage)
            else [msg]
            if isinstance(msg, ToolMessage)
            else []
        )
        for tm in tool_msgs:
            if tm.id not in pending or tm.error:
                continue
            name, _args = pending.pop(tm.id)
            _record(name, _parse(tm.content), ev)
    return ev


def _record(name: str, result: Any, ev: Evidence) -> None:
    if name == "find_merchant_id_by_email" and isinstance(result, str):
        # The first successful lookup is the authenticated merchant; later
        # lookups (e.g. a "friend's" email) don't switch whose data we act on.
        ev.authenticated_merchant_id = ev.authenticated_merchant_id or result
    elif name == "get_transaction_details" and isinstance(result, dict):
        ev.transactions[result["transaction_id"]] = result
    elif name == "list_transactions" and isinstance(result, list):
        for txn in result:
            if isinstance(txn, dict) and "transaction_id" in txn:
                ev.transactions[txn["transaction_id"]] = txn
    elif name == "get_dispute_details" and isinstance(result, dict):
        ev.disputes[result["dispute_id"]] = result
