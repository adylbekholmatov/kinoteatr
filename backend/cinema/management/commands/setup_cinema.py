from django.core.management.base import BaseCommand
from cinema.models import Hall, Seat, Genre


class Command(BaseCommand):
    help = 'Создаёт залы, места и жанры для кинотеатра Байэл'

    def handle(self, *args, **options):
        # Жанры
        genres = [
            ('Боевик', 'Экшн'),
            ('Комедия', 'Комедия'),
            ('Драма', 'Драма'),
            ('Ужасы', 'Коркунуч'),
            ('Фантастика', 'Фантастика'),
            ('Мультфильм', 'Анимация'),
            ('Триллер', 'Триллер'),
            ('Романтика', 'Романтика'),
        ]
        for name_ru, name_ky in genres:
            Genre.objects.get_or_create(name_ru=name_ru, defaults={'name_ky': name_ky})
        self.stdout.write(self.style.SUCCESS(f'Создано {len(genres)} жанров'))

        # Залы
        halls_config = [
            ('Зал 1', 'regular', 6, 7),   # 42 места
            ('Зал 2', 'regular', 6, 7),   # 42 места
            ('Зал 3', 'regular', 6, 7),   # 42 места
            ('VIP Зал 1', 'vip', 4, 5),   # 20 мест
            ('VIP Зал 2', 'vip', 4, 5),   # 20 мест
            ('VIP Зал 3', 'vip', 4, 5),   # 20 мест
        ]

        for name, hall_type, rows, seats_per_row in halls_config:
            hall, created = Hall.objects.get_or_create(
                name=name,
                defaults={
                    'hall_type': hall_type,
                    'rows': rows,
                    'seats_per_row': seats_per_row,
                }
            )
            if created:
                hall.create_seats()
                self.stdout.write(self.style.SUCCESS(
                    f'Создан зал "{name}" ({rows}×{seats_per_row} = {rows*seats_per_row} мест)'
                ))
            else:
                self.stdout.write(f'Зал "{name}" уже существует')

        self.stdout.write(self.style.SUCCESS('\nНастройка кинотеатра Байэл завершена!'))
