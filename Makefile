.PHONY: install api worker seed test lint format typecheck migrate web mobile infra check

install:
	python -m pip install -e ".[dev]"

api:
	python -m uvicorn backend.app.main:app --reload --port 8000

worker:
	python -m backend.app.worker

seed:
	python -m backend.app.seed

test:
	python -m pytest

lint:
	python -m ruff check backend

format:
	python -m ruff format backend

typecheck:
	python -m mypy backend/app

migrate:
	python -m alembic -c backend/alembic.ini upgrade head

web:
	corepack pnpm --dir apps/web dev

mobile:
	corepack pnpm --dir apps/mobile start

infra:
	corepack pnpm --dir infra/cdk synth

check: lint typecheck test

