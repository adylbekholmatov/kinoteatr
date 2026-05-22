from rest_framework import serializers
from .models import Movie, Genre, Screening, Hall, Seat, Booking


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name_ru', 'name_ky']


class MovieSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    poster_url = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        fields = ['id', 'title_ru', 'title_ky', 'duration', 'age_rating', 'genres', 'poster_url', 'release_date']

    def get_poster_url(self, obj):
        request = self.context.get('request')
        if obj.poster and request:
            return request.build_absolute_uri(obj.poster.url)
        return None


class HallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hall
        fields = ['id', 'name', 'hall_type', 'rows', 'seats_per_row', 'total_seats']


class ScreeningSerializer(serializers.ModelSerializer):
    movie = MovieSerializer(read_only=True)
    hall = HallSerializer(read_only=True)
    available_seats = serializers.SerializerMethodField()

    class Meta:
        model = Screening
        fields = ['id', 'movie', 'hall', 'start_time', 'price', 'available_seats']

    def get_available_seats(self, obj):
        return obj.hall.total_seats - len(obj.get_booked_seat_ids())


class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ['id', 'row', 'number']


class CreateBookingSerializer(serializers.Serializer):
    screening_id = serializers.IntegerField()
    seat_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    address = serializers.CharField(max_length=300, required=False, default='Касса')


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['id', 'booking_code', 'email', 'phone', 'total_amount', 'status', 'created_at']
