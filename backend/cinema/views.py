import json
import logging
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction

from .models import Movie, Screening, Seat, Booking, BookedSeat, Hall
from .forms import RegisterForm, LoginForm, CheckoutForm

logger = logging.getLogger(__name__)


def get_lang(request):
    # LocaleMiddleware sets request.LANGUAGE_CODE based on session/_language, cookie, or URL prefix
    lang = getattr(request, 'LANGUAGE_CODE', 'ru')
    return 'ky' if lang == 'ky' else 'ru'


@require_POST
def set_theme(request):
    theme = request.POST.get('theme', 'dark')
    if theme not in ('dark', 'light'):
        theme = 'dark'
    request.session['site_theme'] = theme
    next_url = request.POST.get('next', '/')
    return redirect(next_url)


@require_POST
def set_language_custom(request):
    import re
    from django.conf import settings as django_settings

    lang = request.POST.get('language', 'ru')
    if lang not in ('ru', 'ky'):
        lang = 'ru'

    # Save in Django session key (used by LocaleMiddleware)
    request.session['_language'] = lang

    # Compute redirect: strip /ky prefix, then re-add if switching to ky
    next_url = request.POST.get('next', '/')
    clean = re.sub(r'^/ky(?=/|$)', '', next_url) or '/'
    target = ('/ky' + clean) if lang == 'ky' else clean

    response = redirect(target or '/')
    response.set_cookie(
        django_settings.LANGUAGE_COOKIE_NAME,
        lang,
        max_age=365 * 24 * 60 * 60,
        path='/',
        samesite='Lax',
    )
    return response


# ── ГЛАВНАЯ ──────────────────────────────────────────────────────────────────

def index(request):
    lang = get_lang(request)
    new_movies = Movie.objects.filter(is_active=True, is_new=True).prefetch_related('genres')[:8]
    all_movies = Movie.objects.filter(is_active=True).prefetch_related('genres')[:12]
    upcoming_screenings = Screening.objects.filter(
        is_active=True,
        start_time__date=date.today()
    ).select_related('movie', 'hall').order_by('start_time')[:6]

    return render(request, 'cinema/index.html', {
        'new_movies': new_movies,
        'all_movies': all_movies,
        'upcoming_screenings': upcoming_screenings,
        'lang': lang,
    })


# ── РАСПИСАНИЕ ───────────────────────────────────────────────────────────────

def schedule(request):
    lang = get_lang(request)
    selected_date_str = request.GET.get('date', '')
    try:
        selected_date = date.fromisoformat(selected_date_str)
    except ValueError:
        selected_date = date.today()

    # Build 7-day date strip
    dates = [date.today() + timedelta(days=i) for i in range(7)]

    screenings = Screening.objects.filter(
        is_active=True,
        start_time__date=selected_date
    ).select_related('movie', 'hall').order_by('start_time')

    # Group by movie
    movies_screenings = {}
    for s in screenings:
        if s.movie_id not in movies_screenings:
            movies_screenings[s.movie_id] = {'movie': s.movie, 'screenings': []}
        movies_screenings[s.movie_id]['screenings'].append(s)

    return render(request, 'cinema/schedule.html', {
        'dates': dates,
        'selected_date': selected_date,
        'movies_screenings': list(movies_screenings.values()),
        'lang': lang,
    })


# ── ДЕТАЛИ ФИЛЬМА ─────────────────────────────────────────────────────────────

def movie_detail(request, pk):
    lang = get_lang(request)
    movie = get_object_or_404(Movie, pk=pk, is_active=True)
    screenings = Screening.objects.filter(
        movie=movie,
        is_active=True,
        start_time__gte=timezone.now()
    ).select_related('hall').order_by('start_time')

    # Group by date
    screenings_by_date = {}
    for s in screenings:
        d = s.start_time.date()
        if d not in screenings_by_date:
            screenings_by_date[d] = []
        screenings_by_date[d].append(s)

    return render(request, 'cinema/movie_detail.html', {
        'movie': movie,
        'screenings_by_date': screenings_by_date,
        'lang': lang,
    })


# ── ВЫБОР МЕСТ ────────────────────────────────────────────────────────────────

def seat_selection(request, screening_id):
    lang = get_lang(request)
    screening = get_object_or_404(Screening, pk=screening_id, is_active=True)
    hall = screening.hall
    seats = Seat.objects.filter(hall=hall).order_by('row', 'number')

    booked_seat_ids = screening.get_booked_seat_ids()

    # Build seat map per row
    rows = {}
    for seat in seats:
        if seat.row not in rows:
            rows[seat.row] = []
        rows[seat.row].append({
            'id': seat.id,
            'number': seat.number,
            'is_booked': seat.id in booked_seat_ids,
        })

    return render(request, 'cinema/seat_selection.html', {
        'screening': screening,
        'rows': rows,
        'booked_seat_ids': booked_seat_ids,
        'lang': lang,
    })


# ── ОФОРМЛЕНИЕ ────────────────────────────────────────────────────────────────

