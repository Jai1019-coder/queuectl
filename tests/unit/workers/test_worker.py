"""Unit tests for WorkerRuntime."""

from __future__ import annotations

import threading
import time

from queuectl.application.use_cases.complete_job import CompleteJob
from queuectl.application.use_cases.enqueue_job import EnqueueJob
from queuectl.application.use_cases.fail_job import FailJob
from queuectl.application.use_cases.move_to_dlq import MoveToDlq
from queuectl.application.use_cases.process_job import ProcessJob
from queuectl.application.use_cases.retry_job import RetryJob
from queuectl.core.interfaces import SystemClock
from queuectl.domain.policies.retry_policy import RetryPolicy
from queuectl.domain.value_objects.backoff_policy import BackoffPolicy
from queuectl.domain.value_objects.job_state import JobState
from queuectl.workers.shutdown import ShutdownSignal
from queuectl.workers.worker import WorkerRuntime
from tests.fakes.fake_command_executor import FakeCommandExecutor
from tests.fakes.fake_dlq_repository import FakeDlqRepository
from tests.fakes.fake_job_repository import FakeJobRepository
from tests.fakes.fake_worker_repository import FakeWorkerRepository


def _build_runtime(
    *,
    job_repository: FakeJobRepository,
    worker_repository: FakeWorkerRepository,
    dlq_repository: FakeDlqRepository,
    command_executor: FakeCommandExecutor,
    retry_policy: RetryPolicy,
    shutdown_signal: ShutdownSignal,
    poll_interval_seconds: float = 0.01,
) -> WorkerRuntime:
    """Assemble a WorkerRuntime wired to the given fakes."""
    return WorkerRuntime(
        worker_id="worker-under-test",
        process_job=ProcessJob(job_repository),
        complete_job=CompleteJob(job_repository),
        fail_job=FailJob(job_repository),
        retry_job=RetryJob(job_repository, retry_policy),
        move_to_dlq=MoveToDlq(job_repository, dlq_repository, retry_policy),
        worker_repository=worker_repository,
        command_executor=command_executor,
        retry_policy=retry_policy,
        clock=SystemClock(),
        shutdown_signal=shutdown_signal,
        poll_interval_seconds=poll_interval_seconds,
    )


def _run_until_idle(runtime: WorkerRuntime, shutdown_signal: ShutdownSignal) -> None:
    """Run the runtime in a background thread until jobs are drained.

    Args:
        runtime: The runtime to run.
        shutdown_signal: Set once by the test to stop the loop.
    """
    thread = threading.Thread(target=runtime.run)
    thread.start()
    thread.join(timeout=5)
    if thread.is_alive():
        shutdown_signal.request()
        thread.join(timeout=5)


class TestSuccessfulJob:
    """A job whose command succeeds should be marked COMPLETED."""

    def test_successful_job_is_completed(self) -> None:
        job_repository = FakeJobRepository()
        worker_repository = FakeWorkerRepository()
        dlq_repository = FakeDlqRepository()
        executor = FakeCommandExecutor()
        retry_policy = RetryPolicy(max_retries=3, backoff=BackoffPolicy())
        shutdown_signal = ShutdownSignal()

        enqueue = EnqueueJob(job_repository)
        job = enqueue.execute(name="echo hello")

        runtime = _build_runtime(
            job_repository=job_repository,
            worker_repository=worker_repository,
            dlq_repository=dlq_repository,
            command_executor=executor,
            retry_policy=retry_policy,
            shutdown_signal=shutdown_signal,
        )

        def stop_when_done() -> None:
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if job_repository.get(job.id).state is JobState.COMPLETED:
                    break
                time.sleep(0.01)
            shutdown_signal.request()

        threading.Thread(target=stop_when_done).start()
        _run_until_idle(runtime, shutdown_signal)

        assert job_repository.get(job.id).state is JobState.COMPLETED
        assert executor.calls == ["echo hello"]

    def test_worker_records_completion_in_repository(self) -> None:
        job_repository = FakeJobRepository()
        worker_repository = FakeWorkerRepository()
        dlq_repository = FakeDlqRepository()
        executor = FakeCommandExecutor()
        retry_policy = RetryPolicy(max_retries=3, backoff=BackoffPolicy())
        shutdown_signal = ShutdownSignal()

        EnqueueJob(job_repository).execute(name="echo hi")

        runtime = _build_runtime(
            job_repository=job_repository,
            worker_repository=worker_repository,
            dlq_repository=dlq_repository,
            command_executor=executor,
            retry_policy=retry_policy,
            shutdown_signal=shutdown_signal,
        )

        def stop_soon() -> None:
            time.sleep(0.3)
            shutdown_signal.request()

        threading.Thread(target=stop_soon).start()
        _run_until_idle(runtime, shutdown_signal)

        worker = worker_repository.get("worker-under-test")
        assert worker is not None
        assert worker.jobs_processed == 1
        assert worker.status.value == "offline"


