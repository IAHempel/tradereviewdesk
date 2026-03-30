from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.auth import CurrentUser, require_current_user
from app.core.persistence import require_database_result, use_file_persistence
from app.schemas.trades import TradeEntryCreate, TradeEntryResponse, TradeEntryUpdate, TradeImportResponse
from app.services.csv_parser import parse_trade_csv
from app.services import state_store, trade_repository

router = APIRouter()


@router.get("", response_model=list[TradeEntryResponse])
def list_trades(current_user: CurrentUser = Depends(require_current_user)) -> list[TradeEntryResponse]:
    if use_file_persistence():
        return state_store.list_trades(current_user)

    return require_database_result(trade_repository.list_trades(current_user), "Trades")


@router.post("", response_model=TradeEntryResponse)
def create_trade(
    payload: TradeEntryCreate,
    current_user: CurrentUser = Depends(require_current_user),
) -> TradeEntryResponse:
    if use_file_persistence():
        trades = state_store.list_trades(current_user)
        item = TradeEntryResponse(id=f"trade-{len(trades) + 1}", **payload.model_dump())
        trades.append(item)
        state_store.save_trades(trades, current_user)
        return item

    return require_database_result(trade_repository.create_trade(payload, current_user), "Trade")


@router.put("/{trade_id}", response_model=TradeEntryResponse)
def update_trade(
    trade_id: str,
    payload: TradeEntryUpdate,
    current_user: CurrentUser = Depends(require_current_user),
) -> TradeEntryResponse:
    if use_file_persistence():
        trades = state_store.list_trades(current_user)
        for idx, trade in enumerate(trades):
            if trade.id == trade_id:
                updated = trade.model_copy(update=payload.model_dump(exclude_unset=True))
                trades[idx] = updated
                state_store.save_trades(trades, current_user)
                return updated
        raise HTTPException(status_code=404, detail="Trade not found")

    updated = trade_repository.update_trade(trade_id, payload, current_user)
    if updated is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return updated


@router.delete("/{trade_id}")
def delete_trade(
    trade_id: str,
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, str]:
    if use_file_persistence():
        trades = state_store.list_trades(current_user)
        filtered = [trade for trade in trades if trade.id != trade_id]
        if len(filtered) == len(trades):
            raise HTTPException(status_code=404, detail="Trade not found")
        state_store.save_trades(filtered, current_user)
        return {"deleted": trade_id}

    deleted = trade_repository.delete_trade(trade_id, current_user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trade not found")
    return {"deleted": trade_id}


@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_current_user),
) -> TradeImportResponse:
    preview_rows, errors, rows_received = parse_trade_csv(await file.read())
    imported_count = 0

    if use_file_persistence():
        existing_trades = state_store.list_trades(current_user)
        next_id = len(existing_trades) + 1
        created = []
        for row in preview_rows:
            created.append(TradeEntryResponse(id=f"trade-{next_id}", **row.trade.model_dump()))
            next_id += 1
            imported_count += 1

        if created:
            state_store.save_trades(existing_trades + created, current_user)
    else:
        for row in preview_rows:
            require_database_result(trade_repository.create_trade(row.trade, current_user), "Trade import")
            imported_count += 1

    return TradeImportResponse(
        file_name=file.filename or "upload.csv",
        rows_received=rows_received,
        imported_count=imported_count,
        rejected_count=len(errors),
        preview=preview_rows[:5],
        errors=errors[:10],
    )
