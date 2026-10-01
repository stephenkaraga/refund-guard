"""Data model for the merchant_ops domain.

A small, fictional payments platform: merchants, card transactions, chargeback
disputes and payouts. All data is invented; nothing comes from a real company.
"""

from typing import Literal

from pydantic import BaseModel, Field
from tau2.environment.db import DB

TransactionStatus = Literal["pending", "settled", "partially_refunded", "refunded", "failed"]
DisputeStatus = Literal["open", "under_review", "won", "lost"]
PayoutStatus = Literal["scheduled", "paid", "on_hold"]
# Enumerated (not free text) so the end-state DB comparison is deterministic.
RefundReason = Literal["customer_request", "duplicate_charge", "product_issue", "other"]
EvidenceType = Literal[
    "proof_of_delivery", "refund_already_issued", "customer_authorized", "product_as_described"
]


class Merchant(BaseModel):
    merchant_id: str = Field(description="Unique merchant identifier")
    business_name: str = Field(description="Legal business name")
    owner_name: str = Field(description="Name of the account owner")
    email: str = Field(description="Owner's login email")
    plan: Literal["starter", "growth", "enterprise"] = Field(description="Pricing plan")
    risk_score: int = Field(description="Internal risk score 0-100. Never disclose to merchants.")


class Refund(BaseModel):
    refund_id: str = Field(description="Unique refund identifier")
    amount: float = Field(description="Refunded amount in USD")
    reason: RefundReason = Field(description="Reason category for the refund")


class Transaction(BaseModel):
    transaction_id: str = Field(description="Unique transaction identifier")
    merchant_id: str = Field(description="Merchant that received the payment")
    amount: float = Field(description="Original charge amount in USD")
    status: TransactionStatus = Field(description="Current transaction status")
    card_last4: str = Field(description="Last four digits of the customer's card")
    created_date: str = Field(description="Charge date, YYYY-MM-DD")
    refunds: list[Refund] = Field(default_factory=list, description="Refunds issued so far")
    dispute_id: str | None = Field(None, description="Linked dispute, if any")

    @property
    def refunded_amount(self) -> float:
        return round(sum(r.amount for r in self.refunds), 2)

    @property
    def refundable_amount(self) -> float:
        return round(self.amount - self.refunded_amount, 2)


class Dispute(BaseModel):
    dispute_id: str = Field(description="Unique dispute identifier")
    transaction_id: str = Field(description="Disputed transaction")
    reason: Literal["fraudulent", "product_not_received", "duplicate", "not_as_described"]
    status: DisputeStatus = Field(description="Dispute status")
    evidence_due_date: str = Field(description="Last day to submit evidence, YYYY-MM-DD")
    evidence_type: EvidenceType | None = Field(
        None, description="Type of evidence submitted by the merchant"
    )


class Payout(BaseModel):
    payout_id: str = Field(description="Unique payout identifier")
    merchant_id: str = Field(description="Merchant receiving the payout")
    amount: float = Field(description="Payout amount in USD")
    status: PayoutStatus = Field(description="Payout status")
    scheduled_date: str = Field(description="Scheduled date, YYYY-MM-DD")
    hold_reason: str | None = Field(None, description="Why the payout is on hold, if it is")


class MerchantOpsDB(DB):
    """Merchants, transactions, disputes and payouts, each keyed by ID."""

    merchants: dict[str, Merchant] = Field(description="Merchants by merchant_id")
    transactions: dict[str, Transaction] = Field(description="Transactions by transaction_id")
    disputes: dict[str, Dispute] = Field(description="Disputes by dispute_id")
    payouts: dict[str, Payout] = Field(description="Payouts by payout_id")
    today: str = Field(description="The simulated current date, YYYY-MM-DD")
