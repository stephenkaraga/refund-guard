# Notes for coding agents

- Python 3.12, uv. Install with `make install`; run `make test` and `make lint` before finishing.
- tau2 is pinned to `v1.0.1`. Its API differs from tau2 `main`; check the installed package under `.venv/lib/python3.12/site-packages/tau2` before using a function.
- Never edit tau2. Add domains and agents through `src/merchant_ops/register.py`.
- Tools enforce hard platform limits only; business policy belongs in `data/merchant_ops/policy.md` and the guard. Don't move policy into tools.
- Task fields must be deterministic: tool arguments that change the DB use enums, not free text.
- Every new task needs a test in `tests/test_domain.py` to pass (reference actions must replay cleanly).
- Don't commit `results/` or `.env`.
