# Job Lifecycle

## States

| State | Meaning |
|---|---|
| `PENDING` | Waiting to be claimed by a worker (immediately, or after a scheduled retry delay). |
| `PROCESSING` | Currently being executed by a worker. |
| `COMPLETED` | Command exited 0. Terminal state. |
| `FAILED` | Command exited non-zero (or timed out). Transient — always followed immediately by either a retry reschedule or a DLQ move. |
| `DEAD` | Retries exhausted; moved to the Dead Letter Queue. Terminal state. |

## Transitions

```
                 ┌──────────────────────────────────────────────┐
                 │                                                │
                 ▼                                                │
   create() → PENDING ──claim()/mark_processing()──▶ PROCESSING   │
                 ▲                                       │        │
                 │                                       │        │
                 │                              mark_completed()  │
                 │                                       │        │
                 │                                       ▼        │
        schedule_retry()                            COMPLETED     │
                 │                                    (terminal)  │
                 │                                                │
                 │                              mark_failed()     │
                 │                                       │        │
                 │                                       ▼        │
                 └───────────────────────────────────  FAILED     │
                                                          │        │
                                                  move_to_dead()   │
                                                          │        │
                                                          ▼        │
                                                        DEAD ──────┘
                                                     (terminal)
```

## Rules enforced by the `Job` entity

- A job can only be **claimed** (or `mark_processing()`'d) from `PENDING`,
  and only once `available_at <= now` — this is what makes retry backoff
  actually delay re-execution.
- A job can only be **completed** from `PROCESSING`.
- A job can only be **failed** from `PROCESSING`.
- `schedule_retry(delay_seconds)` moves a job back to `PENDING` and pushes
  `available_at` into the future by `delay_seconds`. It does **not**
  increment `retry_count` — that's `increment_retry()`'s job, called
  separately by the `RetryJob` use case.
- `move_to_dead()` is disallowed only from `COMPLETED` (idempotent from
  every other state).
- Every valid transition refreshes `updated_at`.
- Illegal transitions raise `ValueError` — never silently no-op.

## Who decides retry vs. DLQ?

The `Job` entity itself has no opinion on *how many* retries are allowed —
that's `RetryPolicy` (domain layer), given `max_retries` and a
`BackoffPolicy`. The worker runtime (`workers/worker.py`) asks
`RetryPolicy.should_retry(job.retry_count)` after a failure:

- **True** → `RetryJob` use case: `increment_retry()` +
  `schedule_retry(backoff.compute_delay(retry_count))`.
- **False** → `MoveToDlq` use case: `move_to_dead()` + persist a
  `DlqEntry` recording the failure reason and last error message.
