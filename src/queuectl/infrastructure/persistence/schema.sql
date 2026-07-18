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
    error_message TEXT,
    FOREIGN KEY(worker_id)
    REFERENCES workers(id)
    ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS workers (
    id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    status TEXT NOT NULL,

    started_at TEXT NOT NULL,
    last_heartbeat TEXT NOT NULL,

    max_concurrency INTEGER NOT NULL,
    jobs_processed INTEGER NOT NULL,

    current_job_id TEXT,

    tags TEXT NOT NULL,

    FOREIGN KEY(current_job_id)
        REFERENCES jobs(id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS dead_letter_queue (
    job_id TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    failed_at TEXT NOT NULL,
    retry_count INTEGER NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(id)
);