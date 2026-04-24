# monitoring_module/routes/monitoring.py
from fastapi import APIRouter, Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from monitoring_module.config import MonitoringConfig
from monitoring_module.security import verify_hmac_with_secret, is_ip_allowed

limiter = Limiter(key_func=get_remote_address)


def make_monitoring_router(config: MonitoringConfig) -> APIRouter:
    router = APIRouter()

    def _require_auth(request: Request, body: bytes = b""):
        client_ip = request.client.host if request.client else ""
        if not is_ip_allowed(client_ip, config.allowed_ips):
            raise HTTPException(403, "IP não autorizado")
        app_id = request.headers.get("X-Monitoring-App-Id", "")
        timestamp = request.headers.get("X-Monitoring-Timestamp", "")
        signature = request.headers.get("X-Monitoring-Signature", "")
        if not verify_hmac_with_secret(app_id, timestamp, signature, body, config.secret):
            raise HTTPException(403, "Assinatura inválida")

    @router.post("/ping")
    @limiter.limit("10/minute")
    async def ping(request: Request):
        _require_auth(request)
        return {"pong": True, "app_id": config.app_id}

    return router
