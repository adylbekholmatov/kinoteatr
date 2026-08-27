import random
import string
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Genre(models.Model):
    name_ru = models.CharField('Жанр (рус)', max_length=100)
    name_ky = models.CharField('Жанр (кырг)', max_length=100)

    class Meta:
        verbose_name = 'Жанр'
        verbose_name_plural = 'Жанры'

    def __str__(self):
        return self.name_ru


class Movie(models.Model):
    AGE_RATINGS = [('0+', '0+'), ('6+', '6+'), ('12+', '12+'), ('16+', '16+'), ('18+', '18+')]

    title_ru = models.CharField('Название (рус)', max_length=200)
    title_ky = models.CharField('Название (кырг)', max_length=200)
    description_ru = models.TextField('Описание (рус)', blank=True, default='')
    description_ky = models.TextField('Описание (кырг)', blank=True, default='')
    poster = models.ImageField('Постер', upload_to='posters/')
    trailer_url = models.URLField('Трейлер (YouTube URL)', blank=True)
    duration = models.PositiveIntegerField('Длительность (мин)')
    genres = models.ManyToManyField(Genre, verbose_name='Жанры', blank=True)
    release_date = models.DateField('Дата выхода')
    age_rating = models.CharField('Возрастной рейтинг', max_length=3, choices=AGE_RATINGS, default='0+')
    country = models.CharField('Страна', max_length=100, blank=True)
    director = models.CharField('Режиссёр', max_length=200, blank=True)
    is_active = models.BooleanField('Активен', default=True)
    is_new = models.BooleanField('Новинка', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Фильм'
        verbose_name_plural = 'Фильмы'
        ordering = ['-created_at']

    def __str__(self):
        return self.title_ru

    def get_title(self, lang='ru'):
        return self.title_ky if lang == 'ky' else self.title_ru

    def get_description(self, lang='ru'):
        return self.description_ky if lang == 'ky' else self.description_ru

    @property
    def duration_display(self):
        h = self.duration // 60
        m = self.duration % 60
        if h:
            return f'{h} ч {m} мин'
        return f'{m} мин'


class Hall(models.Model):
    HALL_TYPES = [('regular', 'Обычный'), ('vip', 'VIP')]

    name = models.CharField('Название зала', max_length=100)
    hall_type = models.CharField('Тип зала', max_length=10, choices=HALL_TYPES, default='regular')
    rows = models.PositiveIntegerField('Количество рядов')
    seats_per_row = models.PositiveIntegerField('Мест в ряду')

    class Meta:
        verbose_name = 'Зал'
        verbose_name_plural = 'Залы'

    def __str__(self):
        return f'{self.name} ({self.get_hall_type_display()})'

    @property
    def total_seats(self):
        return self.rows * self.seats_per_row

    def create_seats(self):
        Seat.objects.filter(hall=self).delete()
        seats = []
        for row in range(1, self.rows + 1):
            for num in range(1, self.seats_per_row + 1):
                seats.append(Seat(hall=self, row=row, number=num))
        Seat.objects.bulk_create(seats)


class Seat(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='seats', verbose_name='Зал')
    row = models.PositiveIntegerField('Ряд')
    number = models.PositiveIntegerField('Место')

    class Meta:
        verbose_name = 'Место'
        verbose_name_plural = 'Места'
        unique_together = ('hall', 'row', 'number')
        ordering = ['row', 'number']

    def __str__(self):
        return f'{self.hall.name} | Ряд {self.row}, Место {self.number}'


class Screening(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='screenings', verbose_name='Фильм')
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='screenings', verbose_name='Зал')
    start_time = models.DateTimeField('Время начала')
    price = models.DecimalField('Цена билета (сом)', max_digits=8, decimal_places=2)
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        verbose_name = 'Сеанс'
        verbose_name_plural = 'Сеансы'
        ordering = ['start_time']

    def __str__(self):
        return f'{self.movie.title_ru} | {self.start_time.strftime("%d.%m.%Y %H:%M")} | {self.hall.name}'

    @property
    def end_time(self):
        return self.start_time + timedelta(minutes=self.movie.duration)

    def get_booked_seat_ids(self):
        booked = BookedSeat.objects.filter(
            booking__screening=self,
            booking__status__in=['paid', 'reserved']
        ).values_list('seat_id', flat=True)
        return list(booked)


def generate_booking_code():
    return 'BAYEL-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидание оплаты'),
        ('paid', 'Оплачено'),
        ('reserved', 'Зарезервировано (касса)'),
        ('cancelled', 'Отменено'),
    ]

    screening = models.ForeignKey(Screening, on_delete=models.CASCADE, related_name='bookings', verbose_name='Сеанс')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Пользователь')
    email = models.EmailField('Email')
    phone = models.CharField('Телефон', max_length=20)
    address = models.CharField('Адрес', max_length=300, blank=True, default='')
    total_amount = models.DecimalField('Сумма', max_digits=10, decimal_places=2)
    booking_code = models.CharField('Код бронирования', max_length=20, unique=True, default=generate_booking_code)
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default='pending')
    paybox_payment_id = models.CharField('Paybox Payment ID', max_length=50, blank=True, default='')
    card_last4 = models.CharField('Последние 4 цифры карты', max_length=4, blank=True)
    is_admin_booking = models.BooleanField('Касса', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.booking_code} | {self.screening.movie.title_ru}'

    @property
    def seats_list(self):
        return self.booked_seats.select_related('seat')

    @property
    def seats_count(self):
        return self.booked_seats.count()


class BookedSeat(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booked_seats')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='booked_seats')

    class Meta:
        verbose_name = 'Забронированное место'
        verbose_name_plural = 'Забронированные места'
        unique_together = ('booking', 'seat')

    def __str__(self):
        return f'{self.booking.booking_code} | Ряд {self.seat.row}, Место {self.seat.number}'
