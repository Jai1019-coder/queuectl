# QueueCTL Architecture

QueueCTL follows Clean Architecture, adapted for Python, with dependencies
pointing strictly inward: `cli/` depends on `application/`, which depends
only on `domain/` and abstract `repositories/` interfaces —
`infrastructure/` implements those interfaces but nothing in `domain/` or
`application/` imports from it.

## Layers

| Layer | Responsibility | Depends on |
|---|---|---|
| `domain/` | Entities, value objects, policies. Pure Python, no I/O. | nothing |
| `application/` | Use cases orchestrating domain entities. | `domain/`, `repositories/` (interfaces) |
| `repositories/` | Abstract repository interfaces. | `domain/` |
| `infrastructure/` | SQLite/in-memory repositories, process execution, logging, persistence. | `domain/`, `repositories/` |
| `workers/` | Worker runtime loop, process pool, lifecycle/shutdown. | `application/`, `core/`, `infrastructure/process` |
| `cli/` | Typer commands. | `core/container` (composition root) |
| `core/` | Composition root (`container.py`), shared interfaces (`Clock`), constants. | everything (wires it together) |
| `config/` | Pydantic settings, layered defaults → `.env` → env vars → persisted overrides. | nothing |

## Composition root

`core/container.py` is the only place concrete infrastructure classes are
instantiated. `Container` holds every wired dependency (repositories, use
cases, retry policy, command executor, clock) built from a resolved
`Settings` object. CLI commands call `build_container()` inside a
`with cli_container() as container:` block (see `cli/state.py`) so each
command's database connection is opened and closed cleanly, and `--help`
never touches disk.

## Job lifecycle

See [job_lifecycle.md](job_lifecycle.md) for the full state diagram and
transition rules.

## Concurrency model

Multiple worker *processes* (not threads — see below) compete for jobs via
`JobRepository.claim_next()`. Both concrete implementations guarantee at
most one caller ever claims a given job:

- **SQLite** (`SQLiteJobRepository.claim_next`): opens a `BEGIN IMMEDIATE`
  transaction (acquiring SQLite's write lock up front), selects the best
  candidate, and claims it with a single conditional
  `UPDATE ... WHERE state = 'pending'`. Any other process attempting to
  claim concurrently blocks on the same write lock until this transaction
  commits, so two processes can never see the same row as still-pending.
- **In-memory** (`InMemoryJobRepository.claim_next`): a `threading.Lock`
  serializes the equivalent select-and-mutate sequence for concurrent
  threads within one process.

`tests/integration/test_repository.py` proves this directly: real OS
threads (each with their own SQLite connection to a shared file, mirroring
separate worker processes) race to claim a fixed set of jobs, and the test
asserts every job was claimed by exactly one caller.

### Why processes, not threads, for workers?

The assignment specifies "multiple worker processes." `workers/worker_pool.py`
spawns each worker as an independent `multiprocessing.Process` (using the
`spawn` start method for cross-platform consistency), each opening its own
SQLite connection — connections cannot cross process boundaries, and this
also gives true OS-level parallelism for CPU-bound job commands, unlike
Python threads under the GIL.

## Worker lifecycle & graceful shutdown

`queuectl worker start` and `queuectl worker stop` are separate CLI
invocations with no shared memory. Coordination happens the same way
traditional Unix daemons coordinate:

1. `worker start` spawns N processes and writes their PIDs to
   `.queuectl.worker.pid` in the current directory.
2. Each worker process installs its own SIGINT/SIGTERM handler
   (`workers/lifecycle.py`) that sets an in-process `ShutdownSignal`.
3. The `WorkerRuntime` loop (`workers/worker.py`) only checks this signal
   *between* jobs — a job already executing always runs to completion.
4. `worker stop` reads the PID file, sends SIGTERM to each recorded PID,
   and waits (up to a timeout) for them to exit before cleaning up the PID
   file.

## Retry & Dead Letter Queue

`RetryPolicy` (domain layer) decides, given a job's current `retry_count`,
whether to retry and what the next backoff delay should be
(`BackoffPolicy`, supporting fixed/linear/exponential strategies). The
`RetryJob` use case reschedules a job back to `PENDING` with a future
`available_at`; `MoveToDlq` moves an exhausted job to `DEAD` and records a
`DlqEntry`. `ReplayDlqJob` resets a DLQ entry's job back to `PENDING` for
another attempt.

## Configuration

`config/schema.py` defines a Pydantic `Settings` model. Values resolve in
increasing priority: built-in defaults → `.env` file → environment
variables → a local `.queuectl.config.json` overrides file written by
`queuectl config set` (see `config/loader.py`). This file always takes
precedence so explicit configuration changes persist across restarts.
