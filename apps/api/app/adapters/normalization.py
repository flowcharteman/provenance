"""Normalization boundary between source observations and canonical facts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable
from uuid import UUID

from app.adapters.types import NormalizedFactCandidate, PersistedSourceObservation


@runtime_checkable
class ObservationNormalizer(Protocol):
    @property
    def version(self) -> str: ...

    async def normalize(
        self,
        observations: Sequence[PersistedSourceObservation],
        *,
        company_id: UUID,
    ) -> Sequence[NormalizedFactCandidate]: ...
