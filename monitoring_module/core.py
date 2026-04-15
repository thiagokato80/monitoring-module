# monitoring_module/core.py
from fastapi import FastAPI
from monitoring_module.config import MonitoringConfig
from monitoring_module.middleware import ErrorLoggingMiddleware, MaintenanceMiddleware
from monitoring_module.routes.health import make_health_router
from monitoring_module.routes.monitoring import make_monitoring_router


class MonitoringModule:
    """
    Ponto de entrada único. Registra middlewares e routers
    condicionalmente ao tier configurado no .env.

    Uso:
        app = FastAPI()
        MonitoringModule(app)
    """

    def __init__(self, app: FastAPI):
        self.config = MonitoringConfig.from_env()
        self._register(app)

    def _register(self, app: FastAPI):
        # Middlewares (order: Maintenance before ErrorLogging in add_middleware call)
        app.add_middleware(ErrorLoggingMiddleware, config=self.config)
        app.add_middleware(MaintenanceMiddleware, config=self.config)

        # Routers
        app.include_router(make_health_router(self.config))
        app.include_router(make_monitoring_router(self.config))
