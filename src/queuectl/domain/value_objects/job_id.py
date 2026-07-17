"""
Job ID value object.

Represents the unique identifier of a Job within QueueCTL.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class JobId:
    """
    Immutable value object representing a Job identifier.

    Internally wraps a UUID to provide:
    - Type safety
    - Value equality
    - Easy serialization
    """

    value: UUID

    @classmethod
    def generate(cls) -> "JobId":
        """
        Generate a new unique JobId.

        Returns:
            JobId: Newly generated identifier.
        """
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> "JobId":
        """
        Create a JobId from a UUID string.

        Args:
            value: UUID string.

        Raises:
            ValueError:
                If the supplied string is not a valid UUID.
        """
        return cls(UUID(value))

    @property
    def hex(self) -> str:
        """
        Return UUID without hyphens.
        """
        return self.value.hex

    def __str__(self) -> str:
        """
        Return canonical UUID string.
        """
        return str(self.value)

    def __repr__(self) -> str:
        """
        Developer-friendly representation.
        """
        return f"JobId('{self.value}')"