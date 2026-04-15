# monitoring_module/db/base.py
from abc import ABC, abstractmethod


class DBAdapter(ABC):
    @abstractmethod
    def check(self) -> dict:
        """
        Retorna {"status": "ok" | "error", "latency_ms": int | None}.
        Nunca lança exceção — captura internamente.
        """
        ...
