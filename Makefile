.PHONY: setup test lint fmt clean

setup:
	uv pip install -e ".[dev]"

test:
	uv run --no-sync pytest tests/ -v

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

fmt:
	uv run ruff format src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -name "*.pyc" -delete 2>/dev/null; \
	rm -rf dist/ .pytest_cache/ src/mote.egg-info/
