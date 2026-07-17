FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE alembic.ini ./
COPY alembic ./alembic
COPY src ./src

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["queuectl"]
