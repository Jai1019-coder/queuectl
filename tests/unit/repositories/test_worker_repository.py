"""
Unit tests for WorkerRepository interface.
"""

from __future__ import annotations

from abc import ABC

import pytest

from queuectl.repositories.worker_repository import WorkerRepository


def test_worker_repository_is_abstract():
    assert issubclass(WorkerRepository, ABC)


def test_worker_repository_cannot_be_instantiated():
    with pytest.raises(TypeError):
        WorkerRepository()


class IncompleteWorkerRepository(WorkerRepository):
    pass


def test_incomplete_repository_cannot_be_instantiated():
    with pytest.raises(TypeError):
        IncompleteWorkerRepository()


class DummyWorkerRepository(WorkerRepository):

    def save(self, worker):
        pass

    def get(self, worker_id):
        return None

    def update(self, worker):
        pass

    def delete(self, worker_id):
        pass

    def exists(self, worker_id):
        return False

    def list(self, *, status=None, limit=None, offset=0):
        return []

    def list_available(self):
        return []

    def count(self, *, status=None):
        return 0

    def clear(self):
        pass


def test_complete_repository_can_be_instantiated():
    repo = DummyWorkerRepository()
    assert isinstance(repo, WorkerRepository)