from typing import Any, Literal

from pydantic import BaseModel, Field


AssetType = Literal["stock", "option", "other"]
TradeSide = Literal["long", "short", "call", "put", "other"]
SourceType = Literal["manual", "csv_upload"]


class TradeEntryCreate(BaseModel):
    trade_date: str
    symbol: str
    asset_type: AssetType
    side: TradeSide
    quantity: float | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    pnl: float | None = None
    fees: float | None = None
    tags: list[str] = []
    notes: str | None = None
    source_type: SourceType = "manual"


class TradeEntryUpdate(BaseModel):
    trade_date: str | None = None
    symbol: str | None = None
    asset_type: AssetType | None = None
    side: TradeSide | None = None
    quantity: float | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    pnl: float | None = None
    fees: float | None = None
    notes: str | None = None
    tags: list[str] | None = None


class TradeEntryResponse(TradeEntryCreate):
    id: str


class TradeImportPreviewRow(BaseModel):
    row_number: int
    trade: TradeEntryCreate


class TradeImportError(BaseModel):
    row_number: int
    message: str
    raw_row: dict[str, Any]


class TradeImportResponse(BaseModel):
    file_name: str
    rows_received: int
    imported_count: int
    rejected_count: int
    preview: list[TradeImportPreviewRow] = Field(default_factory=list)
    errors: list[TradeImportError] = Field(default_factory=list)
