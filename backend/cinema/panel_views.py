import json
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Booking, Hall, Movie, Screening
from .panel_forms import BookingStatusForm, HallForm, MovieForm, ScreeningForm


def _staff_required(request):
    """Return a redirect response if user is not staff, else None."""
    if not request.user.is_staff:
        return redirect('/')
    return None


# ── DASHBOARD ────────────────────────────────────────────────────────────────

@login_required
def panel_dashboard(request):
    guard = _staff_required(request)
    if guard:
        return guard

    today = date.today()
    month_start = today.replace(day=1)

    # ── Today ──
    movie_count = Movie.objects.count()
    screening_count_today = Screening.objects.filter(start_time__date=today).count()
    bookings_today = Booking.objects.filter(created_at__date=today)
    bookings_today_count = bookings_today.count()
    revenue_today = bookings_today.filter(status='paid').aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    # ── This month ──
    bookings_month = Booking.objects.filter(created_at__date__gte=month_start)
    bookings_month_count = bookings_month.count()
    revenue_month = bookings_month.filter(status='paid').aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    # ── Chart: daily revenue for current month (last 30 days max) ──
    daily_qs = (
        Booking.objects
        .filter(status='paid', created_at__date__gte=month_start)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('total_amount'), cnt=Count('id'))
        .order_by('day')
    )

    # Build full day-by-day series from month_start to today
    chart_labels = []
    chart_revenue = []
    chart_bookings = []
    daily_map = {row['day']: row for row in daily_qs}
    d = month_start
    while d <= today:
        chart_labels.append(d.strftime('%d.%m'))
        row = daily_map.get(d)
        chart_revenue.append(float(row['total']) if row else 0)
        chart_bookings.append(row['cnt'] if row else 0)
        d += timedelta(days=1)

    recent_bookings = Booking.objects.select_related(
        'screening__movie'
    ).order_by('-created_at')[:5]

    return render(request, 'panel/dashboard.html', {
        'page_title': 'Dashboard',
        'movie_count': movie_count,
        'screening_count_today': screening_count_today,
        'bookings_today_count': bookings_today_count,
        'revenue_today': revenue_today,
        # month
        'bookings_month_count': bookings_month_count,
        'revenue_month': revenue_month,
        'month_label': today.strftime('%B %Y'),
        # chart
        'chart_labels': json.dumps(chart_labels, ensure_ascii=False),
        'chart_revenue': json.dumps(chart_revenue),
        'chart_bookings': json.dumps(chart_bookings),
        # table
        'recent_bookings': recent_bookings,
    })


# ── MOVIES ───────────────────────────────────────────────────────────────────

