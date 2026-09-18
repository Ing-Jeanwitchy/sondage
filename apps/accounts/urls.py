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
    AdminCandidateCreateView,
    AdminCandidateModerateView,
    AdminSurveyConfigView,
    AdminDashboardStatsView,
    AdminPurgeTestDataView,
    AdminResetDevicesView,
    AdminTeamListView,
    AdminTeamCreateView,
    AdminTeamDeleteView,
    AdminUserListView,
    AdminUserToggleActiveView,
    AdminUserResetPasswordView,
    AdminUserDeleteView,
    CandidateDashboardView,
    CheckDeviceRegistrationView,
    VoterDashboardView
)
try:
    from elections.views import AppTranslationView
except ImportError:
    from apps.elections.views import AppTranslationView

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
    path('admin/candidates/create/', AdminCandidateCreateView.as_view(), name='admin-candidate-create'),
    path('admin/candidates/<uuid:candidate_id>/moderate/', AdminCandidateModerateView.as_view(), name='admin-candidate-moderate'),
    path('admin/team/', AdminTeamListView.as_view(), name='admin-team-list'),
    path('admin/team/create/', AdminTeamCreateView.as_view(), name='admin-team-create'),
    path('admin/team/<uuid:user_id>/', AdminTeamDeleteView.as_view(), name='admin-team-delete'),
    path('admin/users/', AdminUserListView.as_view(), name='admin-users-list'),
    path('admin/users/<uuid:user_id>/toggle-active/', AdminUserToggleActiveView.as_view(), name='admin-users-toggle-active'),
    path('admin/users/<uuid:user_id>/reset-password/', AdminUserResetPasswordView.as_view(), name='admin-users-reset-password'),
    path('admin/users/<uuid:user_id>/delete/', AdminUserDeleteView.as_view(), name='admin-users-delete'),
    path('admin/survey-config/', AdminSurveyConfigView.as_view(), name='admin-survey-config'),
    path('admin/stats/', AdminDashboardStatsView.as_view(), name='admin-stats'),
    path('admin/purge-test-data/', AdminPurgeTestDataView.as_view(), name='admin-purge-test-data'),
    path('admin/devices/reset/', AdminResetDevicesView.as_view(), name='admin-devices-reset'),
    path('translations/', AppTranslationView.as_view(), name='accounts-translations'),
    path('elections/translations/', AppTranslationView.as_view(), name='accounts-elections-translations'),
]


