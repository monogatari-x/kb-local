.PHONY: install lint test test-int clean

install:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy kb_core kb_cli

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest tests/unit -v --cov=kb_core --cov-report=term-missing

test-int:
	uv run pytest tests/integration -v

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
