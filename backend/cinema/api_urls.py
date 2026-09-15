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
    # Pending receipts + confirm/reject (WPF)
    path('pending-receipts/', api_views.PendingReceiptsAPI.as_view(), name='api_pending_receipts'),
    path('bookings-admin/<int:pk>/confirm/', api_views.AdminConfirmBookingAPI.as_view(), name='api_confirm_booking'),
    path('bookings-admin/<int:pk>/reject/', api_views.AdminRejectBookingAPI.as_view(), name='api_reject_booking'),
    path('bookings-admin/<int:pk>/request-topup/', api_views.AdminRequestTopupAPI.as_view(), name='api_request_topup'),
    path('bookings-admin/<int:pk>/restore/', api_views.AdminRestoreBookingAPI.as_view(), name='api_restore_booking'),
    # Ticket verification (QR scanner)
    path('verify-ticket/', api_views.VerifyTicketAPI.as_view(), name='api_verify_ticket'),
    # User notifications (website)
    path('my-notifications/', api_views.UserNotificationsAPI.as_view(), name='api_notifications'),
]
