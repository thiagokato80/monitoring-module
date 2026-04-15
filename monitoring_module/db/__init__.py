# monitoring_module/db/__init__.py
from monitoring_module.config import MonitoringConfig
from monitoring_module.db.base import DBAdapter


def get_db_adapter(config: MonitoringConfig) -> DBAdapter | None:
    if config.tier < 2 or not config.db_provider:
        return None
    if config.db_provider == "supabase":
        from monitoring_module.db.supabase_adapter import SupabaseAdapter
        return SupabaseAdapter(config.database_url)
    return None
