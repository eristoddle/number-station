# Number Station - Development Makefile

.PHONY: help build run test clean lint format type-check install dev-install

help: ## Show this help message
	@echo "Number Station - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

dev-install: ## Install development dependencies
	pip install -r requirements.txt
	pip install -e .

build: ## Build Docker image
	docker-compose build

run: ## Run the application with Docker
	docker-compose up

run-local: ## Run the application locally
	streamlit run src/main.py

test: ## Run all tests
	pytest tests/ -v

test-coverage: ## Run tests with coverage report
	pytest tests/ --cov=src --cov-report=html --cov-report=term

test-property: ## Run property-based tests only
	pytest tests/ -k "property" -v

lint: ## Run linting
	flake8 src/ plugins/ tests/

format: ## Format code with black
	black src/ plugins/ tests/

type-check: ## Run type checking
	mypy src/

quality: lint type-check ## Run all code quality checks

clean: ## Clean up build artifacts and cache
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/ .mypy_cache/

docker-clean: ## Clean up Docker containers and images
	docker-compose down --rmi all --volumes --remove-orphans

logs: ## Show application logs
	docker-compose logs -f number-station

shell: ## Open shell in running container
	docker-compose exec number-station /bin/bash

dev: ## Start development environment
	docker-compose up --build