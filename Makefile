PYTHON ?= .venv/Scripts/python.exe
PYTEST ?= .venv/Scripts/pytest.exe
RUFF ?= .venv/Scripts/ruff.exe
BLACK ?= .venv/Scripts/black.exe
ALEMBIC ?= .venv/Scripts/alembic.exe
QUEUECTL ?= .venv/Scripts/queuectl.exe

.PHONY: install test lint format migrate run

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTEST)

lint:
	$(RUFF) check .

format:
	$(BLACK) .

migrate:
	$(ALEMBIC) upgrade head

run:
	$(QUEUECTL) --help
