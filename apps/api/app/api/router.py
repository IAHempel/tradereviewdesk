from fastapi import APIRouter

from app.api.routes import billing, checklist_runs, checklist_templates, health, profile, reports, trades, watchlists

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(watchlists.router, prefix="/watchlists", tags=["watchlists"])
api_router.include_router(
    checklist_templates.router,
    prefix="/checklist-templates",
    tags=["checklist-templates"],
)
api_router.include_router(checklist_runs.router, prefix="/checklist-runs", tags=["checklist-runs"])
api_router.include_router(trades.router, prefix="/trades", tags=["trades"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
