.PHONY: help install dev test format lint clean db-init db-migrate run

help:  ## Show this help message
	@echo "Boxcatering Chatbot - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -e .

dev:  ## Install development dependencies
	pip install -e ".[dev]"

test:  ## Run tests
	pytest

format:  ## Format code with black and isort
	black .
	isort .

lint:  ## Run linting checks
	flake8 .
	mypy .

clean:  ## Clean up Python cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

db-init:  ## Initialize database tables and create initial data (admin user, configs)
	python scripts/init_db.py

db-migrate:  ## Run database migrations
	alembic upgrade head

db-revision:  ## Create new migration (usage: make db-revision msg="description")
	alembic revision --autogenerate -m "$(msg)"

setup-system-config:  ## Initialize default system configuration values (now included in db-init)
	@echo "ℹ️  This target is now included in 'make db-init'"
	@echo "Run 'make db-init' to initialize database with all initial data"

test-system-config:  ## Test system configuration API endpoints
	python scripts/test_system_config.py

setup: db-init db-migrate  ## Complete setup: init DB with data, run migrations

run:  ## Run the development server
	python start.py

run-prod:  ## Run the production server
	python -m app.main
