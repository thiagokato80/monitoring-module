# monitoring_module/config.py
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MonitoringConfig:
    tier: int
    app_id: str
    secret_hash: str           # SHA-256 do MONITORING_SECRET gerado pelo cliente
    hub_url: str
    allowed_ips: list[str]     # vazio = bloqueia tudo
    db_provider: Optional[str] # supabase | firestore | postgres | mongodb | None
    database_url: Optional[str]
    maintenance_mode: bool
    maintenance_message: str

    @classmethod
    def from_env(cls) -> "MonitoringConfig":
        tier = int(os.getenv("MONITORING_TIER", "1"))
        app_id = os.getenv("MONITORING_APP_ID", "")
        secret_hash = os.getenv("MONITORING_SECRET_HASH", "")
        hub_url = os.getenv("MONITORING_HUB_URL", "")
        allowed_ips_raw = os.getenv("MONITORING_ALLOWED_IPS", "")
        allowed_ips = [ip.strip() for ip in allowed_ips_raw.split(",") if ip.strip()]
        db_provider = os.getenv("DB_PROVIDER") if tier >= 2 else None
        database_url = os.getenv("DATABASE_URL") if tier >= 2 else None
        maintenance_mode = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
        maintenance_message = os.getenv(
            "MAINTENANCE_MESSAGE", "Sistema em manutenção. Retorne em breve."
        )

        if not app_id:
            raise ValueError("MONITORING_APP_ID é obrigatório")
        if tier not in (1, 2, 3):
            raise ValueError("MONITORING_TIER deve ser 1, 2 ou 3")

        return cls(
            tier=tier,
            app_id=app_id,
            secret_hash=secret_hash,
            hub_url=hub_url,
            allowed_ips=allowed_ips,
            db_provider=db_provider,
            database_url=database_url,
            maintenance_mode=maintenance_mode,
            maintenance_message=maintenance_message,
        )
