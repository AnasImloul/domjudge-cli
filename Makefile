.PHONY: help setup install test lint format typecheck clean build check ensure-uv

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Internal target: ensure uv is installed
ensure-uv:
	@command -v uv >/dev/null 2>&1 || { \
		echo "Installing uv..."; \
		pip install -q uv; \
	}

# Detect if we need --system flag (CI or no venv)
UV_SYSTEM_FLAG := $(if $(or $(CI),$(if $(VIRTUAL_ENV),,1)),--system,)

setup: ensure-uv ## Complete setup (run this first)
	@echo "Installing package..."
	@uv pip install $(UV_SYSTEM_FLAG) -e .
	@echo "Installing pre-commit hooks..."
	@pre-commit install
	@echo "✓ Setup complete"

install: ensure-uv ## Install/reinstall package
	uv pip install $(UV_SYSTEM_FLAG) -e .

test: ## Run tests with coverage
	pytest --cov --cov-report=term-missing --cov-report=html -v

lint: ## Run all linters
	ruff check .
	ruff format --check .
	bandit -c pyproject.toml -r dom/ -q
	lint-imports

format: ## Format code (auto-fix)
	ruff format .
	ruff check --fix .

typecheck: ## Type check with mypy
	mypy dom/ --config-file pyproject.toml

clean: ## Clean build artifacts
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build: ensure-uv clean ## Build distribution
	uv build

check: format lint typecheck test ## Run all checks (format, lint, typecheck, test)
