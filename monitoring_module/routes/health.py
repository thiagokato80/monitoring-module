# monitoring_module/routes/health.py
import time
from fastapi import APIRouter
from monitoring_module.config import MonitoringConfig
from monitoring_module.db import get_db_adapter


def make_health_router(config: MonitoringConfig) -> APIRouter:
    router = APIRouter()
    start_time = time.time()          # per-router instance, not module-global
    db_adapter = get_db_adapter(config) if config.tier >= 2 else None

    @router.get("/health")
    async def health():
        response = {
            "status": "ok",
            "tier": config.tier,
            "app_id": config.app_id,
            "uptime_seconds": int(time.time() - start_time),
            "version": "1.0.1",
        }
        if db_adapter:
            db_result = db_adapter.check()
            response["db_status"] = db_result["status"]
            response["db_latency_ms"] = db_result["latency_ms"]
            if db_result["status"] != "ok":
                response["status"] = "degraded"
        return response

    return router
