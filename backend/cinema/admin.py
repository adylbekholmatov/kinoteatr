from django.contrib import admin
from django.utils.html import format_html
from .models import Genre, Movie, Hall, Seat, Screening, Booking, BookedSeat


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name_ru', 'name_ky')
    search_fields = ('name_ru', 'name_ky')


class BookedSeatInline(admin.TabularInline):
    model = BookedSeat
    extra = 0
    readonly_fields = ('seat',)


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title_ru', 'age_rating', 'duration_display', 'release_date', 'is_new', 'is_active', 'poster_preview')
    list_filter = ('is_active', 'is_new', 'age_rating', 'genres')
    search_fields = ('title_ru', 'title_ky', 'director')
    filter_horizontal = ('genres',)
    list_editable = ('is_active', 'is_new')
    readonly_fields = ('poster_preview',)
    fieldsets = (
        ('Основное', {'fields': ('title_ru', 'title_ky', 'poster', 'poster_preview', 'trailer_url')}),
        ('Описание', {'fields': ('description_ru', 'description_ky')}),
        ('Детали', {'fields': ('duration', 'genres', 'release_date', 'age_rating', 'country', 'director')}),
        ('Публикация', {'fields': ('is_active', 'is_new')}),
    )

    def poster_preview(self, obj):
        if obj.poster:
            return format_html('<img src="{}" style="height:80px;border-radius:4px;" />', obj.poster.url)
        return '—'
    poster_preview.short_description = 'Превью'

    def duration_display(self, obj):
        return obj.duration_display
    duration_display.short_description = 'Длительность'


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ('name', 'hall_type', 'rows', 'seats_per_row', 'total_seats')
    list_filter = ('hall_type',)
    actions = ['create_seats_action']

    def total_seats(self, obj):
        return obj.total_seats
    total_seats.short_description = 'Всего мест'

    def create_seats_action(self, request, queryset):
        for hall in queryset:
            hall.create_seats()
        self.message_user(request, f'Места созданы для {queryset.count()} зала(ов).')
    create_seats_action.short_description = 'Создать/пересоздать места'


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('hall', 'row', 'number')
    list_filter = ('hall',)
    search_fields = ('hall__name',)


@admin.register(Screening)
class ScreeningAdmin(admin.ModelAdmin):
    list_display = ('movie', 'hall', 'start_time', 'price', 'is_active', 'booked_count')
    list_filter = ('is_active', 'hall', 'movie')
    search_fields = ('movie__title_ru',)
    list_editable = ('price', 'is_active')
    date_hierarchy = 'start_time'

    def booked_count(self, obj):
        count = BookedSeat.objects.filter(
            booking__screening=obj,
            booking__status__in=['paid', 'reserved']
        ).count()
        return f'{count} / {obj.hall.total_seats}'
    booked_count.short_description = 'Продано мест'


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_code', 'screening', 'email', 'phone', 'total_amount', 'status', 'seats_count', 'created_at', 'is_admin_booking')
    list_filter = ('status', 'is_admin_booking', 'created_at')
    search_fields = ('booking_code', 'email', 'phone')
    readonly_fields = ('booking_code', 'total_amount', 'created_at', 'seats_display')
    inlines = [BookedSeatInline]

    def seats_count(self, obj):
        return obj.booked_seats.count()
    seats_count.short_description = 'Мест'

    def seats_display(self, obj):
        seats = obj.booked_seats.select_related('seat')
        return ', '.join([f'Ряд {bs.seat.row} М.{bs.seat.number}' for bs in seats])
    seats_display.short_description = 'Места'
