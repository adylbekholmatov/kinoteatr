"""
Freedom Pay (freedompay.money) payment gateway integration.
Documentation: https://freedompay.money/documentation

API очень похож на Paybox — те же pg_* параметры, та же MD5 подпись.
Отличие только в URL и merchant credentials.
"""

import hashlib
import random
import string
import requests
import xml.etree.ElementTree as ET
from django.conf import settings


FREEDOM_PAY_API_URL = 'https://api.freedompay.money/payment.php'
_INIT_SCRIPT        = 'payment.php'
_CB_SCRIPT          = 'check_url.php'


# ── helpers ──────────────────────────────────────────────────────────────────

def _salt(n: int = 16) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


def _sig(script: str, params: dict, secret: str) -> str:
    """
    Freedom Pay MD5 signature:
    MD5( script_name ; pg_param_val1 ; pg_param_val2 ; ... ; secret_key )
    Параметры сортируются по ключу.
    """
    sorted_keys = sorted(k for k in params if k.startswith('pg_'))
    values      = [str(params[k]) for k in sorted_keys]
    raw         = script + ';' + ';'.join(values) + ';' + secret
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


# ── public API ───────────────────────────────────────────────────────────────

def create_payment(
    order_id:    str,
    amount,
    description: str,
    success_url: str,
    fail_url:    str,
    result_url:  str,
    user_phone:  str = '',
    user_email:  str = '',
) -> tuple[str, str]:
    """
    Создаёт платёж в Freedom Pay.

    Возвращает: (freedom_payment_id, redirect_url)
    Бросает Exception при ошибке Freedom Pay.
    """
    merchant_id = str(getattr(settings, 'FREEDOM_PAY_MERCHANT_ID', ''))
    secret      = getattr(settings, 'FREEDOM_PAY_SECRET_KEY', '')
    testing     = getattr(settings, 'FREEDOM_PAY_TESTING_MODE', False)

    salt   = _salt()
    params = {
        'pg_merchant_id':    merchant_id,
        'pg_order_id':       str(order_id),
        'pg_amount':         str(amount),
        'pg_description':    description,
        'pg_salt':           salt,
        'pg_currency':       'KGS',
        'pg_success_url':    success_url,
        'pg_failure_url':    fail_url,
        'pg_result_url':     result_url,
        'pg_request_method': 'POST',
        'pg_language':       'ru',
    }

    if testing:
        params['pg_testing_mode'] = '1'
    if user_phone:
        params['pg_user_phone'] = user_phone
    if user_email:
        params['pg_user_email'] = user_email

    params['pg_sig'] = _sig(_INIT_SCRIPT, params, secret)

    resp = requests.post(FREEDOM_PAY_API_URL, data=params, timeout=30)
    resp.raise_for_status()

    root   = ET.fromstring(resp.content)
    status = root.findtext('pg_status')

    if status != 'ok':
        error = (
            root.findtext('pg_error_description')
            or root.findtext('pg_error_code')
            or 'Unknown Freedom Pay error'
        )
        raise Exception(error)

    payment_id   = root.findtext('pg_payment_id') or ''
    redirect_url = root.findtext('pg_redirect_url') or ''
    return payment_id, redirect_url


def verify_callback(post_data: dict) -> bool:
    """Проверяет подпись server-to-server callback от Freedom Pay."""
    secret   = getattr(settings, 'FREEDOM_PAY_SECRET_KEY', '')
    received = post_data.get('pg_sig', '')
    clean    = {k: v for k, v in post_data.items() if k != 'pg_sig'}
    return received == _sig(_CB_SCRIPT, clean, secret)


def callback_xml(status: str, description: str) -> str:
    """
    Возвращает XML-ответ который Freedom Pay ожидает от нашего callback.
    status: 'ok' | 'rejected' | 'error'
    """
    secret = getattr(settings, 'FREEDOM_PAY_SECRET_KEY', '')
    salt   = _salt()
    params = {
        'pg_description': description,
        'pg_salt':        salt,
        'pg_status':      status,
    }
    sig = _sig(_CB_SCRIPT, params, secret)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<response>\n'
        f'  <pg_status>{status}</pg_status>\n'
        f'  <pg_description>{description}</pg_description>\n'
        f'  <pg_salt>{salt}</pg_salt>\n'
        f'  <pg_sig>{sig}</pg_sig>\n'
        '</response>'
    )
