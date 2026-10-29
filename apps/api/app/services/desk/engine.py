"""Runs a paper desk session: the six agents stepping bar by bar over a synthetic tape."""

import secrets
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Literal

import httpx

from app.schemas.desk import (
    DESK_DISCLAIMER,
    HISTORICAL_DESK_DISCLAIMER,
    DeskAgent,
    DeskCheckpoint,
    DeskConfig,
    DeskFrame,
    DeskKillReason,
    DeskPosition,
    DeskRunResponse,
    DeskScanMark,
    DeskSeatAnswer,
    DeskSeatVerdict,
    DeskSetup,
    DeskSetupEdge,
    DeskTrade,
)
from app.schemas.trades import TradeEntryResponse
from app.services.desk.agents import (
    JOURNAL_PRIOR_CAP,
    KILL_LABELS,
    SETUP_LABELS,
    SETUP_PRIORS,
    TILT_COOLDOWN_BARS,
    AnalystAgent,
    DeskGate,
    ExecutorAgent,
    ExitFill,
    FilterAgent,
    LoggerAgent,
    PaperOrder,
    PaperPosition,
    RiskAgent,
    ScoutAgent,
    SymbolTape,
    map_journal_tags,
)
from app.services.desk.calendar import market_today
from app.services.desk.flow import FlowMemory, flow_level, proxy_flow
from app.services.desk.historical import PROVIDERS, load_historical_feed
from app.services.desk.market import Bar, MarketFeed, SimulatedMarketFeed, bar_clock
from app.services.desk.seat import QUESTION_TEXT, SkepticSeat, build_context
from app.services.desk.stats import build_summary, run_monte_carlo

FALLBACK_SYMBOLS = ("SPY", "QQQ", "IWM", "AMD", "MSFT", "TSLA")
MIN_SYMBOLS = 4
MAX_DEFAULT_SYMBOLS = 6


def resolve_config(config: DeskConfig, watchlist_symbols: list[str]) -> tuple[DeskConfig, list[str]]:
    """Fills in symbols, seed, and replay date. Returns the resolved config plus any symbols added as filler."""
    updates: dict[str, object] = {}
    added: list[str] = []

    if config.data_source == "synthetic":
        updates["end_date"] = None
    elif config.end_date is None:
        updates["end_date"] = market_today() - timedelta(days=1)

    if not config.symbols:
        symbols = [symbol.upper() for symbol in watchlist_symbols][:MAX_DEFAULT_SYMBOLS]
        for fallback in FALLBACK_SYMBOLS:
            if len(symbols) >= MIN_SYMBOLS:
                break
            if fallback not in symbols:
                symbols.append(fallback)
                added.append(fallback)
        updates["symbols"] = symbols

    if config.seed is None:
        updates["seed"] = secrets.randbelow(2**31)

    return config.model_copy(update=updates), added


def journal_counts(trades: list[TradeEntryResponse]) -> dict[DeskSetup, tuple[int, int]]:
    """Wins and losses per desk setup from the user's own tagged journal trades."""
    tallies: dict[DeskSetup, list[int]] = {}
    for trade in trades:
        if trade.pnl is None or trade.pnl == 0:
            continue
        setup = map_journal_tags(trade.tags)
        if setup is None:
            continue
        tally = tallies.setdefault(setup, [0, 0])
        if sum(tally) >= JOURNAL_PRIOR_CAP:
            continue
        tally[0 if trade.pnl > 0 else 1] += 1
    return {setup: (tally[0], tally[1]) for setup, tally in tallies.items()}


@dataclass(frozen=True)
class CheckpointDecision:
    decision: Literal["continue", "stop"]
    # The last completed bar when the user decided; the decision takes effect from the next bar.
    step: int


@dataclass
class CheckpointPolicy:
    """Live mode's keep-running checkpoints: each milestone crossed, and one drawdown level, pause new entries."""

    milestones: list[float]
    drawdown_pct: float
    decisions: dict[int, CheckpointDecision] = field(default_factory=dict)
    # Stop at any time, without a checkpoint: takes effect from the bar after this step.
    manual_stop_step: int | None = None


