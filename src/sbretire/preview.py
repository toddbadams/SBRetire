"""Deterministic preview run (F-015)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from sbretire.config import Scenario


def death_months_from_ages(scenario: Scenario, ages: tuple[int, int]) -> NDArray[np.int64]:
    raise NotImplementedError
