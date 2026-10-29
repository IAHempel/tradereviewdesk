"""Synthetic market tape for paper desk sessions.

The feed is a regime-switching random walk (trend up, trend down, chop) with
intraday volatility seasonality and rare jump shocks. It is deterministic for a
given seed and symbol so a desk run can be replayed exactly. It deliberately
encodes no edge for any setup: whatever the agents earn or lose comes from how
their rules interact with ordinary noise, which is the point of a rehearsal.
"""

import hashlib
import math
import random
from dataclasses import dataclass

BARS_PER_SESSION = 78
BAR_MINUTES = 5
SESSION_OPEN_MINUTES = 9 * 60 + 30

_REGIME_PERSISTENCE = 0.97
_TREND_DRIFT_SIGMAS = 0.2
_CHOP_PULL = 0.08
_JUMP_PROBABILITY = 0.004
_JUMP_SIGMAS = 3.5


@dataclass(frozen=True)
class Bar:
    index: int
    open: float
    high: float
    low: float
    close: float
    volume: float


def bar_clock(index: int) -> str:
    """Wall-clock label for the close of a bar, e.g. bar 0 closes at 09:35."""
    minutes = SESSION_OPEN_MINUTES + (index + 1) * BAR_MINUTES
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _stable_int(*parts: object) -> int:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _intraday_vol_multiplier(index: int) -> float:
    return 1.0 + 0.8 * math.exp(-index / 6) + 0.4 * math.exp(-(BARS_PER_SESSION - 1 - index) / 8)


class SimulatedMarketFeed:
    """Generates `sessions + 1` sessions per symbol; session 0 is warmup history."""

    data_source = "synthetic"

    def __init__(self, symbols: list[str], seed: int, sessions: int) -> None:
        self.symbols = list(symbols)
        self.seed = seed
        self.sessions = sessions
        self._tape = {symbol: self._generate(symbol) for symbol in self.symbols}

    def session_bars(self, symbol: str, session: int) -> list[Bar]:
        return self._tape[symbol][session]

    def _generate(self, symbol: str) -> list[list[Bar]]:
        profile = _stable_int("profile", symbol)
        rng = random.Random(_stable_int(self.seed, symbol))

        price = 20.0 + (profile % 48000) / 100.0
        daily_vol = 0.015 + ((profile >> 16) % 25) / 1000.0
        bar_sigma = daily_vol / math.sqrt(BARS_PER_SESSION)
        base_volume = 40_000.0 * (1 + (profile >> 24) % 10)

        regime = rng.choice(("up", "down", "chop"))
        anchor = price
        sessions: list[list[Bar]] = []

        for session in range(self.sessions + 1):
            if session > 0:
                price *= math.exp(rng.gauss(0.0, daily_vol * 0.4))

            bars: list[Bar] = []
            for index in range(BARS_PER_SESSION):
                if rng.random() > _REGIME_PERSISTENCE:
                    regime = rng.choice([state for state in ("up", "down", "chop") if state != regime])
                    anchor = price

                multiplier = _intraday_vol_multiplier(index)
                sigma = bar_sigma * multiplier
                if regime == "up":
                    drift = _TREND_DRIFT_SIGMAS * bar_sigma
                elif regime == "down":
                    drift = -_TREND_DRIFT_SIGMAS * bar_sigma
                else:
                    drift = -_CHOP_PULL * math.log(price / anchor)

                log_return = drift + rng.gauss(0.0, sigma)
                if rng.random() < _JUMP_PROBABILITY:
                    log_return += rng.choice((-1, 1)) * _JUMP_SIGMAS * sigma

                open_price = price
                close_price = open_price * math.exp(log_return)
                high = max(open_price, close_price) * math.exp(abs(rng.gauss(0.0, 0.6 * sigma)))
                low = min(open_price, close_price) * math.exp(-abs(rng.gauss(0.0, 0.6 * sigma)))
                volume = (
                    base_volume
                    * multiplier**1.2
                    * math.exp(rng.gauss(0.0, 0.35))
                    * (1.0 + 2.0 * abs(log_return) / sigma)
                )

                bars.append(
                    Bar(
                        index=index,
                        open=round(open_price, 2),
                        high=round(high, 2),
                        low=round(low, 2),
                        close=round(close_price, 2),
                        volume=round(volume),
                    )
                )
                price = close_price

            sessions.append(bars)

        return sessions
