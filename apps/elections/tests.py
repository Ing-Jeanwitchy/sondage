"""
Tests automatisés — Application Elections
Sondage Électoral Nord-Ouest, Haïti
"""
import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status as http_status
from accounts.models import User, UserRole, CandidateProfile, VoterProfile, CommuneChoices, ElectivePostChoices, CandidateStatus
from elections.models import Vote


# ============================================================
# Tests Modèle Vote
# ============================================================

class TestVoteModel(TestCase):
    """Tests du modèle de vote avec contraintes d'unicité."""

    def setUp(self):
        """Créer un électeur et un candidat approuvé pour les tests."""
        self.voter_user = User.objects.create_user(
            username='voter_vote_test',
            phone='+50937100001',
            password='VoterPass!',
            role=UserRole.VOTER
        )
        self.voter_profile = VoterProfile.objects.create(
            user=self.voter_user,
            commune=CommuneChoices.PORT_DE_PAIX
        )
        self.candidate_user = User.objects.create_user(
            username='candidate_vote_test',
            phone='+50937100002',
            password='CandPass!',
            role=UserRole.CANDIDATE
        )
        self.candidate_profile = CandidateProfile.objects.create(
            user=self.candidate_user,
            first_name='Jean',
            last_name='Pierre',
            post=ElectivePostChoices.SENATEUR,
            commune='PORT_DE_PAIX',
            slogan='Pou Nòdwès',
            biography='Lidè kominotè',
            platform_priorities='Edikasyon, Sante, Agrikilti',
            status=CandidateStatus.APPROVED
        )

    def test_create_vote(self):
        """Créer un vote valide."""
        vote = Vote.objects.create(
            voter=self.voter_user,
            candidate=self.candidate_profile,
            post=ElectivePostChoices.SENATEUR,
            commune=CommuneChoices.PORT_DE_PAIX
        )
        assert vote.pk is not None
        assert vote.receipt_code is not None
        assert vote.post == 'SENATEUR'

    def test_unique_vote_per_voter_per_post(self):
        """Un électeur ne peut pas voter deux fois pour le même poste (contrainte DB)."""
        Vote.objects.create(
            voter=self.voter_user,
            candidate=self.candidate_profile,
            post=ElectivePostChoices.SENATEUR,
            commune=CommuneChoices.PORT_DE_PAIX
        )
        with pytest.raises(Exception):
            Vote.objects.create(
                voter=self.voter_user,
                candidate=self.candidate_profile,
                post=ElectivePostChoices.SENATEUR,
                commune=CommuneChoices.PORT_DE_PAIX
            )

    def test_voter_can_vote_for_different_posts(self):
        """Un électeur peut voter pour des postes différents."""
        # Créer un candidat pour un autre poste
        cand_user2 = User.objects.create_user(
            username='cand_maire',
            phone='+50937100003',
            password='CandPass!',
            role=UserRole.CANDIDATE
        )
        cand_maire = CandidateProfile.objects.create(
            user=cand_user2,
            first_name='Marie',
            last_name='Joseph',
            post=ElectivePostChoices.MAIRE,
            commune='PORT_DE_PAIX',
            slogan='Chanjman',
            biography='Enseignante',
            platform_priorities='Edikasyon, Enfrastrikti',
            status=CandidateStatus.APPROVED
        )
        vote1 = Vote.objects.create(
            voter=self.voter_user,
            candidate=self.candidate_profile,
            post=ElectivePostChoices.SENATEUR,
            commune=CommuneChoices.PORT_DE_PAIX
        )
        vote2 = Vote.objects.create(
            voter=self.voter_user,
            candidate=cand_maire,
            post=ElectivePostChoices.MAIRE,
            commune=CommuneChoices.PORT_DE_PAIX
        )
        assert vote1.pk != vote2.pk
        assert Vote.objects.filter(voter=self.voter_user).count() == 2

    def test_vote_str_representation(self):
        """Le __str__ du vote affiche le poste et le téléphone."""
        vote = Vote.objects.create(
            voter=self.voter_user,
            candidate=self.candidate_profile,
            post=ElectivePostChoices.SENATEUR,
            commune=CommuneChoices.PORT_DE_PAIX
        )
        vote_str = str(vote)
        assert '+50937100001' in vote_str


