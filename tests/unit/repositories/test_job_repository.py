"""
Unit tests for JobRepository interface.
"""

from __future__ import annotations

from abc import ABC

import pytest

from queuectl.repositories.job_repository import JobRepository


def test_job_repository_is_abstract():
    """JobRepository should be an abstract base class."""
    assert issubclass(JobRepository, ABC)


def test_job_repository_cannot_be_instantiated():
    """Cannot instantiate abstract repository."""
    with pytest.raises(TypeError):
        JobRepository()


class IncompleteJobRepository(JobRepository):
    """Implements nothing."""

    pass


def test_incomplete_repository_cannot_be_instantiated():
    """Subclass must implement every abstract method."""
    with pytest.raises(TypeError):
        IncompleteJobRepository()


class DummyJobRepository(JobRepository):
    """Minimal concrete implementation for contract testing."""

    def save(self, job):
        pass

    def get(self, job_id):
        return None

    def update(self, job):
        pass

    def delete(self, job_id):
        pass

    def exists(self, job_id):
        return False

    def list(self, *, state=None, limit=None, offset=0):
        return []

    def next_available(self):
        return None

    def claim_next(self, worker_id, *, now=None):
        return None

    def count(self, *, state=None):
        return 0

    def clear(self):
        pass


def test_complete_repository_can_be_instantiated():
    """Concrete implementation should instantiate successfully."""
    repo = DummyJobRepository()
    assert isinstance(repo, JobRepository)
