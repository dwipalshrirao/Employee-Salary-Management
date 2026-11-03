.PHONY: setup backend frontend migrate seed test test-watch lint openapi

SEED_ARGS ?= --reset --verify

setup:
	@echo "setup: not implemented yet (scaffold only)"
	@exit 1

backend:
	@set -a; . ./.env; set +a; cd backend && .venv/bin/python manage.py runserver 127.0.0.1:8001

frontend:
	cd frontend && npm run dev

migrate:
	@set -a; . ./.env; set +a; cd backend && .venv/bin/python manage.py migrate

seed:
	@set -a; . ./.env; set +a; cd backend && .venv/bin/python manage.py seed --employees 10000 --seed 42 $(SEED_ARGS)

test:
	cd backend && SECRET_KEY=test-secret DEBUG=true .venv/bin/python -m pytest
	cd frontend && npm test

test-watch:
	@echo "test-watch: not implemented yet (scaffold only)"
	@exit 1

lint:
	cd backend && .venv/bin/python -m ruff check .
	cd frontend && npm run lint

openapi:
	cd backend && SECRET_KEY=test-secret DEBUG=true .venv/bin/python manage.py spectacular --file ../docs/openapi.json --format openapi-json
