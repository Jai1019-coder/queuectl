"""Composition root for QueueCTL.

Builds and wires together every concrete dependency (database
connection, repositories, use cases, retry policy, command executor,
logger) from a resolved :class:`~queuectl.config.schema.Settings`
object. The CLI and worker layers depend only on this container and
on abstractions -- never on concrete infrastructure classes directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from queuectl.application.use_cases.complete_job import CompleteJob
from queuectl.application.use_cases.enqueue_job import EnqueueJob
from queuectl.application.use_cases.fail_job import FailJob
from queuectl.application.use_cases.get_status import GetStatus
from queuectl.application.use_cases.move_to_dlq import MoveToDlq
from queuectl.application.use_cases.process_job import ProcessJob
from queuectl.application.use_cases.replay_dlq_job import ReplayDlqJob
from queuectl.application.use_cases.retry_job import RetryJob
from queuectl.config.schema import Settings
from queuectl.config.settings import get_settings
from queuectl.core.interfaces import Clock, SystemClock
from queuectl.domain.policies.retry_policy import RetryPolicy
from queuectl.domain.value_objects.backoff_policy import (
    BackoffPolicy,
    BackoffStrategy,
)
from queuectl.infrastructure.persistence.connection import SQLiteConnection
from queuectl.infrastructure.persistence.migrations import initialize_database
from queuectl.infrastructure.process.command_executor import CommandExecutor
from queuectl.infrastructure.process.subprocess_executor import (
    SubprocessCommandExecutor,
)
from queuectl.infrastructure.repositories.sqlite_dlq_repository import (
    SQLiteDlqRepository,
)
from queuectl.infrastructure.repositories.sqlite_job_repository import (
    SQLiteJobRepository,
)
from queuectl.infrastructure.repositories.sqlite_worker_repository import (
    SQLiteWorkerRepository,
)
from queuectl.repositories.dlq_repository import DlqRepository
from queuectl.repositories.job_repository import JobRepository
from queuectl.repositories.worker_repository import WorkerRepository


@dataclass(slots=True)
class Container:
    """Holds every wired dependency needed by the CLI and workers.

    Attributes:
        settings: The resolved configuration.
        connection: The shared SQLite connection.
        job_repository: Repository for Job aggregates.
        worker_repository: Repository for Worker aggregates.
        dlq_repository: Repository for Dead Letter Queue entries.
        retry_policy: Policy governing retry eligibility and backoff.
        command_executor: Executes a job's shell command.
        clock: Source of the current time.
        enqueue_job: Use case for enqueuing new jobs.
        process_job: Use case for atomically claiming the next job.
        complete_job: Use case for marking a job completed.
        fail_job: Use case for marking a job failed.
        retry_job: Use case for scheduling a retry.
        move_to_dlq: Use case for moving an exhausted job to the DLQ.
        replay_dlq_job: Use case for replaying a DLQ entry.
        get_status: Use case for reading a job's current status.
    """

    settings: Settings
    connection: SQLiteConnection
    job_repository: JobRepository
    worker_repository: WorkerRepository
    dlq_repository: DlqRepository
    retry_policy: RetryPolicy
    command_executor: CommandExecutor
    clock: Clock
    enqueue_job: EnqueueJob
    process_job: ProcessJob
    complete_job: CompleteJob
    fail_job: FailJob
    retry_job: RetryJob
    move_to_dlq: MoveToDlq
    replay_dlq_job: ReplayDlqJob
    get_status: GetStatus

    def close(self) -> None:
        """Release resources held by the container (e.g. the DB connection)."""
        self.connection.close()

    def __enter__(self) -> Container:
        """Support use as a context manager.

        Returns:
            Container: This container.
        """
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Close resources when leaving a ``with`` block."""
        self.close()


def build_container(settings: Settings | None = None) -> Container:
    """Construct a fully-wired :class:`Container`.

    Args:
        settings: Configuration to build the container from. Defaults
            to :func:`queuectl.config.settings.get_settings`.

    Returns:
        Container: A container with every dependency wired together
        and the database schema initialized.
    """
    resolved_settings = settings or get_settings()

    connection = SQLiteConnection(resolved_settings.database_path)
    initialize_database(connection)

    job_repository: JobRepository = SQLiteJobRepository(connection)
    worker_repository: WorkerRepository = SQLiteWorkerRepository(connection)
    dlq_repository: DlqRepository = SQLiteDlqRepository(connection)

    retry_policy = RetryPolicy(
        max_retries=resolved_settings.max_retries,
        backoff=BackoffPolicy(
            strategy=BackoffStrategy(resolved_settings.backoff_strategy),
            initial_delay=resolved_settings.backoff_initial_delay,
            multiplier=resolved_settings.backoff_multiplier,
            max_delay=resolved_settings.backoff_max_delay,
        ),
    )

    return Container(
        settings=resolved_settings,
        connection=connection,
        job_repository=job_repository,
        worker_repository=worker_repository,
        dlq_repository=dlq_repository,
        retry_policy=retry_policy,
        command_executor=SubprocessCommandExecutor(),
        clock=SystemClock(),
        enqueue_job=EnqueueJob(job_repository),
        process_job=ProcessJob(job_repository),
        complete_job=CompleteJob(job_repository),
        fail_job=FailJob(job_repository),
        retry_job=RetryJob(job_repository, retry_policy),
        move_to_dlq=MoveToDlq(job_repository, dlq_repository, retry_policy),
        replay_dlq_job=ReplayDlqJob(job_repository, dlq_repository),
        get_status=GetStatus(job_repository),
    )
