"""tau2 environment and task loaders for the merchant_ops domain."""

from tau2.data_model.tasks import Task
from tau2.environment.environment import Environment
from tau2.utils import load_file

from merchant_ops.domain.data_model import MerchantOpsDB
from merchant_ops.domain.tools import MerchantOpsTools
from merchant_ops.domain.utils import (
    DB_PATH,
    DOMAIN_NAME,
    POLICY_PATH,
    SPLIT_PATH,
    TASK_SET_PATH,
)


def get_environment(db: MerchantOpsDB | None = None, solo_mode: bool = False) -> Environment:
    if solo_mode:
        raise ValueError("merchant_ops does not support solo mode")
    if db is None:
        db = MerchantOpsDB.load(DB_PATH)
    policy = POLICY_PATH.read_text()
    return Environment(domain_name=DOMAIN_NAME, policy=policy, tools=MerchantOpsTools(db))


def get_tasks_split() -> dict[str, list[str]]:
    return load_file(SPLIT_PATH)


def get_tasks(task_split_name: str | None = "base") -> list[Task]:
    tasks = [Task.model_validate(t) for t in load_file(TASK_SET_PATH)]
    if task_split_name is None:
        return tasks
    splits = get_tasks_split()
    if task_split_name not in splits:
        raise ValueError(f"Unknown split {task_split_name!r}; valid: {list(splits)}")
    wanted = set(splits[task_split_name])
    return [t for t in tasks if t.id in wanted]
