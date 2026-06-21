.PHONY: install lint typecheck test build audit api-dev web-dev infra-up infra-down compose-config pre-commit backup-restore-drill migration-dry-run smoke-check migrate seed-demo

install:
	cd apps/api && uv sync --extra dev
	npm install

lint:
	cd apps/api && uv run ruff check app tests
	npm run lint

typecheck:
	cd apps/api && uv run mypy app tests
	cd apps/web && npm run typecheck

.PHONY: audit
audit:
	cd apps/api && uv run bandit -r app
	cd apps/api && uv run safety check
	cd apps/web && npm audit --audit-level=moderate

test:
	cd apps/api && uv run pytest

build:
	npm run build

api-dev:
	cd apps/api && uv run uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000

web-dev:
	npm --workspace apps/web run dev

infra-up:
	docker compose -f infra/docker-compose.local.yml up -d

infra-down:
	docker compose -f infra/docker-compose.local.yml down

compose-config:
	docker compose -f infra/docker-compose.local.yml config

pre-commit:
	pre-commit run --all-files

backup-restore-drill:
	./scripts/backup-restore-drill.sh $(DRILL_ARGS)

migration-dry-run:
	./scripts/migration-dry-run.sh $(DRILL_ARGS)

smoke-check:
	./scripts/smoke-check.sh $(DRILL_ARGS)


migrate:
	cd apps/api && uv run alembic upgrade head

seed-demo:
	cd apps/api && uv run python ../../scripts/seed_demo_data.py
