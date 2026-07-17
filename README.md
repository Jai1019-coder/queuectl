# QueueCTL

QueueCTL is a small, durable command queue for local jobs, retries, workers,
and dead-letter handling.

## Setup

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\queuectl.exe --help
```

On Unix-like shells, use `python3` and `.venv/bin/python` instead.

The full architecture, usage guide, and trade-offs will be filled in after the
core modules are implemented.