@login_required
def checkout(request, screening_id):
    lang = get_lang(request)
    screening = get_object_or_404(Screening, pk=screening_id, is_active=True)

    seat_ids_str = request.GET.get('seats', '') or request.POST.get('seats', '')
    try:
        seat_ids = [int(x) for x in seat_ids_str.split(',') if x.strip()]
    except ValueError:
        messages.error(request, 'Орун тандоодо ката.' if lang == 'ky' else 'Ошибка выбора мест.')
        return redirect('seat_selection', screening_id=screening_id)

    if not seat_ids:
        messages.error(request, 'Жок дегенде бир орун тандаңыз.' if lang == 'ky' else 'Выберите хотя бы одно место.')
        return redirect('seat_selection', screening_id=screening_id)

    seats = Seat.objects.filter(id__in=seat_ids, hall=screening.hall)
    if seats.count() != len(seat_ids):
        messages.error(request, 'Орун туура эмес тандалды.' if lang == 'ky' else 'Некорректный выбор мест.')
        return redirect('seat_selection', screening_id=screening_id)

    # Check availability
    booked_ids = screening.get_booked_seat_ids()
    conflict = [s for s in seats if s.id in booked_ids]
    if conflict:
        messages.error(request, 'Бир же бирнече орун буга чейин алынган.' if lang == 'ky' else 'Одно или несколько выбранных мест уже заняты.')
        return redirect('seat_selection', screening_id=screening_id)

    total = screening.price * len(seat_ids)

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            request.session['checkout_data'] = {
                'email': form.cleaned_data['email'],
                'phone': form.cleaned_data['phone'],
                'seat_ids': seat_ids,
                'screening_id': screening_id,
                'total': str(total),
            }
            return redirect('payment')
    else:
        initial = {}
        if request.user.is_authenticated:
            initial['email'] = request.user.email
        form = CheckoutForm(initial=initial)

    return render(request, 'cinema/checkout.html', {
        'form': form,
        'screening': screening,
        'seats': seats,
        'total': total,
        'seat_ids_str': seat_ids_str,
        'lang': lang,
    })


# ── ОПЛАТА через Paybox ───────────────────────────────────────────────────────

@login_required
def payment(request):
    """
    Creates a pending Booking, initiates Paybox payment and redirects the user
    to the Paybox hosted payment page.
    """
    lang = get_lang(request)
    checkout_data = request.session.get('checkout_data')
    if not checkout_data:
        return redirect('index')

    screening = get_object_or_404(Screening, pk=checkout_data['screening_id'])
    seat_ids  = checkout_data['seat_ids']
    total     = Decimal(checkout_data['total'])

    # Re-check seat availability before creating booking
    booked_ids = screening.get_booked_seat_ids()
    conflict   = [sid for sid in seat_ids if sid in booked_ids]
    if conflict:
        messages.error(request, 'Орундар алынган. Башка орун тандаңыз.' if lang == 'ky' else 'Места уже заняты. Выберите другие.')
        return redirect('seat_selection', screening_id=screening.id)

    # Create a PENDING booking (seats are held; becomes 'paid' after callback)
    with transaction.atomic():
        booking = Booking.objects.create(
            screening=screening,
            user=request.user,
            email=checkout_data['email'],
            phone=checkout_data['phone'],
            address='',
            total_amount=total,
            status='pending',
        )
        for sid in seat_ids:
            BookedSeat.objects.create(booking=booking, seat_id=sid)

    # Remove checkout data from session immediately so page refresh won't duplicate
    del request.session['checkout_data']

    # Initiate Paybox payment
    from cinema.paybox import create_payment
    site_url = getattr(settings, 'PAYBOX_SITE_URL', '').rstrip('/')

    try:
        payment_id, redirect_url = create_payment(
            order_id    = booking.booking_code,
            amount      = total,
            description = f'AKI Cinema — {screening.movie.title_ru} ({screening.start_time.strftime("%d.%m.%Y %H:%M")})',
            success_url = f'{site_url}/payment/success/',
            fail_url    = f'{site_url}/payment/fail/',
            result_url  = f'{site_url}/payment/callback/',
            user_phone  = checkout_data.get('phone', ''),
            user_email  = checkout_data.get('email', ''),
        )
        booking.paybox_payment_id = payment_id
        booking.save(update_fields=['paybox_payment_id'])
        return redirect(redirect_url)

    except Exception as exc:
        logger.error('Paybox create_payment error: %s', exc)
        # Cancel the booking if Paybox is unavailable
        booking.status = 'cancelled'
        booking.save(update_fields=['status'])
        messages.error(
            request,
            'Ката кетти. Кийинчерээк кайра аракет кылыңыз.' if lang == 'ky'
            else f'Ошибка платёжной системы: {exc}. Попробуйте позже.'
        )
        return redirect('seat_selection', screening_id=screening.id)


# ── PAYBOX CALLBACK (server → server) ────────────────────────────────────────

