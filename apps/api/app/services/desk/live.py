"""Live paper mode: today's session, run bar by bar as Alpaca's IEX feed completes each 5-minute bar.

A live session stores only its market data so far, a snapshot of the inputs that
must not drift (journal priors, AI seat verdicts), and the user's decisions.
Every tick fetches what is new and reruns the deterministic desk engine over the
whole day, so a restart, a second worker, or a page refresh can never leave it
half-updated, and a decision made at 11:40 replays exactly at 15:55.
"""

from datetime import UTC, date, datetime, time, timedelta

import httpx

from app.core.config import settings
from app.schemas.desk import (
    DESK_LIVE_ACTIVE_STATUSES,
    DeskCheckpoint,
    DeskConfig,
    DeskLiveSessionRecord,
    DeskLiveSessionResponse,
    DeskRunResponse,
    DeskSetup,
)
from app.services.desk import alpaca, notify
from app.services.desk.calendar import MARKET_TIMEZONE, session_bar_count
from app.services.desk.engine import CheckpointDecision, CheckpointPolicy, DeskSession
from app.services.desk.flow import PROXY_FLOW_SOURCE, TRADE_FLOW_SOURCE, FlowSlot, TickRuleClassifier
from app.services.desk.historical import align_session, group_by_day
from app.services.desk.market import BAR_MINUTES, Bar, MarketDataError

WARMUP_LOOKBACK_DAYS = 10
# Bars are aggregated a few seconds after their interval ends; fetching too early would miss the newest one.
BAR_SETTLE_SECONDS = 15
HOLIDAY_GRACE = timedelta(minutes=30)


def live_now() -> datetime:
    return datetime.now(UTC)


def _http_client() -> httpx.Client:
    return httpx.Client()


def open_at(day: date) -> datetime:
    return datetime.combine(day, time(9, 30), tzinfo=MARKET_TIMEZONE)


def close_at(day: date) -> datetime:
    return open_at(day) + timedelta(minutes=BAR_MINUTES * session_bar_count(day))


