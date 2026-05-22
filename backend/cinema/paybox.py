"""
Paybox.money payment gateway integration.
Documentation: https://paybox.money/documentation
"""

import hashlib
import random
import string
import requests
import xml.etree.ElementTree as ET
from django.conf import settings


PAYBOX_API_URL = 'https://api.paybox.money/payment.php'
_INIT_SCRIPT   = 'payment.php'
_CB_SCRIPT     = 'check_url.php'


# ── helpers ──────────────────────────────────────────────────────────────────

def _salt(n: int = 16) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


def _sig(script: str, params: dict, secret: str) -> str:
    """MD5 signature used by Paybox (keys sorted alphabetically)."""
    sorted_keys = sorted(k for k in params if k.startswith('pg_'))
    values = [str(params[k]) for k in sorted_keys]
    raw = script + ';' + ';'.join(values) + ';' + secret
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


# ── public API ───────────────────────────────────────────────────────────────

def create_payment(
    order_id: str,
    amount,
    description: str,
    success_url: str,
    fail_url: str,
    result_url: str,
    user_phone: str = '',
    user_email: str = '',
) -> tuple[str, str]:
    """
    Initiate a payment on Paybox side.

    Returns:
        (paybox_payment_id, redirect_url)

    Raises:
        Exception on Paybox API error.
    """
    merchant_id = str(getattr(settings, 'PAYBOX_MERCHANT_ID', ''))
    secret      = getattr(settings, 'PAYBOX_SECRET_KEY', '')
    testing     = getattr(settings, 'PAYBOX_TESTING_MODE', False)

    salt = _salt()
    params = {
        'pg_merchant_id':   merchant_id,
        'pg_order_id':      str(order_id),
        'pg_amount':        str(amount),
        'pg_description':   description,
        'pg_salt':          salt,
        'pg_currency':      'KGS',
        'pg_success_url':   success_url,
        'pg_failure_url':   fail_url,
        'pg_result_url':    result_url,
        'pg_request_method': 'POST',
        'pg_language':      'ru',
    }
    if testing:
        params['pg_testing_mode'] = '1'
    if user_phone:
        params['pg_user_phone'] = user_phone
    if user_email:
        params['pg_user_email'] = user_email

    params['pg_sig'] = _sig(_INIT_SCRIPT, params, secret)

    resp = requests.post(PAYBOX_API_URL, data=params, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)

    status = root.findtext('pg_status')
    if status != 'ok':
        error = (
            root.findtext('pg_error_description')
            or root.findtext('pg_error_code')
            or 'Unknown Paybox error'
        )
        raise Exception(error)

    payment_id   = root.findtext('pg_payment_id') or ''
    redirect_url = root.findtext('pg_redirect_url') or ''
    return payment_id, redirect_url


def verify_callback(post_data: dict) -> bool:
    """Verify the Paybox server-to-server callback signature."""
    secret   = getattr(settings, 'PAYBOX_SECRET_KEY', '')
    received = post_data.get('pg_sig', '')
    clean    = {k: v for k, v in post_data.items() if k != 'pg_sig'}
    return received == _sig(_CB_SCRIPT, clean, secret)


def callback_xml(status: str, description: str) -> str:
    """Build the XML response that Paybox expects from our callback endpoint."""
    secret = getattr(settings, 'PAYBOX_SECRET_KEY', '')
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
