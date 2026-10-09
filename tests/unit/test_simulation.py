"""F-002.2 — path loop: deaths, Depletion, Household End, censoring, observer (simulation-conventions §2)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pytest
from cash_flow_doubles import PerPersonCashFlows, constant

from sbretire.portfolio import BoolArray, FloatArray
from sbretire.simulation import PathOutcomes, simulate_paths

FAR = 10_000  # a Death Month beyond any horizon used here


def deaths(*pairs: tuple[int, int]) -> np.ndarray:
    """death_month array (2, n_paths) from (person_1, person_2) pairs."""
    return np.array(pairs, dtype=np.int64).T.copy()


@dataclass
class Recorder:
    months: list[int] = field(default_factory=list)
    balances: list[FloatArray] = field(default_factory=list)
    alive: list[BoolArray] = field(default_factory=list)
    active: list[BoolArray] = field(default_factory=list)

    def __call__(self, month: int, balance: FloatArray, alive: BoolArray, active: BoolArray) -> None:
        self.months.append(month)
        self.balances.append(balance.copy())
        self.alive.append(alive.copy())
        self.active.append(active.copy())


def run(**kwargs: object) -> PathOutcomes:
    defaults: dict[str, object] = {"starting_balance": 1000.0, "annual_return": 0.0, "horizon_months": 24}
    return simulate_paths(**{**defaults, **kwargs})  # type: ignore[arg-type]


def test_simulate_paths_records_first_depletion_month() -> None:
    # Path 0: 1000 -> 700 -> 400 -> 100; month 3 has 100 < 300 -> depleted, shortfall 200.
    # Path 1 spends nothing.
    flows = PerPersonCashFlows(spending_both=np.array([300.0, 0.0]), income_per_person=np.zeros(2))
    out = run(death_month=deaths((FAR, FAR), (FAR, FAR)), cash_flows=flows)
    assert out.depletion_month.tolist() == [3, -1]
    assert out.shortfall.tolist() == pytest.approx([200.0, 0.0])
    assert out.final_balance.tolist() == pytest.approx([0.0, 1000.0])


def test_simulate_paths_no_compounding_after_depletion() -> None:
    # Strong return and a huge income from month 6 must not revive a path depleted in month 3.
    flows = constant(1, spending=300.0)
    flows.extra_income = lambda month: 1e6 if month >= 6 else 0.0
    recorder = Recorder()
    out = run(
        annual_return=0.5,
        starting_balance=800.0,
        death_month=deaths((FAR, FAR)),
        cash_flows=flows,
        observer=recorder,
    )
    depleted_at = int(out.depletion_month[0])
    assert 0 < depleted_at < 6
    after = [float(b[0]) for m, b in zip(recorder.months, recorder.balances, strict=True) if m >= depleted_at]
    assert after and all(b == 0.0 for b in after)
    assert out.final_balance.tolist() == [0.0]


@pytest.mark.parametrize(
    ("start", "annual", "income"), [(0.0, 0.0, 0.0), (0.0, -0.5, 0.0), (5e5, -0.9, 100.0)]
)
def test_simulate_paths_zero_spending_never_depletes(start: float, annual: float, income: float) -> None:
    out = run(
        starting_balance=start,
        annual_return=annual,
        death_month=deaths((FAR, FAR), (5, 9)),
        cash_flows=constant(2, spending=0.0, income=income),
    )
    assert out.depletion_month.tolist() == [-1, -1]
    assert (out.shortfall == 0).all()


def test_simulate_paths_no_capital_no_income_depletes_immediately() -> None:
    out = run(starting_balance=0.0, death_month=deaths((FAR, FAR)), cash_flows=constant(1, spending=10.0))
    assert out.depletion_month.tolist() == [0]
    assert out.shortfall.tolist() == pytest.approx([10.0])


def test_simulate_paths_deaths_take_effect_at_month_start() -> None:
    # Person 1 dies at month 3, person 2 at month 5. Spending 200 while both alive, 100 (factor 0.5) after.
    flows = PerPersonCashFlows(
        spending_both=np.array([200.0]), income_per_person=np.zeros(1), survivor_factor=0.5
    )
    recorder = Recorder()
    out = run(starting_balance=10_000.0, death_month=deaths((3, 5)), cash_flows=flows, observer=recorder)

    alive_by_month = {m: a[:, 0].tolist() for m, a in zip(recorder.months, recorder.alive, strict=True)}
    assert alive_by_month[2] == [True, True]  # alive for the whole month before the Death Month
    assert alive_by_month[3] == [False, True]  # dead from the start of the Death Month
    assert alive_by_month[4] == [False, True]
    assert 5 not in alive_by_month  # both dead at the start of month 5: path ends before its cash flows
    assert out.household_end_month.tolist() == [5]
    assert out.final_balance.tolist() == pytest.approx([10_000.0 - 3 * 200.0 - 2 * 100.0])
    assert out.depletion_month.tolist() == [-1]
    assert out.censored.tolist() == [False]


def test_simulate_paths_flags_censored_paths() -> None:
    out = run(
        horizon_months=12,
        death_month=deaths((3, 11), (12, 4), (FAR, FAR), (2, 2)),
        cash_flows=constant(4, spending=1.0),
    )
    # death_month >= horizon means alive at the horizon.
    assert out.censored.tolist() == [False, True, True, False]
    assert out.household_end_month.tolist() == [11, -1, -1, 2]


def test_simulate_paths_calls_observer_each_month() -> None:
    recorder = Recorder()
    out = run(
        horizon_months=6,
        death_month=deaths((FAR, FAR), (2, 2)),
        cash_flows=constant(2, spending=100.0),
        observer=recorder,
    )
    assert recorder.months == [0, 1, 2, 3, 4, 5]
    assert all(
        b.shape == (2,) and a.shape == (2, 2) and act.shape == (2,)
        for b, a, act in zip(recorder.balances, recorder.alive, recorder.active, strict=True)
    )
    assert [act.tolist() for act in recorder.active] == [[True, True]] * 2 + [[True, False]] * 4
    assert recorder.balances[0].tolist() == pytest.approx([900.0, 900.0])  # closing balance after month 0
    assert recorder.balances[-1].tolist() == pytest.approx([400.0, 800.0])  # path 1 frozen after month 1
    assert out.final_balance.tolist() == pytest.approx([400.0, 800.0])


def test_simulate_paths_stops_when_no_path_is_active() -> None:
    recorder = Recorder()
    run(
        horizon_months=120,
        death_month=deaths((2, 1)),
        cash_flows=constant(1, spending=1.0),
        observer=recorder,
    )
    assert recorder.months == [0, 1]


def test_simulate_paths_vectorised_matches_single_paths() -> None:
    rng = np.random.default_rng(20261009)  # pinned: fixture generation only
    n = 40
    death_month = rng.integers(0, 80, size=(2, n)).astype(np.int64)
    death_month[:, :5] = FAR  # some censored paths
    spending = rng.uniform(0, 400, size=n)
    income = rng.uniform(0, 150, size=n)

    def flows(idx: slice) -> PerPersonCashFlows:
        return PerPersonCashFlows(
            spending_both=spending[idx], income_per_person=income[idx], survivor_factor=0.7
        )

    together = run(
        starting_balance=5000.0,
        annual_return=0.03,
        horizon_months=72,
        death_month=death_month,
        cash_flows=flows(slice(None)),
    )
    for i in range(n):
        alone = run(
            starting_balance=5000.0,
            annual_return=0.03,
            horizon_months=72,
            death_month=death_month[:, i : i + 1],
            cash_flows=flows(slice(i, i + 1)),
        )
        for name in ("depletion_month", "shortfall", "household_end_month", "censored", "final_balance"):
            np.testing.assert_array_equal(
                getattr(together, name)[i : i + 1], getattr(alone, name), err_msg=f"{name}[{i}]"
            )
    assert (together.depletion_month >= 0).any() and (together.depletion_month == -1).any()


@pytest.mark.parametrize(
    ("death_month", "horizon", "fragment"),
    [
        (np.zeros((3, 2), dtype=np.int64), 12, "shape (2, n_paths)"),
        (np.zeros((2, 2), dtype=np.int64), 0, "horizon_months"),
        (np.full((2, 2), -1, dtype=np.int64), 12, "non-negative"),
    ],
)
def test_simulate_paths_rejects_invalid_inputs(death_month: np.ndarray, horizon: int, fragment: str) -> None:
    with pytest.raises(ValueError, match=fragment.replace("(", r"\(").replace(")", r"\)")):
        run(
            death_month=death_month,
            horizon_months=horizon,
            cash_flows=constant(death_month.shape[1], spending=1.0),
        )
