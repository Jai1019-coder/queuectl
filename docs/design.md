# Design Notes

This file records design decisions made while completing QueueCTL that
aren't obvious from the code alone. See also
[architecture.md](architecture.md) for the layer-by-layer structure and
[job_lifecycle.md](job_lifecycle.md) for the state machine.

## Why raw `sqlite3` instead of SQLAlchemy?

The original scaffolding declared `sqlalchemy` and `alembic` as
dependencies, but the persistence layer (`infrastructure/persistence/`,
`infrastructure/repositories/sqlite_*`) was implemented directly against
`sqlite3` with a hand-written `schema.sql`. This was kept rather than
migrated to an ORM because:

- The atomic `claim_next()` operation (see below) needs precise control
  over the transaction boundary (`BEGIN IMMEDIATE`) and the exact `UPDATE
  ... WHERE state = 'pending'` statement — an ORM would obscure this
  without adding safety.
- The unused `sqlalchemy`/`alembic` dependencies and empty `alembic/`
  migration scaffold were removed to keep the dependency list honest.

## The duplicate-processing bug that was here, and the fix

The as-received `ProcessJob` use case called `repository.next_available()`
(a plain read), then `job.claim(worker_id)` in Python, then
`repository.update(job)` — three separate steps with no lock across them.
Two workers calling this concurrently could both read the same pending
job before either had written back its claim, and both would then execute
it: exactly the "race conditions or duplicate job execution" failure mode
the assignment calls out as disqualifying.

The fix was a new `JobRepository.claim_next(worker_id)` method, implemented
atomically in both concrete repositories (SQLite via `BEGIN IMMEDIATE` +
conditional `UPDATE`; in-memory via a `threading.Lock`), with
`ProcessJob.execute()` now delegating to it. Verified directly in
`tests/integration/test_repository.py` with real concurrent
threads/connections.

## Two other latent bugs found and fixed while wiring the CLI/workers

1. **Missing FK-friendly design**: `schema.sql` declared foreign keys from
   `jobs.worker_id → workers.id` and `workers.current_job_id → jobs.id`,
   but nothing in the system ever pre-registers a `Worker` row before a
   job references its `worker_id` (workers are ad-hoc string identifiers
   in this design, not a strict aggregate reference) — so the very first
   real claim against SQLite failed with `FOREIGN KEY constraint failed`.
   The constraints were dropped; `worker_id` remains a plain identifying
   tag, consistent with how the in-memory repository already treated it.
2. **Missing column**: `dead_letter_queue` never had an `error_message`
   column, even though `SQLiteDlqRepository.save()` always tried to insert
   one and `DlqEntry` always carries one. This was invisible to the
   existing test suite because the only integration test exercising the
   DLQ flow used `InMemoryDlqRepository`, not the SQLite implementation.
   Found via an end-to-end CLI smoke test (`worker start` → job fails →
   DLQ), fixed by adding the column to `schema.sql`.

## Batch/drain mode

`--drain` on `worker start` isn't in the base spec — it was added because
`worker start` normally blocks forever (by design, per "worker lifecycle
management"), which makes it untestable and unusable for one-off batch
runs without a second terminal running `worker stop`. `--drain` makes each
worker exit as soon as the queue is empty, which both `tests/e2e/` and
real batch/CI usage rely on.

## What was intentionally left unimplemented

The original directory scaffolding (see the repo root `AGENTS.md`) included
several packages that were never wired into the working system:
`retry/`, `scheduler/` (beyond the read-only `queuectl scheduler` view),
`models/`, `services/`, `utils/`, `validators/`,
`infrastructure/config/`, `infrastructure/locking/`,
`infrastructure/storage/`. Their responsibilities are already fully
covered by `domain/policies/retry_policy.py` +
`domain/value_objects/backoff_policy.py` (retry), `application/use_cases/`
+ `dlq/` via `MoveToDlq`/`ReplayDlqJob` (DLQ), `config/` (settings), and
`infrastructure/persistence/` + `infrastructure/repositories/` (storage).
Filling these with parallel, unused implementations would only invite
confusion about which system is authoritative; they're left as empty
placeholders from the initial architecture brainstorm rather than being
built out as dead code.
