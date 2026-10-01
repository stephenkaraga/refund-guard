import pytest

from merchant_ops.domain.data_model import MerchantOpsDB
from merchant_ops.domain.environment import get_environment, get_tasks, get_tasks_split
from merchant_ops.domain.tools import MerchantOpsTools
from merchant_ops.domain.utils import DB_PATH


@pytest.fixture
def tools():
    return MerchantOpsTools(MerchantOpsDB.load(DB_PATH))


def test_find_merchant_by_email_is_case_insensitive(tools):
    assert tools.find_merchant_id_by_email("ANA@sunrisebakery.com") == "m_1001"


def test_full_refund_marks_transaction_refunded(tools):
    txn = tools.issue_refund("tx_5001", 42.5, "customer_request")
    assert txn.status == "refunded"
    assert txn.refunds[-1].refund_id == "rf_tx_5001_1"


def test_partial_refund_respects_remaining_balance(tools):
    with pytest.raises(ValueError):
        tools.issue_refund("tx_5003", 120.0, "product_issue")
    txn = tools.issue_refund("tx_5003", 100.0, "product_issue")
    assert txn.status == "refunded"


def test_pending_transaction_cannot_be_refunded(tools):
    with pytest.raises(ValueError):
        tools.issue_refund("tx_5009", 10.0, "customer_request")


def test_submit_evidence_moves_dispute_to_review(tools):
    d = tools.submit_dispute_evidence("dp_7001", "customer_authorized")
    assert d.status == "under_review"


def test_environment_loads_with_policy():
    env = get_environment()
    assert "Merchant Support Agent Policy" in env.get_policy()


def test_splits_reference_real_tasks():
    ids = {t.id for t in get_tasks(None)}
    for name, members in get_tasks_split().items():
        assert set(members) <= ids, name
    assert "base" in get_tasks_split()


@pytest.mark.parametrize("task", get_tasks(None), ids=lambda t: t.id)
def test_reference_actions_replay_cleanly(task):
    """Every reference action must succeed on a fresh DB, or the task can't be scored."""
    t = MerchantOpsTools(MerchantOpsDB.load(DB_PATH))
    for action in task.evaluation_criteria.actions or []:
        getattr(t, action.name)(**action.arguments)
