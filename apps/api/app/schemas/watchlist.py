from pydantic import BaseModel


class WatchlistSymbolResponse(BaseModel):
    id: str
    symbol: str
    notes: str | None = None
    display_order: int


class WatchlistCreate(BaseModel):
    name: str
    is_default: bool = False


class WatchlistUpdate(BaseModel):
    name: str | None = None
    is_default: bool | None = None


class SymbolCreate(BaseModel):
    symbol: str
    notes: str | None = None


class SymbolUpdate(BaseModel):
    notes: str | None = None


class WatchlistResponse(BaseModel):
    id: str
    name: str
    is_default: bool
    symbols: list[WatchlistSymbolResponse]