def completed_slots(day: date, now: datetime) -> int:
    """How many of today's 5-minute bars have closed (and settled) by `now`."""
    elapsed = (now - open_at(day)).total_seconds() - BAR_SETTLE_SECONDS
    return int(max(0, min(elapsed // (BAR_MINUTES * 60), session_bar_count(day))))


def next_bar_at(day: date, now: datetime) -> datetime | None:
    done = completed_slots(day, now)
    if done >= session_bar_count(day):
        return None
    return open_at(day) + timedelta(minutes=BAR_MINUTES * (done + 1), seconds=BAR_SETTLE_SECONDS)


def check_can_start(now: datetime) -> date:
    """Today's market date, or a MarketDataError explaining why a live session can't start now."""
    if not settings.is_alpaca_configured:
        raise MarketDataError(
            "Live mode streams Alpaca's IEX bars. Set ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY on the API.",
            status_code=503,
        )
    today = now.astimezone(MARKET_TIMEZONE).date()
    if today.weekday() >= 5:
        raise MarketDataError("The market is closed today. Replay a past session instead.", status_code=422)
    if now >= close_at(today):
        raise MarketDataError("Today's session is over. Replay it as a historical run instead.", status_code=422)
    return today


class LiveMarketFeed:
    """Yesterday as warmup plus today's completed bars; `session_length` is the full scheduled day."""

    data_source = "alpaca"

    def __init__(
        self,
        day: date,
        warmup: dict[str, list[Bar]],
        today: dict[str, list[Bar]],
        flows: dict[str, list[FlowSlot]] | None,
    ) -> None:
        self.day = day
        self.symbols = list(today)
        self.session_labels = [day.isoformat()]
        self.flow_source = TRADE_FLOW_SOURCE if flows else PROXY_FLOW_SOURCE
        self._warmup = warmup
        self._today = today
        self._flows = flows

    def session_bars(self, symbol: str, session: int) -> list[Bar]:
        return self._warmup[symbol] if session == 0 else self._today[symbol]

    def session_length(self, session: int) -> int:
        return len(self._warmup[self.symbols[0]]) if session == 0 else session_bar_count(self.day)

    def session_flow(self, symbol: str, session: int) -> list[FlowSlot] | None:
        if session == 0 or not self._flows or symbol not in self._flows:
            return None
        return self._flows[symbol][: len(self._today[symbol])]


def _load_warmup(state: dict, symbols: list[str], day: date, client: httpx.Client) -> None:
    fetched = alpaca.fetch_bars(
        symbols, day - timedelta(days=WARMUP_LOOKBACK_DAYS), day - timedelta(days=1), client=client, feed=settings.alpaca_live_feed
    )
    by_symbol = {symbol: group_by_day(bars) for symbol, bars in fetched.items()}
    days = sorted({item for grouped in by_symbol.values() for item in grouped})
    if not days:
        raise MarketDataError("Alpaca returned no recent bars to warm the indicators up. Check the symbols.", status_code=422)

    warm_day = days[-1]
    warmup: dict[str, list[list[float]]] = {}
    notes: list[str] = []
    for symbol, grouped in by_symbol.items():
        aligned = align_session(warm_day, grouped.get(warm_day, []))
        if aligned is None:
            notes.append(f"Dropped {symbol}: too few IEX bars on {warm_day.isoformat()} to warm up indicators.")
            continue
        warmup[symbol] = [[bar.open, bar.high, bar.low, bar.close, bar.volume] for bar in aligned]
    if not warmup:
        raise MarketDataError("None of the symbols had enough IEX bars yesterday to trade live.", status_code=422)

    state["warmup_day"] = warm_day.isoformat()
    state["warmup"] = warmup
    state["notes"] = notes


def _refresh_today(state: dict, day: date, done: int, client: httpx.Client) -> None:
    symbols = list(state["warmup"])
    end_at = open_at(day) + timedelta(minutes=BAR_MINUTES * done) - timedelta(seconds=1)
    fetched = alpaca.fetch_bars(symbols, day, day, client=client, feed=settings.alpaca_live_feed, end_at=end_at)
    state["today"] = {
        symbol: [
            [bar.slot, bar.open, bar.high, bar.low, bar.close, bar.volume]
            for bar in fetched.get(symbol, [])
            if bar.day == day and bar.slot < done
        ]
        for symbol in symbols
    }
    state["done"] = done


def _refresh_flow(state: dict, day: date, done: int, client: httpx.Client) -> None:
    """Classifies only the prints since the last tick, carrying each symbol's tick-rule state forward."""
    symbols = list(state["warmup"])
    through = state.get("flow_done", 0)
    if through >= done:
        return
    slot_count = session_bar_count(day)
    flow = state.setdefault("flow", {symbol: [[0.0, 0.0] for _ in range(slot_count)] for symbol in symbols})
    classifiers: dict[str, TickRuleClassifier] = {}
    for symbol, (last_price, last_side) in state.get("flow_last", {}).items():
        classifier = TickRuleClassifier()
        classifier.last_price, classifier.last_side = last_price, int(last_side)
        classifiers[symbol] = classifier

    slots = alpaca.fetch_trade_flow(
        symbols,
        day,
        client=client,
        start_at=open_at(day) + timedelta(minutes=BAR_MINUTES * through),
        end_at=open_at(day) + timedelta(minutes=BAR_MINUTES * done) - timedelta(seconds=1),
        classifiers=classifiers,
    )
    for symbol, symbol_slots in slots.items():
        for slot in range(through, done):
            flow[symbol][slot][0] += symbol_slots[slot].buy_volume
            flow[symbol][slot][1] += symbol_slots[slot].sell_volume
    state["flow_done"] = done
    state["flow_last"] = {symbol: [classifier.last_price, classifier.last_side] for symbol, classifier in classifiers.items()}
    state.pop("flow_error", None)


def build_feed(record: DeskLiveSessionRecord) -> LiveMarketFeed:
    state = record.market_state
    day = record.session_date
    done = state.get("done", 0)
    warmup = {symbol: [Bar(index, *row) for index, row in enumerate(rows)] for symbol, rows in state["warmup"].items()}
    today: dict[str, list[Bar]] = {}
    for symbol, rows in state.get("today", {}).items():
        if symbol not in warmup:
            continue
        by_slot = {int(row[0]): row for row in rows}
        last_close = warmup[symbol][-1].close
        bars: list[Bar] = []
        for slot in range(done):
            row = by_slot.get(slot)
            if row is None:
                bars.append(Bar(slot, last_close, last_close, last_close, last_close, 0))
                continue
            bars.append(Bar(slot, *row[1:]))
            last_close = row[4]
        today[symbol] = bars

    flows = None
    if record.config.use_trade_flow and state.get("flow") and state.get("flow_done", 0) >= done:
        flows = {symbol: [FlowSlot(buy, sell) for buy, sell in slots] for symbol, slots in state["flow"].items()}
    return LiveMarketFeed(day, {symbol: warmup[symbol] for symbol in today}, today, flows)


def compute(record: DeskLiveSessionRecord) -> DeskRunResponse:
    state = record.market_state
    feed = build_feed(record)
    config = record.config.model_copy(update={"symbols": feed.symbols})
    policy = CheckpointPolicy(
        milestones=config.milestones,
        drawdown_pct=config.checkpoint_drawdown_pct,
        decisions={
            int(index): CheckpointDecision(decision=item["decision"], step=int(item["step"]))
            for index, item in record.decisions.items()
        },
        manual_stop_step=record.manual_stop_step,
    )
    journal: dict[DeskSetup, tuple[int, int]] = {setup: (wins, losses) for setup, (wins, losses) in state.get("journal", {}).items()}
    session = DeskSession(config, journal, feed, policy, seat_cache=state.setdefault("seat_cache", {}))
    for note in state.get("notes", []):
        session.log("logger", "symbols", note)
    if state.get("flow_error"):
        session.log("logger", "flow", f"Flow agent is on the bar proxy this tick: {state['flow_error']}")
    return session.run()


def open_checkpoint(record: DeskLiveSessionRecord) -> DeskCheckpoint | None:
    """The checkpoint still waiting on the user. A decision already recorded closes it at once,
    even though the engine only applies it from the next bar."""
    if record.result is None:
        return None
    return next(
        (
            checkpoint
            for checkpoint in record.result.checkpoints
            if checkpoint.decision is None and str(checkpoint.index) not in record.decisions
        ),
        None,
    )


def _status_after(record: DeskLiveSessionRecord, result: DeskRunResponse, done: int) -> tuple[str, str]:
    day = record.session_date
    stopped = any(event.kind == "stopped" for event in result.events)
    pending_stop = record.manual_stop_step is not None or any(item["decision"] == "stop" for item in record.decisions.values())
    checkpoint = open_checkpoint(record.model_copy(update={"result": result}))
    flat = not result.frames[-1].positions if result.frames else True

    if done >= session_bar_count(day):
        return "closed", "Session closed. Saved to your desk history."
    if stopped and flat:
        return "stopped", "Stopped for the day and flat. Saved to your desk history."
    if pending_stop:
        return "stopping", "Stopping: open positions flatten at the next bar's open."
    if checkpoint is not None:
        return "awaiting_decision", checkpoint.message
    return "running", "Running. The desk updates as each 5-minute bar closes."


def _notifications(record: DeskLiveSessionRecord, result: DeskRunResponse) -> list[tuple[str, notify.DeskNotification]]:
    summary = result.summary
    pending: list[tuple[str, notify.DeskNotification]] = []
    for checkpoint in result.checkpoints:
        key = f"checkpoint-{checkpoint.index}"
        if checkpoint.decision is None and key not in record.notified:
            change = checkpoint.equity - summary.starting_balance
            pending.append(
                (
                    key,
                    notify.DeskNotification(
                        title=f"Paper desk {'up' if change >= 0 else 'down'} {abs(checkpoint.multiple - 1) * 100:.2f}% at {checkpoint.clock}",
                        body=(
                            f"{change:+.2f} on {', '.join(result.config.symbols)} ({summary.wins}W/{summary.losses}L so far). "
                            "New entries are paused. Keep running?"
                        ),
                        urgent=checkpoint.kind == "drawdown",
                    ),
                )
            )
    if "halt" not in record.notified and any(event.kind == "halt" for event in result.events):
        pending.append(
            ("halt", notify.DeskNotification("Paper desk hit its daily loss limit", "No new entries today; open stops stay in place.", urgent=True))
        )
    if record.status in ("closed", "stopped") and "final" not in record.notified:
        pending.append(
            (
                "final",
                notify.DeskNotification(
                    title=f"Paper session {'closed' if record.status == 'closed' else 'stopped'}: {summary.net_pnl:+.2f}",
                    body=f"{summary.trades} trades, {summary.wins}W/{summary.losses}L, max drawdown {summary.max_drawdown_pct:.1f}%.",
                ),
            )
        )
    return pending


def tick(
    record: DeskLiveSessionRecord,
    *,
    now: datetime | None = None,
    client: httpx.Client | None = None,
    force: bool = False,
) -> DeskLiveSessionRecord:
    """Fetches what is new, recomputes the day, updates status, and sends any due notifications."""
    now = now or live_now()
    if record.status not in DESK_LIVE_ACTIVE_STATUSES:
        return record
    if not force and record.last_tick_at:
        last = datetime.fromisoformat(record.last_tick_at)
        if (now - last).total_seconds() < settings.desk_live_stale_seconds and completed_slots(record.session_date, last) == completed_slots(record.session_date, now):
            return record

    record = record.model_copy(deep=True)
    record.last_tick_at = now.isoformat()
    day = record.session_date
    if now < open_at(day):
        record.status = "scheduled"
        record.message = "Waiting for the 09:30 open."
        return record

    done = completed_slots(day, now)
    owns_client = client is None
    http = client or _http_client()
    try:
        state = record.market_state
        if "warmup" not in state:
            _load_warmup(state, record.config.symbols, day, http)
        if done > state.get("done", -1) or force:
            _refresh_today(state, day, done, http)
        if record.config.use_trade_flow and done > 0:
            try:
                _refresh_flow(state, day, done, http)
            except MarketDataError as exc:
                state["flow_error"] = exc.message

        if done == 0:
            record.status = "scheduled"
            record.message = "Waiting for the first 5-minute bar to close at 09:35."
            return record
        if not any(state["today"].values()) and now - open_at(day) > HOLIDAY_GRACE:
            record.status = "closed"
            record.message = "No bars have printed since the open. The market may be closed today."
            return record

        result = compute(record)
        record.result = result
        record.status, record.message = _status_after(record, result, done)

        for key, notification in _notifications(record, result):
            if record.notify_url:
                record.notify_error = notify.send(record.notify_url, notification, client=http)
            record.notified.append(key)
    except MarketDataError as exc:
        record.message = exc.message
        if exc.status_code == 503:
            record.status = "error"
    finally:
        if owns_client:
            http.close()
    return record


def decide(record: DeskLiveSessionRecord, checkpoint_index: int, decision: str) -> DeskLiveSessionRecord:
    """Records the user's choice at the open checkpoint; it applies from the bar after the latest completed one."""
    checkpoint = open_checkpoint(record)
    if checkpoint is None or checkpoint.index != checkpoint_index:
        raise ValueError("That checkpoint isn't waiting for a decision.")
    record = record.model_copy(deep=True)
    assert record.result is not None
    record.decisions[str(checkpoint_index)] = {"decision": decision, "step": len(record.result.frames) - 1}
    return _recompute(record)


def stop(record: DeskLiveSessionRecord) -> DeskLiveSessionRecord:
    record = record.model_copy(deep=True)
    if record.result is None or not record.result.frames:
        record.status = "stopped"
        record.message = "Stopped before the first bar."
        return record
    record.manual_stop_step = len(record.result.frames) - 1
    return _recompute(record)


def _recompute(record: DeskLiveSessionRecord) -> DeskLiveSessionRecord:
    result = compute(record)
    record.result = result
    record.status, record.message = _status_after(record, result, record.market_state.get("done", 0))
    return record


def new_record(
    *, session_id: str, created_at: str, config: DeskConfig, day: date, notify_url: str | None, journal: dict
) -> DeskLiveSessionRecord:
    return DeskLiveSessionRecord(
        id=session_id,
        created_at=created_at,
        status="scheduled",
        session_date=day,
        config=config,
        market_state={"journal": journal},
        notify_url=notify_url,
        message="Starting up.",
    )


def to_response(record: DeskLiveSessionRecord, *, now: datetime | None = None) -> DeskLiveSessionResponse:
    now = now or live_now()
    upcoming = next_bar_at(record.session_date, now) if record.status in DESK_LIVE_ACTIVE_STATUSES else None
    channel = None
    if record.notify_url:
        try:
            channel = notify.channel_for(record.notify_url)
        except notify.NotifyURLError:
            channel = None
    return DeskLiveSessionResponse(
        id=record.id,
        created_at=record.created_at,
        status=record.status,
        session_date=record.session_date,
        config=record.config,
        last_tick_at=record.last_tick_at,
        next_bar_at=upcoming.astimezone(UTC).isoformat() if upcoming else None,
        message=record.message,
        notify_channel=channel,
        notify_error=record.notify_error,
        open_checkpoint=open_checkpoint(record),
        run_id=record.run_id,
        result=record.result,
    )