@login_required
def panel_movies(request):
    guard = _staff_required(request)
    if guard:
        return guard

    qs = Movie.objects.prefetch_related('genres').order_by('-created_at')
    query = request.GET.get('q', '').strip()
    if query:
        qs = qs.filter(Q(title_ru__icontains=query) | Q(title_ky__icontains=query))

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'panel/movies.html', {
        'page_title': 'Фильмы',
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def panel_movie_add(request):
    guard = _staff_required(request)
    if guard:
        return guard

    if request.method == 'POST':
        form = MovieForm(request.POST, request.FILES)
        if form.is_valid():
            movie = form.save()
            messages.success(request, f'Фильм «{movie.title_ru}» успешно добавлен.')
            return redirect('panel_movies')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = MovieForm()

    return render(request, 'panel/movie_form.html', {
        'page_title': 'Добавить фильм',
        'form': form,
        'is_edit': False,
    })


@login_required
def panel_movie_edit(request, pk):
    guard = _staff_required(request)
    if guard:
        return guard

    movie = get_object_or_404(Movie, pk=pk)

    if request.method == 'POST':
        form = MovieForm(request.POST, request.FILES, instance=movie)
        if form.is_valid():
            form.save()
            messages.success(request, f'Фильм «{movie.title_ru}» успешно обновлён.')
            return redirect('panel_movies')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = MovieForm(instance=movie)

    return render(request, 'panel/movie_form.html', {
        'page_title': f'Редактировать: {movie.title_ru}',
        'form': form,
        'movie': movie,
        'is_edit': True,
    })


@login_required
def panel_movie_delete(request, pk):
    guard = _staff_required(request)
    if guard:
        return guard

    if request.method == 'POST':
        movie = get_object_or_404(Movie, pk=pk)
        title = movie.title_ru
        movie.delete()
        messages.success(request, f'Фильм «{title}» удалён.')
    return redirect('panel_movies')


# ── SCREENINGS ───────────────────────────────────────────────────────────────

@login_required
def panel_screenings(request):
    guard = _staff_required(request)
    if guard:
        return guard

    qs = Screening.objects.select_related('movie', 'hall').order_by('-start_time')
    date_filter = request.GET.get('date', '').strip()
    if date_filter:
        try:
            from datetime import date as dt
            filter_date = dt.fromisoformat(date_filter)
            qs = qs.filter(start_time__date=filter_date)
        except ValueError:
            date_filter = ''

    return render(request, 'panel/screenings.html', {
        'page_title': 'Сеансы',
        'screenings': qs,
        'date_filter': date_filter,
    })


@login_required
def panel_screening_add(request):
    guard = _staff_required(request)
    if guard:
        return guard

    if request.method == 'POST':
        form = ScreeningForm(request.POST)
        if form.is_valid():
            first = form.save()
            created = [first]

            # Extra time slots submitted alongside the main form
            extra_raw = request.POST.getlist('extra_times')
            for raw in extra_raw:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    from datetime import datetime as _dt
                    naive = _dt.strptime(raw, '%Y-%m-%dT%H:%M')
                    from django.utils import timezone as _tz
                    aware = _tz.make_aware(naive)
                    Screening.objects.create(
                        movie=first.movie,
                        hall=first.hall,
                        start_time=aware,
                        price=first.price,
                        is_active=first.is_active,
                    )
                    created.append(aware)
                except (ValueError, TypeError):
                    pass

            if len(created) == 1:
                messages.success(
                    request,
                    f'Сеанс «{first.movie.title_ru}» на '
                    f'{first.start_time.strftime("%d.%m.%Y %H:%M")} добавлен.'
                )
            else:
                times_str = ', '.join(
                    t.strftime('%H:%M') if hasattr(t, 'strftime') else ''
                    for t in created
                )
                messages.success(
                    request,
                    f'Создано {len(created)} сеансов для «{first.movie.title_ru}»: {times_str}.'
                )
            return redirect('panel_screenings')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = ScreeningForm()

    return render(request, 'panel/screening_form.html', {
        'page_title': 'Добавить сеанс',
        'form': form,
        'is_edit': False,
    })


@login_required
def panel_screening_edit(request, pk):
    guard = _staff_required(request)
    if guard:
        return guard

    screening = get_object_or_404(Screening, pk=pk)

    if request.method == 'POST':
        form = ScreeningForm(request.POST, instance=screening)
        if form.is_valid():
            form.save()
            messages.success(request, 'Сеанс успешно обновлён.')
            return redirect('panel_screenings')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = ScreeningForm(instance=screening)
        # Pre-format datetime for datetime-local input
        if screening.start_time:
            form.initial['start_time'] = screening.start_time.strftime('%Y-%m-%dT%H:%M')

    return render(request, 'panel/screening_form.html', {
        'page_title': 'Редактировать сеанс',
        'form': form,
        'screening': screening,
        'is_edit': True,
    })


@login_required
def panel_screening_delete(request, pk):
    guard = _staff_required(request)
    if guard:
        return guard

    if request.method == 'POST':
        screening = get_object_or_404(Screening, pk=pk)
        screening.delete()
        messages.success(request, 'Сеанс удалён.')
    return redirect('panel_screenings')


# ── BOOKINGS ─────────────────────────────────────────────────────────────────

@login_required
def panel_bookings(request):
    guard = _staff_required(request)
    if guard:
        return guard

    qs = Booking.objects.select_related(
        'screening__movie', 'screening__hall', 'user'
    ).prefetch_related('booked_seats').order_by('-created_at')

    # Filters
    status_filter = request.GET.get('status', '').strip()
    date_filter   = request.GET.get('date', '').strip()
    search        = request.GET.get('q', '').strip()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if date_filter:
        try:
            from datetime import date as dt
            qs = qs.filter(created_at__date=dt.fromisoformat(date_filter))
        except ValueError:
            date_filter = ''
    if search:
        qs = qs.filter(
            Q(booking_code__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(screening__movie__title_ru__icontains=search)
        )

    paginator  = Paginator(qs, 15)
    page_obj   = paginator.get_page(request.GET.get('page'))

    status_choices = Booking.STATUS_CHOICES

    return render(request, 'panel/bookings.html', {
        'page_title': 'Бронирования',
        'page_obj': page_obj,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'query': search,
        'status_choices': status_choices,
    })


@login_required
def panel_booking_detail(request, pk):
    guard = _staff_required(request)
    if guard:
        return guard

    booking = get_object_or_404(
        Booking.objects.select_related('screening__movie', 'screening__hall', 'user')
                       .prefetch_related('booked_seats__seat'),
        pk=pk,
    )
    form = BookingStatusForm(instance=booking)

    return render(request, 'panel/booking_detail.html', {
        'page_title': f'Бронирование {booking.booking_code}',
        'booking': booking,
        'form': form,
    })


@login_required
def panel_booking_status(request, pk):
    guard = _staff_required(request)
    if guard:
        return guard

    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        form = BookingStatusForm(request.POST, instance=booking)
        if form.is_valid():
            form.save()
            messages.success(request, f'Статус бронирования {booking.booking_code} обновлён.')
        else:
            messages.error(request, 'Ошибка при обновлении статуса.')
    return redirect('panel_booking_detail', pk=pk)


# ── HALLS ─────────────────────────────────────────────────────────────────────

@login_required
def panel_halls(request):
    guard = _staff_required(request)
    if guard:
        return guard

    halls = Hall.objects.all().order_by('name')
    return render(request, 'panel/halls.html', {
        'page_title': 'Залы',
        'halls': halls,
    })


@login_required
def panel_hall_add(request):
    guard = _staff_required(request)
    if guard:
        return guard

    if request.method == 'POST':
        form = HallForm(request.POST)
        if form.is_valid():
            hall = form.save()
            hall.create_seats()
            messages.success(request, f'Зал «{hall.name}» добавлен. Создано {hall.total_seats} мест.')
            return redirect('panel_halls')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = HallForm()

    return render(request, 'panel/hall_form.html', {
        'page_title': 'Добавить зал',
        'form': form,
        'is_edit': False,
    })


@login_required
def panel_hall_edit(request, pk):
    guard = _staff_required(request)
    if guard:
        return guard

    hall = get_object_or_404(Hall, pk=pk)
    old_rows = hall.rows
    old_seats_per_row = hall.seats_per_row

    if request.method == 'POST':
        form = HallForm(request.POST, instance=hall)
        if form.is_valid():
            hall = form.save()
            # Regenerate seats if layout changed
            if hall.rows != old_rows or hall.seats_per_row != old_seats_per_row:
                hall.create_seats()
                messages.success(request, f'Зал «{hall.name}» обновлён. Места пересозданы ({hall.total_seats} шт.).')
            else:
                messages.success(request, f'Зал «{hall.name}» обновлён.')
            return redirect('panel_halls')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = HallForm(instance=hall)

    return render(request, 'panel/hall_form.html', {
        'page_title': f'Редактировать: {hall.name}',
        'form': form,
        'hall': hall,
        'is_edit': True,
    })


@login_required
def panel_hall_delete(request, pk):
    guard = _staff_required(request)
    if guard:
        return guard

    if request.method == 'POST':
        hall = get_object_or_404(Hall, pk=pk)
        name = hall.name
        hall.delete()
        messages.success(request, f'Зал «{name}» удалён.')
    return redirect('panel_halls')


# ── СМЕНА ПАРОЛЯ ─────────────────────────────────────────────────────────────

@login_required
def panel_change_password(request):
    guard = _staff_required(request)
    if guard:
        return guard

    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Обновляем сессию чтобы не вылетело после смены пароля
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменён!')
            return redirect('panel_change_password')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки.')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'panel/change_password.html', {
        'page_title': 'Смена пароля',
        'form': form,
    })
