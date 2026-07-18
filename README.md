# QueueCTL

QueueCTL is a production-grade, CLI-based background job queue. It manages
background jobs across multiple worker processes, retries failed jobs with
exponential backoff, and moves permanently-failed jobs to a Dead Letter Queue
(DLQ). All state is persisted to SQLite, so jobs survive process restarts.

## Setup Instructions

Requires Python 3.12+.

**Unix / macOS:**

```bash
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/queuectl --help
```

**Windows (PowerShell):**

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\queuectl.exe --help
```

Configuration defaults live in `.env.example` — copy it to `.env` to
customize retry counts, backoff behavior, worker count, and log level before
running the CLI:

```bash
cp .env.example .env
```

## Usage Examples

**Enqueue a job** (either a raw shell command, or a JSON payload):

```bash
$ queuectl enqueue "echo 'Hello World'"
{
  "id": "883f8532-14f4-4d3f-b617-f6f0352b8807",
  "name": "echo 'Hello World'",
  "payload": {},
  "priority": 0,
  "state": "pending",
  ...
}

$ queuectl enqueue '{"command":"sleep 2","priority":1}'
```

**Start workers** (blocks in the foreground; use `--drain` to process the
current queue and exit instead of running indefinitely):

```bash
$ queuectl worker start --count 3
Starting 3 worker(s). Press Ctrl+C or run 'queuectl worker stop' to stop.
```

**Stop workers from another terminal:**

```bash
$ queuectl worker stop
Stopped 3 worker(s).
```

**Check status:**

```bash
$ queuectl status
Jobs:
  pending      1
  processing   0
  completed    4
  failed       0
  dead         1

Workers:
  online       0
  busy         0
  offline      3

DLQ entries: 1
```

**List jobs, optionally filtered by state:**

```bash
$ queuectl list --state pending
d2a5c6c2-5cb8-4943-aa46-33f17055f1be  pending     priority=0    retries=0   sleep 2
```

**Inspect and replay the Dead Letter Queue:**

```bash
$ queuectl dlq list
d6eea8b0-3c6b-43d2-a50c-82804f258384  retries=3  reason='Retry attempts exhausted.'  error='Command exited with code 1.'

$ queuectl dlq retry d6eea8b0-3c6b-43d2-a50c-82804f258384
Job d6eea8b0-3c6b-43d2-a50c-82804f258384 reset to pending and ready for retry.
```

**Manage configuration:**

```bash
$ queuectl config set max-retries 5
max-retries = 5

$ queuectl config set backoff-multiplier 2.5
backoff-multiplier = 2.5
```

Valid config keys: `database-url`, `max-retries`, `backoff-strategy`,
`backoff-initial-delay`, `backoff-multiplier`, `backoff-max-delay`,
`worker-count`, `log-level`, `job-timeout`, `poll-interval`.

**View delayed/scheduled retries** (bonus feature):

```bash
$ queuectl scheduler
31f0ebab-4276-42ba-841b-77587d8080a3  retries=1  available_in=3.9s  exit 2
```

## Architecture Overview

QueueCTL follows Clean Architecture, adapted for Python, with dependencies
pointing strictly inward:

```
cli/  →  application/  →  domain/
              ↑
      infrastructure/ (implements domain/core interfaces)
