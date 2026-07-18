#!/usr/bin/env python3
"""Rough throughput benchmark for QueueCTL.

Enqueues N trivial jobs, then drains them with W worker processes,
reporting elapsed time and jobs/second.

Usage:
    python scripts/benchmark.py [job_count] [worker_count]
"""

from __future__ import annotations

import sys
import time

from queuectl.config.settings import get_settings
from queuectl.core.container import build_container
from queuectl.workers.worker_manager import start_workers


def main() -> None:
    """Run the benchmark and print results."""
    job_count = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    worker_count = int(sys.argv[2]) if len(sys.argv) > 2 else 4

    settings = get_settings()

    with build_container(settings) as container:
        for _ in range(job_count):
            container.enqueue_job.execute(name="true")

    print(f"Enqueued {job_count} jobs. Draining with {worker_count} worker(s)...")

    started = time.monotonic()
    start_workers(settings, count=worker_count, block=True, drain=True)
    elapsed = time.monotonic() - started

    throughput = job_count / elapsed if elapsed > 0 else float("inf")
    print(f"Processed {job_count} jobs in {elapsed:.2f}s "
          f"({throughput:.1f} jobs/sec)")


if __name__ == "__main__":
    main()
