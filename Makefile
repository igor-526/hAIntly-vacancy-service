.PHONY: format lint test test-infra migrate

format:
	uv run ruff check . --fix
	uv run ruff format .
	@sh scripts/check-format-excludes.sh

lint:
	uv run mypy src tests
	uv run flake8 src tests

test:
	uv run pytest -m "not infrastructure"

test-infra:
	@sh scripts/test.sh

migrate:
	uv run alembic -c src/alembic.ini upgrade head
