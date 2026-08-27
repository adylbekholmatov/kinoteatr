from django import forms
from .models import Movie, Genre, Screening, Hall, Booking


FIELD_CLASS = 'form-control bg-dark text-light border-secondary'
SELECT_CLASS = 'form-select bg-dark text-light border-secondary'


class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = [
            'title_ru', 'title_ky',
            'description_ru', 'description_ky',
            'poster', 'trailer_url',
            'duration', 'genres', 'release_date',
            'age_rating', 'country', 'director',
            'is_active', 'is_new',
        ]
        widgets = {
            'title_ru': forms.TextInput(attrs={'class': FIELD_CLASS, 'placeholder': 'Название на русском'}),
            'title_ky': forms.TextInput(attrs={'class': FIELD_CLASS, 'placeholder': 'Аталышы кыргызча'}),
            'description_ru': forms.Textarea(attrs={'class': FIELD_CLASS, 'rows': 5, 'placeholder': 'Описание на русском (необязательно)'}),
            'description_ky': forms.Textarea(attrs={'class': FIELD_CLASS, 'rows': 5, 'placeholder': 'Сүрөттөмө кыргызча (милдеттүү эмес)'}),
            'poster': forms.ClearableFileInput(attrs={'class': 'form-control bg-dark text-light border-secondary'}),
            'trailer_url': forms.URLInput(attrs={'class': FIELD_CLASS, 'placeholder': 'https://youtube.com/watch?v=...'}),
            'duration': forms.NumberInput(attrs={'class': FIELD_CLASS, 'placeholder': 'Длительность в минутах'}),
            'genres': forms.CheckboxSelectMultiple(),
            'release_date': forms.DateInput(attrs={'class': FIELD_CLASS, 'type': 'date'}),
            'age_rating': forms.Select(attrs={'class': SELECT_CLASS}),
            'country': forms.TextInput(attrs={'class': FIELD_CLASS, 'placeholder': 'Страна производства'}),
            'director': forms.TextInput(attrs={'class': FIELD_CLASS, 'placeholder': 'Имя режиссёра'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_new': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description_ru'].required = False
        self.fields['description_ky'].required = False
        self.fields['title_ky'].required = False


class ScreeningForm(forms.ModelForm):
    class Meta:
        model = Screening
        fields = ['movie', 'hall', 'start_time', 'price', 'is_active']
        widgets = {
            'movie': forms.Select(attrs={'class': SELECT_CLASS}),
            'hall': forms.Select(attrs={'class': SELECT_CLASS}),
            'start_time': forms.DateTimeInput(
                attrs={'class': FIELD_CLASS, 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'price': forms.NumberInput(attrs={'class': FIELD_CLASS, 'placeholder': '0.00', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_time'].input_formats = ['%Y-%m-%dT%H:%M']


class HallForm(forms.ModelForm):
    class Meta:
        model = Hall
        fields = ['name', 'hall_type', 'rows', 'seats_per_row']
        widgets = {
            'name': forms.TextInput(attrs={'class': FIELD_CLASS, 'placeholder': 'Напр. Зал №1'}),
            'hall_type': forms.Select(attrs={'class': SELECT_CLASS}),
            'rows': forms.NumberInput(attrs={'class': FIELD_CLASS, 'placeholder': 'Количество рядов', 'min': 1}),
            'seats_per_row': forms.NumberInput(attrs={'class': FIELD_CLASS, 'placeholder': 'Мест в ряду', 'min': 1}),
        }


class BookingStatusForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': SELECT_CLASS}),
        }
