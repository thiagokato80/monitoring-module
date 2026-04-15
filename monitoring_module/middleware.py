# monitoring_module/middleware.py
import threading
import traceback
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from monitoring_module.config import MonitoringConfig
from monitoring_module.webhook import send_event

MONITORING_PATHS_PREFIX = ("/health", "/monitoring")


class MaintenanceMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, config: MonitoringConfig):
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next):
        if self.config.maintenance_mode:
            path = request.url.path
            # /health and /monitoring/* always pass through
            if not any(path == p or path.startswith(p + "/") for p in MONITORING_PATHS_PREFIX):
                return JSONResponse(
                    status_code=503,
                    content={"detail": self.config.maintenance_message},
                )
        return await call_next(request)


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, config: MonitoringConfig):
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
        except Exception as exc:
            tb = traceback.format_exc()
            # Include only app frames (skip third-party libs)
            app_frames = [
                line for line in tb.splitlines()
                if "site-packages" not in line and "venv" not in line
            ]
            self._send_error_event(
                request=request,
                status_code=500,
                error_type=type(exc).__name__,
                stack_trace="\n".join(app_frames),
            )
            return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

        if response.status_code >= 500:
            self._send_error_event(
                request=request,
                status_code=response.status_code,
                error_type="HTTP5xxResponse",
                stack_trace="",
            )
        return response

    def _send_error_event(self, request: Request, status_code: int, error_type: str, stack_trace: str):
        if not self.config.hub_url:
            return
        event = {
            "app_id": self.config.app_id,
            "event_type": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tier": self.config.tier,
            "payload": {
                "path": str(request.url.path),
                "method": request.method,
                "status_code": status_code,
                "error_type": error_type,
                "stack_trace": stack_trace,
                # NEVER include: request body, auth headers, user data
            },
        }
        t = threading.Thread(
            target=send_event,
            args=(event, self.config.hub_url, self.config.app_id, self.config.secret),
            daemon=True,
        )
        t.start()
