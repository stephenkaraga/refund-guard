"""Paths to the merchant_ops domain data."""

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = Path(os.getenv("MERCHANT_OPS_DATA_DIR", _REPO_ROOT / "data" / "merchant_ops"))
DB_PATH = DATA_DIR / "db.json"
POLICY_PATH = DATA_DIR / "policy.md"
TASK_SET_PATH = DATA_DIR / "tasks.json"
SPLIT_PATH = DATA_DIR / "split_tasks.json"

DOMAIN_NAME = "merchant_ops"
