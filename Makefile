.PHONY: setup backend frontend migrate seed test test-watch lint openapi

setup:
	@echo "setup: not implemented yet (scaffold only)"
	@exit 1

backend:
	@set -a; . ./.env; set +a; cd backend && .venv/bin/python manage.py runserver 127.0.0.1:8001

frontend:
	@echo "frontend: not implemented yet (scaffold only)"
	@exit 1

migrate:
	@set -a; . ./.env; set +a; cd backend && .venv/bin/python manage.py migrate

seed:
	@echo "seed: not implemented yet (scaffold only)"
	@exit 1

test:
	cd backend && SECRET_KEY=test-secret DEBUG=true .venv/bin/python -m pytest

test-watch:
	@echo "test-watch: not implemented yet (scaffold only)"
	@exit 1

lint:
	cd backend && .venv/bin/python -m ruff check .

openapi:
	cd backend && SECRET_KEY=test-secret DEBUG=true .venv/bin/python manage.py spectacular --file ../docs/openapi.json --format openapi-json
