# monitoring_module/db/supabase_adapter.py
import time
from monitoring_module.db.base import DBAdapter


class SupabaseAdapter(DBAdapter):
    def __init__(self, database_url: str):
        self._url = database_url

    def check(self) -> dict:
        try:
            import psycopg2
            start = time.time()
            conn = psycopg2.connect(self._url, connect_timeout=3)
            conn.cursor().execute("SELECT 1")
            conn.close()
            return {"status": "ok", "latency_ms": int((time.time() - start) * 1000)}
        except Exception:
            return {"status": "error", "latency_ms": None}
