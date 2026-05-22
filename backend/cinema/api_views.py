from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Movie, Screening, Seat, Booking, BookedSeat
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


class BookingDetailAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, code):
        try:
            booking = Booking.objects.get(booking_code=code)
        except Booking.DoesNotExist:
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
        try:
            booking = Booking.objects.get(booking_code=code)
        except Booking.DoesNotExist:
            return Response({'error': 'Бронирование не найдено'}, status=404)

        new_status = request.data.get('status')
        if new_status in ['paid', 'reserved', 'cancelled']:
            booking.status = new_status
            booking.save()
            return Response({'status': booking.status})

        return Response({'error': 'Недопустимый статус'}, status=400)
