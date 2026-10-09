"""Path classification and success metrics (SPEC §11; simulation-conventions §7)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import numpy as np
from numpy.typing import NDArray

from sbretire.simulation import PathOutcomes


class PathClass(IntEnum):
    SUCCESSFUL = 0
    FAILED = 1
    UNRESOLVED = 2


def classify_paths(outcomes: PathOutcomes) -> NDArray[np.int8]:
    raise NotImplementedError


@dataclass(frozen=True)
class SuccessMetrics:
    n_paths: int
    n_successful: int
    n_failed: int
    n_unresolved: int
    n_completed: int
    conservative_success_rate: float
    conservative_standard_error: float
    completed_success_rate: float | None
    completed_standard_error: float | None
    unresolved_share: float

    @classmethod
    def from_outcomes(cls, outcomes: PathOutcomes) -> SuccessMetrics:
        raise NotImplementedError
