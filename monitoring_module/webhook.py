# monitoring_module/webhook.py
import hashlib
import hmac
import json
import time


def send_event(event: dict, hub_url: str, app_id: str, secret: str) -> None:
    """
    Envia evento ao FreelancerHQ Health Hub via POST autenticado.
    Fire-and-forget — disparado em thread separada para não bloquear a app.
    """
    if not hub_url or not secret:
        return

    import threading
    thread = threading.Thread(
        target=_safe_post,
        args=(event, hub_url, app_id, secret),
        daemon=True
    )
    thread.start()


def _safe_post(event: dict, hub_url: str, app_id: str, secret: str) -> None:
    import httpx
    try:
        body = json.dumps(event, default=str).encode()
        ts = str(int(time.time()))
        body_hash = hashlib.sha256(body).hexdigest()
        message = f"{app_id}:{ts}:{body_hash}"
        signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Monitoring-App-Id": app_id,
            "X-Monitoring-Timestamp": ts,
            "X-Monitoring-Signature": signature,
        }

        with httpx.Client(timeout=5.0) as client:
            client.post(hub_url, content=body, headers=headers)
    except Exception:
        pass  # Falhas no monitoramento nunca devem quebrar a app principal
