from queuectl.domain.value_objects.job_id import JobId
from queuectl.domain.value_objects.job_state import JobState

job = {
    "id": JobId.generate(),
    "state": JobState.PENDING,
}

print(job)