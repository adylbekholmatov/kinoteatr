from django.urls import path
from . import api_views

urlpatterns = [
    path('token/', api_views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', api_views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('screenings/', api_views.ScreeningListAPI.as_view(), name='api_screenings'),
    path('screenings/<int:pk>/seats/', api_views.ScreeningSeatMapAPI.as_view(), name='api_seat_map'),
    path('bookings/', api_views.CreateBookingAPI.as_view(), name='api_create_booking'),
    path('bookings/<str:code>/', api_views.BookingDetailAPI.as_view(), name='api_booking_detail'),
    path('movies/', api_views.MovieListAPI.as_view(), name='api_movies'),
]
