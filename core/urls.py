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
    db_ok = False
    db_info = {}
    try:
        connection.ensure_connection()
        db_ok = True
        try:
            from django.apps import apps
            User = apps.get_model('accounts', 'User')
            SurveyConfig = apps.get_model('accounts', 'SurveyConfig')
            Vote = apps.get_model('elections', 'Vote')
            config = SurveyConfig.get_config()
            db_info = {
                "is_registration_open": config.is_registration_open,
                "is_voting_open": config.is_voting_open,
                "registered_voters": User.objects.filter(role='VOTER').count(),
                "total_votes": Vote.objects.count(),
            }
        except Exception as table_err:
            db_info = {"note": "Tables not migrated yet", "detail": str(table_err)}
    except Exception as conn_err:
        db_info = {"note": "DB not connected", "detail": str(conn_err)}

    return JsonResponse({
        "status": "healthy" if db_ok else "starting",
        "service": "Sondage Électoral Nord-Ouest API",
        "version": "1.0.0",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": timezone.now().isoformat(),
        "disclaimer": "SONDAJ PRÉLIMINÈ ET INDÉPENDANT – NON OFFICIEL",
        **db_info,
    }, status=200)


try:
    from elections.views import DonationCreateView, AdminDonationListView, AppTranslationView, AutoTranslateView
except ImportError:
    from apps.elections.views import DonationCreateView, AdminDonationListView, AppTranslationView, AutoTranslateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    path('api/', include('accounts.urls')),
    path('api/elections/', include('elections.urls')),
    path('api/translations/', AppTranslationView.as_view(), name='api-translations'),
    path('api/translations/auto-translate/', AutoTranslateView.as_view(), name='api-translations-auto'),
    path('api/donations/', DonationCreateView.as_view(), name='api-donations'),
    path('api/admin/donations/', AdminDonationListView.as_view(), name='api-admin-donations'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

from django.urls import re_path
from django.views.static import serve

if not settings.IS_CLOUDINARY_ACTIVE:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
elif settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

