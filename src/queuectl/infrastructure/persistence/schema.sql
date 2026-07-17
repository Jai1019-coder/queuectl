CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    payload TEXT NOT NULL,
    priority INTEGER NOT NULL,
    state TEXT NOT NULL,
    retry_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    worker_id TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS workers (
    id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dead_letter_queue (
    job_id TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    failed_at TEXT NOT NULL,
    retry_count INTEGER NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(id)
);