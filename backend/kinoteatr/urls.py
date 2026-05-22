from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('cinema.api_urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('panel/', include('cinema.panel_urls')),
]

urlpatterns += i18n_patterns(
    path('', include('cinema.urls')),
    prefix_default_language=False,
)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
