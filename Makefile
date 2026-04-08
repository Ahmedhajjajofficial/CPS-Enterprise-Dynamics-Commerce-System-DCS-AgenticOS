# ═══════════════════════════════════════════════════════════════════════════════
# CP'S Enterprise Dynamics Commerce System (DCS)
# Makefile — Build, Test, Lint, Run
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: help install build dev lint test clean \
        install-app install-pos install-local-agent install-regional-agent \
        build-app build-pos build-regional-agent \
        dev-app dev-pos \
        lint-app lint-pos lint-regional-agent \
        test-local-agent test-regional-agent \
        docker-up docker-down docker-logs docker-ps \
        proto

# ─── Default ──────────────────────────────────────────────────────────────────

help: ## Show this help message
	@echo ""
	@echo "CP'S Enterprise DCS — Available Targets"
	@echo "════════════════════════════════════════"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ─── Variables ────────────────────────────────────────────────────────────────

APP_DIR           := app
POS_DIR           := cps-enterprise-dcs/pos-interface
LOCAL_AGENT_DIR   := cps-enterprise-dcs/local-agent
REGIONAL_AGENT_DIR := cps-enterprise-dcs/regional-agent
INFRA_DIR         := cps-enterprise-dcs/infrastructure
VENV_DIR          := $(LOCAL_AGENT_DIR)/.venv
PYTHON            := $(VENV_DIR)/bin/python
PIP               := $(VENV_DIR)/bin/pip

# ─── Install ──────────────────────────────────────────────────────────────────

install: install-app install-pos install-local-agent install-regional-agent ## Install all dependencies
	@echo "All dependencies installed."

install-app: ## Install admin app dependencies
	cd $(APP_DIR) && npm install

install-pos: ## Install POS interface dependencies
	cd $(POS_DIR) && npm install

install-local-agent: ## Install local agent (Python) dependencies
	python3 -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip
	$(PIP) install -r $(LOCAL_AGENT_DIR)/requirements.txt

install-regional-agent: ## Install regional agent (Go) dependencies
	cd $(REGIONAL_AGENT_DIR) && go mod download

# ─── Build ────────────────────────────────────────────────────────────────────

build: build-app build-pos build-regional-agent ## Build all components
	@echo "All components built successfully."

build-app: ## Build admin app (React/Vite)
	cd $(APP_DIR) && npm run build

build-pos: ## Build POS interface (React/Vite)
	cd $(POS_DIR) && npm run build

build-regional-agent: ## Build regional agent (Go)
	cd $(REGIONAL_AGENT_DIR) && go build -o bin/regional-agent ./...

# ─── Development Servers ──────────────────────────────────────────────────────

dev: ## Start all frontend dev servers (background)
	@echo "Starting admin app on :5173 and POS on :3000 ..."
	@$(MAKE) dev-app &
	@$(MAKE) dev-pos &
	@wait

dev-app: ## Start admin app dev server (localhost:5173)
	cd $(APP_DIR) && npm run dev

dev-pos: ## Start POS interface dev server (localhost:3000)
	cd $(POS_DIR) && npm run dev

# ─── Lint ─────────────────────────────────────────────────────────────────────

lint: lint-app lint-regional-agent ## Lint all components
	@echo "All lint checks passed."

lint-app: ## Lint admin app (ESLint)
	cd $(APP_DIR) && npm run lint

lint-pos: ## Lint POS interface (ESLint)
	cd $(POS_DIR) && npm run lint

lint-regional-agent: ## Lint regional agent (go vet)
	cd $(REGIONAL_AGENT_DIR) && go vet ./...

# ─── Test ─────────────────────────────────────────────────────────────────────

test: test-local-agent test-regional-agent ## Run all tests
	@echo "All tests passed."

test-local-agent: ## Run local agent tests (pytest)
	$(PYTHON) -m pytest $(LOCAL_AGENT_DIR)/src/ -v --tb=short

test-regional-agent: ## Run regional agent tests (go test)
	cd $(REGIONAL_AGENT_DIR) && go test ./... -v

# ─── Docker ───────────────────────────────────────────────────────────────────

docker-up: ## Start all Docker services
	docker-compose -f $(INFRA_DIR)/docker-compose.yml up -d

docker-down: ## Stop all Docker services
	docker-compose -f $(INFRA_DIR)/docker-compose.yml down

docker-logs: ## Tail Docker service logs
	docker-compose -f $(INFRA_DIR)/docker-compose.yml logs -f

docker-ps: ## Show Docker service status
	docker-compose -f $(INFRA_DIR)/docker-compose.yml ps

docker-rebuild: ## Rebuild and restart Docker services
	docker-compose -f $(INFRA_DIR)/docker-compose.yml up -d --build

# ─── Clean ────────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	rm -rf $(APP_DIR)/dist
	rm -rf $(POS_DIR)/dist
	rm -rf $(REGIONAL_AGENT_DIR)/bin
	rm -rf $(LOCAL_AGENT_DIR)/.pytest_cache
	rm -rf $(LOCAL_AGENT_DIR)/src/__pycache__
	@echo "Build artifacts cleaned."

clean-all: clean ## Remove all artifacts including node_modules and venv
	rm -rf $(APP_DIR)/node_modules
	rm -rf $(POS_DIR)/node_modules
	rm -rf $(VENV_DIR)
	@echo "All artifacts removed (including node_modules and venv)."

# ─── Protobuf ─────────────────────────────────────────────────────────────────

proto: ## Generate protobuf code from .proto definitions
	@echo "Generating protobuf code..."
	cd cps-enterprise-dcs/proto && \
		protoc --go_out=. --go-grpc_out=. cps_enterprise_v4.proto && \
		python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. cps_enterprise_v4.proto
	@echo "Protobuf code generated."
