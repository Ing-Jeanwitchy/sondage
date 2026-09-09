"""
Configuration des URLs pour le projet de Sondage Électoral Nord-Ouest
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.utils import timezone
from django.db import connection

def health_check(request):
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False

    from accounts.models import User, SurveyConfig
    from elections.models import Vote

    config = SurveyConfig.get_config()

    return JsonResponse({
        "status": "healthy" if db_ok else "unhealthy",
        "service": "Sondage Électoral Nord-Ouest API",
        "version": "1.0.0",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": timezone.now().isoformat(),
        "is_registration_open": config.is_registration_open,
        "is_voting_open": config.is_voting_open,
        "registered_voters": User.objects.filter(role='VOTER').count(),
        "total_votes": Vote.objects.count(),
        "disclaimer": "SONDAJ PRÉLIMINÈ ET INDÉPENDANT – NON OFFICIEL"
    }, status=200 if db_ok else 503)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    path('api/', include('accounts.urls')),
    path('api/elections/', include('elections.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
