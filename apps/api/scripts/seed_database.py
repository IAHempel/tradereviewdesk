from argparse import ArgumentParser
from pathlib import Path
import sys

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.auth import CurrentUser, LOCAL_DEMO_AUTH_PROVIDER_ID
from app.db.session import SessionLocal
from app.models.user import User
from app.schemas.checklists import ChecklistItemResponse, ChecklistRunCreate, ChecklistTemplateCreate
from app.schemas.profile import ProfileUpdate
from app.schemas.trades import TradeEntryCreate
from app.schemas.watchlist import SymbolCreate, WatchlistCreate
from app.services import (
    billing_service,
    checklist_repository,
    profile_repository,
    report_repository,
    state_store,
    trade_repository,
    watchlist_repository,
)


def build_demo_user() -> CurrentUser:
    profile = state_store.get_profile()
    return CurrentUser(
        auth_provider="local",
        auth_provider_user_id=LOCAL_DEMO_AUTH_PROVIDER_ID,
        auth_provider_id=f"local:{LOCAL_DEMO_AUTH_PROVIDER_ID}",
        email=profile.email,
        display_name=profile.display_name,
    )


def clear_demo_user(current_user: CurrentUser) -> None:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.auth_provider_id == current_user.auth_provider_id))
        if user is not None:
            session.delete(user)
            session.commit()


def seed_database(reset_demo_user: bool) -> dict[str, int]:
    state_store.reset_state_from_seed()
    current_user = build_demo_user()

    if reset_demo_user:
        clear_demo_user(current_user)

    profile = state_store.get_profile()
    profile_repository.update_profile(
        ProfileUpdate(
            display_name=profile.display_name,
            trading_style=profile.trading_style,
            pain_points=profile.pain_points,
            broker_platform=profile.broker_platform,
            onboarding_completed=profile.onboarding_completed,
        ),
        current_user,
    )
    billing_service.get_subscription(current_user)

    watchlist_count = 0
    symbol_count = 0
    for watchlist in state_store.list_watchlists():
        created_watchlist = watchlist_repository.create_watchlist(
            WatchlistCreate(name=watchlist.name, is_default=watchlist.is_default),
            current_user,
        )
        if created_watchlist is None:
            continue
        watchlist_count += 1
        for symbol in watchlist.symbols:
            created_watchlist = watchlist_repository.create_symbol(
                created_watchlist.id,
                SymbolCreate(symbol=symbol.symbol, notes=symbol.notes),
                current_user,
            )
            if created_watchlist is not None:
                symbol_count += 1

    template_id_map: dict[str, str] = {}
    template_count = 0
    for template in state_store.list_checklist_templates():
        created_template = checklist_repository.create_template(
            ChecklistTemplateCreate(
                name=template.name,
                description=template.description,
                is_default=template.is_default,
                items=[
                    ChecklistItemResponse(
                        id=item.id,
                        label=item.label,
                        description=item.description,
                        is_required=item.is_required,
                        display_order=item.display_order,
                    )
                    for item in template.items
                ],
            ),
            current_user,
        )
        if created_template is None:
            continue
        template_id_map[template.id] = created_template.id
        template_count += 1

    run_count = 0
    for run in state_store.list_checklist_runs():
        created_run = checklist_repository.create_run(
            ChecklistRunCreate(
                template_id=template_id_map.get(run.template_id),
                session_date=run.session_date,
                symbol=run.symbol,
                setup_tag=run.setup_tag,
                reason_for_entry=run.reason_for_entry,
                confidence_score=run.confidence_score,
                items=run.items,
            ),
            current_user,
        )
        if created_run is not None:
            run_count += 1

    trade_count = 0
    for trade in state_store.list_trades():
        created_trade = trade_repository.create_trade(
            TradeEntryCreate(**trade.model_dump(exclude={"id"})),
            current_user,
        )
        if created_trade is not None:
            trade_count += 1

    report_count = 0
    for report in state_store.list_reports():
        created_report = report_repository.save_report(
            report.model_copy(update={"id": "seed-placeholder"}),
            current_user,
            report_job_id=None,
            raw_model_output=None,
        )
        if created_report is not None:
            report_count += 1

    return {
        "watchlists": watchlist_count,
        "symbols": symbol_count,
        "templates": template_count,
        "runs": run_count,
        "trades": trade_count,
        "reports": report_count,
    }


def main() -> None:
    parser = ArgumentParser(description="Seed the TradeReviewDesk database from the local seed JSON.")
    parser.add_argument(
        "--reset-demo-user",
        action="store_true",
        help="Delete and recreate the local demo user before seeding.",
    )
    args = parser.parse_args()

    counts = seed_database(reset_demo_user=args.reset_demo_user)
    print("Database seed complete.")
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
