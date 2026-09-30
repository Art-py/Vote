COMPOSE := docker compose
UV := uv
PYTEST_ARGS ?=
SERVICE ?=

.DEFAULT_GOAL := help

.PHONY: help install up down logs check format test makemigrations superuser

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\nTargets:\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Sync the local uv environment
	$(UV) sync

up: ## Build and start the local stack
	$(COMPOSE) up --build --detach

down: ## Stop the local stack without deleting data
	$(COMPOSE) down

logs: ## Follow logs; optionally pass SERVICE=web
	$(COMPOSE) logs --follow --tail=100 $(SERVICE)

check: ## Verify the lock file, Django configuration, and code style
	$(UV) lock --check
	$(UV) run --locked python manage.py check
	$(UV) run --locked ruff check .

format: ## Fix lint issues and format Python files
	$(UV) run --locked ruff check --fix .
	$(UV) run --locked ruff format .

test: ## Run pytest in Docker; optionally pass PYTEST_ARGS="-k name"
	$(COMPOSE) run --rm web pytest $(PYTEST_ARGS)

makemigrations: ## Create database migrations in Docker
	$(COMPOSE) run --rm web python manage.py makemigrations

superuser: ## Create a Django superuser in Docker
	$(COMPOSE) run --rm web python manage.py createsuperuser
