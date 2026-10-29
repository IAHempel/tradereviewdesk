from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import CurrentUser, require_current_user
from app.core.config import settings
from app.core.persistence import require_database_result, use_file_persistence
from app.schemas.desk import DeskConfig, DeskDataSourceInfo, DeskRunResponse, DeskRunSummaryResponse
from app.schemas.trades import TradeEntryResponse
from app.services import desk_repository, state_store, trade_repository, watchlist_repository
from app.services.desk.engine import resolve_config, run_desk_session
from app.services.desk.market import MarketDataError

router = APIRouter()

RUN_HISTORY_LIMIT = 20
FILE_RUN_HISTORY_LIMIT = 5


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
    ]


@router.get("/runs", response_model=list[DeskRunSummaryResponse])
def list_desk_runs(current_user: CurrentUser = Depends(require_current_user)) -> list[DeskRunSummaryResponse]:
    if use_file_persistence():
        return [
            DeskRunSummaryResponse.model_validate(run.model_dump(include=set(DeskRunSummaryResponse.model_fields)))
            for run in state_store.list_desk_runs(current_user)
        ]

    return require_database_result(
        desk_repository.list_desk_runs(current_user, limit=RUN_HISTORY_LIMIT),
        "Desk runs",
    )


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

    if use_file_persistence():
        run = result.model_copy(update={"id": str(uuid4()), "created_at": datetime.now(UTC).isoformat()})
        history = state_store.list_desk_runs(current_user)
        state_store.save_desk_runs([run, *history][:FILE_RUN_HISTORY_LIMIT], current_user)
        return run

    return require_database_result(desk_repository.create_desk_run(result, current_user), "Desk run")


@router.get("/runs/{run_id}", response_model=DeskRunResponse)
def get_desk_run(run_id: str, current_user: CurrentUser = Depends(require_current_user)) -> DeskRunResponse:
    if use_file_persistence():
        run = next((item for item in state_store.list_desk_runs(current_user) if item.id == run_id), None)
    else:
        run = desk_repository.get_desk_run(run_id, current_user)

    if run is None:
        raise HTTPException(status_code=404, detail="Desk run not found")
    return run
