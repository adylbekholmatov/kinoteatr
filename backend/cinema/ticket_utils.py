import hashlib
import hmac

from django.conf import settings


def sign_booking_code(booking_code: str) -> str:
    """HMAC-подпись кода брони — защита от подделки QR."""
    digest = hmac.new(
        settings.SECRET_KEY.encode(),
        booking_code.encode(),
        hashlib.sha256,
    ).hexdigest()
    return digest[:16]


def build_qr_payload(booking_code: str) -> str:
    """Содержимое QR-кода: BAYEL:<код>:<подпись>."""
    return f'BAYEL:{booking_code}:{sign_booking_code(booking_code)}'


def parse_qr_payload(payload: str):
    """Разбирает QR и проверяет подпись. Возвращает код брони или None."""
    parts = payload.strip().split(':')
    if len(parts) != 3 or parts[0] != 'BAYEL':
        return None

    _, booking_code, signature = parts
    if not hmac.compare_digest(signature, sign_booking_code(booking_code)):
        return None

    return booking_code
