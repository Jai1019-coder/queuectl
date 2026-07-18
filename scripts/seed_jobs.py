#!/usr/bin/env python3
"""Seed the queue with sample jobs for manual testing.

Usage:
    python scripts/seed_jobs.py [count]

Enqueues ``count`` (default: 10) jobs: a mix of commands that succeed
immediately and commands that fail, so ``queuectl worker start --drain``
exercises both the completion and retry/DLQ paths.
"""

from __future__ import annotations

import sys

from queuectl.core.container import build_container


def main() -> None:
    """Enqueue a batch of sample jobs."""
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    with build_container() as container:
        for i in range(count):
            if i % 3 == 0:
                command = "exit 1"
            else:
                command = f"echo 'sample job {i}'"

            job = container.enqueue_job.execute(
                name=command,
                priority=i % 5,
            )
            print(f"enqueued {job.id}  priority={job.priority}  {job.name}")

    print(f"\nSeeded {count} job(s). Run 'queuectl worker start --drain' "
          "to process them.")


if __name__ == "__main__":
    main()
