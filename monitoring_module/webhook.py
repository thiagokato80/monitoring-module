# monitoring_module/webhook.py
import hashlib
import hmac
import json
import time


def send_event(event: dict, hub_url: str, app_id: str, secret: str) -> None:
    """
    Envia evento ao FreelancerHQ Health Hub via POST autenticado.
    Fire-and-forget — não bloqueia a resposta da aplicação.
    Falhas silenciosas (não devem impactar o usuário final).
    """
    if not hub_url or not secret:
        return

    body = _serialize(event)
    ts = str(int(time.time()))
    body_hash = hashlib.sha256(body).hexdigest()
    message = f"{app_id}:{ts}:{body_hash}"
    sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Monitoring-App-Id": app_id,
        "X-Monitoring-Timestamp": ts,
        "X-Monitoring-Signature": sig,
    }

    try:
        _blocking_post(hub_url, body, headers)
    except BaseException:
        pass  # fire-and-forget — never impacts the app


def _blocking_post(hub_url: str, body: bytes, headers: dict) -> None:
    import httpx
    with httpx.Client(timeout=5.0) as client:
        client.post(hub_url, content=body, headers=headers)


def _serialize(event: dict) -> bytes:
    return json.dumps(event, default=str).encode()
