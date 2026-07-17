import pytest

from queuectl.domain.value_objects.worker_status import WorkerStatus


def test_enum_values():
    assert WorkerStatus.ONLINE.value == "online"
    assert WorkerStatus.BUSY.value == "busy"
    assert WorkerStatus.OFFLINE.value == "offline"


def test_online_properties():
    status = WorkerStatus.ONLINE

    assert status.is_online
    assert status.is_available
    assert not status.is_busy
    assert not status.is_offline


def test_busy_properties():
    status = WorkerStatus.BUSY

    assert status.is_online
    assert not status.is_available
    assert status.is_busy
    assert not status.is_offline


def test_offline_properties():
    status = WorkerStatus.OFFLINE

    assert not status.is_online
    assert not status.is_available
    assert not status.is_busy
    assert status.is_offline


def test_string_conversion():
    assert str(WorkerStatus.ONLINE) == "online"
    assert str(WorkerStatus.BUSY) == "busy"
    assert str(WorkerStatus.OFFLINE) == "offline"


def test_unique_enum_values():
    values = {status.value for status in WorkerStatus}
    assert len(values) == len(WorkerStatus)


@pytest.mark.parametrize(
    "status,expected",
    [
        (WorkerStatus.ONLINE, True),
        (WorkerStatus.BUSY, False),
        (WorkerStatus.OFFLINE, False),
    ],
)
def test_is_available(status, expected):
    assert status.is_available is expected


@pytest.mark.parametrize(
    "status,expected",
    [
        (WorkerStatus.ONLINE, True),
        (WorkerStatus.BUSY, True),
        (WorkerStatus.OFFLINE, False),
    ],
)
def test_is_online(status, expected):
    assert status.is_online is expected