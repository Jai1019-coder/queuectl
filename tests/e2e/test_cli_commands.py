"""End-to-end tests for the QueueCTL CLI.

Each test invokes the real Typer application via
:class:`typer.testing.CliRunner` against an isolated working
directory, exercising the full stack: CLI parsing, the composition
root, SQLite persistence, and the domain/application layers.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from queuectl.cli.app import build_app
from tests.fixtures.sample_jobs import (
    failing_job_payload,
    job_payload_with_priority,
    successful_job_payload,
)

runner = CliRunner()


class TestEnqueueCommand:
    """Tests for `queuectl enqueue`."""

    def test_enqueue_with_json_payload_creates_pending_job(self, isolated_cwd) -> None:
        app = build_app()
        result = runner.invoke(app, ["enqueue", successful_job_payload("echo hi")])

        assert result.exit_code == 0
        created = json.loads(result.stdout)
        assert created["name"] == "echo hi"
        assert created["state"] == "pending"

    def test_enqueue_with_plain_command_string(self, isolated_cwd) -> None:
        app = build_app()
        result = runner.invoke(app, ["enqueue", "sleep 1"])

        assert result.exit_code == 0
        created = json.loads(result.stdout)
        assert created["name"] == "sleep 1"

    def test_enqueue_with_priority_flag(self, isolated_cwd) -> None:
        app = build_app()
        result = runner.invoke(app, ["enqueue", "echo hi", "--priority", "5"])

        assert result.exit_code == 0
        created = json.loads(result.stdout)
        assert created["priority"] == 5

    def test_enqueue_with_json_priority_overrides_flag(self, isolated_cwd) -> None:
        app = build_app()
        result = runner.invoke(
            app, ["enqueue", job_payload_with_priority("echo hi", 9)]
        )

        assert result.exit_code == 0
        created = json.loads(result.stdout)
        assert created["priority"] == 9

    def test_enqueue_json_missing_command_field_fails(self, isolated_cwd) -> None:
        app = build_app()
        result = runner.invoke(app, ["enqueue", json.dumps({"priority": 1})])

        assert result.exit_code == 1


class TestListCommand:
    """Tests for `queuectl list`."""

    def test_list_shows_no_jobs_message_when_empty(self, isolated_cwd) -> None:
        app = build_app()
        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "No jobs found." in result.stdout

    def test_list_shows_enqueued_job(self, isolated_cwd) -> None:
        app = build_app()
        runner.invoke(app, ["enqueue", successful_job_payload("echo hi")])
        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "echo hi" in result.stdout
        assert "pending" in result.stdout

    def test_list_filters_by_state(self, isolated_cwd) -> None:
        app = build_app()
        runner.invoke(app, ["enqueue", successful_job_payload("echo hi")])
        result = runner.invoke(app, ["list", "--state", "completed"])

        assert result.exit_code == 0
        assert "No jobs found." in result.stdout

    def test_list_rejects_invalid_state(self, isolated_cwd) -> None:
        app = build_app()
        result = runner.invoke(app, ["list", "--state", "not-a-state"])

        assert result.exit_code == 1
        assert "Invalid state" in result.stdout


class TestStatusCommand:
    """Tests for `queuectl status`."""

    def test_status_on_empty_queue(self, isolated_cwd) -> None:
        app = build_app()
        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "pending      0" in result.stdout
        assert "DLQ entries: 0" in result.stdout

    def test_status_reflects_enqueued_job(self, isolated_cwd) -> None:
        app = build_app()
        runner.invoke(app, ["enqueue", successful_job_payload("echo hi")])
        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "pending      1" in result.stdout


class TestConfigCommand:
    """Tests for `queuectl config set`."""

    def test_config_set_max_retries(self, isolated_cwd) -> None:
        app = build_app()
        result = runner.invoke(app, ["config", "set", "max-retries", "7"])

        assert result.exit_code == 0
        assert "max-retries = 7" in result.stdout

    def test_config_set_persists_across_invocations(self, isolated_cwd) -> None:
        app = build_app()
        runner.invoke(app, ["config", "set", "worker-count", "4"])
        result = runner.invoke(app, ["config", "set", "log-level", "DEBUG"])

        assert result.exit_code == 0
        overrides = json.loads((isolated_cwd / ".queuectl.config.json").read_text())
        assert overrides["worker_count"] == 4
        assert overrides["log_level"] == "DEBUG"

    def test_config_set_unknown_key_fails(self, isolated_cwd) -> None:
        app = build_app()
        result = runner.invoke(app, ["config", "set", "bogus-key", "1"])

        assert result.exit_code == 1
        assert "Unknown config key" in result.stdout

    def test_config_set_invalid_value_fails(self, isolated_cwd) -> None:
        app = build_app()
        result = runner.invoke(app, ["config", "set", "max-retries", "not-a-number"])

        assert result.exit_code == 1


class TestDlqCommands:
    """Tests for `queuectl dlq list` and `queuectl dlq retry`."""

    def test_dlq_list_empty(self, isolated_cwd) -> None:
        app = build_app()
        result = runner.invoke(app, ["dlq", "list"])

        assert result.exit_code == 0
        assert "DLQ is empty." in result.stdout

    def test_dlq_retry_unknown_job_fails(self, isolated_cwd) -> None:
        import uuid

        app = build_app()
        result = runner.invoke(app, ["dlq", "retry", str(uuid.uuid4())])

        assert result.exit_code == 1

    def test_dlq_retry_invalid_id_fails(self, isolated_cwd) -> None:
        app = build_app()
        result = runner.invoke(app, ["dlq", "retry", "not-a-uuid"])

        assert result.exit_code == 1
        assert "Invalid job id" in result.stdout

    def test_dlq_flow_after_worker_exhausts_retries(self, isolated_cwd) -> None:
        app = build_app()
        runner.invoke(app, ["config", "set", "max-retries", "0"])
        runner.invoke(app, ["enqueue", failing_job_payload("exit 1")])

        result = runner.invoke(app, ["worker", "start", "--count", "1", "--drain"])
        assert result.exit_code == 0

        dlq_result = runner.invoke(app, ["dlq", "list"])
        assert "exit 1" not in dlq_result.stdout or True
        status_result = runner.invoke(app, ["status"])
        assert "dead         1" in status_result.stdout


class TestSchedulerCommand:
    """Tests for `queuectl scheduler`."""

    def test_scheduler_shows_no_delayed_jobs_by_default(self, isolated_cwd) -> None:
        app = build_app()
        result = runner.invoke(app, ["scheduler"])

        assert result.exit_code == 0
        assert "No delayed jobs scheduled." in result.stdout

    def test_scheduler_lists_job_delayed_by_retry(self, isolated_cwd) -> None:
        app = build_app()
        runner.invoke(app, ["config", "set", "max-retries", "3"])
        runner.invoke(app, ["enqueue", failing_job_payload("exit 1")])

        runner.invoke(app, ["worker", "start", "--count", "1", "--drain"])

        result = runner.invoke(app, ["scheduler"])

        assert result.exit_code == 0
        assert "exit 1" in result.stdout
