COMPOSE := docker compose
UV := uv
PYTEST_ARGS ?=
SERVICE ?=

.DEFAULT_GOAL := help

.PHONY: help install lock lock-check build up down restart ps logs \
	check django-check lint format test migrate makemigrations superuser shell manage

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\nTargets:\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Sync the local uv environment
	$(UV) sync

lock: ## Update the dependency lock file
	$(UV) lock

lock-check: ## Verify that uv.lock matches pyproject.toml
	$(UV) lock --check

build: ## Build application images
	$(COMPOSE) build

up: ## Build and start the local stack
	$(COMPOSE) up --build --detach

down: ## Stop the local stack without deleting data
	$(COMPOSE) down

restart: down up ## Restart the local stack

ps: ## Show service status
	$(COMPOSE) ps

logs: ## Follow logs; optionally pass SERVICE=web
	$(COMPOSE) logs --follow --tail=100 $(SERVICE)

check: lock-check django-check lint ## Run all fast project checks

django-check: ## Run Django system checks locally
	$(UV) run --locked python manage.py check

lint: ## Run Ruff checks
	$(UV) run --locked ruff check .

format: ## Fix lint issues and format Python files
	$(UV) run --locked ruff check --fix .
	$(UV) run --locked ruff format .

test: ## Run pytest in Docker; optionally pass PYTEST_ARGS="-k name"
	$(COMPOSE) run --rm web pytest $(PYTEST_ARGS)

migrate: ## Apply database migrations in Docker
	$(COMPOSE) run --rm web python manage.py migrate

makemigrations: ## Create database migrations in Docker
	$(COMPOSE) run --rm web python manage.py makemigrations

superuser: ## Create a Django superuser in Docker
	$(COMPOSE) run --rm web python manage.py createsuperuser

shell: ## Open the Django shell in Docker
	$(COMPOSE) run --rm web python manage.py shell

manage: ## Run a management command, for example CMD="showmigrations"
	$(COMPOSE) run --rm web python manage.py $(CMD)
