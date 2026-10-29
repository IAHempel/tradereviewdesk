"""Performance math for desk runs: summary statistics and a bootstrap Monte Carlo fan."""

import random

from app.schemas.desk import DeskMonteCarlo, DeskMonteCarloBand, DeskSummary, DeskTrade

MONTE_CARLO_PATHS = 500
MONTE_CARLO_TRADES = 100
MONTE_CARLO_MIN_SAMPLE = 5
_BAND_POINTS = 25


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _round(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


def max_drawdown_pct(equity_curve: list[float], starting_balance: float) -> float:
    peak = starting_balance
    worst = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        worst = max(worst, (peak - equity) / peak)
    return round(worst * 100, 2)


def build_summary(
    *,
    starting_balance: float,
    ending_balance: float,
    trades: list[DeskTrade],
    equity_curve: list[float],
    fees_paid: float,
    sessions: int,
    halted_sessions: int,
) -> DeskSummary:
    wins = [trade for trade in trades if trade.pnl > 0]
    losses = [trade for trade in trades if trade.pnl <= 0]
    gross_win = sum(trade.pnl for trade in wins)
    gross_loss = -sum(trade.pnl for trade in losses)

    return DeskSummary(
        starting_balance=round(starting_balance, 2),
        ending_balance=round(ending_balance, 2),
        net_pnl=round(ending_balance - starting_balance, 2),
        return_pct=round((ending_balance / starting_balance - 1) * 100, 2),
        multiple=round(ending_balance / starting_balance, 4),
        trades=len(trades),
        wins=len(wins),
        losses=len(losses),
        win_rate=_round(len(wins) / len(trades), 3) if trades else None,
        avg_win_r=_round(_mean([trade.r_multiple for trade in wins])),
        avg_loss_r=_round(_mean([trade.r_multiple for trade in losses])),
        expectancy_r=_round(_mean([trade.r_multiple for trade in trades])),
        profit_factor=_round(gross_win / gross_loss) if gross_loss > 0 else None,
        max_drawdown_pct=max_drawdown_pct(equity_curve, starting_balance),
        best_trade=max((trade.pnl for trade in trades), default=None),
        worst_trade=min((trade.pnl for trade in trades), default=None),
        fees_paid=round(fees_paid, 2),
        sessions=sessions,
        halted_sessions=halted_sessions,
    )


def _percentile(sorted_values: list[float], fraction: float) -> float:
    position = fraction * (len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def run_monte_carlo(trade_returns: list[float], *, seed: int) -> DeskMonteCarlo | None:
    """Resamples this run's per-trade equity returns to show the spread of the next 100 trades.

    Returned values are equity multiples of the starting balance. With a small
    sample the fan is wide, which is the honest answer: a handful of paper
    trades says very little about an edge.
    """
    if len(trade_returns) < MONTE_CARLO_MIN_SAMPLE:
        return None

    rng = random.Random(seed)
    checkpoints = sorted({round(i * MONTE_CARLO_TRADES / _BAND_POINTS) for i in range(_BAND_POINTS + 1)})
    snapshots: dict[int, list[float]] = {checkpoint: [] for checkpoint in checkpoints}
    finals: list[float] = []
    deep_drawdowns = 0

    for _ in range(MONTE_CARLO_PATHS):
        equity = 1.0
        peak = 1.0
        worst_drawdown = 0.0
        snapshots[0].append(equity)
        for trade_index in range(1, MONTE_CARLO_TRADES + 1):
            equity *= max(1 + rng.choice(trade_returns), 0.0)
            peak = max(peak, equity)
            worst_drawdown = max(worst_drawdown, (peak - equity) / peak if peak > 0 else 1.0)
            if trade_index in snapshots:
                snapshots[trade_index].append(equity)
        finals.append(equity)
        if worst_drawdown >= 0.2:
            deep_drawdowns += 1

    bands = []
    for checkpoint in checkpoints:
        values = sorted(snapshots[checkpoint])
        bands.append(
            DeskMonteCarloBand(
                trade_index=checkpoint,
                p5=round(_percentile(values, 0.05), 4),
                p25=round(_percentile(values, 0.25), 4),
                p50=round(_percentile(values, 0.50), 4),
                p75=round(_percentile(values, 0.75), 4),
                p95=round(_percentile(values, 0.95), 4),
            )
        )

    sorted_finals = sorted(finals)
    return DeskMonteCarlo(
        paths=MONTE_CARLO_PATHS,
        trades_per_path=MONTE_CARLO_TRADES,
        sample_size=len(trade_returns),
        bands=bands,
        probability_below_start=round(sum(1 for value in finals if value < 1.0) / len(finals), 3),
        probability_drawdown_20=round(deep_drawdowns / MONTE_CARLO_PATHS, 3),
        median_multiple=round(_percentile(sorted_finals, 0.5), 4),
    )
