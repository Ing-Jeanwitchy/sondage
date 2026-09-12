from django.urls import path
from .views import (
    BallotListView, 
    CastVoteView, 
    MyVotesReceiptView, 
    SurveyResultsView, 
    AdminVoteAuditView,
    PublicAnnouncementListView,
    AdminAnnouncementView,
    DonationCreateView,
    AdminDonationListView
)
from .export_views import (
    AdminExportResultsCSVView,
    AdminExportCandidatesCSVView,
    AdminExportVotesAuditCSVView
)

urlpatterns = [
    path('ballots/', BallotListView.as_view(), name='ballot-list'),
    path('vote/', CastVoteView.as_view(), name='cast-vote'),
    path('my-votes/', MyVotesReceiptView.as_view(), name='my-votes'),
    path('results/', SurveyResultsView.as_view(), name='survey-results'),
    path('announcements/', PublicAnnouncementListView.as_view(), name='public-announcements'),
    path('donations/', DonationCreateView.as_view(), name='donation-create'),
    path('admin/donations/', AdminDonationListView.as_view(), name='admin-donations'),
    path('admin/announcements/', AdminAnnouncementView.as_view(), name='admin-announcements'),
    path('admin/announcements/<uuid:pk>/', AdminAnnouncementView.as_view(), name='admin-announcements-detail'),
    path('admin/audit-votes/', AdminVoteAuditView.as_view(), name='admin-audit-votes'),
    path('admin/export/results-csv/', AdminExportResultsCSVView.as_view(), name='admin-export-results-csv'),
    path('admin/export/candidates-csv/', AdminExportCandidatesCSVView.as_view(), name='admin-export-candidates-csv'),
    path('admin/export/votes-audit-csv/', AdminExportVotesAuditCSVView.as_view(), name='admin-export-votes-audit-csv'),
]

