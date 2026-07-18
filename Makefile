PYTHON ?= .venv/Scripts/python.exe
PYTEST ?= .venv/Scripts/pytest.exe
RUFF ?= .venv/Scripts/ruff.exe
BLACK ?= .venv/Scripts/black.exe
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
	$(PYTHON) -c "from queuectl.config.settings import get_settings; from queuectl.infrastructure.persistence.connection import SQLiteConnection; from queuectl.infrastructure.persistence.migrations import initialize_database; s = get_settings(); initialize_database(SQLiteConnection(s.database_path)); print('database initialized at', s.database_path)"

run:
	$(QUEUECTL) --help
