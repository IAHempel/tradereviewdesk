from decimal import Decimal

from sqlalchemy import select

from app.core.auth import CurrentUser
from app.core.persistence import use_file_persistence
from app.db.session import SessionLocal
from app.models.trade import TradeEntry
from app.schemas.trades import TradeEntryCreate, TradeEntryResponse, TradeEntryUpdate
from app.services import state_store
from app.services.db_demo_context import get_or_create_current_user, with_db_fallback


def _as_float(value: Decimal | float | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _to_response(trade: TradeEntry) -> TradeEntryResponse:
    return TradeEntryResponse(
        id=trade.id,
        trade_date=str(trade.trade_date),
        symbol=trade.symbol,
        asset_type=trade.asset_type,
        side=trade.side,
        quantity=_as_float(trade.quantity),
        entry_price=_as_float(trade.entry_price),
        exit_price=_as_float(trade.exit_price),
        pnl=_as_float(trade.pnl),
        fees=_as_float(trade.fees),
        tags=list(trade.tags or []),
        notes=trade.notes,
        source_type=trade.source_type,
    )


def _seed_trades(session, user_id: str, current_user: CurrentUser) -> None:
    for trade in state_store.list_trades(current_user):
        session.add(
            TradeEntry(
                user_id=user_id,
                trade_date=trade.trade_date,
                symbol=trade.symbol,
                asset_type=trade.asset_type,
                side=trade.side,
                quantity=trade.quantity,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                pnl=trade.pnl,
                fees=trade.fees,
                tags=trade.tags,
                notes=trade.notes,
                source_type=trade.source_type,
            )
        )


def list_trades(current_user: CurrentUser) -> list[TradeEntryResponse] | None:
    def action() -> list[TradeEntryResponse]:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            trades = list(
                session.scalars(
                    select(TradeEntry)
                    .where(TradeEntry.user_id == user.id)
                    .order_by(TradeEntry.trade_date.desc(), TradeEntry.created_at.desc())
                )
            )
            if not trades and use_file_persistence():
                _seed_trades(session, user.id, current_user)
                session.commit()
                trades = list(
                    session.scalars(
                        select(TradeEntry)
                        .where(TradeEntry.user_id == user.id)
                        .order_by(TradeEntry.trade_date.desc(), TradeEntry.created_at.desc())
                    )
                )
            return [_to_response(trade) for trade in trades]

    return with_db_fallback(action)


def create_trade(payload: TradeEntryCreate, current_user: CurrentUser) -> TradeEntryResponse | None:
    def action() -> TradeEntryResponse:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            trade = TradeEntry(
                user_id=user.id,
                trade_date=payload.trade_date,
                symbol=payload.symbol,
                asset_type=payload.asset_type,
                side=payload.side,
                quantity=payload.quantity,
                entry_price=payload.entry_price,
                exit_price=payload.exit_price,
                pnl=payload.pnl,
                fees=payload.fees,
                tags=payload.tags,
                notes=payload.notes,
                source_type=payload.source_type,
            )
            session.add(trade)
            session.commit()
            session.refresh(trade)
            return _to_response(trade)

    return with_db_fallback(action)


def update_trade(trade_id: str, payload: TradeEntryUpdate, current_user: CurrentUser) -> TradeEntryResponse | None:
    def action() -> TradeEntryResponse | None:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            trade = session.scalar(select(TradeEntry).where(TradeEntry.id == trade_id, TradeEntry.user_id == user.id))
            if trade is None:
                return None

            if payload.trade_date is not None:
                trade.trade_date = payload.trade_date
            if payload.symbol is not None:
                trade.symbol = payload.symbol
            if payload.asset_type is not None:
                trade.asset_type = payload.asset_type
            if payload.side is not None:
                trade.side = payload.side
            if payload.quantity is not None:
                trade.quantity = payload.quantity
            if payload.entry_price is not None:
                trade.entry_price = payload.entry_price
            if payload.exit_price is not None:
                trade.exit_price = payload.exit_price
            if payload.pnl is not None:
                trade.pnl = payload.pnl
            if payload.fees is not None:
                trade.fees = payload.fees
            if payload.notes is not None:
                trade.notes = payload.notes
            if payload.tags is not None:
                trade.tags = payload.tags

            session.add(trade)
            session.commit()
            session.refresh(trade)
            return _to_response(trade)

    return with_db_fallback(action)


def delete_trade(trade_id: str, current_user: CurrentUser) -> bool | None:
    def action() -> bool:
        with SessionLocal() as session:
            user = get_or_create_current_user(session, current_user)
            trade = session.scalar(select(TradeEntry).where(TradeEntry.id == trade_id, TradeEntry.user_id == user.id))
            if trade is None:
                return False
            session.delete(trade)
            session.commit()
            return True

    return with_db_fallback(action)
