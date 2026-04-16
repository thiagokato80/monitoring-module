# monitoring_module/middleware.py
import re
import threading
import traceback
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from monitoring_module.config import MonitoringConfig
from monitoring_module.webhook import send_event

MONITORING_PATHS_PREFIX = ("/health", "/monitoring")

# Padrões que identificam dados pessoais/sensíveis nos paths de URL.
# UUIDs e IDs numéricos são substituídos por {id} antes de sair para o hub.
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)
_NUMERIC_ID_RE = re.compile(r"(?<=/)\d{4,}(?=/|$)")

# Linhas de stack trace que podem conter dados de negócio.
# Filtradas para reduzir risco de vazar CPF, nome, e-mail etc. em strings de erro.
_SENSITIVE_PATTERNS = re.compile(
    r"(cpf|cnpj|email|senha|password|token|secret|nome|name|phone|telefone)",
    re.IGNORECASE,
)

# Limite de caracteres por linha de stack trace enviada ao hub.
_STACK_LINE_MAX = 200
# Máximo de linhas de stack trace enviadas ao hub.
_STACK_LINES_MAX = 30


def sanitize_path(path: str) -> str:
    """
    Substitui UUIDs e IDs numéricos longos por {id} no path da URL.
    /api/v1/usuarios/f47ac10b-... → /api/v1/usuarios/{id}
    /api/v1/processos/12345/itens → /api/v1/processos/{id}/itens
    """
    path = _UUID_RE.sub("{id}", path)
    path = _NUMERIC_ID_RE.sub("{id}", path)
    return path


def sanitize_stack(stack: str) -> str:
    """
    Remove ou trunca linhas de stack trace que possam conter dados pessoais.
    Regras:
    - Remove linhas que contêm palavras-chave sensíveis (cpf, email, senha etc.)
    - Trunca cada linha em _STACK_LINE_MAX caracteres
    - Limita a _STACK_LINES_MAX linhas no total
    """
    lines = stack.splitlines()
    cleaned = []
    for line in lines:
        if _SENSITIVE_PATTERNS.search(line):
            cleaned.append("[linha removida — possível dado sensível]")
        else:
            cleaned.append(line[:_STACK_LINE_MAX])
    return "\n".join(cleaned[:_STACK_LINES_MAX])


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
                "path": sanitize_path(str(request.url.path)),  # UUIDs → {id}
                "method": request.method,
                "status_code": status_code,
                "error_type": error_type,
                "stack_trace": sanitize_stack(stack_trace),    # linhas sensíveis removidas
                # NEVER include: request body, auth headers, user data
            },
        }
        t = threading.Thread(
            target=send_event,
            args=(event, self.config.hub_url, self.config.app_id, self.config.secret),
            daemon=True,
        )
        t.start()
