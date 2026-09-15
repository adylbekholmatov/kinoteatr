from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Movie, Screening, Seat, Booking, BookedSeat, Notification
from .serializers import (
    MovieSerializer, ScreeningSerializer, SeatSerializer,
    BookingSerializer, CreateBookingSerializer
)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['username'] = self.user.username
        data['is_staff'] = self.user.is_staff
        data['is_superuser'] = self.user.is_superuser
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    pass


class MovieListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        movies = Movie.objects.filter(is_active=True).prefetch_related('genres')
        data = MovieSerializer(movies, many=True, context={'request': request}).data
        return Response(data)


class ScreeningListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get('date', '')
        qs = Screening.objects.filter(is_active=True).select_related('movie', 'hall')
        if date_str:
            try:
                from datetime import date
                d = date.fromisoformat(date_str)
                qs = qs.filter(start_time__date=d)
            except ValueError:
                pass
        else:
            qs = qs.filter(start_time__gte=timezone.now())
        qs = qs.order_by('start_time')
        data = ScreeningSerializer(qs, many=True).data
        return Response(data)


class ScreeningSeatMapAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            screening = Screening.objects.get(pk=pk, is_active=True)
        except Screening.DoesNotExist:
            return Response({'error': 'Сеанс не найден'}, status=404)

        hall = screening.hall
        seats = Seat.objects.filter(hall=hall).order_by('row', 'number')
        booked_ids = screening.get_booked_seat_ids()

        rows = {}
        for seat in seats:
            row_key = str(seat.row)
            if row_key not in rows:
                rows[row_key] = []
            rows[row_key].append({
                'id': seat.id,
                'number': seat.number,
                'row': seat.row,
                'is_booked': seat.id in booked_ids,
            })

        return Response({
            'screening_id': screening.id,
            'movie': screening.movie.title_ru,
            'hall': screening.hall.name,
            'hall_type': screening.hall.hall_type,
            'start_time': screening.start_time.strftime('%d.%m.%Y %H:%M'),
            'price': str(screening.price),
            'rows': rows,
        })


class CreateBookingAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateBookingSerializer(data=request.data)
        if serializer.is_valid():
            screening_id = serializer.validated_data['screening_id']
            seat_ids = serializer.validated_data['seat_ids']
            email = serializer.validated_data['email']
            phone = serializer.validated_data['phone']

            try:
                screening = Screening.objects.get(pk=screening_id, is_active=True)
            except Screening.DoesNotExist:
                return Response({'error': 'Сеанс не найден'}, status=404)

            booked_ids = screening.get_booked_seat_ids()
            conflict = [sid for sid in seat_ids if sid in booked_ids]
            if conflict:
                return Response({'error': 'Некоторые места уже заняты'}, status=400)

            seats = Seat.objects.filter(id__in=seat_ids, hall=screening.hall)
            if seats.count() != len(seat_ids):
                return Response({'error': 'Некорректные места'}, status=400)

            total = screening.price * len(seat_ids)

            from django.db import transaction
            with transaction.atomic():
                booking = Booking.objects.create(
                    screening=screening,
                    user=request.user,
                    email=email,
                    phone=phone,
                    address=serializer.validated_data.get('address', 'Касса'),
                    total_amount=total,
                    status='reserved',
                    is_admin_booking=True,
                )
                for sid in seat_ids:
                    BookedSeat.objects.create(booking=booking, seat_id=sid)

            return Response({
                'booking_code': booking.booking_code,
                'total_amount': str(total),
                'seats_count': len(seat_ids),
                'status': 'reserved',
            }, status=201)

        return Response(serializer.errors, status=400)


def find_booking(code, qs=None):
    """Бронь по коду, набранному руками.

    Кассир печатает код с бумажки: регистр не тот, префикс (BAYEL- / AKI-)
    часто пропускают. Точное сравнение тут отсекает почти всё.
    """
    code = (code or '').strip().upper()
    if not code:
        return None

    qs = Booking.objects.all() if qs is None else qs

    booking = qs.filter(booking_code__iexact=code).first()
    if booking:
        return booking

    # Набрали только хвост, без префикса — принимаем, если совпадение одно
    if '-' not in code:
        found = list(qs.filter(booking_code__iendswith=f'-{code}')[:2])
        if len(found) == 1:
            return found[0]

    return None


class BookingDetailAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, code):
        booking = find_booking(code)
        if booking is None:
            return Response({'error': 'Бронирование не найдено'}, status=404)

        seats = booking.booked_seats.select_related('seat')
        seats_data = [{'row': bs.seat.row, 'number': bs.seat.number} for bs in seats]

        return Response({
            'booking_code': booking.booking_code,
            'movie': booking.screening.movie.title_ru,
            'hall': booking.screening.hall.name,
            'start_time': booking.screening.start_time.strftime('%d.%m.%Y %H:%M'),
            'email': booking.email,
            'phone': booking.phone,
            'total_amount': str(booking.total_amount),
            'status': booking.status,
            'seats': seats_data,
            'created_at': booking.created_at.strftime('%d.%m.%Y %H:%M'),
        })

    def patch(self, request, code):
        booking = find_booking(code)
        if booking is None:
            return Response({'error': 'Бронирование не найдено'}, status=404)

        new_status = request.data.get('status')
        if new_status in ['paid', 'reserved', 'cancelled']:
            booking.status = new_status
            booking.save()
            return Response({'status': booking.status})

        return Response({'error': 'Недопустимый статус'}, status=400)


# ── Pending receipts (для WPF) ────────────────────────────────────────────────

class PendingReceiptsAPI(APIView):
    """Список броней с загруженным чеком + недавно отменённые клиентом — для WPF."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({'error': 'Нет доступа'}, status=403)

        from django.utils import timezone as tz
        from datetime import timedelta

        # Ожидают подтверждения
        pending_qs = Booking.objects.filter(
            status='receipt_uploaded'
        ).select_related('screening__movie', 'screening__hall').order_by('-created_at')

        # Отменены клиентом в последние 24 ч (и при этом был загружен чек)
        cancelled_qs = Booking.objects.filter(
            status='cancelled',
            payment_note='Отменено клиентом',
            payment_receipt__isnull=False,
            created_at__gte=tz.now() - timedelta(hours=24),
        ).select_related('screening__movie', 'screening__hall').order_by('-created_at')

        def serialize(b, label='pending'):
            receipt_url = request.build_absolute_uri(b.payment_receipt.url) if b.payment_receipt else ''
            return {
                'id': b.pk,
                'booking_code': b.booking_code,
                'movie': b.screening.movie.title_ru,
                'screening_time': b.screening.start_time.strftime('%d.%m.%Y %H:%M'),
                'hall': b.screening.hall.name,
                'total_amount': str(b.total_amount),
                'email': b.email,
                'phone': b.phone,
                'receipt_url': receipt_url,
                'created_at': b.created_at.strftime('%d.%m.%Y %H:%M'),
                'alert_type': label,
            }

        data = [serialize(b, 'pending') for b in pending_qs] + \
               [serialize(b, 'cancelled_by_client') for b in cancelled_qs]

        return Response({'count': len([d for d in data if d['alert_type'] == 'pending']),
                         'bookings': data})


class AdminConfirmBookingAPI(APIView):
    """Подтвердить оплату — WPF нажимает Подтвердить."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_staff:
            return Response({'error': 'Нет доступа'}, status=403)

        try:
            booking = Booking.objects.get(pk=pk, status='receipt_uploaded')
        except Booking.DoesNotExist:
            return Response({'error': 'Бронирование не найдено или уже обработано'}, status=404)

        booking.status = 'paid'
        booking.processed_by = request.user
        booking.processed_at = timezone.now()
        booking.save(update_fields=['status', 'processed_by', 'processed_at'])

        # Уведомление для клиента на сайте
        if booking.user:
            Notification.objects.create(
                user=booking.user,
                booking=booking,
                message=(
                    f'Оплата подтверждена! '
                    f'«{booking.screening.movie.title_ru}» '
                    f'{booking.screening.start_time.strftime("%d.%m в %H:%M")}. '
                    f'Билет с QR-кодом уже в разделе «Мои билеты». Ждём в кино! 🎬'
                ),
            )

        return Response({'status': 'paid', 'booking_code': booking.booking_code})


class AdminRejectBookingAPI(APIView):
    """Отклонить оплату — WPF нажимает Отклонить."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_staff:
            return Response({'error': 'Нет доступа'}, status=403)

        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({'error': 'Бронирование не найдено'}, status=404)

        note = request.data.get('note', '').strip()
        booking.status = 'cancelled'
        booking.payment_note = note
        booking.processed_by = request.user
        booking.processed_at = timezone.now()
        booking.save(update_fields=['status', 'payment_note',
                                    'processed_by', 'processed_at'])

        if booking.user:
            msg = 'Оплата не подтверждена, бронирование отменено.'
            if note:
                msg += f' Причина: {note}'
            Notification.objects.create(
                user=booking.user,
                booking=booking,
                message=msg,
            )

        return Response({'status': 'cancelled', 'booking_code': booking.booking_code})


class AdminRequestTopupAPI(APIView):
    """Запросить доплату — сумма пришла не полностью, ждём новый чек."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_staff:
            return Response({'error': 'Нет доступа'}, status=403)

        try:
            booking = Booking.objects.get(pk=pk, status='receipt_uploaded')
        except Booking.DoesNotExist:
            return Response({'error': 'Бронирование не найдено или уже обработано'}, status=404)

        note = request.data.get('note', '').strip()

        booking.status = 'pending'
        booking.payment_note = note
        booking.payment_receipt = None      # ждём новый чек
        booking.processed_by = request.user
        booking.processed_at = timezone.now()
        booking.save(update_fields=['status', 'payment_note', 'payment_receipt',
                                    'processed_by', 'processed_at'])

        if booking.user:
            msg = f'Требуется доплата по брони {booking.booking_code}.'
            if note:
                msg += f' {note}'
            msg += ' Загрузите новый чек на странице оплаты.'
            Notification.objects.create(user=booking.user, booking=booking, message=msg)

        return Response({'status': 'pending', 'booking_code': booking.booking_code})