```

- **`domain/`** — Pure Python, zero I/O. `Job`, `Worker`, and `DlqEntry`
  entities own all state-transition rules (e.g. a job can only be completed
  from `PROCESSING`, illegal transitions raise `ValueError`). `RetryPolicy`
  and `BackoffPolicy` are value objects computing retry eligibility and
  exponential delay.
- **`application/`** — Use cases (`EnqueueJob`, `ProcessJob`, `CompleteJob`,
  `FailJob`, `RetryJob`, `MoveToDlq`, `ReplayDlqJob`, `GetStatus`) orchestrate
  domain entities via repository interfaces only — never a concrete
  database class.
- **`repositories/`** — Abstract `JobRepository`, `WorkerRepository`, and
  `DlqRepository` interfaces the application layer depends on.
- **`infrastructure/`** — Concrete implementations: `SQLiteJobRepository` /
  `SQLiteWorkerRepository` / `SQLiteDlqRepository` (production), and
  `InMemory*Repository` (fast unit testing). Also contains process execution
  (`SubprocessCommandExecutor`), structured logging, and raw-SQL schema
  migrations.
- **`workers/`** — `WorkerRuntime` runs the claim → execute → record loop for
  one worker; `WorkerPool` spawns N of these as independent OS processes;
  `worker_manager` coordinates `start`/`stop` across separate CLI
  invocations via a PID file and OS signals.
- **`cli/`** — Typer commands. Each command builds its own short-lived
  `Container` (composition root, `core/container.py`) so `--help` never
  touches the database.

### Job lifecycle

```
PENDING → PROCESSING → COMPLETED
             ↓
          FAILED → (schedule_retry) → PENDING   [if retries remain]
             ↓
           DEAD                                  [once retries exhausted]
```

### Concurrency & duplicate-processing prevention

Multiple worker **processes** compete for jobs via
`JobRepository.claim_next()`, which is atomic:

- **SQLite**: a `BEGIN IMMEDIATE` transaction acquires SQLite's write lock,
  then a `SELECT` + conditional `UPDATE ... WHERE state = 'pending'`
  guarantees at most one caller ever claims a given row, even under heavy
  concurrent load from separate OS processes.
- **In-memory**: a `threading.Lock` serializes the same select-and-mutate
  sequence for concurrent threads.

This is verified directly in `tests/integration/test_repository.py`, where
real threads/connections race to claim jobs and every job is confirmed
claimed exactly once.

### Graceful shutdown

Each worker only checks its shutdown signal *between* jobs — never
mid-execution — so a job already running always finishes before the worker
exits. `queuectl worker stop` sends SIGTERM to every recorded worker PID and
waits (up to a timeout) for graceful exit before returning.

## Assumptions & Trade-offs

- **Persistence**: raw `sqlite3` + hand-written schema/migrations were used
  instead of SQLAlchemy ORM, for a smaller, more auditable persistence
  layer with full control over the atomic `claim_next` SQL. SQLAlchemy and
  Alembic were removed from dependencies since they were unused.
- **Job identity**: the CLI accepts either a raw shell command string or a
  JSON payload (`{"command": "...", "priority": ..., "payload": {...}}`).
  User-supplied job IDs are not honored — QueueCTL always generates its own
  UUID — since allowing client-chosen IDs would reintroduce the same
  race/duplication class of bug `claim_next` was built to eliminate.
- **Worker coordination**: `worker start` and `worker stop` are separate CLI
  invocations with no shared memory, so coordination happens through a PID
  file plus OS signals (SIGTERM) — the same mechanism traditional Unix
  daemons use, rather than requiring a persistent supervisor process.
- **`--drain` mode**: added beyond the base spec so a worker fleet can
  process the current queue and exit deterministically — useful for CI,
  batch runs, and automated testing, in addition to the default
  run-until-stopped mode.
- **Scheduler (bonus)**: `queuectl scheduler` is a read-only view of jobs
  currently waiting out a retry backoff delay. Full arbitrary `run_at`
  scheduling on initial enqueue was out of scope for this pass.
- **Job timeout (bonus)**: supported via `--job-timeout` config; `0`
  (default) means no timeout.

## Testing Instructions

```bash
# Run the full suite
.venv/bin/pytest

# With coverage
.venv/bin/pytest --cov=queuectl --cov-report=term-missing

# Lint / format check
.venv/bin/ruff check .
.venv/bin/black --check .
```

The suite includes:

- **Unit tests** (`tests/unit/`) — domain entities, policies, use cases,
  and both concrete repository implementations, using fakes for isolation.
- **Integration tests** (`tests/integration/`) — real SQLite persistence,
  end-to-end retry/DLQ flows, and multi-threaded concurrency proofs for
  `claim_next`.
- **End-to-end tests** (`tests/e2e/`) — the real Typer CLI invoked via
  `CliRunner` against an isolated working directory, covering every command.

As of this submission: **377 tests passing, ~94% line coverage**, `ruff`
and `black` both clean.
