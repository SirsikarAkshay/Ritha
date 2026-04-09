from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from arokah.services.views import WeatherView
from arokah.health import HealthCheckView
from arokah.config_view import ConfigView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/',                admin.site.urls),
    path('api/auth/',             include('auth_app.urls')),
    path('api/wardrobe/',         include('wardrobe.urls')),
    path('api/itinerary/',        include('itinerary.urls')),
    path('api/outfits/',          include('outfits.urls')),
    path('api/cultural/',         include('cultural.urls')),
    path('api/sustainability/',   include('sustainability.urls')),
    path('api/agents/',           include('agents.urls')),
    path('api/weather/',          WeatherView.as_view(),      name='weather'),
    path('api/calendar/',         include('calendar_sync.urls')),
    path('api/social/',           include('social.urls')),
    path('api/messages/',         include('messaging.urls')),
    path('api/shared-wardrobes/', include('shared_wardrobe.urls')),
    path('api/config',   ConfigView.as_view(),   name='config'),
    path('api/health/',           HealthCheckView.as_view(),  name='health'),
    # API Documentation
    path('api/schema/',           SpectacularAPIView.as_view(),        name='schema'),
    path('api/docs/',             SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/',            SpectacularRedocView.as_view(url_name='schema'),   name='redoc'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
