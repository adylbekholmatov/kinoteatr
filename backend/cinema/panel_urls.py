from django.urls import path
from . import panel_views

urlpatterns = [
    path('', panel_views.panel_dashboard, name='panel_dashboard'),

    # Movies
    path('movies/', panel_views.panel_movies, name='panel_movies'),
    path('movies/add/', panel_views.panel_movie_add, name='panel_movie_add'),
    path('movies/<int:pk>/edit/', panel_views.panel_movie_edit, name='panel_movie_edit'),
    path('movies/<int:pk>/delete/', panel_views.panel_movie_delete, name='panel_movie_delete'),

    # Screenings
    path('screenings/', panel_views.panel_screenings, name='panel_screenings'),
    path('screenings/add/', panel_views.panel_screening_add, name='panel_screening_add'),
    path('screenings/<int:pk>/edit/', panel_views.panel_screening_edit, name='panel_screening_edit'),
    path('screenings/<int:pk>/delete/', panel_views.panel_screening_delete, name='panel_screening_delete'),

    # Bookings
    path('bookings/', panel_views.panel_bookings, name='panel_bookings'),
    path('bookings/<int:pk>/', panel_views.panel_booking_detail, name='panel_booking_detail'),
    path('bookings/<int:pk>/status/', panel_views.panel_booking_status, name='panel_booking_status'),

    # Halls
    path('halls/', panel_views.panel_halls, name='panel_halls'),
    path('halls/add/', panel_views.panel_hall_add, name='panel_hall_add'),
    path('halls/<int:pk>/edit/', panel_views.panel_hall_edit, name='panel_hall_edit'),
    path('halls/<int:pk>/delete/', panel_views.panel_hall_delete, name='panel_hall_delete'),

    # Профиль / Безопасность
    path('change-password/', panel_views.panel_change_password, name='panel_change_password'),
]
