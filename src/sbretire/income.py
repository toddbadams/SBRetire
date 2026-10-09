"""Household income from the Scenario's Income Streams (SPEC §8; configuration §3–§5).

:class:`ScenarioIncome` supplies the engine's ``income(month, alive)``: for every path, the nominal GBP
received in ``month``. Per active stream, the monthly amount is ``annual_amount_today / 12``, times the
Inflation Index I_t when the stream is inflation-linked, times a survivor factor that depends on who is alive:

- person stream: 1 while the Recipient lives; ``survivor_percentage`` once the Recipient has died and the
  other person lives (also when the Recipient died before ``start_date``); 0 once both have died;
- Household Stream: 1 while both live; ``survivor_percentage`` while exactly one lives; 0 after.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sbretire.config import HOUSEHOLD, Scenario
from sbretire.inflation import PriceIndex
from sbretire.portfolio import BoolArray, FloatArray
from sbretire.timeline import month_index


@dataclass(frozen=True)
class _ActiveRule:
    start: int  # first paying month index
    end: int | None  # first month no longer paying (exclusive); None = no end
    monthly_today: float  # annual_amount_today / 12, today's GBP
    linked: bool
    survivor_percentage: float
    recipient: int | None  # row in ``alive``; None for a Household Stream

    def pays_in(self, month: int) -> bool:
        return self.start <= month and (self.end is None or month < self.end)


class ScenarioIncome:
    """Monthly household income for every path, built from a validated Scenario."""

    def __init__(self, scenario: Scenario, price_index: PriceIndex) -> None:
        as_of = scenario.model.as_of_date
        person_rows = {person.id: row for row, person in enumerate(scenario.people)}
        self._streams = tuple(
            _ActiveRule(
                start=month_index(as_of, stream.start_date),
                end=None if stream.end_date is None else month_index(as_of, stream.end_date),
                monthly_today=stream.annual_amount_today / 12.0,
                linked=stream.inflation_linked,
                survivor_percentage=stream.survivor_percentage,
                recipient=None if stream.recipient == HOUSEHOLD else person_rows[stream.recipient],
            )
            for stream in scenario.income
        )
        self._price_index = price_index

    def income(self, month: int, alive: BoolArray) -> FloatArray:
        """Nominal GBP income in ``month`` per path; ``alive`` is (2, n_paths) at the month's start."""
        n_paths = alive.shape[1]
        total = np.zeros(n_paths, dtype=np.float64)
        paying = [stream for stream in self._streams if stream.pays_in(month)]
        if not paying:
            return total
        level = self._price_index.level(month)
        if level.shape != (n_paths,):
            raise ValueError(f"price index covers {level.shape} paths but alive covers {n_paths} paths")
        n_alive = alive.sum(axis=0)
        for stream in paying:
            if stream.recipient is None:
                factor = np.where(n_alive == 2, 1.0, np.where(n_alive == 1, stream.survivor_percentage, 0.0))
            else:
                own, other = alive[stream.recipient], alive[1 - stream.recipient]
                factor = np.where(own, 1.0, np.where(other, stream.survivor_percentage, 0.0))
            amount = stream.monthly_today * level if stream.linked else stream.monthly_today
            total += amount * factor
        return total