@csrf_exempt
@require_POST
def paybox_callback(request):
    """
    Paybox calls this URL server-to-server after payment attempt.
    Must respond with XML: pg_status = ok | rejected | error.
    """
    from cinema.paybox import verify_callback, callback_xml

    # Flatten QueryDict lists → plain dict
    data = {k: v[0] if isinstance(v, list) else v for k, v in request.POST.items()}

    if not verify_callback(data):
        logger.warning('Paybox callback: invalid signature. data=%s', data)
        return HttpResponse(callback_xml('error', 'Invalid signature'), content_type='text/xml')

    order_id   = data.get('pg_order_id', '')
    pg_result  = data.get('pg_result', '0')
    payment_id = data.get('pg_payment_id', '')

    try:
        booking = Booking.objects.get(booking_code=order_id)
    except Booking.DoesNotExist:
        logger.error('Paybox callback: booking not found order_id=%s', order_id)
        return HttpResponse(callback_xml('error', 'Order not found'), content_type='text/xml')

    if pg_result == '1':
        booking.status            = 'paid'
        booking.paybox_payment_id = payment_id
        booking.save(update_fields=['status', 'paybox_payment_id'])
        logger.info('Paybox: booking %s marked as PAID', order_id)
        return HttpResponse(callback_xml('ok', 'Payment accepted'), content_type='text/xml')
    else:
        booking.status = 'cancelled'
        booking.save(update_fields=['status'])
        logger.info('Paybox: booking %s marked as CANCELLED (pg_result=%s)', order_id, pg_result)
        return HttpResponse(callback_xml('ok', 'Payment rejected'), content_type='text/xml')


# ── PAYBOX SUCCESS redirect ───────────────────────────────────────────────────

def paybox_success(request):
    """
    Paybox redirects the user here after a successful payment.
    The callback may arrive slightly after the redirect, so we handle both states.
    """
    lang     = get_lang(request)
    order_id = request.GET.get('pg_order_id') or request.POST.get('pg_order_id', '')

    if order_id:
        try:
            booking = Booking.objects.get(booking_code=order_id)
            if booking.status == 'paid':
                return redirect('booking_success', code=booking.booking_code)
            # Callback not yet received — show a "processing" page
            return render(request, 'cinema/payment_processing.html', {
                'booking': booking,
                'lang': lang,
            })
        except Booking.DoesNotExist:
            pass

    return redirect('index')


# ── PAYBOX FAIL redirect ──────────────────────────────────────────────────────

def paybox_fail(request):
    """Paybox redirects the user here after a failed or cancelled payment."""
    lang     = get_lang(request)
    order_id = request.GET.get('pg_order_id') or request.POST.get('pg_order_id', '')
    booking  = None
    if order_id:
        try:
            booking = Booking.objects.select_related('screening__movie', 'screening__hall').get(
                booking_code=order_id
            )
        except Booking.DoesNotExist:
            pass

    return render(request, 'cinema/payment_fail.html', {
        'booking': booking,
        'lang': lang,
    })


# ── УСПЕШНОЕ БРОНИРОВАНИЕ ─────────────────────────────────────────────────────

def booking_success(request, code):
    lang = get_lang(request)
    booking = get_object_or_404(Booking, booking_code=code)
    seats = booking.booked_seats.select_related('seat')
    return render(request, 'cinema/booking_success.html', {
        'booking': booking,
        'seats': seats,
        'lang': lang,
    })


# ── АВТОРИЗАЦИЯ ───────────────────────────────────────────────────────────────

def register_view(request):
    lang = get_lang(request)
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Катталуу ийгиликтүү өттү!' if lang == 'ky' else 'Регистрация прошла успешно!')
            return redirect('index')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form, 'lang': lang})


def login_view(request):
    lang = get_lang(request)
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', '')
            if next_url:
                return redirect(next_url)
            if user.is_staff:
                return redirect('panel_dashboard')
            return redirect('index')
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form, 'lang': lang})


def logout_view(request):
    logout(request)
    return redirect('index')


# ── МОИ БРОНИРОВАНИЯ ──────────────────────────────────────────────────────────

@login_required
def my_bookings(request):
    lang = get_lang(request)
    bookings = Booking.objects.filter(
        user=request.user
    ).select_related('screening__movie', 'screening__hall').prefetch_related('booked_seats__seat').order_by('-created_at')
    return render(request, 'cinema/my_bookings.html', {'bookings': bookings, 'lang': lang})


# ── О НАС / КОНТАКТЫ ──────────────────────────────────────────────────────────

def about(request):
    return render(request, 'cinema/about.html', {'lang': get_lang(request)})


def contacts(request):
    return render(request, 'cinema/contacts.html', {'lang': get_lang(request)})


# ── API для получения сеансов по фильму (AJAX) ────────────────────────────────

def screenings_by_movie(request, movie_id):
    screenings = Screening.objects.filter(
        movie_id=movie_id,
        is_active=True,
        start_time__gte=timezone.now()
    ).select_related('hall').order_by('start_time')
    data = [{
        'id': s.id,
        'start_time': s.start_time.strftime('%d.%m.%Y %H:%M'),
        'hall': s.hall.name,
        'hall_type': s.hall.hall_type,
        'price': str(s.price),
        'available': s.hall.total_seats - len(s.get_booked_seat_ids()),
    } for s in screenings]
    return JsonResponse({'screenings': data})
