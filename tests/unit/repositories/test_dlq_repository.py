"""
Unit tests for DlqRepository interface.
"""

from __future__ import annotations

from abc import ABC

import pytest

from queuectl.repositories.dlq_repository import DlqRepository


def test_dlq_repository_is_abstract():
    assert issubclass(DlqRepository, ABC)


def test_dlq_repository_cannot_be_instantiated():
    with pytest.raises(TypeError):
        DlqRepository()


class IncompleteDlqRepository(DlqRepository):
    pass


def test_incomplete_repository_cannot_be_instantiated():
    with pytest.raises(TypeError):
        IncompleteDlqRepository()


class DummyDlqRepository(DlqRepository):

    def save(self, entry):
        pass

    def get(self, job_id):
        return None

    def delete(self, job_id):
        pass

    def exists(self, job_id):
        return False

    def list(self, *, limit=None, offset=0):
        return []

    def count(self):
        return 0

    def clear(self):
        pass


def test_complete_repository_can_be_instantiated():
    repo = DummyDlqRepository()
    assert isinstance(repo, DlqRepository)