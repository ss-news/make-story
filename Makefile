.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "%-18s %s\n", $$1, $$2}'

dev-db: ## Start postgres in docker
	docker run --rm -d --name make-story-pg \
	  -e POSTGRES_USER=makestory -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=makestory \
	  -p 5432:5432 postgres:16-alpine

dev-db-stop: ## Stop dev postgres
	docker stop make-story-pg || true

dev-be: ## Run backend with hot reload
	cd backend && air

dev-fe: ## Run frontend dev server
	cd frontend && npm run dev

test-be: ## Run backend tests
	cd backend && go test ./...

test-fe: ## Run frontend tests
	cd frontend && npm test -- --run

lint-be: ## Lint backend
	cd backend && go vet ./... && gofmt -l . | (! grep .)

typecheck-fe: ## Frontend type-check
	cd frontend && npm run typecheck

build-fe: ## Build frontend bundle
	cd frontend && npm run build && rm -rf ../backend/internal/api/static/dist && cp -r dist ../backend/internal/api/static/dist

build: build-fe ## Build single docker image
	docker build -f deploy/Dockerfile -t make-story:dev .

up: ## docker-compose up
	cd deploy && docker compose up -d

down: ## docker-compose down
	cd deploy && docker compose down

.PHONY: help dev-db dev-db-stop dev-be dev-fe test-be test-fe lint-be typecheck-fe build-fe build up down
