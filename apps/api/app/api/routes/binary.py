from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import CurrentUser, require_current_user
from app.schemas.binary import BinaryConfig, BinaryRunResponse, BinaryRunSummaryResponse
from app.services import binary_run_store
from app.services.binary.engine import run_binary
from app.services.desk.market import MarketDataError

router = APIRouter()


@router.get("/defaults", response_model=BinaryConfig)
def get_binary_defaults(current_user: CurrentUser = Depends(require_current_user)) -> BinaryConfig:
    return BinaryConfig()


@router.get("/runs", response_model=list[BinaryRunSummaryResponse])
def list_binary_runs(current_user: CurrentUser = Depends(require_current_user)) -> list[BinaryRunSummaryResponse]:
    return binary_run_store.list_runs(current_user)


@router.post("/runs", response_model=BinaryRunResponse)
def create_binary_run(payload: BinaryConfig, current_user: CurrentUser = Depends(require_current_user)) -> BinaryRunResponse:
    try:
        result = run_binary(payload)
    except MarketDataError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return binary_run_store.save_run(result, current_user)


@router.get("/runs/{run_id}", response_model=BinaryRunResponse)
def get_binary_run(run_id: str, current_user: CurrentUser = Depends(require_current_user)) -> BinaryRunResponse:
    run = binary_run_store.get_run(run_id, current_user)
    if run is None:
        raise HTTPException(status_code=404, detail="Binary run not found")
    return run
