from uuid import UUID

import pytest

from queuectl.domain.value_objects.job_id import JobId


def test_generate_returns_job_id():
    job_id = JobId.generate()

    assert isinstance(job_id, JobId)
    assert isinstance(job_id.value, UUID)


def test_generated_job_ids_are_unique():
    first = JobId.generate()
    second = JobId.generate()

    assert first != second


def test_from_string():
    original = JobId.generate()

    recreated = JobId.from_string(str(original))

    assert recreated == original


def test_invalid_uuid_string():
    with pytest.raises(ValueError):
        JobId.from_string("invalid-uuid")


def test_hex_property():
    job_id = JobId.generate()

    assert job_id.hex == job_id.value.hex


def test_string_conversion():
    job_id = JobId.generate()

    assert str(job_id) == str(job_id.value)


def test_repr():
    job_id = JobId.generate()

    assert "JobId" in repr(job_id)
    assert str(job_id.value) in repr(job_id)


def test_value_equality():
    first = JobId.generate()

    second = JobId.from_string(str(first))

    assert first == second


def test_hashability():
    job_id = JobId.generate()

    mapping = {job_id: "queue"}

    assert mapping[job_id] == "queue"