# ============================================================
# Tests API Elections
# ============================================================

class TestResultsAPI(TestCase):
    """Tests de l'endpoint des résultats publics."""

    def test_results_accessible_without_auth(self):
        """Les résultats sont accessibles publiquement (IsAuthenticatedOrReadOnly)."""
        client = APIClient()
        response = client.get('/api/elections/results/')
        assert response.status_code == 200

    def test_results_structure(self):
        """La réponse des résultats contient la bonne structure."""
        client = APIClient()
        response = client.get('/api/elections/results/')
        data = response.json()
        assert isinstance(data, dict)


class TestBallotAPI(TestCase):
    """Tests de l'endpoint des bulletins de vote."""

    def test_ballots_require_auth(self):
        """Les bulletins nécessitent une authentification."""
        client = APIClient()
        response = client.get('/api/elections/ballots/')
        assert response.status_code in (401, 403)

    def test_ballots_accessible_with_auth(self):
        """Un utilisateur authentifié peut voir les bulletins."""
        user = User.objects.create_user(
            username='ballot_test',
            phone='+50937200001',
            password='BallotPass!',
            role=UserRole.VOTER
        )
        VoterProfile.objects.create(
            user=user,
            commune=CommuneChoices.JEAN_RABEL
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/elections/ballots/')
        assert response.status_code == 200
        data = response.json()
        assert 'ballots' in data


class TestCastVoteAPI(TestCase):
    """Tests de l'endpoint de soumission de vote."""

    def setUp(self):
        """Créer les données nécessaires pour voter."""
        self.voter = User.objects.create_user(
            username='cast_voter',
            phone='+50937300001',
            password='VotePass!',
            role=UserRole.VOTER
        )
        self.voter_profile = VoterProfile.objects.create(
            user=self.voter,
            commune=CommuneChoices.PORT_DE_PAIX
        )
        self.candidate_user = User.objects.create_user(
            username='cast_candidate',
            phone='+50937300002',
            password='CandPass!',
            role=UserRole.CANDIDATE
        )
        self.candidate = CandidateProfile.objects.create(
            user=self.candidate_user,
            first_name='Pierre',
            last_name='Louis',
            post=ElectivePostChoices.SENATEUR,
            commune='PORT_DE_PAIX',
            slogan='Ansanm',
            biography='Avoka',
            platform_priorities='Jistis, Sante',
            status=CandidateStatus.APPROVED
        )

    def test_cast_vote_requires_auth(self):
        """Voter nécessite une authentification."""
        client = APIClient()
        response = client.post('/api/elections/vote/', {
            'candidate_id': str(self.candidate.id),
            'post': 'SENATEUR'
        }, format='json')
        assert response.status_code in (401, 403)


class TestAuditAPI(TestCase):
    """Tests de l'endpoint d'audit admin des votes."""

    def test_audit_denied_for_non_admin(self):
        """L'audit est inaccessible pour un non-admin."""
        voter = User.objects.create_user(
            username='audit_voter',
            phone='+50937400001',
            password='AuditPass!',
            role=UserRole.VOTER
        )
        client = APIClient()
        client.force_authenticate(user=voter)
        response = client.get('/api/elections/admin/audit-votes/')
        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_audit_accessible_for_admin(self):
        """L'audit est accessible pour un admin."""
        admin = User.objects.create_user(
            username='audit_admin',
            phone='+50937400002',
            password='AdminPass!',
            role=UserRole.ADMIN,
            is_staff=True
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/elections/admin/audit-votes/')
        assert response.status_code == 200
