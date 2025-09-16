# Makefile for Spanish Transcription API Testing and Quality Assurance

# Python command - adjust if needed
PYTHON := python3
PIP := pip3

.PHONY: help install test test-unit test-integration test-api test-security test-performance
.PHONY: coverage lint format type-check security-scan quality-check clean

# Default target
help: ## Show this help message
	@echo "Spanish Transcription API - Testing and QA Commands"
	@echo "=================================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  install          Install all dependencies (dev and prod)"
	@echo "  install-dev      Install development dependencies only"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test             Run full test suite with quality gates"
	@echo "  test-quick       Run tests without performance tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-api         Run API tests only"
	@echo "  test-security    Run security tests only"
	@echo "  test-performance Run performance tests only"
	@echo ""
	@echo "Quality Commands:"
	@echo "  coverage         Generate coverage report"
	@echo "  lint             Run all linting checks"
	@echo "  format           Format code with black and isort"
	@echo "  type-check       Run type checking with mypy"
	@echo "  security-scan    Run security analysis"
	@echo "  quality-check    Run all quality checks"
	@echo ""
	@echo "Utility Commands:"
	@echo "  clean            Clean up generated files"
	@echo "  serve            Start development server"
	@echo "  serve-ui         Start Streamlit UI"
	@echo ""

# Installation targets
install: ## Install all dependencies
	$(PYTHON) -m pip install --break-system-packages -r requirements.txt
	$(PYTHON) -m pip install --break-system-packages -r requirements-dev.txt

install-dev: ## Install development dependencies
	$(PYTHON) -m pip install --break-system-packages -r requirements-dev.txt

# Testing targets
test: ## Run complete test suite with quality gates
	$(PYTHON) scripts/test_runner.py

test-quick: ## Run tests without performance tests
	$(PYTHON) scripts/test_runner.py --skip-performance

test-unit: ## Run unit tests with coverage
	$(PYTHON) -m pytest tests/unit/ tests/security/ -v --cov=src --cov-report=html --cov-report=term

test-integration: ## Run integration tests
	$(PYTHON) -m pytest tests/integration/ -v

test-api: ## Run API endpoint tests
	$(PYTHON) -m pytest tests/api/ -v

test-security: ## Run security-specific tests
	$(PYTHON) -m pytest tests/security/ -v

test-performance: ## Run performance and load tests
	$(PYTHON) -m pytest tests/performance/ -v

# Coverage targets
coverage: ## Generate detailed coverage report
	$(PYTHON) -m pytest tests/unit/ tests/security/ --cov=src --cov-report=html --cov-report=xml --cov-report=term
	@echo "Coverage report generated in htmlcov/"

coverage-xml: ## Generate XML coverage report for CI
	$(PYTHON) -m pytest tests/unit/ tests/security/ --cov=src --cov-report=xml

# Code quality targets
lint: ## Run all linting checks
	flake8 src/ tests/ --max-line-length=120 --extend-ignore=E203,W503
	pylint src/ --fail-under=8.0

format: ## Format code with black and isort
	black src/ tests/
	isort src/ tests/

format-check: ## Check code formatting
	black --check --diff src/ tests/
	isort --check-only --diff src/ tests/

type-check: ## Run type checking
	mypy src/ --ignore-missing-imports

security-scan: ## Run security analysis
	bandit -r src/ --severity-level medium
	safety check

quality-check: format-check lint type-check security-scan ## Run all quality checks

# Development server targets
serve: ## Start FastAPI development server
	$(PYTHON) main.py

serve-ui: ## Start Streamlit UI
	$(PYTHON) -m streamlit run app.py

# Utility targets
clean: ## Clean up generated files
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyc" -delete
	rm -f quality-report.json
	rm -f test-results-detailed.json
	rm -f security-report.json
	rm -f performance-results.json

# CI/CD specific targets
ci-test: ## Run tests for CI environment
	$(PYTHON) -m pytest tests/unit/ tests/integration/ tests/api/ tests/security/ -v --cov=src --cov-report=xml --cov-fail-under=80

ci-quality: ## Run quality checks for CI
	$(PYTHON) -m flake8 src/ tests/ --max-line-length=120 --extend-ignore=E203,W503
	$(PYTHON) -m black --check src/ tests/
	$(PYTHON) -m isort --check-only src/ tests/
	$(PYTHON) -m mypy src/ --ignore-missing-imports
	$(PYTHON) -m bandit -r src/ --severity-level medium
	$(PYTHON) -m safety check