class DeskSession:
    def __init__(
        self,
        config: DeskConfig,
        journal: dict[DeskSetup, tuple[int, int]],
        feed: MarketFeed,
        checkpoint_policy: CheckpointPolicy | None = None,
        seat_cache: dict[str, dict] | None = None,
    ) -> None:
        assert config.seed is not None and config.symbols, "resolve_config must run first"
        self.config = config
        self.feed = feed
        self.checkpoint_policy = checkpoint_policy
        self.checkpoints: list[DeskCheckpoint] = []
        self.open_checkpoint: DeskCheckpoint | None = None
        self.next_milestone = 0
        self.drawdown_checkpoint_hit = False
        self.stopped = False
        self.tapes = {symbol: SymbolTape(symbol) for symbol in config.symbols}
        self.flow_memory = {symbol: FlowMemory() for symbol in config.symbols}
        self.flow: dict[str, float] = {symbol: 0.0 for symbol in config.symbols}
        self.scout = ScoutAgent()
        self.filter = FilterAgent(config)
        self.analyst = AnalystAgent(config, journal)
        self.risk = RiskAgent(config)
        self.executor = ExecutorAgent(config)
        self.seat = SkepticSeat(config, cache=seat_cache)
        self.logger = LoggerAgent()
        self.seat_verdicts: list[DeskSeatVerdict] = []
        self.tape: dict[str, list[list[float]]] = {symbol: [] for symbol in config.symbols}

        self.realized = 0.0
        self.fees_paid = 0.0
        self.orders: dict[str, PaperOrder] = {}
        self.positions: dict[str, PaperPosition] = {}
        self.initial_stops: dict[str, float] = {}
        self.trades: list[DeskTrade] = []
        self.frames: list[DeskFrame] = []
        self.trade_returns: list[float] = []
        self.halted_sessions = 0
        self.next_trade_number = 1

        self.session = 0
        self.step = 0
        self.session_length = 0
        self.clock = bar_clock(0)
        self.halted = False
        self.cooldown_until = -1
        self.loss_streak = 0

    def equity(self, marks: dict[str, float]) -> float:
        unrealized = sum(
            position.gross_pnl_at(marks[position.order.setup.symbol]) for position in self.positions.values()
        )
        return self.config.starting_balance + self.realized + unrealized

    def committed_notional(self) -> float:
        open_notional = sum(position.entry * position.quantity for position in self.positions.values())
        pending_notional = sum(order.setup.entry * order.sizing.quantity for order in self.orders.values())
        return open_notional + pending_notional

    def log(self, agent: DeskAgent, kind: str, message: str, symbol: str | None = None) -> None:
        self.logger.log(
            step=self.step, session=self.session, clock=self.clock, agent=agent, kind=kind, message=message, symbol=symbol
        )

    def run(self) -> DeskRunResponse:
        for symbol in self.config.symbols:
            for bar in self.feed.session_bars(symbol, 0):
                self.tapes[symbol].append(bar)

        labels = self.feed.session_labels
        tape = (
            "a synthetic tape"
            if self.feed.data_source == "synthetic"
            else f"{PROVIDERS[self.feed.data_source].name} 5-minute bars, {labels[0]} to {labels[-1]}"
        )
        self.log(
            "logger",
            "session_plan",
            f"Paper desk armed on {', '.join(self.config.symbols)} ({tape}) with {self.config.risk_per_trade_pct:g}% "
            f"risk cap, {self.config.kelly_fraction:g} Kelly, max {self.config.max_open_positions} open.",
        )

        for session in range(1, self.config.sessions + 1):
            self.run_session(session)

        return self.build_response()

    def run_session(self, session: int) -> None:
        self.session = session
        self.halted = False
        self.cooldown_until = -1
        self.loss_streak = 0
        session_bars = {symbol: self.feed.session_bars(symbol, session) for symbol in self.config.symbols}
        session_flow = {symbol: self.feed.session_flow(symbol, session) for symbol in self.config.symbols}
        for memory in self.flow_memory.values():
            memory.reset()
        # Sessions vary in length on real data (1:00 pm early closes), and a live session has only the bars
        # completed so far; every symbol is aligned to the same slots.
        self.session_length = self.feed.session_length(session)
        available = len(session_bars[self.config.symbols[0]])
        first_step = len(self.frames)
        day_start_equity = self.config.starting_balance + self.realized

        for index in range(available):
            self.step = first_step + index
            self.clock = bar_clock(index)
            bars = {symbol: session_bars[symbol][index] for symbol in self.config.symbols}
            marks = {symbol: bar.close for symbol, bar in bars.items()}

            self.resolve_checkpoint(bars)
            self.fill_orders(bars)
            self.manage_positions(bars, is_last_bar=index == self.session_length - 1)
            for symbol, bar in bars.items():
                self.tapes[symbol].append(bar)
                self.tape[symbol].append([bar.open, bar.high, bar.low, bar.close, bar.volume])
                prints = session_flow[symbol]
                self.read_flow(symbol, prints[index] if prints is not None else proxy_flow(bar))

            day_pnl = self.equity(marks) - day_start_equity
            if not self.halted and day_pnl <= -day_start_equity * self.config.max_daily_loss_pct / 100:
                self.halted = True
                self.halted_sessions += 1
                self.log(
                    "risk",
                    "halt",
                    f"Day P&L {day_pnl:+.2f} breached the {self.config.max_daily_loss_pct:g}% daily loss limit. "
                    "No new entries for the rest of the session; open stops stay in place.",
                )
            self.trigger_checkpoint(marks, day_start_equity)

            scans = self.scan(index, marks) if index < self.session_length - 1 else []
            self.frames.append(self.frame(marks, scans))

    def resolve_checkpoint(self, bars: dict[str, Bar]) -> None:
        """Applies the user's decisions from the bar after they made them."""
        policy = self.checkpoint_policy
        if policy is None or self.stopped:
            return

        checkpoint = self.open_checkpoint
        if checkpoint is not None:
            decision = policy.decisions.get(checkpoint.index)
            if decision is not None and self.step > max(decision.step, checkpoint.step):
                checkpoint.decision = decision.decision
                checkpoint.decided_step = max(decision.step, checkpoint.step)
                self.open_checkpoint = None
                if decision.decision == "stop":
                    self.stop_desk(bars, f"You stopped the desk at checkpoint {checkpoint.index + 1}.")
                    return
                self.log("risk", "resume", f"You chose to keep running after checkpoint {checkpoint.index + 1}. Entries resume.")

        if policy.manual_stop_step is not None and self.step > policy.manual_stop_step:
            self.stop_desk(bars, "You stopped the desk.")

    def stop_desk(self, bars: dict[str, Bar], reason: str) -> None:
        self.stopped = True
        self.open_checkpoint = None
        for symbol in list(self.orders):
            del self.orders[symbol]
            self.logger.counts.executor_cancels += 1
            self.log("executor", "cancel", "Pending paper order cancelled: the desk was stopped.", symbol)
        for position in list(self.positions.values()):
            self.close_position(position, self.executor.stop_exit(position, bars[position.order.setup.symbol]))
        self.log("risk", "stopped", f"{reason} Flat at this bar's open; no new entries today.")

    def trigger_checkpoint(self, marks: dict[str, float], day_start_equity: float) -> None:
        """Opens a keep-running checkpoint when equity crosses the next milestone or the drawdown level."""
        policy = self.checkpoint_policy
        if policy is None or self.stopped or self.open_checkpoint is not None:
            return

        equity = self.equity(marks)
        multiple = equity / self.config.starting_balance
        kind: Literal["milestone", "drawdown"] | None = None
        while self.next_milestone < len(policy.milestones) and multiple >= policy.milestones[self.next_milestone]:
            kind = "milestone"
            reached = policy.milestones[self.next_milestone]
            self.next_milestone += 1
        day_pnl = equity - day_start_equity
        if kind is None and not self.drawdown_checkpoint_hit and day_pnl <= -day_start_equity * policy.drawdown_pct / 100:
            kind = "drawdown"
            self.drawdown_checkpoint_hit = True
        if kind is None:
            return

        change = equity - self.config.starting_balance
        if kind == "milestone":
            message = (
                f"Reached the {reached}× milestone: {change:+.2f} ({(multiple - 1) * 100:+.2f}%). "
                "New entries are paused until you choose to keep running or stop."
            )
        else:
            message = (
                f"Down {day_pnl:+.2f} today ({day_pnl / day_start_equity * 100:+.2f}%), past the "
                f"{policy.drawdown_pct:g}% checkpoint. New entries are paused until you choose to keep running or stop."
            )
        checkpoint = DeskCheckpoint(
            index=len(self.checkpoints),
            kind=kind,
            step=self.step,
            session=self.session,
            clock=self.clock,
            equity=round(equity, 2),
            multiple=round(multiple, 4),
            message=message,
        )
        self.checkpoints.append(checkpoint)
        self.open_checkpoint = checkpoint
        self.log("risk", "checkpoint", message)

    def fill_orders(self, bars: dict[str, Bar]) -> None:
        for symbol, order in list(self.orders.items()):
            del self.orders[symbol]
            outcome = self.executor.fill_price(order, bars[symbol])
            if isinstance(outcome, str):
                self.logger.counts.executor_cancels += 1
                self.logger.kill("executor", outcome)
                self.log("executor", "cancel", f"Order cancelled: {KILL_LABELS[outcome].lower()} at the open.", symbol)
                continue

            setup = order.setup
            entry_fee = self.executor.fee(outcome, order.sizing.quantity)
            position = PaperPosition(
                trade_id=order.trade_id,
                order=order,
                session=self.session,
                open_step=self.step,
                opened_at=self.clock,
                entry=outcome,
                quantity=order.sizing.quantity,
                stop=setup.stop,
                target=setup.target,
                risk_per_unit=abs(outcome - setup.stop),
                entry_fee=entry_fee,
            )
            self.positions[symbol] = position
            self.initial_stops[order.trade_id] = setup.stop
            self.logger.counts.executor_fills += 1
            self.log(
                "executor",
                "fill",
                f"Paper fill {setup.side} {position.quantity:g} @ {outcome:.2f}, stop {setup.stop:.2f}, target {setup.target:.2f}.",
                symbol,
            )

    def manage_positions(self, bars: dict[str, Bar], *, is_last_bar: bool) -> None:
        for symbol, position in list(self.positions.items()):
            bar = bars[symbol]
            exit_fill = self.executor.check_exit(position, bar, self.initial_stops[position.trade_id])
            if exit_fill is None and is_last_bar:
                exit_fill = self.executor.bell_exit(position, bar)
            if exit_fill is not None:
                self.close_position(position, exit_fill)
                continue

            tighter = self.executor.trail(position, bar)
            if tighter is not None:
                position.stop = tighter
                self.logger.counts.stops_trailed += 1
                self.log(
                    "risk",
                    "trail",
                    f"Trailed stop to {tighter:.2f} (locks {position.r_at(tighter):+.2f}R) after a {position.high_water_r:.2f}R run.",
                    symbol,
                )

    def close_position(self, position: PaperPosition, exit_fill: ExitFill) -> None:
        symbol = position.order.setup.symbol
        del self.positions[symbol]
        exit_fee = self.executor.fee(exit_fill.price, position.quantity)
        fees = position.entry_fee + exit_fee
        pnl = position.gross_pnl_at(exit_fill.price) - fees
        risk_dollars = position.risk_per_unit * position.quantity
        r_multiple = pnl / risk_dollars if risk_dollars > 0 else 0.0
        equity_before = self.config.starting_balance + self.realized

        self.realized += pnl
        self.fees_paid += fees
        self.trade_returns.append(pnl / equity_before)
        self.logger.counts.executor_exits += 1

        won = pnl > 0
        setup_type = position.order.setup.setup
        self.analyst.record_outcome(setup_type, won)
        self.trades.append(
            DeskTrade(
                id=position.trade_id,
                symbol=symbol,
                side=position.side,
                setup=setup_type,
                session=position.session,
                open_step=position.open_step,
                close_step=self.step,
                opened_at=position.opened_at,
                closed_at=self.clock,
                entry=round(position.entry, 4),
                exit=round(exit_fill.price, 4),
                stop_initial=round(self.initial_stops[position.trade_id], 4),
                stop_final=round(position.stop, 4),
                target=round(position.target, 4),
                quantity=position.quantity,
                risk_dollars=round(risk_dollars, 2),
                fees=round(fees, 2),
                pnl=round(pnl, 2),
                r_multiple=round(r_multiple, 2),
                exit_reason=exit_fill.reason,
                score=position.order.assessment.score,
                win_probability=round(position.order.assessment.win_probability, 3),
                thesis=position.order.setup.thesis,
            )
        )
        self.log(
            "executor",
            "exit",
            f"Closed {position.side} on {exit_fill.reason} @ {exit_fill.price:.2f}: {pnl:+.2f} ({r_multiple:+.2f}R).",
            symbol,
        )
        self.log(
            "analyst",
            "update",
            f"{SETUP_LABELS[setup_type]} posterior win rate now {self.analyst.posterior(setup_type):.0%} "
            f"after a {'win' if won else 'loss'}.",
            symbol,
        )

        if won:
            self.loss_streak = 0
            return

        self.loss_streak += 1
        if self.loss_streak >= self.config.max_consecutive_losses:
            self.cooldown_until = self.step + TILT_COOLDOWN_BARS
            self.loss_streak = 0
            self.log(
                "risk",
                "cooldown",
                f"{self.config.max_consecutive_losses} losses in a row. Desk cools down for "
                f"{TILT_COOLDOWN_BARS * 5} minutes before taking new entries.",
            )

    def read_flow(self, symbol: str, slot) -> None:
        """Flow agent: updates the symbol's flow memory and speaks up when pressure turns strong."""
        previous = self.flow[symbol]
        imbalance = self.flow_memory[symbol].push(slot)
        self.flow[symbol] = imbalance
        if self.flow_memory[symbol].warmed_up and abs(imbalance) >= 0.5 > abs(previous):
            self.log(
                "flow",
                "pressure",
                f"Flow turned {flow_level(imbalance)} ({imbalance:+.2f} imbalance over the last "
                f"{len(self.flow_memory[symbol].slots)} bars, {self.feed.flow_source}).",
                symbol,
            )

    def scan(self, index: int, marks: dict[str, float]) -> list[DeskScanMark]:
        scans: list[DeskScanMark] = []
        for symbol in self.config.symbols:
            for setup in self.scout.scan(self.tapes[symbol]):
                self.logger.counts.scout_flagged += 1
                label = f"{SETUP_LABELS[setup.setup]} {setup.side}"

                gate = DeskGate(
                    bar_index=index,
                    session_length=self.session_length,
                    halted=self.halted,
                    cooldown_until=self.cooldown_until,
                    step=self.step,
                    busy_symbols=set(self.positions) | set(self.orders),
                    working_count=len(self.positions) + len(self.orders),
                    flow=self.flow[symbol],
                    paused=self.open_checkpoint is not None,
                    stopped=self.stopped,
                )
                kill = self.filter.review(setup, gate)
                if kill is not None:
                    self.logger.counts.filter_killed += 1
                    self.logger.kill("filter", kill)
                    if kill == "flow_against":
                        self.logger.counts.flow_vetoes += 1
                        self.log(
                            "flow",
                            "veto",
                            f"{label} killed: {flow_level(self.flow[symbol])} flow ({self.flow[symbol]:+.2f}) "
                            "against a continuation setup.",
                            symbol,
                        )
                    else:
                        self.log("filter", "kill", f"{label} killed: {KILL_LABELS[kill].lower()}.", symbol)
                    scans.append(DeskScanMark(symbol=symbol, setup=setup.setup, side=setup.side, status="killed"))
                    continue

                assessment = self.analyst.assess(setup, self.flow[symbol])
                self.logger.counts.analyst_scored += 1
                verdict = self.analyst.verdict(assessment)
                if verdict is not None:
                    self.logger.counts.analyst_killed += 1
                    self.logger.kill("analyst", verdict)
                    self.log(
                        "analyst",
                        "kill",
                        f"{label} scored {assessment.score} with EV {assessment.expected_r:+.2f}R: {KILL_LABELS[verdict].lower()}.",
                        symbol,
                    )
                    scans.append(DeskScanMark(symbol=symbol, setup=setup.setup, side=setup.side, status="killed"))
                    continue

                equity = self.equity(marks)
                sizing = self.risk.size(setup, assessment, equity, self.committed_notional())
                if isinstance(sizing, str):
                    self.logger.counts.risk_rejected += 1
                    self.logger.kill("risk", sizing)
                    self.log("risk", "reject", f"{label} rejected: {KILL_LABELS[sizing].lower()}.", symbol)
                    scans.append(DeskScanMark(symbol=symbol, setup=setup.setup, side=setup.side, status="killed"))
                    continue

                self.logger.counts.risk_sized += 1
                capped_note = " Size capped by buying power." if sizing.capped else ""
                self.log(
                    "analyst",
                    "score",
                    f"{label}: {setup.thesis}. Score {assessment.score}, win rate {assessment.win_probability:.0%}, "
                    f"R:R {setup.reward_risk:.1f}, flow {self.flow[symbol]:+.2f}, EV {assessment.expected_r:+.2f}R.",
                    symbol,
                )
                self.log(
                    "risk",
                    "size",
                    f"Risking {sizing.risk_dollars:.2f} ({sizing.risk_fraction:.2%} of equity; full Kelly {sizing.kelly:.1%}) "
                    f"on {sizing.quantity:g} units.{capped_note}",
                    symbol,
                )

                review = self.seat.review(
                    build_context(setup, self.tapes[symbol], self.flow[symbol], self.clock),
                    key=f"{self.step}:{symbol}:{setup.setup}:{setup.side}",
                )
                self.logger.counts.seat_reviews += 1
                self.logger.counts.seat_ai_calls = self.seat.ai_calls
                if review.note:
                    self.log("seat", "fallback", review.note, symbol)
                worst = review.worst
                vetoed = worst.probability >= self.config.seat_veto
                trade_id = None if vetoed else f"T{self.next_trade_number:03d}"
                self.seat_verdicts.append(
                    DeskSeatVerdict(
                        step=self.step,
                        session=self.session,
                        clock=self.clock,
                        symbol=symbol,
                        setup=setup.setup,
                        side=setup.side,
                        trade_id=trade_id,
                        source=review.source,
                        model=review.model,
                        answers=[
                            DeskSeatAnswer(
                                id=answer.id,
                                question=QUESTION_TEXT[answer.id],
                                probability=answer.probability,
                                reason=answer.reason,
                            )
                            for answer in review.output.answers
                        ],
                        thesis=review.output.thesis,
                        vetoed=vetoed,
                    )
                )
                if vetoed:
                    self.logger.counts.seat_vetoes += 1
                    self.logger.kill("seat", "seat_veto")
                    self.log(
                        "seat",
                        "veto",
                        f"{label} vetoed: {QUESTION_TEXT[worst.id]} {worst.probability:.0%}. {worst.reason}",
                        symbol,
                    )
                    scans.append(DeskScanMark(symbol=symbol, setup=setup.setup, side=setup.side, status="killed"))
                    continue

                self.log(
                    "seat",
                    "pass",
                    f"Passed: highest risk {worst.probability:.0%} ({worst.id.replace('_', ' ')}). {review.output.thesis}",
                    symbol,
                )
                assert trade_id is not None
                self.next_trade_number += 1
                self.orders[symbol] = PaperOrder(
                    trade_id=trade_id, setup=setup, sizing=sizing, assessment=assessment, placed_step=self.step
                )
                self.log("executor", "order", f"Paper order queued for the next open ({trade_id}).", symbol)
                scans.append(DeskScanMark(symbol=symbol, setup=setup.setup, side=setup.side, status="ordered"))
        return scans

    def frame(self, marks: dict[str, float], scans: list[DeskScanMark]) -> DeskFrame:
        positions = [
            DeskPosition(
                trade_id=position.trade_id,
                symbol=symbol,
                side=position.side,
                setup=position.order.setup.setup,
                entry=round(position.entry, 4),
                stop=round(position.stop, 4),
                target=round(position.target, 4),
                last=marks[symbol],
                r_now=round(position.r_at(marks[symbol]), 2),
                unrealized=round(position.gross_pnl_at(marks[symbol]), 2),
            )
            for symbol, position in self.positions.items()
        ]
        return DeskFrame(
            step=self.step,
            session=self.session,
            clock=self.clock,
            equity=round(self.equity(marks), 2),
            positions=positions,
            scans=scans,
            pipeline=self.logger.counts.model_copy(),
            halted=self.halted,
            flow={symbol: round(value, 3) for symbol, value in self.flow.items()},
        )

    def build_response(self) -> DeskRunResponse:
        summary = build_summary(
            starting_balance=self.config.starting_balance,
            ending_balance=self.config.starting_balance + self.realized,
            trades=self.trades,
            equity_curve=[frame.equity for frame in self.frames],
            fees_paid=self.fees_paid,
            sessions=self.config.sessions,
            halted_sessions=self.halted_sessions,
        )
        setup_edges = []
        for setup in SETUP_PRIORS:
            prior_wins, prior_losses = self.analyst.prior_counts(setup)
            journal_wins, journal_losses = self.analyst.journal_counts.get(setup, (0, 0))
            live_wins, live_losses = self.analyst.live_counts[setup]
            setup_trades = [trade for trade in self.trades if trade.setup == setup]
            setup_edges.append(
                DeskSetupEdge(
                    setup=setup,
                    enabled=setup in self.config.allowed_setups,
                    prior_wins=round(prior_wins, 2),
                    prior_losses=round(prior_losses, 2),
                    journal_wins=journal_wins,
                    journal_losses=journal_losses,
                    live_wins=live_wins,
                    live_losses=live_losses,
                    posterior_win_rate=round(self.analyst.posterior(setup), 3),
                    trades=len(setup_trades),
                    avg_r=(
                        round(sum(trade.r_multiple for trade in setup_trades) / len(setup_trades), 2)
                        if setup_trades
                        else None
                    ),
                )
            )

        # Audit, not a constant: a stop that ended looser than it started counts as widened.
        pipeline = self.logger.counts.model_copy()
        pipeline.stops_widened = sum(
            1
            for trade in self.trades
            if (trade.stop_final - trade.stop_initial) * (1 if trade.side == "long" else -1) < 0
        )

        kill_reasons = sorted(
            (
                DeskKillReason(agent=agent, code=code, label=KILL_LABELS[code], count=count)
                for (agent, code), count in self.logger.kills.items()
            ),
            key=lambda item: item.count,
            reverse=True,
        )

        return DeskRunResponse(
            id="pending",
            created_at="",
            data_source=self.feed.data_source,
            config=self.config,
            summary=summary,
            session_labels=self.feed.session_labels,
            session_lengths=[self.feed.session_length(session) for session in range(1, self.config.sessions + 1)],
            checkpoints=self.checkpoints,
            pipeline=pipeline,
            setup_edges=setup_edges,
            kill_reasons=kill_reasons,
            trades=self.trades,
            frames=self.frames,
            events=self.logger.events,
            monte_carlo=run_monte_carlo(self.trade_returns, seed=self.config.seed or 0),
            disclaimer=DESK_DISCLAIMER if self.feed.data_source == "synthetic" else HISTORICAL_DESK_DISCLAIMER,
            flow_source=self.feed.flow_source,
            seat_verdicts=self.seat_verdicts,
            tape=self.tape,
        )


