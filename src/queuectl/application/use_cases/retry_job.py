"""
Application use case for retrying a failed job.
"""

from __future__ import annotations

from queuectl.domain.entities.job import Job
from queuectl.domain.policies.retry_policy import RetryPolicy
from queuectl.domain.value_objects.job_id import JobId
from queuectl.repositories.job_repository import JobRepository


class RetryJob:
    """
    Retries a failed job if allowed by the retry policy.

    Responsibilities:
        - Retrieve the job.
        - Determine whether another retry is permitted.
        - Increment retry count.
        - Schedule the next retry.
        - Persist the updated job.

    This use case does NOT move jobs to the Dead Letter Queue.
    That responsibility belongs to MoveToDlq.
    """

    def __init__(
        self,
        repository: JobRepository,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._retry_policy = retry_policy or RetryPolicy()

    def execute(
        self,
        *,
        job_id: JobId,
    ) -> Job | None:
        """
        Retry a failed job if retries remain.

        Args:
            job_id:
                Identifier of the failed job.

        Returns:
            The updated job if a retry was scheduled.
            None if the retry limit has been reached.

        Raises:
            ValueError:
                If the job does not exist.

            Any exception raised by the Job entity is intentionally
            propagated.
        """

        job = self._repository.get(job_id)

        if job is None:
            raise ValueError(f"Job '{job_id}' does not exist.")

        if not self._retry_policy.should_retry(job.retry_count):
            return None

        delay = self._retry_policy.next_retry_delay(job.retry_count)

        job.increment_retry()
        job.schedule_retry(delay)

        self._repository.update(job)

        return job