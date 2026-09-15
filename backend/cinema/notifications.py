from django.conf import settings
from django.core.mail import send_mail


def _admin_email():
    return getattr(settings, 'ADMIN_EMAIL', 'info@bayelcinema.kg')


def _site_url():
    return getattr(settings, 'FREEDOM_PAY_SITE_URL', 'https://bayel-cinema.online').rstrip('/')


def notify_admin_receipt_uploaded(booking):
    """Уведомить администратора: клиент загрузил чек."""
    panel_url = f"{_site_url()}/panel/bookings/{booking.pk}/"
    subject = f"[Байэл Cinema] Новый чек — {booking.booking_code}"
    body = (
        f"Клиент загрузил чек оплаты.\n\n"
        f"Бронирование: {booking.booking_code}\n"
        f"Фильм: {booking.screening.movie.title_ru}\n"
        f"Сеанс: {booking.screening.start_time.strftime('%d.%m.%Y %H:%M')}\n"
        f"Сумма: {booking.total_amount} сом\n"
        f"Email клиента: {booking.email}\n"
        f"Телефон клиента: {booking.phone}\n\n"
        f"Перейдите в панель для подтверждения:\n{panel_url}"
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [_admin_email()], fail_silently=True)
    except Exception:
        pass


def notify_user_confirmed(booking):
    """Уведомить клиента: оплата подтверждена."""
    ticket_url = f"{_site_url()}/booking/{booking.booking_code}/success/"
    subject = "Ваш билет подтверждён — Байэл Cinema"
    body = (
        f"Здравствуйте!\n\n"
        f"Ваша оплата по бронированию {booking.booking_code} подтверждена.\n\n"
        f"Фильм: {booking.screening.movie.title_ru}\n"
        f"Дата: {booking.screening.start_time.strftime('%d.%m.%Y')}\n"
        f"Время: {booking.screening.start_time.strftime('%H:%M')}\n"
        f"Зал: {booking.screening.hall.name}\n"
        f"Мест: {booking.booked_seats.count()}\n"
        f"Сумма: {booking.total_amount} сом\n\n"
        f"Ваш билет: {ticket_url}\n\n"
        f"Приятного просмотра!\nБайэл Cinema"
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [booking.email], fail_silently=True)
    except Exception:
        pass


def notify_user_rejected(booking):
    """Уведомить клиента: оплата отклонена."""
    subject = "Бронирование отклонено — Байэл Cinema"
    note_line = f"\nПричина: {booking.payment_note}\n" if booking.payment_note else ""
    body = (
        f"Здравствуйте!\n\n"
        f"К сожалению, ваше бронирование {booking.booking_code} было отклонено.\n"
        f"{note_line}\n"
        f"Фильм: {booking.screening.movie.title_ru}\n"
        f"Сумма к возврату: {booking.total_amount} сом\n\n"
        f"Если у вас есть вопросы, свяжитесь с нами:\n"
        f"Тел: {getattr(settings, 'TRANSFER_PHONE', '')}\n"
        f"Email: {_admin_email()}\n\n"
        f"Байэл Cinema"
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [booking.email], fail_silently=True)
    except Exception:
        pass


def notify_user_topup_required(booking):
    """Уведомить клиента: требуется доплата."""
    pay_url = f"{_site_url()}/payment/{booking.booking_code}/pending/"
    subject = f"Требуется доплата — {booking.booking_code} — Байэл Cinema"
    note_line = f"\n{booking.payment_note}\n" if booking.payment_note else ""
    body = (
        f"Здравствуйте!\n\n"
        f"По бронированию {booking.booking_code} требуется доплата.\n"
        f"{note_line}\n"
        f"Пожалуйста, переведите недостающую сумму и загрузите новый чек:\n"
        f"{pay_url}\n\n"
        f"Фильм: {booking.screening.movie.title_ru}\n"
        f"Итого должно быть: {booking.total_amount} сом\n\n"
        f"Байэл Cinema"
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [booking.email], fail_silently=True)
    except Exception:
        pass
