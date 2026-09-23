.PHONY: setup test lint run-pilot dashboard-backend dashboard-frontend clean

PYTHON ?= python

setup:
	uv pip install -e ".[dev]"

test:
	pytest tests/ -v --durations=10

lint:
	python -m pyproject_check || true
	ruff check evaeval tests || true

run-pilot:
	python -m evaeval.runner.cli run --config configs/experiments/pilot.yaml

dashboard-backend:
	uvicorn evaeval.dashboard_backend.main:app --host 0.0.0.0 --port 8000 --reload

dashboard-frontend:
	cd evaeval/dashboard_frontend && npm run dev

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ *.egg-info build dist