class AdminRestoreBookingAPI(APIView):
    """Восстановить бронь, отменённую клиентом — WPF нажимает Восстановить."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_staff:
            return Response({'error': 'Нет доступа'}, status=403)

        try:
            booking = Booking.objects.get(pk=pk, status='cancelled',
                                          payment_note='Отменено клиентом')
        except Booking.DoesNotExist:
            return Response({'error': 'Бронирование не найдено или уже активно'}, status=404)

        # Восстанавливаем статус: если был чек — обратно в receipt_uploaded, иначе pending
        new_status = 'receipt_uploaded' if booking.payment_receipt else 'pending'
        booking.status = new_status
        booking.payment_note = ''
        booking.processed_by = request.user
        booking.processed_at = timezone.now()
        booking.save(update_fields=['status', 'payment_note',
                                    'processed_by', 'processed_at'])

        if booking.user:
            Notification.objects.create(
                user=booking.user,
                booking=booking,
                message=(
                    f'Ваша бронь восстановлена администратором! '
                    f'«{booking.screening.movie.title_ru}» '
                    f'{booking.screening.start_time.strftime("%d.%m в %H:%M")}. '
                    f'Код: {booking.booking_code}'
                ),
            )

        return Response({'status': new_status, 'booking_code': booking.booking_code})


# ── Проверка билета по QR (WPF, сканер) ──────────────────────────────────────

class VerifyTicketAPI(APIView):
    """Проверка QR-билета на входе. Кассир сканирует — получает все данные."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response({'error': 'Нет доступа'}, status=403)

        from .ticket_utils import parse_qr_payload

        raw = (request.data.get('qr_data') or '').strip()
        if not raw:
            return Response({'valid': False, 'reason': 'Пустой QR-код'}, status=400)

        qs = Booking.objects.select_related('screening__movie', 'screening__hall')

        # Подписанный QR всегда содержит двоеточия (BAYEL:<код>:<подпись>),
        # а набранный руками код — нет. Так подделку не спутать с ручным вводом.
        if ':' in raw:
            booking_code = parse_qr_payload(raw)
            if booking_code is None:
                return Response({'valid': False,
                                 'reason': 'Недействительный QR — подпись не совпадает'})
            booking = qs.filter(booking_code=booking_code).first()
            manual_entry = False
        else:
            booking = find_booking(raw, qs)
            manual_entry = True

        if booking is None:
            return Response({'valid': False, 'reason': 'Бронирование не найдено'})

        if booking.status != 'paid':
            return Response({
                'valid': False,
                'reason': f'Билет не оплачен (статус: {booking.get_status_display()})',
            })

        already_used = booking.checked_in_at is not None
        if not already_used:
            booking.checked_in_at = timezone.now()
            booking.save(update_fields=['checked_in_at'])

        seats = [f'Ряд {bs.seat.row}, место {bs.seat.number}'
                 for bs in booking.booked_seats.select_related('seat')]

        return Response({
            'valid': True,
            'already_used': already_used,
            'manual_entry': manual_entry,
            'booking_code': booking.booking_code,
            'movie': booking.screening.movie.title_ru,
            'screening_time': booking.screening.start_time.strftime('%d.%m.%Y %H:%M'),
            'hall': booking.screening.hall.name,
            'seats': seats,
            'seats_count': len(seats),
            'total_amount': str(booking.total_amount),
            'phone': booking.phone,
            'checked_in_at': booking.checked_in_at.strftime('%d.%m.%Y %H:%M'),
        })


# ── Уведомления для пользователя на сайте ────────────────────────────────────

class UserNotificationsAPI(APIView):
    """Получить уведомления текущего пользователя.

    Единственный эндпоинт, который дёргает сайт, а не WPF: колокольчик в шапке
    ходит с сессионной кукой. Глобально включён только JWT, поэтому сессию
    разрешаем здесь — админские эндпоинты остаются на JWT.
    """
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifs = Notification.objects.filter(
            user=request.user, is_read=False
        ).select_related('booking')[:20]

        data = [{
            'id': n.pk,
            'message': n.message,
            'booking_code': n.booking.booking_code if n.booking else '',
            'created_at': n.created_at.strftime('%d.%m %H:%M'),
        } for n in notifs]

        return Response({'count': len(data), 'notifications': data})

    def post(self, request):
        """Отметить все как прочитанные."""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'ok'})
