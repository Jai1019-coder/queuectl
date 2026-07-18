# CLI Reference

## `queuectl enqueue <job>`

Add a new job to the queue. `<job>` is either a raw shell command, or a
JSON object with a required `command` key and optional `priority`/`payload`.

```
queuectl enqueue "sleep 2"
queuectl enqueue '{"command":"sleep 2","priority":1}'
queuectl enqueue "echo hi" --priority 5
```

## `queuectl worker start [--count N] [--drain/--no-drain]`

Start `N` worker processes (default: configured `worker-count`). Blocks in
the foreground until interrupted (Ctrl+C) or stopped via
`queuectl worker stop` from another terminal. With `--drain`, each worker
exits as soon as the queue is empty instead of running indefinitely.

## `queuectl worker stop`

Send SIGTERM to every recorded worker process and wait for graceful exit
(finishing any job currently in progress) before returning.

## `queuectl status`

Show a count of jobs by state, workers by status, and total DLQ entries.

## `queuectl list [--state STATE] [--limit N]`

List jobs, optionally filtered by state (`pending`, `processing`,
`completed`, `failed`, `dead`). Default limit: 50.

## `queuectl dlq list`

Show every job currently in the Dead Letter Queue, with its retry count,
reason, and last error message.

## `queuectl dlq retry <job_id>`

Reset a DLQ entry's job back to `PENDING` so it can be attempted again.

## `queuectl config set <key> <value>`

Persist a configuration override to `.queuectl.config.json` in the current
directory. Valid keys:

| Key | Type | Default |
|---|---|---|
| `database-url` | str | `sqlite:///./queuectl.db` |
| `max-retries` | int | `3` |
| `backoff-strategy` | `fixed`\|`linear`\|`exponential` | `exponential` |
| `backoff-initial-delay` | int (seconds) | `5` |
| `backoff-multiplier` | float | `2.0` |
| `backoff-max-delay` | int (seconds) | `300` |
| `worker-count` | int | `1` |
| `log-level` | str | `INFO` |
| `job-timeout` | float (seconds, `0` = none) | `0` |
| `poll-interval` | float (seconds) | `0.5` |

## `queuectl scheduler`

List jobs currently `PENDING` with a future `available_at` — i.e. jobs
waiting out a retry backoff delay.
