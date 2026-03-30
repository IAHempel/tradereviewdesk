from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.db.session import check_database_connection

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return get_live_status()


@router.get("/ready")
def readiness_check() -> JSONResponse:
    status_code, payload = get_readiness_report()
    return JSONResponse(content=payload, status_code=status_code)


def get_live_status() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "tradenoc-api",
        "environment": settings.app_env,
    }


def get_readiness_report() -> tuple[int, dict[str, object]]:
    database_status = {"status": "skipped"}

    if settings.persistence_mode == "database":
        database_ok, database_error = check_database_connection()
        database_status = {
            "status": "ok" if database_ok else "error",
            "mode": settings.persistence_mode,
        }

        if database_error:
            database_status["error"] = database_error
    else:
        database_ok = True
        database_status = {
            "status": "ok",
            "mode": settings.persistence_mode,
        }

    redis_status = check_redis_connection()
    is_ready = database_ok

    payload = {
        "status": "ready" if is_ready else "not_ready",
        "service": "tradenoc-api",
        "environment": settings.app_env,
        "dependencies": {
            "database": database_status,
            "redis": redis_status,
        },
    }
    return (200 if is_ready else 503), payload


def check_redis_connection() -> dict[str, str]:
    if not settings.redis_url:
        return {"status": "disabled"}

    client = Redis.from_url(settings.redis_url)

    try:
        client.ping()
        return {"status": "ok"}
    except RedisError as exc:
        return {"status": "error", "error": exc.__class__.__name__}
    finally:
        client.close()
