import json
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

from app.core.auth import LOCAL_DEMO_AUTH_PROVIDER_ID
from app.schemas.checklists import ChecklistRunResponse, ChecklistTemplateResponse
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.schemas.reports import ReportResponse
from app.schemas.trades import TradeEntryResponse
from app.schemas.watchlist import WatchlistResponse

if TYPE_CHECKING:
    from app.core.auth import CurrentUser

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SEED_PATH = DATA_DIR / "seed_state.json"
STORE_PATH = DATA_DIR / "store_state.json"
_LOCK = Lock()


def _ensure_store_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        STORE_PATH.write_text(SEED_PATH.read_text(encoding="utf-8"), encoding="utf-8")


def _load_state() -> dict[str, Any]:
    _ensure_store_file()
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))


def _save_state(state: dict[str, Any]) -> None:
    STORE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _with_state(mutator):
    with _LOCK:
        state = _load_state()
        result = mutator(state)
        _save_state(state)
        return result


def _read(mapper):
    with _LOCK:
        state = _load_state()
        return mapper(state)


def _make_seed_state(email: str | None = None, display_name: str | None = None) -> dict[str, Any]:
    seed_state = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    profile = deepcopy(seed_state["profile"])

    if email:
        profile["email"] = email
    if display_name:
        profile["display_name"] = display_name

    return {
        "profile": profile,
        "watchlists": deepcopy(seed_state["watchlists"]),
        "checklist_templates": deepcopy(seed_state["checklist_templates"]),
        "checklist_runs": deepcopy(seed_state["checklist_runs"]),
        "trades": deepcopy(seed_state["trades"]),
        "reports": deepcopy(seed_state["reports"]),
    }


def _is_legacy_demo_user(current_user: "CurrentUser | None") -> bool:
    return current_user is None or current_user.auth_provider_id == f"local:{LOCAL_DEMO_AUTH_PROVIDER_ID}"


def _get_scoped_state(state: dict[str, Any], current_user: "CurrentUser | None") -> dict[str, Any]:
    if _is_legacy_demo_user(current_user):
        return state

    scoped_state = state.setdefault("user_state", {})
    user_bucket = scoped_state.get(current_user.auth_provider_id)

    if user_bucket is None:
        user_bucket = _make_seed_state(email=current_user.email, display_name=current_user.display_name)
        scoped_state[current_user.auth_provider_id] = user_bucket

    profile = user_bucket.setdefault("profile", {})
    profile["email"] = current_user.email
    if current_user.display_name and not profile.get("display_name"):
        profile["display_name"] = current_user.display_name

    return user_bucket


def get_profile(current_user: "CurrentUser | None" = None) -> ProfileResponse:
    return _read(lambda state: ProfileResponse.model_validate(_get_scoped_state(state, current_user)["profile"]))


def update_profile(payload: ProfileUpdate, current_user: "CurrentUser | None" = None) -> ProfileResponse:
    def mutator(state: dict[str, Any]) -> ProfileResponse:
        scoped_state = _get_scoped_state(state, current_user)
        current = ProfileResponse.model_validate(scoped_state["profile"])
        updated = current.model_copy(update=payload.model_dump(exclude_unset=True))
        scoped_state["profile"] = updated.model_dump()
        return updated

    return _with_state(mutator)


def list_watchlists(current_user: "CurrentUser | None" = None) -> list[WatchlistResponse]:
    return _read(
        lambda state: [WatchlistResponse.model_validate(item) for item in _get_scoped_state(state, current_user)["watchlists"]]
    )


def save_watchlists(items: list[WatchlistResponse], current_user: "CurrentUser | None" = None) -> list[WatchlistResponse]:
    def mutator(state: dict[str, Any]) -> list[WatchlistResponse]:
        scoped_state = _get_scoped_state(state, current_user)
        scoped_state["watchlists"] = [item.model_dump() for item in items]
        return items

    return _with_state(mutator)


def list_checklist_templates(current_user: "CurrentUser | None" = None) -> list[ChecklistTemplateResponse]:
    return _read(
        lambda state: [
            ChecklistTemplateResponse.model_validate(item)
            for item in _get_scoped_state(state, current_user)["checklist_templates"]
        ]
    )


def save_checklist_templates(
    items: list[ChecklistTemplateResponse],
    current_user: "CurrentUser | None" = None,
) -> list[ChecklistTemplateResponse]:
    def mutator(state: dict[str, Any]) -> list[ChecklistTemplateResponse]:
        scoped_state = _get_scoped_state(state, current_user)
        scoped_state["checklist_templates"] = [item.model_dump() for item in items]
        return items

    return _with_state(mutator)


def list_checklist_runs(current_user: "CurrentUser | None" = None) -> list[ChecklistRunResponse]:
    return _read(
        lambda state: [ChecklistRunResponse.model_validate(item) for item in _get_scoped_state(state, current_user)["checklist_runs"]]
    )


def save_checklist_runs(
    items: list[ChecklistRunResponse],
    current_user: "CurrentUser | None" = None,
) -> list[ChecklistRunResponse]:
    def mutator(state: dict[str, Any]) -> list[ChecklistRunResponse]:
        scoped_state = _get_scoped_state(state, current_user)
        scoped_state["checklist_runs"] = [item.model_dump() for item in items]
        return items

    return _with_state(mutator)


def list_trades(current_user: "CurrentUser | None" = None) -> list[TradeEntryResponse]:
    return _read(
        lambda state: [TradeEntryResponse.model_validate(item) for item in _get_scoped_state(state, current_user)["trades"]]
    )


def save_trades(items: list[TradeEntryResponse], current_user: "CurrentUser | None" = None) -> list[TradeEntryResponse]:
    def mutator(state: dict[str, Any]) -> list[TradeEntryResponse]:
        scoped_state = _get_scoped_state(state, current_user)
        scoped_state["trades"] = [item.model_dump() for item in items]
        return items

    return _with_state(mutator)


def list_reports(current_user: "CurrentUser | None" = None) -> list[ReportResponse]:
    return _read(
        lambda state: [ReportResponse.model_validate(item) for item in _get_scoped_state(state, current_user)["reports"]]
    )


def save_reports(items: list[ReportResponse], current_user: "CurrentUser | None" = None) -> list[ReportResponse]:
    def mutator(state: dict[str, Any]) -> list[ReportResponse]:
        scoped_state = _get_scoped_state(state, current_user)
        scoped_state["reports"] = [item.model_dump() for item in items]
        return items

    return _with_state(mutator)


def reset_state_from_seed() -> None:
    with _LOCK:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        STORE_PATH.write_text(SEED_PATH.read_text(encoding="utf-8"), encoding="utf-8")


def get_store_path() -> Path:
    _ensure_store_file()
    return STORE_PATH


def get_seed_path() -> Path:
    return SEED_PATH
