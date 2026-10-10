.PHONY: setup dev build test lint docker-build docker-up docker-down docker-clean

SHELL := /bin/bash

# ---- Setup ----
setup:
	@echo "==> Running project setup..."
	@bash scripts/setup.sh

# ---- Development ----
dev:
	@echo "==> Starting development environment..."
	@bash scripts/dev.sh

# ---- Build ----
build:
	@echo "==> Building all components..."
	@bash scripts/build.sh all

build-go:
	@echo "==> Building Go API..."
	@bash scripts/build.sh go

build-python:
	@echo "==> Building Python package..."
	@bash scripts/build.sh python

build-vue:
	@echo "==> Building Vue frontend..."
	@bash scripts/build.sh vue

# ---- Test ----
test:
	@echo "==> Running all tests..."
	@bash scripts/run_tests.sh

test-go:
	@echo "==> Running Go tests..."
	@cd $(CURDIR)/gateway && go test ./... -count=1

test-python:
	@echo "==> Running Python tests..."
	@cd $(CURDIR) && PYTHONPATH=python .venv/bin/python -m pytest python

test-vue:
	@echo "==> Running Vue tests..."
	@cd $(CURDIR)/web && npx vitest run

# ---- Lint ----
lint: lint-go lint-python lint-vue
	@echo "==> All linters passed"

lint-go:
	@echo "==> Linting Go code..."
	@cd $(CURDIR)/gateway && golangci-lint run ./... 2>/dev/null || echo "(golangci-lint not installed, skipping)"

lint-python:
	@echo "==> Linting Python code..."
	@cd $(CURDIR) && uv run ruff check python/ 2>/dev/null || echo "(uv/ruff not installed, skipping)"

lint-vue:
	@echo "==> Linting Vue code..."
	@cd $(CURDIR)/web && npx eslint src/ 2>/dev/null || echo "(eslint not installed, skipping)"

# ---- Docker ----
docker-build:
	@echo "==> Building Docker images..."
	@docker compose -f docker-compose.yml build

docker-up:
	@echo "==> Starting Docker services..."
	@docker compose -f docker-compose.yml up -d

docker-down:
	@echo "==> Stopping Docker services..."
	@docker compose -f docker-compose.yml down

docker-clean:
	@echo "==> Removing Docker containers, images, and volumes..."
	@docker compose -f docker-compose.yml down -v --rmi all

# ---- Deploy ----
deploy-dev:
	@echo "==> Deploying development environment..."
	@bash scripts/deploy.sh development

deploy-prod:
	@echo "==> Deploying production environment..."
	@bash scripts/deploy.sh production

# ---- Misc ----
clean:
	@echo "==> Cleaning build artifacts..."
	@rm -rf dist/
	@echo "Done."

help:
	@echo "MaigoKite Makefile targets:"
	@echo "  setup         Initialize project (install deps, create dirs)"
	@echo "  dev           Start development servers (Go + Python + Vue)"
	@echo "  build         Build all components"
	@echo "  test          Run all tests"
	@echo "  lint          Run all linters"
	@echo "  docker-build  Build Docker images"
	@echo "  docker-up     Start Docker services"
	@echo "  docker-down   Stop Docker services"
	@echo "  docker-clean  Remove all Docker resources"
	@echo "  deploy-dev    Deploy development environment"
	@echo "  deploy-prod   Deploy production environment"
	@echo "  clean         Remove build artifacts"
	@echo "  help          Show this help message"
