# monitoring_module/core.py
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from monitoring_module.config import MonitoringConfig
from monitoring_module.middleware import ErrorLoggingMiddleware, MaintenanceMiddleware
from monitoring_module.routes.health import make_health_router
from monitoring_module.routes.monitoring import make_monitoring_router, limiter


class MonitoringModule:
    """
    Ponto de entrada único. Registra middlewares e routers
    condicionalmente ao tier configurado no .env.

    IMPORTANT: Must be called before the first request is processed.
    FastAPI/Starlette freezes the middleware stack on the first request —
    calling MonitoringModule(app) afterwards will silently have no effect.

    Uso:
        app = FastAPI()
        MonitoringModule(app)   # before any requests
    """

    def __init__(self, app: FastAPI):
        self.config = MonitoringConfig.from_env()
        self._register(app)

    def _register(self, app: FastAPI):
        # Rate limiter — deve ser registrado antes dos middlewares
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        # Starlette applies middleware in reverse add order.
        # MaintenanceMiddleware is added first → runs innermost (after error logging).
        # ErrorLoggingMiddleware is added last → runs outermost (wraps all layers).
        app.add_middleware(MaintenanceMiddleware, config=self.config)
        app.add_middleware(ErrorLoggingMiddleware, config=self.config)

        # Routers
        app.include_router(make_health_router(self.config))
        app.include_router(make_monitoring_router(self.config))
