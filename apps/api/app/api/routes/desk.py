from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import CurrentUser, require_current_user
from app.core.config import settings
from app.core.persistence import require_database_result, use_file_persistence
from app.schemas.desk import (
    DESK_LIVE_ACTIVE_STATUSES,
    DeskConfig,
    DeskDataSourceInfo,
    DeskLiveDecisionRequest,
    DeskLiveSessionRecord,
    DeskLiveSessionResponse,
    DeskLiveStartRequest,
    DeskRunResponse,
    DeskRunSummaryResponse,
)
from app.schemas.trades import TradeEntryResponse
from app.services import desk_live_service, desk_run_store, state_store, trade_repository, watchlist_repository
from app.services.desk import live, notify
from app.services.desk.engine import journal_counts, resolve_config, run_desk_session
from app.services.desk.market import MarketDataError

router = APIRouter()


def _watchlist_symbols(current_user: CurrentUser) -> list[str]:
    if use_file_persistence():
        watchlists = state_store.list_watchlists(current_user)
    else:
        watchlists = require_database_result(watchlist_repository.list_watchlists(current_user), "Watchlists")

    primary = next((watchlist for watchlist in watchlists if watchlist.is_default), watchlists[0] if watchlists else None)
    if primary is None:
        return []
    return [item.symbol for item in sorted(primary.symbols, key=lambda item: item.display_order)]


def _journal_trades(current_user: CurrentUser) -> list[TradeEntryResponse]:
    if use_file_persistence():
        return state_store.list_trades(current_user)
    return require_database_result(trade_repository.list_trades(current_user), "Trades")


@router.get("/defaults", response_model=DeskConfig)
def get_desk_defaults(current_user: CurrentUser = Depends(require_current_user)) -> DeskConfig:
    resolved, _ = resolve_config(DeskConfig(), _watchlist_symbols(current_user))
    return resolved.model_copy(update={"seed": None})


@router.get("/sources", response_model=list[DeskDataSourceInfo])
def list_desk_sources(current_user: CurrentUser = Depends(require_current_user)) -> list[DeskDataSourceInfo]:
    return [
        DeskDataSourceInfo(
            id="synthetic",
            label="Synthetic tape",
            available=True,
            detail="Seeded random market with no edge built in. Good for stress-testing rules.",
        ),
        DeskDataSourceInfo(
            id="polygon",
            label="Polygon historical",
            available=settings.is_polygon_configured,
            detail=(
                "Real 5-minute bars for completed sessions, cached after the first load."
                if settings.is_polygon_configured
                else "Set POLYGON_API_KEY on the API to replay real historical bars."
            ),
        ),
        DeskDataSourceInfo(
            id="alpaca",
            label="Alpaca historical",
            available=settings.is_alpaca_configured,
            detail=(
                "Real 5-minute consolidated bars for completed sessions, cached after the first load."
                if settings.is_alpaca_configured
                else "Set ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY on the API to replay real historical bars."
            ),
        ),
    ]


@router.get("/runs", response_model=list[DeskRunSummaryResponse])
def list_desk_runs(current_user: CurrentUser = Depends(require_current_user)) -> list[DeskRunSummaryResponse]:
    return desk_run_store.list_runs(current_user)


@router.post("/runs", response_model=DeskRunResponse)
def create_desk_run(
    payload: DeskConfig,
    current_user: CurrentUser = Depends(require_current_user),
) -> DeskRunResponse:
    try:
        result = run_desk_session(
            payload,
            watchlist_symbols=_watchlist_symbols(current_user),
            journal_trades=_journal_trades(current_user),
        )
    except MarketDataError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return desk_run_store.save_run(result, current_user)


@router.get("/runs/{run_id}", response_model=DeskRunResponse)
def get_desk_run(run_id: str, current_user: CurrentUser = Depends(require_current_user)) -> DeskRunResponse:
    run = desk_run_store.get_run(run_id, current_user)
    if run is None:
        raise HTTPException(status_code=404, detail="Desk run not found")
    return run


def _live_session(session_id: str, current_user: CurrentUser) -> DeskLiveSessionRecord:
    record = desk_live_service.get(session_id, current_user)
    if record is None:
        raise HTTPException(status_code=404, detail="Live session not found")
    return record


@router.get("/live", response_model=DeskLiveSessionResponse | None)
def get_live_session(current_user: CurrentUser = Depends(require_current_user)) -> DeskLiveSessionResponse | None:
    """The latest live session, ticked first if a new bar has closed since it last updated."""
    record = desk_live_service.latest(current_user)
    if record is None:
        return None
    return live.to_response(desk_live_service.tick_and_save(record, current_user))


@router.post("/live", response_model=DeskLiveSessionResponse)
def start_live_session(
    payload: DeskLiveStartRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> DeskLiveSessionResponse:
    now = live.live_now()
    try:
        day = live.check_can_start(now)
    except MarketDataError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    existing = desk_live_service.latest(current_user)
    if existing is not None and existing.session_date == day and existing.status in DESK_LIVE_ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="A live session is already running today. Stop it before starting another.")

    notify_url = (payload.notify_url or "").strip() or None
    if notify_url:
        try:
            notify.channel_for(notify_url)
        except notify.NotifyURLError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    config_fields = payload.model_dump(exclude={"notify_url"})
    resolved, _ = resolve_config(DeskConfig.model_validate(config_fields), _watchlist_symbols(current_user))
    resolved = resolved.model_copy(update={"data_source": "alpaca", "sessions": 1, "end_date": day})
    journal = journal_counts(_journal_trades(current_user)) if resolved.use_journal_priors else {}
    record = live.new_record(
        session_id=str(uuid4()),
        created_at=now.isoformat(),
        config=resolved,
        day=day,
        notify_url=notify_url,
        journal={setup: list(counts) for setup, counts in journal.items()},
    )
    record = live.tick(record, now=now, force=True)
    return live.to_response(desk_live_service.create(record, current_user), now=now)


@router.post("/live/{session_id}/decision", response_model=DeskLiveSessionResponse)
def decide_live_checkpoint(
    session_id: str,
    payload: DeskLiveDecisionRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> DeskLiveSessionResponse:
    record = _live_session(session_id, current_user)
    if record.status not in DESK_LIVE_ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="This live session has already finished.")
    try:
        record = live.decide(record, payload.checkpoint, payload.decision)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return live.to_response(desk_live_service.save(record, current_user))


@router.post("/live/{session_id}/stop", response_model=DeskLiveSessionResponse)
def stop_live_session(session_id: str, current_user: CurrentUser = Depends(require_current_user)) -> DeskLiveSessionResponse:
    record = _live_session(session_id, current_user)
    if record.status not in DESK_LIVE_ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="This live session has already finished.")
    return live.to_response(desk_live_service.save(live.stop(record), current_user))
