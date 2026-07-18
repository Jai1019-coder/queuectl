"""Single-worker execution loop.

A :class:`WorkerRuntime` repeatedly claims the next available job,
executes its command, and records the outcome (completed, retried,
or moved to the Dead Letter Queue). It is designed to run as the
entire body of one OS process, spawned by
:class:`queuectl.workers.worker_pool.WorkerPool`.
"""

from __future__ import annotations

import socket

from queuectl.application.use_cases.complete_job import CompleteJob
from queuectl.application.use_cases.fail_job import FailJob
from queuectl.application.use_cases.move_to_dlq import MoveToDlq
from queuectl.application.use_cases.process_job import ProcessJob
from queuectl.application.use_cases.retry_job import RetryJob
from queuectl.core.interfaces import Clock
from queuectl.domain.entities.worker import Worker as WorkerEntity
from queuectl.domain.policies.retry_policy import RetryPolicy
from queuectl.domain.value_objects.job_id import JobId
from queuectl.infrastructure.logging.logger import get_logger
from queuectl.infrastructure.process.command_executor import CommandExecutor
from queuectl.repositories.worker_repository import WorkerRepository
from queuectl.workers.heartbeat import HeartbeatRecorder
from queuectl.workers.shutdown import ShutdownSignal

_logger = get_logger("workers.worker")


class WorkerRuntime:
    """Runs the claim -> execute -> record lifecycle for one worker.

    The loop checks ``shutdown_signal`` only between jobs, so a job
    already in progress always runs to completion before the worker
    exits -- satisfying QueueCTL's graceful shutdown requirement.
    """

    def __init__(
        self,
        *,
        worker_id: str,
        process_job: ProcessJob,
        complete_job: CompleteJob,
        fail_job: FailJob,
        retry_job: RetryJob,
        move_to_dlq: MoveToDlq,
        worker_repository: WorkerRepository,
        command_executor: CommandExecutor,
        retry_policy: RetryPolicy,
        clock: Clock,
        shutdown_signal: ShutdownSignal,
        poll_interval_seconds: float = 0.5,
        job_timeout_seconds: float | None = None,
        stop_when_idle: bool = False,
    ) -> None:
        """Initialize the worker runtime.

        Args:
            worker_id: Unique identifier for this worker process.
            process_job: Use case for atomically claiming a job.
            complete_job: Use case for marking a job completed.
            fail_job: Use case for marking a job failed.
            retry_job: Use case for scheduling a retry.
            move_to_dlq: Use case for moving an exhausted job to the
                DLQ.
            worker_repository: Repository for persisting worker
                state.
            command_executor: Executes a job's shell command.
            retry_policy: Determines whether a failed job may retry.
            clock: Source of the current time.
            shutdown_signal: Checked between jobs to know when to
                stop.
            poll_interval_seconds: How long to sleep when no job is
                available.
            job_timeout_seconds: Maximum time a single job's command
                may run. ``None`` disables the timeout.
            stop_when_idle: If True, exit as soon as no job is
                available instead of polling indefinitely. Used for
                "drain the current queue and exit" batch runs.
        """
        self._worker_id = worker_id
        self._process_job = process_job
        self._complete_job = complete_job
        self._fail_job = fail_job
        self._retry_job = retry_job
        self._move_to_dlq = move_to_dlq
        self._worker_repository = worker_repository
        self._command_executor = command_executor
        self._retry_policy = retry_policy
        self._clock = clock
        self._shutdown_signal = shutdown_signal
        self._poll_interval_seconds = poll_interval_seconds
        self._job_timeout_seconds = job_timeout_seconds
        self._stop_when_idle = stop_when_idle
        self._heartbeat = HeartbeatRecorder(worker_repository, clock)

    def run(self) -> None:
        """Run the worker loop until shutdown is requested.

        Registers the worker, repeatedly claims and executes jobs,
        and deregisters (marks offline) the worker before returning.
        """
        worker_entity = WorkerEntity.register(
            worker_id=self._worker_id,
            hostname=socket.gethostname(),
            now=self._clock.now(),
        )
        self._worker_repository.save(worker_entity)
        _logger.info("worker %s starting", self._worker_id)

        try:
            while not self._shutdown_signal.is_set():
                job = self._process_job.execute(worker_id=self._worker_id)

                if job is None:
                    if self._stop_when_idle:
                        break
                    self._heartbeat.beat(worker_entity)
                    self._shutdown_signal.wait(self._poll_interval_seconds)
                    continue

                self._execute_claimed_job(
                    worker_entity, job.id, job.name, job.retry_count
                )
        finally:
            worker_entity.set_offline()
            self._worker_repository.update(worker_entity)
            _logger.info("worker %s stopped", self._worker_id)

    def _execute_claimed_job(
        self,
        worker_entity: WorkerEntity,
        job_id: JobId,
        command: str,
        retry_count: int,
    ) -> None:
        """Execute one claimed job and record its outcome.

        Args:
            worker_entity: This worker's domain entity, mutated in
                place to reflect the assignment/completion.
            job_id: Identifier of the claimed job.
            command: The shell command to execute.
            retry_count: The job's retry count at claim time, used to
                decide between scheduling a retry and moving to the
                DLQ.
        """
        worker_entity.assign_job(job_id)
        self._worker_repository.update(worker_entity)
        _logger.info("worker %s executing job %s", self._worker_id, job_id)

        result = self._command_executor.run(
            command,
            timeout_seconds=self._job_timeout_seconds,
        )

        if result.succeeded:
            self._complete_job.execute(job_id=job_id)
            _logger.info("job %s completed", job_id)
        else:
            error_message = (
                result.stderr.strip()
                or result.stdout.strip()
                or f"Command exited with code {result.exit_code}."
            )
            if result.timed_out:
                error_message = f"Command timed out: {error_message}"

            self._fail_job.execute(job_id=job_id, error_message=error_message)

            if self._retry_policy.should_retry(retry_count):
                self._retry_job.execute(job_id=job_id)
                _logger.warning("job %s failed, retry scheduled", job_id)
            else:
                self._move_to_dlq.execute(
                    job_id=job_id,
                    reason="Retry attempts exhausted.",
                )
                _logger.error("job %s moved to DLQ", job_id)

        if result.succeeded:
            worker_entity.complete_job()
        else:
            worker_entity.fail_job()
        self._worker_repository.update(worker_entity)
