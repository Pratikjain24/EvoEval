.PHONY: setup test lint run-pilot run-full reproduce docker-up build-images verify-images dashboard-backend dashboard-frontend clean

PYTHON ?= python

setup:
	uv pip install -e ".[dev]"

reproduce:
	$(PYTHON) -m sage.runner.cli verify-env --config configs/experiments/full_study.yaml

verify:
	$(PYTHON) scripts/verify_reproducibility.py

attest:
	$(PYTHON) -m sage.runner.cli verify

run-full:
	sage run --config configs/experiments/full_study.yaml

docker-up:
	docker compose -f docker/docker-compose.yml up -d

build-images:
	$(PYTHON) scripts/build_and_inspect_images.py

verify-images:
	$(PYTHON) scripts/build_and_inspect_images.py --verify

test:
	pytest tests/ -v --durations=10

smoke-real-llm:
	$(PYTHON) scripts/run_vllm_smoke_test.py --tasks task_001,task_006
	pytest tests/test_vllm_integration.py -v

audit-contamination:
	$(PYTHON) scripts/audit_task_contamination.py

cross-family:
	$(PYTHON) scripts/run_cross_family_pilot.py

horizon-sensitivity:
	$(PYTHON) scripts/run_horizon_sensitivity.py


lint:
	python -m pyproject_check || true
	ruff check sage tests || true

run-pilot:
	python -m sage.runner.cli run --config configs/experiments/pilot.yaml

dashboard-backend:
	uvicorn sage.dashboard_backend.main:app --host 0.0.0.0 --port 8000 --reload

dashboard-frontend:
	cd sage/dashboard_frontend && npm run dev

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ *.egg-info build dist
