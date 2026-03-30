from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import CurrentUser, require_current_user
from app.core.persistence import require_database_result, use_file_persistence
from app.schemas.watchlist import (
    SymbolCreate,
    SymbolUpdate,
    WatchlistCreate,
    WatchlistResponse,
    WatchlistSymbolResponse,
    WatchlistUpdate,
)
from app.services import state_store, watchlist_repository

router = APIRouter()


@router.get("", response_model=list[WatchlistResponse])
def list_watchlists(current_user: CurrentUser = Depends(require_current_user)) -> list[WatchlistResponse]:
    if use_file_persistence():
        return state_store.list_watchlists(current_user)

    return require_database_result(watchlist_repository.list_watchlists(current_user), "Watchlists")


@router.post("", response_model=WatchlistResponse)
def create_watchlist(
    payload: WatchlistCreate,
    current_user: CurrentUser = Depends(require_current_user),
) -> WatchlistResponse:
    if use_file_persistence():
        watchlists = state_store.list_watchlists(current_user)
        item = WatchlistResponse(id=f"watchlist-{len(watchlists) + 1}", symbols=[], **payload.model_dump())
        watchlists.append(item)
        state_store.save_watchlists(watchlists, current_user)
        return item

    return require_database_result(watchlist_repository.create_watchlist(payload, current_user), "Watchlist")


@router.put("/{watchlist_id}", response_model=WatchlistResponse)
def update_watchlist(
    watchlist_id: str,
    payload: WatchlistUpdate,
    current_user: CurrentUser = Depends(require_current_user),
) -> WatchlistResponse:
    if use_file_persistence():
        watchlists = state_store.list_watchlists(current_user)
        for idx, watchlist in enumerate(watchlists):
            if watchlist.id == watchlist_id:
                updated = watchlist.model_copy(update=payload.model_dump(exclude_unset=True))
                watchlists[idx] = updated
                state_store.save_watchlists(watchlists, current_user)
                return updated
        raise HTTPException(status_code=404, detail="Watchlist not found")

    updated = watchlist_repository.update_watchlist(watchlist_id, payload, current_user)
    if updated is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return updated


@router.delete("/{watchlist_id}")
def delete_watchlist(
    watchlist_id: str,
    _current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, str]:
    return {"deleted": watchlist_id}


@router.post("/{watchlist_id}/symbols", response_model=WatchlistResponse)
def create_symbol(
    watchlist_id: str,
    payload: SymbolCreate,
    current_user: CurrentUser = Depends(require_current_user),
) -> WatchlistResponse:
    if use_file_persistence():
        watchlists = state_store.list_watchlists(current_user)
        for idx, watchlist in enumerate(watchlists):
            if watchlist.id == watchlist_id:
                symbols = list(watchlist.symbols)
                symbols.append(
                    WatchlistSymbolResponse(
                        id=payload.symbol.lower(),
                        symbol=payload.symbol,
                        notes=payload.notes,
                        display_order=len(symbols) + 1,
                    )
                )
                updated = watchlist.model_copy(update={"symbols": symbols})
                watchlists[idx] = updated
                state_store.save_watchlists(watchlists, current_user)
                return updated
        raise HTTPException(status_code=404, detail="Watchlist not found")

    updated = watchlist_repository.create_symbol(watchlist_id, payload, current_user)
    if updated is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return updated


@router.put("/{watchlist_id}/symbols/{symbol_id}", response_model=WatchlistResponse)
def update_symbol(
    watchlist_id: str,
    symbol_id: str,
    payload: SymbolUpdate,
    current_user: CurrentUser = Depends(require_current_user),
) -> WatchlistResponse:
    if use_file_persistence():
        watchlists = state_store.list_watchlists(current_user)
        for idx, watchlist in enumerate(watchlists):
            if watchlist.id != watchlist_id:
                continue
            symbols = []
            found = False
            for symbol in watchlist.symbols:
                if symbol.id == symbol_id:
                    symbols.append(symbol.model_copy(update={"notes": payload.notes}))
                    found = True
                else:
                    symbols.append(symbol)
            if not found:
                raise HTTPException(status_code=404, detail="Watchlist symbol not found")
            updated = watchlist.model_copy(update={"symbols": symbols})
            watchlists[idx] = updated
            state_store.save_watchlists(watchlists, current_user)
            return updated
        raise HTTPException(status_code=404, detail="Watchlist not found")

    updated = watchlist_repository.update_symbol(watchlist_id, symbol_id, payload, current_user)
    if updated is None:
        raise HTTPException(status_code=404, detail="Watchlist symbol not found")
    return updated


@router.delete("/{watchlist_id}/symbols/{symbol_id}")
def delete_symbol(
    watchlist_id: str,
    symbol_id: str,
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, str]:
    if use_file_persistence():
        watchlists = state_store.list_watchlists(current_user)
        for idx, watchlist in enumerate(watchlists):
            if watchlist.id != watchlist_id:
                continue
            symbols = [symbol for symbol in watchlist.symbols if symbol.id != symbol_id]
            if len(symbols) == len(watchlist.symbols):
                raise HTTPException(status_code=404, detail="Watchlist symbol not found")
            updated = watchlist.model_copy(update={"symbols": symbols})
            watchlists[idx] = updated
            state_store.save_watchlists(watchlists, current_user)
            return {"deleted": symbol_id, "watchlist_id": watchlist_id}
        raise HTTPException(status_code=404, detail="Watchlist not found")

    deleted = watchlist_repository.delete_symbol(watchlist_id, symbol_id, current_user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watchlist symbol not found")
    return {"deleted": symbol_id, "watchlist_id": watchlist_id}
