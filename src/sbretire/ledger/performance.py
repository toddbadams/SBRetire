"""Performance and drawdown of today's portfolio mix over past prices (F-027)."""

from __future__ import annotations


def monthly_rate(annual: float) -> float:
    raise NotImplementedError


def metrics(*args: object) -> object:
    raise NotImplementedError


def rolling(*args: object) -> object:
    raise NotImplementedError
