.PHONY: all build test clean up down health-check lint proto

# ============================================================
# CIVA Platform — Makefile
# ============================================================

# --- Docker Compose ---
up:
	docker-compose up -d

up-build:
	docker-compose up -d --build

down:
	docker-compose down

down-clean:
	docker-compose down -v --remove-orphans

logs:
	docker-compose logs -f

# --- Build ---
build-sentinel:
	cd services/sentinel-sdk && go build -o bin/sentinel cmd/sentinel/main.go

build-all: build-sentinel
	@echo "All services built"

# --- Test ---
test-sentinel:
	cd services/sentinel-sdk && go test ./... -v -cover

test-behavior:
	cd services/behavior-agent && python -m pytest tests/ -v --cov=src

test-orchestrator:
	cd services/orchestrator && python -m pytest tests/ -v --cov=src

test-deception:
	cd services/deception-agent && python -m pytest tests/ -v --cov=src

test-threat-intel:
	cd services/threat-intel && python -m pytest tests/ -v --cov=src

test: test-sentinel test-behavior test-orchestrator test-deception test-threat-intel

test-integration:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	sleep 15
	cd services/sentinel-sdk && go test ./tests/ -tags=integration -v
	cd services/behavior-agent && python -m pytest tests/test_integration.py -v
	cd services/orchestrator && python -m pytest tests/test_integration.py -v
	cd services/deception-agent && python -m pytest tests/test_integration.py -v
	cd services/threat-intel && python -m pytest tests/test_integration.py -v
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# --- Lint ---
lint-go:
	cd services/sentinel-sdk && golangci-lint run ./...

lint-python:
	ruff check services/behavior-agent services/orchestrator services/deception-agent services/threat-intel
	mypy services/behavior-agent/src services/orchestrator/src services/deception-agent/src services/threat-intel/src

lint: lint-go lint-python

# --- Proto ---
proto:
	protoc --go_out=services/sentinel-sdk/pkg/models --go_opt=paths=source_relative \
		--python_out=shared/python/civa_common \
		shared/proto/*.proto

# --- Health Check ---
health-check:
	@echo "Checking Sentinel SDK..."
	@curl -sf http://localhost:8001/health || echo "UNHEALTHY"
	@echo "Checking Behavior Agent..."
	@curl -sf http://localhost:8002/health || echo "UNHEALTHY"
	@echo "Checking Orchestrator..."
	@curl -sf http://localhost:8003/health || echo "UNHEALTHY"
	@echo "Checking Deception Agent..."
	@curl -sf http://localhost:8004/health || echo "UNHEALTHY"
	@echo "Checking Threat Intel..."
	@curl -sf http://localhost:8005/health || echo "UNHEALTHY"
	@echo "Health check complete."

# --- Train ---
train-model:
	cd services/behavior-agent && python training/train_model.py

generate-synthetic:
	cd services/behavior-agent && python training/generate_synthetic.py

# --- Deploy ---
deploy-staging:
	kubectl apply -f infrastructure/kubernetes/namespaces.yaml
	kubectl apply -f infrastructure/kubernetes/ -R

deploy-prod:
	@echo "Production deployment requires manual approval"
	@echo "Run: kubectl apply -f infrastructure/kubernetes/ -R --context=prod"
