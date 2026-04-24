# monitoring_module/security.py
import hashlib
import hmac
import time


def verify_hmac_with_secret(
    app_id: str,
    timestamp: str,
    signature: str,
    body: bytes,
    secret: str,
) -> bool:
    """
    Verifica HMAC-SHA256.
    Retorna False se timestamp fora de ±300s, ou assinatura inválida.
    Mensagem assinada: "{app_id}:{timestamp}:{sha256(body)}"
    """
    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        return False

    if abs(time.time() - ts) > 300:
        return False

    body_hash = hashlib.sha256(body).hexdigest()
    message = f"{app_id}:{timestamp}:{body_hash}"
    expected = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    return hmac.compare_digest(expected, signature)


def is_ip_allowed(client_ip: str, allowed_ips: list[str]) -> bool:
    """
    Retorna True se allowed_ips estiver vazio (desabilita whitelist de IP).
    Caso contrário, verifica se o IP está na lista.
    """
    if not allowed_ips:
        return True
    return client_ip in allowed_ips
