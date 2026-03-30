from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.auth import CurrentUser
from app.core.persistence import use_file_persistence
from app.db.session import SessionLocal
from app.models.user import Watchlist, WatchlistSymbol
from app.schemas.watchlist import (
    SymbolCreate,
    SymbolUpdate,
    WatchlistCreate,
    WatchlistResponse,
    WatchlistSymbolResponse,
    WatchlistUpdate,
)
from app.services import state_store
from app.services.db_demo_context import get_or_create_current_user, with_db_fallback


def _to_response(watchlist: Watchlist) -> WatchlistResponse:
    symbols = sorted(watchlist.symbols, key=lambda item: item.display_order)
    return WatchlistResponse(
        id=watchlist.id,
        name=watchlist.name,
        is_default=watchlist.is_default,
        symbols=[
            WatchlistSymbolResponse(
                id=item.id,
                symbol=item.symbol,
                notes=item.notes,
                display_order=item.display_order,
            )
            for item in symbols
        ],
    )


def _seed_watchlists(session, user_id: str, current_user: CurrentUser) -> list[Watchlist]:
    seeded_watchlists: list[Watchlist] = []
    for watchlist in state_store.list_watchlists(current_user):
        db_watchlist = Watchlist(user_id=user_id, name=watchlist.name, is_default=watchlist.is_default)
        session.add(db_watchlist)
        session.flush()
        for symbol in watchlist.symbols:
            session.add(
                WatchlistSymbol(
                    watchlist_id=db_watchlist.id,
                    symbol=symbol.symbol,
                    notes=symbol.notes,
                    display_order=symbol.display_order,
                )
            )
        session.flush()
        session.refresh(db_watchlist)
        seeded_watchlists.append(db_watchlist)
    return seeded_watchlists


def list_watchlists(current_user: CurrentUser) -> list[WatchlistResponse] | None:
    def action() -> list[WatchlistResponse]:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            watchlists = list(
                session.scalars(
                    select(Watchlist)
                    .options(selectinload(Watchlist.symbols))
                    .where(Watchlist.user_id == user.id)
                    .order_by(Watchlist.created_at.asc())
                )
            )

            if not watchlists and use_file_persistence():
                watchlists = _seed_watchlists(session, user.id, current_user)
                session.commit()
                watchlists = list(
                    session.scalars(
                        select(Watchlist)
                        .options(selectinload(Watchlist.symbols))
                        .where(Watchlist.user_id == user.id)
                        .order_by(Watchlist.created_at.asc())
                    )
                )

            return [_to_response(item) for item in watchlists]

    return with_db_fallback(action)


def create_watchlist(payload: WatchlistCreate, current_user: CurrentUser) -> WatchlistResponse | None:
    def action() -> WatchlistResponse:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            existing_watchlists = list(session.scalars(select(Watchlist).where(Watchlist.user_id == user.id)))
            is_default = payload.is_default or not existing_watchlists
            if is_default:
                for item in existing_watchlists:
                    item.is_default = False
                    session.add(item)

            watchlist = Watchlist(user_id=user.id, name=payload.name, is_default=is_default)
            session.add(watchlist)
            session.commit()
            session.refresh(watchlist)
            return _to_response(watchlist)

    return with_db_fallback(action)


def update_watchlist(watchlist_id: str, payload: WatchlistUpdate, current_user: CurrentUser) -> WatchlistResponse | None:
    def action() -> WatchlistResponse | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            watchlist = session.scalar(
                select(Watchlist)
                .options(selectinload(Watchlist.symbols))
                .where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id)
            )
            if watchlist is None:
                return None

            if payload.name is not None:
                watchlist.name = payload.name
            if payload.is_default is not None:
                if payload.is_default:
                    for item in session.scalars(select(Watchlist).where(Watchlist.user_id == user.id, Watchlist.id != watchlist_id)):
                        item.is_default = False
                        session.add(item)
                    watchlist.is_default = True
                else:
                    has_other_default = session.scalar(
                        select(Watchlist.id).where(
                            Watchlist.user_id == user.id,
                            Watchlist.id != watchlist_id,
                            Watchlist.is_default.is_(True),
                        )
                    )
                    watchlist.is_default = bool(has_other_default)
                    if not watchlist.is_default:
                        replacement = session.scalar(
                            select(Watchlist)
                            .where(Watchlist.user_id == user.id, Watchlist.id != watchlist_id)
                            .order_by(Watchlist.created_at.asc())
                        )
                        if replacement is not None:
                            replacement.is_default = True
                            session.add(replacement)

            session.add(watchlist)
            session.commit()
            session.refresh(watchlist)
            return _to_response(watchlist)

    return with_db_fallback(action)


def create_symbol(watchlist_id: str, payload: SymbolCreate, current_user: CurrentUser) -> WatchlistResponse | None:
    def action() -> WatchlistResponse | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            watchlist = session.scalar(
                select(Watchlist)
                .options(selectinload(Watchlist.symbols))
                .where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id)
            )
            if watchlist is None:
                return None

            display_order = len(watchlist.symbols) + 1
            session.add(
                WatchlistSymbol(
                    watchlist_id=watchlist.id,
                    symbol=payload.symbol,
                    notes=payload.notes,
                    display_order=display_order,
                )
            )
            session.commit()
            refreshed = session.scalar(
                select(Watchlist)
                .options(selectinload(Watchlist.symbols))
                .where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id)
            )
            return _to_response(refreshed) if refreshed is not None else None

    return with_db_fallback(action)


def update_symbol(
    watchlist_id: str,
    symbol_id: str,
    payload: SymbolUpdate,
    current_user: CurrentUser,
) -> WatchlistResponse | None:
    def action() -> WatchlistResponse | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            watchlist = session.scalar(
                select(Watchlist)
                .options(selectinload(Watchlist.symbols))
                .where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id)
            )
            if watchlist is None:
                return None

            symbol = next((item for item in watchlist.symbols if item.id == symbol_id), None)
            if symbol is None:
                return None

            symbol.notes = payload.notes
            session.add(symbol)
            session.commit()
            refreshed = session.scalar(
                select(Watchlist)
                .options(selectinload(Watchlist.symbols))
                .where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id)
            )
            return _to_response(refreshed) if refreshed is not None else None

    return with_db_fallback(action)


def delete_symbol(watchlist_id: str, symbol_id: str, current_user: CurrentUser) -> bool | None:
    def action() -> bool:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            symbol = session.scalar(
                select(WatchlistSymbol)
                .join(Watchlist, WatchlistSymbol.watchlist_id == Watchlist.id)
                .where(
                    WatchlistSymbol.id == symbol_id,
                    WatchlistSymbol.watchlist_id == watchlist_id,
                    Watchlist.user_id == user.id,
                )
            )
            if symbol is None:
                return False
            session.delete(symbol)
            session.commit()
            return True

    return with_db_fallback(action)


def delete_watchlist(watchlist_id: str, current_user: CurrentUser) -> bool | None:
    def action() -> bool:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            watchlist = session.scalar(
                select(Watchlist)
                .options(selectinload(Watchlist.symbols))
                .where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id)
            )
            if watchlist is None:
                return False

            was_default = watchlist.is_default
            session.delete(watchlist)
            session.flush()

            if was_default:
                replacement = session.scalar(
                    select(Watchlist)
                    .where(Watchlist.user_id == user.id)
                    .order_by(Watchlist.created_at.asc())
                )
                if replacement is not None:
                    replacement.is_default = True
                    session.add(replacement)

            session.commit()
            return True

    return with_db_fallback(action)
