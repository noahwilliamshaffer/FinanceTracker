.PHONY: help setup test test-coverage lint format clean dev deploy docs

# Default target
help:
	@echo "Available targets:"
	@echo "  setup        - Install dependencies and setup development environment"
	@echo "  test         - Run test suite"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code with black and isort"
	@echo "  clean        - Clean up temporary files and caches"
	@echo "  dev          - Start development server"
	@echo "  deploy       - Deploy infrastructure with Terraform"
	@echo "  docs         - Generate documentation"

# Setup development environment
setup:
	@echo "Setting up development environment..."
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	pip install -e .
	@echo "Creating sample data directory..."
	mkdir -p samples/treasury samples/repo
	@echo "Setup complete!"

# Run tests
test:
	@echo "Running test suite..."
	pytest tests/ -v

# Run tests with coverage
test-coverage:
	@echo "Running tests with coverage..."
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Linting
lint:
	@echo "Running linting checks..."
	flake8 src/ tests/
	mypy src/
	black --check src/ tests/
	isort --check-only src/ tests/

# Format code
format:
	@echo "Formatting code..."
	black src/ tests/
	isort src/ tests/

# Clean up
clean:
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/
	rm -rf dist/ build/

# Development server
dev:
	@echo "Starting development server..."
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Deploy infrastructure
deploy:
	@echo "Deploying infrastructure..."
	cd infra/terraform && terraform plan
	cd infra/terraform && terraform apply

# Generate documentation
docs:
	@echo "Generating documentation..."
	mkdir -p docs/api
	python -c "import src.api.main; help(src.api.main)" > docs/api/fastapi.md

# Install pre-commit hooks
install-hooks:
	@echo "Installing pre-commit hooks..."
	pip install pre-commit
	pre-commit install

# Run security checks
security:
	@echo "Running security checks..."
	pip install bandit safety
	bandit -r src/
	safety check

# Docker targets
docker-build:
	@echo "Building Docker image..."
	docker build -t finance-tracker .

docker-run:
	@echo "Running Docker container..."
	docker run -p 8000:8000 finance-tracker

# Terraform specific targets
tf-init:
	@echo "Initializing Terraform..."
	cd infra/terraform && terraform init

tf-plan:
	@echo "Planning Terraform deployment..."
	cd infra/terraform && terraform plan

tf-apply:
	@echo "Applying Terraform configuration..."
	cd infra/terraform && terraform apply

tf-destroy:
	@echo "Destroying Terraform infrastructure..."
	cd infra/terraform && terraform destroy
