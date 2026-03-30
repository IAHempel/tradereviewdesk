import csv
import io
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from app.schemas.trades import TradeEntryCreate, TradeImportError, TradeImportPreviewRow


FIELD_ALIASES = {
    "trade_date": {"trade_date", "date", "tradedate", "execution_date", "filled_at"},
    "symbol": {"symbol", "ticker", "underlying"},
    "asset_type": {"asset_type", "asset", "instrument_type", "security_type"},
    "side": {"side", "direction", "action", "position_side"},
    "quantity": {"quantity", "qty", "shares", "contracts", "size"},
    "entry_price": {"entry_price", "entry", "entryprice", "buy_price", "open_price"},
    "exit_price": {"exit_price", "exit", "exitprice", "sell_price", "close_price"},
    "pnl": {"pnl", "profit_loss", "realized_pnl", "net_pnl"},
    "fees": {"fees", "commission", "commissions", "fee"},
    "tags": {"tags", "setup_tags", "labels"},
    "notes": {"notes", "note", "comment", "comments", "memo"},
    "source_type": {"source_type", "source", "import_source"},
}

ASSET_TYPE_MAP = {
    "stock": "stock",
    "equity": "stock",
    "share": "stock",
    "shares": "stock",
    "option": "option",
    "options": "option",
    "other": "other",
}

SIDE_MAP = {
    "buy": "long",
    "long": "long",
    "sell": "short",
    "short": "short",
    "sell short": "short",
    "cover": "long",
    "call": "call",
    "put": "put",
    "other": "other",
}


def _canonicalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _pick_value(row: dict[str, str], field_name: str) -> str | None:
    aliases = FIELD_ALIASES[field_name]
    for key, value in row.items():
        if _canonicalize_header(key) in aliases:
            return value.strip() if isinstance(value, str) else value
    return None


def _parse_decimal(value: str | None) -> float | None:
    if value is None or value == "":
        return None

    normalized = value.replace("$", "").replace(",", "").strip()
    if normalized.startswith("(") and normalized.endswith(")"):
        normalized = f"-{normalized[1:-1]}"

    try:
        return float(Decimal(normalized))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid numeric value '{value}'.") from exc


def _parse_tags(value: str | None) -> list[str]:
    if value is None or value == "":
        return []

    normalized = value.replace("|", ",").replace(";", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _normalize_asset_type(value: str | None) -> str:
    if not value:
        return "stock"

    normalized = value.strip().lower()
    if normalized not in ASSET_TYPE_MAP:
        raise ValueError(f"Unsupported asset type '{value}'.")
    return ASSET_TYPE_MAP[normalized]


def _normalize_side(value: str | None) -> str:
    if not value:
        raise ValueError("Missing side/action column.")

    normalized = " ".join(value.strip().lower().split())
    if normalized not in SIDE_MAP:
        raise ValueError(f"Unsupported side '{value}'.")
    return SIDE_MAP[normalized]


def _build_trade(row: dict[str, str]) -> TradeEntryCreate:
    trade_date = _pick_value(row, "trade_date")
    symbol = _pick_value(row, "symbol")
    if not trade_date:
        raise ValueError("Missing trade date.")
    if not symbol:
        raise ValueError("Missing symbol.")

    payload = {
        "trade_date": trade_date,
        "symbol": symbol.upper(),
        "asset_type": _normalize_asset_type(_pick_value(row, "asset_type")),
        "side": _normalize_side(_pick_value(row, "side")),
        "quantity": _parse_decimal(_pick_value(row, "quantity")),
        "entry_price": _parse_decimal(_pick_value(row, "entry_price")),
        "exit_price": _parse_decimal(_pick_value(row, "exit_price")),
        "pnl": _parse_decimal(_pick_value(row, "pnl")),
        "fees": _parse_decimal(_pick_value(row, "fees")) or 0.0,
        "tags": _parse_tags(_pick_value(row, "tags")),
        "notes": _pick_value(row, "notes") or None,
        "source_type": "csv_upload",
    }

    try:
        return TradeEntryCreate.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(exc.errors()[0]["msg"]) from exc


def parse_trade_csv(data: bytes) -> tuple[list[TradeImportPreviewRow], list[TradeImportError], int]:
    if not data:
        return [], [TradeImportError(row_number=0, message="CSV file is empty.", raw_row={})], 0

    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        return [], [TradeImportError(row_number=0, message="CSV must be UTF-8 encoded.", raw_row={})], 0

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], [TradeImportError(row_number=0, message="CSV is missing a header row.", raw_row={})], 0

    preview: list[TradeImportPreviewRow] = []
    errors: list[TradeImportError] = []
    rows_received = 0

    for index, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue

        rows_received += 1

        try:
            trade = _build_trade(row)
        except ValueError as exc:
            errors.append(TradeImportError(row_number=index, message=str(exc), raw_row=dict(row)))
            continue

        preview.append(TradeImportPreviewRow(row_number=index, trade=trade))

    return preview, errors, rows_received