def run_desk_session(
    config: DeskConfig,
    *,
    watchlist_symbols: list[str],
    journal_trades: list[TradeEntryResponse],
    market_client: httpx.Client | None = None,
) -> DeskRunResponse:
    """Runs one paper desk session. Raises MarketDataError when historical bars can't be loaded."""
    resolved, added = resolve_config(config, watchlist_symbols)
    notes: list[str] = []
    feed: MarketFeed
    if resolved.data_source in PROVIDERS:
        assert resolved.end_date is not None
        feed, notes = load_historical_feed(
            resolved.data_source,
            resolved.symbols,
            resolved.end_date,
            resolved.sessions,
            client=market_client,
            trade_flow=resolved.use_trade_flow,
        )
        resolved = resolved.model_copy(update={"symbols": feed.symbols})
    else:
        feed = SimulatedMarketFeed(resolved.symbols, resolved.seed or 0, resolved.sessions)

    journal = journal_counts(journal_trades) if resolved.use_journal_priors else {}
    session = DeskSession(resolved, journal, feed)
    if added:
        session.log(
            "logger",
            "symbols",
            f"Watchlist had fewer than {MIN_SYMBOLS} symbols, so the tape was topped up with {', '.join(added)}.",
        )
    for note in notes:
        session.log("logger", "symbols", note)
    return session.run()
