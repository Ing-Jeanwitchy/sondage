from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CandidateRegisterView, 
    CandidateListView, 
    UnifiedLoginView, 
    SurveyConfigView,
    VoterRegisterView,
    UserProfileView,
    AdminCandidateListView,
    AdminCandidateModerateView,
    AdminSurveyConfigView,
    AdminDashboardStatsView,
    CandidateDashboardView,
    CheckDeviceRegistrationView,
    VoterDashboardView
)

urlpatterns = [
    path('auth/register/candidate/', CandidateRegisterView.as_view(), name='register-candidate'),
    path('auth/register/voter/', VoterRegisterView.as_view(), name='register-voter'),
    path('auth/device/check/', CheckDeviceRegistrationView.as_view(), name='check-device-registration'),
    path('auth/login/', UnifiedLoginView.as_view(), name='unified-login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/me/', UserProfileView.as_view(), name='user-profile'),
    path('candidates/', CandidateListView.as_view(), name='candidate-list'),
    path('candidate/dashboard/', CandidateDashboardView.as_view(), name='candidate-dashboard'),
    path('voter/dashboard/', VoterDashboardView.as_view(), name='voter-dashboard'),
    path('survey-config/', SurveyConfigView.as_view(), name='survey-config'),
    path('admin/candidates/', AdminCandidateListView.as_view(), name='admin-candidates-list'),
    path('admin/candidates/<uuid:candidate_id>/moderate/', AdminCandidateModerateView.as_view(), name='admin-candidate-moderate'),
    path('admin/survey-config/', AdminSurveyConfigView.as_view(), name='admin-survey-config'),
    path('admin/stats/', AdminDashboardStatsView.as_view(), name='admin-stats'),
]
