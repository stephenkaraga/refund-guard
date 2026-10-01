TAU2_VERSION := v1.0.1

.PHONY: install tau2-data test lint fmt tasks baseline guarded compare

install:
	uv venv --python 3.12
	uv pip install -e ".[dev]"
	$(MAKE) tau2-data

# tau2's pip package doesn't ship its data folder (user-simulator guidelines).
# Fetch the matching release once; .env points TAU2_DATA_DIR at it.
tau2-data:
	@test -d .tau2-bench || git clone --depth 1 --branch $(TAU2_VERSION) https://github.com/sierra-research/tau2-bench.git .tau2-bench
	@test -f .env || cp .env.example .env
	@grep -q '^TAU2_DATA_DIR=' .env || echo "TAU2_DATA_DIR=$(CURDIR)/.tau2-bench/data" >> .env
	@echo "tau2 data ready at .tau2-bench/data"

test:
	TAU2_DATA_DIR=$(CURDIR)/.tau2-bench/data .venv/bin/python -m pytest -q

lint:
	.venv/bin/ruff check src tests evals deploy
	.venv/bin/ruff format --check src tests evals deploy

fmt:
	.venv/bin/ruff check --fix src tests evals deploy
	.venv/bin/ruff format src tests evals deploy

tasks:
	.venv/bin/merchant-ops tasks

baseline:
	.venv/bin/merchant-ops run --agent baseline --trials 4

guarded:
	.venv/bin/merchant-ops run --agent guarded --trials 4

compare:
	.venv/bin/merchant-ops compare results/*.summary.json
