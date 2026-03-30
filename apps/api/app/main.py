from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.health import get_live_status, get_readiness_report
from app.api.router import api_router
from app.core.config import settings


def create_application() -> FastAPI:
    app = FastAPI(
        title="TradeReviewDesk API",
        version="0.1.0",
        description="Workflow and review API for TradeReviewDesk MVP.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        return get_live_status()

    @app.get("/readyz", include_in_schema=False)
    def readyz() -> JSONResponse:
        status_code, payload = get_readiness_report()
        return JSONResponse(content=payload, status_code=status_code)

    return app


app = create_application()
