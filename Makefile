.PHONY: format lint test migrate

format:
	uv run ruff check . --fix
	uv run ruff format .

lint:
	uv run mypy src tests
	uv run flake8 src tests

test:
	@sh scripts/test.sh

migrate:
	uv run alembic -c src/alembic.ini upgrade head