class TestFailedJobRetried:
    """A failing job with retries remaining should be rescheduled."""

    def test_failed_job_is_rescheduled_pending(self) -> None:
        job_repository = FakeJobRepository()
        worker_repository = FakeWorkerRepository()
        dlq_repository = FakeDlqRepository()
        executor = FakeCommandExecutor()
        executor.fail_on("exit 1", "boom")
        retry_policy = RetryPolicy(max_retries=3, backoff=BackoffPolicy())
        shutdown_signal = ShutdownSignal()

        job = EnqueueJob(job_repository).execute(name="exit 1")

        runtime = _build_runtime(
            job_repository=job_repository,
            worker_repository=worker_repository,
            dlq_repository=dlq_repository,
            command_executor=executor,
            retry_policy=retry_policy,
            shutdown_signal=shutdown_signal,
        )

        def stop_soon() -> None:
            time.sleep(0.3)
            shutdown_signal.request()

        threading.Thread(target=stop_soon).start()
        _run_until_idle(runtime, shutdown_signal)

        updated = job_repository.get(job.id)
        assert updated.state is JobState.PENDING
        assert updated.retry_count == 1
        assert dlq_repository.count() == 0


class TestExhaustedJobMovesToDlq:
    """A job that exhausts all retries should be moved to the DLQ."""

    def test_job_moved_to_dlq_after_max_retries(self) -> None:
        job_repository = FakeJobRepository()
        worker_repository = FakeWorkerRepository()
        dlq_repository = FakeDlqRepository()
        executor = FakeCommandExecutor()
        executor.fail_on("exit 1", "boom")
        retry_policy = RetryPolicy(max_retries=0, backoff=BackoffPolicy())
        shutdown_signal = ShutdownSignal()

        job = EnqueueJob(job_repository).execute(name="exit 1")

        runtime = _build_runtime(
            job_repository=job_repository,
            worker_repository=worker_repository,
            dlq_repository=dlq_repository,
            command_executor=executor,
            retry_policy=retry_policy,
            shutdown_signal=shutdown_signal,
        )

        def stop_soon() -> None:
            time.sleep(0.3)
            shutdown_signal.request()

        threading.Thread(target=stop_soon).start()
        _run_until_idle(runtime, shutdown_signal)

        updated = job_repository.get(job.id)
        assert updated.state is JobState.DEAD
        assert dlq_repository.count() == 1
        assert dlq_repository.get(job.id) is not None


class TestGracefulShutdown:
    """The worker should never claim new work once shutdown fires."""

    def test_no_new_job_claimed_after_shutdown_requested(self) -> None:
        job_repository = FakeJobRepository()
        worker_repository = FakeWorkerRepository()
        dlq_repository = FakeDlqRepository()
        executor = FakeCommandExecutor()
        retry_policy = RetryPolicy(max_retries=3, backoff=BackoffPolicy())
        shutdown_signal = ShutdownSignal()
        shutdown_signal.request()

        EnqueueJob(job_repository).execute(name="echo should-not-run")

        runtime = _build_runtime(
            job_repository=job_repository,
            worker_repository=worker_repository,
            dlq_repository=dlq_repository,
            command_executor=executor,
            retry_policy=retry_policy,
            shutdown_signal=shutdown_signal,
        )

        runtime.run()

        assert executor.calls == []
        assert job_repository.count(state=JobState.PENDING) == 1

    def test_worker_marked_offline_after_run_returns(self) -> None:
        job_repository = FakeJobRepository()
        worker_repository = FakeWorkerRepository()
        dlq_repository = FakeDlqRepository()
        executor = FakeCommandExecutor()
        retry_policy = RetryPolicy(max_retries=3, backoff=BackoffPolicy())
        shutdown_signal = ShutdownSignal()
        shutdown_signal.request()

        runtime = _build_runtime(
            job_repository=job_repository,
            worker_repository=worker_repository,
            dlq_repository=dlq_repository,
            command_executor=executor,
            retry_policy=retry_policy,
            shutdown_signal=shutdown_signal,
        )

        runtime.run()

        worker = worker_repository.get("worker-under-test")
        assert worker is not None
        assert worker.status.value == "offline"
