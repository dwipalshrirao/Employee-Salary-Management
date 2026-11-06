.PHONY: setup backend frontend migrate seed test test-slow lint openapi

PYTHON ?= python3.12
SEED_ARGS ?= --reset --verify

setup:
	$(PYTHON) -m venv backend/.venv
	backend/.venv/bin/python -m pip install --upgrade pip
	backend/.venv/bin/python -c 'import tomllib; from pathlib import Path; print(*tomllib.loads(Path("backend/pyproject.toml").read_text())["project"]["dependencies"], sep="\n")' | xargs backend/.venv/bin/python -m pip install
	cd frontend && npm ci

backend:
	@set -a; . ./.env; set +a; cd backend && .venv/bin/python manage.py runserver 127.0.0.1:8000

frontend:
	cd frontend && npm run dev

migrate:
	@set -a; . ./.env; set +a; cd backend && .venv/bin/python manage.py migrate

seed:
	@set -a; . ./.env; set +a; cd backend && .venv/bin/python manage.py seed --employees 10000 --seed 42 $(SEED_ARGS)

test:
	cd backend && SECRET_KEY=test-secret DEBUG=true .venv/bin/python -m pytest -m "not slow"
	cd frontend && npm test

test-slow:
	cd backend && SECRET_KEY=test-secret DEBUG=true .venv/bin/python -m pytest -m slow

lint:
	cd backend && .venv/bin/python -m ruff check .
	cd frontend && npm run lint

openapi:
	cd backend && SECRET_KEY=test-secret DEBUG=true .venv/bin/python manage.py spectacular --file ../docs/openapi.json --format openapi-json
