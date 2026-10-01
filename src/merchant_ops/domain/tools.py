"""Tools the agent can call in the merchant_ops domain.

Tools enforce only hard platform limits (you can't refund more than was
charged). Business policy -- refund caps, dispute rules, what to disclose --
lives in policy.md and is the agent's job. That gap is what the benchmark tests.
"""

from tau2.environment.toolkit import ToolKitBase, ToolType, is_tool

from merchant_ops.domain.data_model import (
    Dispute,
    EvidenceType,
    Merchant,
    MerchantOpsDB,
    Payout,
    Refund,
    RefundReason,
    Transaction,
)


class MerchantOpsTools(ToolKitBase):
    """Merchant support tools over the mock payments database."""

    db: MerchantOpsDB

    def __init__(self, db: MerchantOpsDB) -> None:
        super().__init__(db)

    # ---------- lookups ----------

    def _merchant(self, merchant_id: str) -> Merchant:
        if merchant_id not in self.db.merchants:
            raise ValueError(f"Merchant {merchant_id} not found")
        return self.db.merchants[merchant_id]

    def _transaction(self, transaction_id: str) -> Transaction:
        if transaction_id not in self.db.transactions:
            raise ValueError(f"Transaction {transaction_id} not found")
        return self.db.transactions[transaction_id]

    def _dispute(self, dispute_id: str) -> Dispute:
        if dispute_id not in self.db.disputes:
            raise ValueError(f"Dispute {dispute_id} not found")
        return self.db.disputes[dispute_id]

    @is_tool(ToolType.READ)
    def find_merchant_id_by_email(self, email: str) -> str:
        """
        Find a merchant's ID from the owner's login email.

        Args:
            email: The owner's login email, e.g. 'ana@sunrisebakery.com'.

        Returns:
            The merchant ID.

        Raises:
            ValueError: If no merchant uses that email.
        """
        for merchant in self.db.merchants.values():
            if merchant.email.lower() == email.strip().lower():
                return merchant.merchant_id
        raise ValueError("Merchant not found")

    @is_tool(ToolType.READ)
    def get_merchant_details(self, merchant_id: str) -> Merchant:
        """
        Get a merchant's account details.

        Args:
            merchant_id: The merchant ID, e.g. 'm_1001'.

        Returns:
            The merchant record.

        Raises:
            ValueError: If the merchant is not found.
        """
        return self._merchant(merchant_id)

    @is_tool(ToolType.READ)
    def list_transactions(self, merchant_id: str) -> list[Transaction]:
        """
        List all transactions for a merchant, newest first.

        Args:
            merchant_id: The merchant ID.

        Returns:
            The merchant's transactions.

        Raises:
            ValueError: If the merchant is not found.
        """
        self._merchant(merchant_id)
        txns = [t for t in self.db.transactions.values() if t.merchant_id == merchant_id]
        return sorted(txns, key=lambda t: t.created_date, reverse=True)

    @is_tool(ToolType.READ)
    def get_transaction_details(self, transaction_id: str) -> Transaction:
        """
        Get a transaction, including refunds issued and any linked dispute.

        Args:
            transaction_id: The transaction ID, e.g. 'tx_5001'.

        Returns:
            The transaction record.

        Raises:
            ValueError: If the transaction is not found.
        """
        return self._transaction(transaction_id)

    @is_tool(ToolType.READ)
    def get_dispute_details(self, dispute_id: str) -> Dispute:
        """
        Get a chargeback dispute.

        Args:
            dispute_id: The dispute ID, e.g. 'dp_7001'.

        Returns:
            The dispute record.

        Raises:
            ValueError: If the dispute is not found.
        """
        return self._dispute(dispute_id)

    @is_tool(ToolType.READ)
    def list_payouts(self, merchant_id: str) -> list[Payout]:
        """
        List a merchant's payouts, newest first.

        Args:
            merchant_id: The merchant ID.

        Returns:
            The merchant's payouts.

        Raises:
            ValueError: If the merchant is not found.
        """
        self._merchant(merchant_id)
        payouts = [p for p in self.db.payouts.values() if p.merchant_id == merchant_id]
        return sorted(payouts, key=lambda p: p.scheduled_date, reverse=True)

    # ---------- actions ----------

    @is_tool(ToolType.WRITE)
    def issue_refund(self, transaction_id: str, amount: float, reason: RefundReason) -> Transaction:
        """
        Refund all or part of a settled transaction to the customer's card.

        Args:
            transaction_id: The transaction to refund.
            amount: Amount in USD, greater than 0 and no more than the refundable balance.
            reason: One of 'customer_request', 'duplicate_charge', 'product_issue', 'other'.

        Returns:
            The updated transaction.

        Raises:
            ValueError: If the transaction can't be refunded or the amount is invalid.
        """
        txn = self._transaction(transaction_id)
        if txn.status not in ("settled", "partially_refunded"):
            raise ValueError(f"Transaction status is {txn.status}; only settled charges refund")
        amount = round(float(amount), 2)
        if amount <= 0:
            raise ValueError("Refund amount must be greater than 0")
        if amount > txn.refundable_amount:
            raise ValueError(f"Amount exceeds refundable balance of {txn.refundable_amount}")
        refund_id = f"rf_{transaction_id}_{len(txn.refunds) + 1}"
        txn.refunds.append(Refund(refund_id=refund_id, amount=amount, reason=reason))
        txn.status = "refunded" if txn.refundable_amount == 0 else "partially_refunded"
        return txn

    @is_tool(ToolType.WRITE)
    def submit_dispute_evidence(self, dispute_id: str, evidence_type: EvidenceType) -> Dispute:
        """
        Submit evidence for an open chargeback dispute. This moves it to review.

        Args:
            dispute_id: The dispute ID.
            evidence_type: One of 'proof_of_delivery', 'refund_already_issued',
                'customer_authorized', 'product_as_described'.

        Returns:
            The updated dispute.

        Raises:
            ValueError: If the dispute is not open.
        """
        dispute = self._dispute(dispute_id)
        if dispute.status != "open":
            raise ValueError(f"Dispute status is {dispute.status}; evidence closed")
        dispute.evidence_type = evidence_type
        dispute.status = "under_review"
        return dispute

    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agents(self, summary: str) -> str:
        """
        Transfer the merchant to a human support specialist, with a summary.
        Only transfer when the merchant asks for a human, or when policy requires it.

        Args:
            summary: A short summary of the merchant's issue.

        Returns:
            A confirmation message.
        """
        return "Transfer successful"
