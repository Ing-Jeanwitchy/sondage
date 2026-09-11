"""
Tests automatisés — Application Accounts
Sondage Électoral Nord-Ouest, Haïti
"""
import pytest
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status as http_status
from accounts.models import User, UserRole, CandidateProfile, VoterProfile, SurveyConfig, DeviceRegistration, CommuneChoices, ElectivePostChoices


# ============================================================
# Tests Modèle User
# ============================================================

class TestUserModel(TestCase):
    """Tests du modèle utilisateur personnalisé (UUID, téléphone, rôles)."""

    def test_create_voter_user(self):
        """Créer un utilisateur avec le rôle VOTER par défaut."""
        user = User.objects.create_user(
            username='voter1',
            phone='+50937000001',
            password='TestPass123!'
        )
        assert user.role == UserRole.VOTER
        assert user.phone == '+50937000001'
        assert user.check_password('TestPass123!')
        assert user.pk is not None  # UUID auto-generated

    def test_create_admin_user(self):
        """Créer un utilisateur admin."""
        user = User.objects.create_user(
            username='admin1',
            phone='+50937000099',
            password='AdminPass123!',
            role=UserRole.ADMIN,
            is_staff=True
        )
        assert user.role == UserRole.ADMIN
        assert user.is_staff is True

    def test_create_candidate_user(self):
        """Créer un utilisateur candidat."""
        user = User.objects.create_user(
            username='candidate1',
            phone='+50937000010',
            password='CandPass123!',
            role=UserRole.CANDIDATE
        )
        assert user.role == UserRole.CANDIDATE

    def test_phone_is_unique(self):
        """Deux utilisateurs ne peuvent pas avoir le même numéro de téléphone."""
        User.objects.create_user(
            username='user_a',
            phone='+50937111111',
            password='pass123!'
        )
        with pytest.raises(Exception):
            User.objects.create_user(
                username='user_b',
                phone='+50937111111',
                password='pass456!'
            )

    def test_user_str_representation(self):
        """Le __str__ affiche le téléphone et le rôle."""
        user = User.objects.create_user(
            username='str_test',
            phone='+50937000002',
            password='pass123!'
        )
        assert '+50937000002' in str(user)


# ============================================================
# Tests Modèle SurveyConfig (Singleton)
# ============================================================

class TestSurveyConfigModel(TestCase):
    """Tests de la configuration singleton du sondage."""

    def test_get_config_creates_singleton(self):
        """get_config() crée une instance unique si elle n'existe pas."""
        config = SurveyConfig.get_config()
        assert config is not None
        assert config.pk == 1
        assert config.is_registration_open is True

    def test_get_config_returns_same_instance(self):
        """Appels multiples retournent la même instance."""
        config1 = SurveyConfig.get_config()
        config2 = SurveyConfig.get_config()
        assert config1.pk == config2.pk


# ============================================================
# Tests Modèle VoterProfile
# ============================================================

class TestVoterProfileModel(TestCase):
    """Tests du profil électeur avec commune verrouillée."""

    def test_create_voter_profile(self):
        """Créer un profil électeur avec commune verrouillée."""
        user = User.objects.create_user(
            username='voter_profile_test',
            phone='+50937000003',
            password='pass123!'
        )
        profile = VoterProfile.objects.create(
            user=user,
            commune=CommuneChoices.PORT_DE_PAIX
        )
        assert profile.commune == 'PORT_DE_PAIX'
        assert profile.commune_locked is True
        assert profile.has_voted_senateur is False
        assert profile.has_voted_depute is False
        assert profile.has_voted_maire is False


# ============================================================
# Tests Modèle DeviceRegistration
# ============================================================

class TestDeviceRegistrationModel(TestCase):
    """Tests de l'enregistrement des appareils."""

    def test_device_fingerprint_unique(self):
        """Deux enregistrements ne peuvent pas avoir le même fingerprint."""
        user = User.objects.create_user(
            username='device_test',
            phone='+50937000004',
            password='pass123!'
        )
        DeviceRegistration.objects.create(
            user=user,
            device_fingerprint='abc123unique',
            role=UserRole.VOTER
        )
        with pytest.raises(Exception):
            DeviceRegistration.objects.create(
                user=user,
                device_fingerprint='abc123unique',
                role=UserRole.VOTER
            )

    def test_is_device_registered_check(self):
        """Vérifier si un appareil est déjà enregistré."""
        user = User.objects.create_user(
            username='device_check',
            phone='+50937000005',
            password='pass123!'
        )
        DeviceRegistration.objects.create(
            user=user,
            device_fingerprint='device_xyz_789',
            role=UserRole.VOTER
        )
        assert DeviceRegistration.is_device_registered('device_xyz_789') is True
        assert DeviceRegistration.is_device_registered('unknown_device') is False
        assert DeviceRegistration.is_device_registered('') is False


# ============================================================
# Tests API Endpoints
# ============================================================

class TestHealthCheckAPI(TestCase):
    """Tests de l'endpoint health check."""

    def test_health_check_returns_200(self):
        """L'endpoint /api/health/ doit retourner 200 avec les infos du système."""
        client = APIClient()
        response = client.get('/api/health/')
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
        assert 'service' in data
        assert data['service'] == 'Sondage Électoral Nord-Ouest API'


class TestVoterRegistrationAPI(TestCase):
    """Tests de l'endpoint d'inscription des électeurs."""

    def test_register_voter_success(self):
        """Inscription réussie d'un électeur."""
        client = APIClient()
        response = client.post('/api/auth/register/voter/', {
            'phone': '+50937000020',
            'email': 'voter20@example.com',
            'password': 'SecurePass123!',
            'commune': 'PORT_DE_PAIX',
        }, format='json')
        assert response.status_code == http_status.HTTP_201_CREATED
        data = response.json()
        assert 'tokens' in data
        assert 'user' in data
        assert data['user']['role'] == 'VOTER'

    def test_register_voter_duplicate_phone(self):
        """Inscription avec un numéro déjà utilisé doit échouer."""
        client = APIClient()
        # 1ère inscription
        client.post('/api/auth/register/voter/', {
            'phone': '+50937000021',
            'email': 'voter21@example.com',
            'password': 'SecurePass123!',
            'commune': 'PORT_DE_PAIX',
        }, format='json')
        # 2e inscription (même téléphone)
        response = client.post('/api/auth/register/voter/', {
            'phone': '+50937000021',
            'email': 'voter21_other@example.com',
            'password': 'AnotherPass!',
            'commune': 'JEAN_RABEL',
        }, format='json')
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST


class TestLoginAPI(TestCase):
    """Tests de l'endpoint de connexion unifiée."""

    def test_login_success(self):
        """Connexion avec identifiants valides."""
        User.objects.create_user(
            username='login_test',
            phone='+50937000030',
            password='LoginPass123!',
            role=UserRole.VOTER
        )
        client = APIClient()
        response = client.post('/api/auth/login/', {
            'phone': '+50937000030',
            'password': 'LoginPass123!',
        }, format='json')
        assert response.status_code == 200
        data = response.json()
        assert 'tokens' in data
        assert data['user']['phone'] == '+50937000030'

    def test_login_wrong_password(self):
        """Connexion avec mauvais mot de passe doit échouer."""
        User.objects.create_user(
            username='login_fail',
            phone='+50937000031',
            password='CorrectPass!',
            role=UserRole.VOTER
        )
        client = APIClient()
        response = client.post('/api/auth/login/', {
            'phone': '+50937000031',
            'password': 'WrongPass!',
        }, format='json')
        assert response.status_code in (400, 401)


class TestPermissionsAPI(TestCase):
    """Tests des permissions d'accès basées sur les rôles."""

    def test_admin_endpoint_denied_for_voter(self):
        """Un électeur ne peut pas accéder aux endpoints admin."""
        user = User.objects.create_user(
            username='voter_perm',
            phone='+50937000040',
            password='VoterPass!',
            role=UserRole.VOTER
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/admin/candidates/')
        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_admin_endpoint_allowed_for_admin(self):
        """Un admin peut accéder aux endpoints admin."""
        admin = User.objects.create_user(
            username='admin_perm',
            phone='+50937000041',
            password='AdminPass!',
            role=UserRole.ADMIN,
            is_staff=True
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/admin/candidates/')
        assert response.status_code == 200

    def test_user_profile_requires_auth(self):
        """L'endpoint /api/auth/me/ nécessite une authentification."""
        client = APIClient()
        response = client.get('/api/auth/me/')
        assert response.status_code in (401, 403)


class TestSurveyConfigAPI(TestCase):
    """Tests de l'endpoint de configuration du sondage."""

    def test_survey_config_public_access(self):
        """La configuration du sondage est accessible publiquement."""
        client = APIClient()
        response = client.get('/api/survey-config/')
        assert response.status_code == 200
        data = response.json()
        assert 'is_registration_open' in data


class TestCandidateModerateAndDeletionAPI(TestCase):
    """Tests pou modirasyon ak efasman kandida pa admin."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_del_test',
            phone='+50937000088',
            password='AdminPass123!',
            role=UserRole.ADMIN,
            is_staff=True
        )
        self.cand_user = User.objects.create_user(
            username='cand_del_test',
            phone='+50937000089',
            password='CandPass123!',
            role=UserRole.CANDIDATE
        )
        self.candidate = CandidateProfile.objects.create(
            user=self.cand_user,
            first_name='Jean',
            last_name='Baptiste',
            post=ElectivePostChoices.SENATEUR,
            commune=CommuneChoices.PORT_DE_PAIX,
            slogan='Pwogrè ak Transparans',
            biography='Biyografi tès',
            platform_priorities='Edikasyon, Sante'
        )

    def test_admin_delete_candidate_via_action_post(self):
        """Admin ka efase yon kandida ak aksyon 'delete' nan endpoint moderate."""
        client = APIClient()
        client.force_authenticate(user=self.admin)
        response = client.post(f'/api/admin/candidates/{self.candidate.id}/moderate/', {
            'action': 'delete'
        }, format='json')
        assert response.status_code == http_status.HTTP_200_OK
        assert not CandidateProfile.objects.filter(id=self.candidate.id).exists()
        assert not User.objects.filter(id=self.cand_user.id).exists()

    def test_admin_delete_candidate_via_http_delete(self):
        """Admin ka efase yon kandida dirèkteman ak vèb HTTP DELETE."""
        client = APIClient()
        client.force_authenticate(user=self.admin)
        response = client.delete(f'/api/admin/candidates/{self.candidate.id}/moderate/')
        assert response.status_code == http_status.HTTP_200_OK
        assert not CandidateProfile.objects.filter(id=self.candidate.id).exists()

    def test_voter_cannot_delete_candidate(self):
        """Yon senp elektè pa gen dwa efase yon kandida."""
        voter = User.objects.create_user(
            username='voter_no_del',
            phone='+50937000087',
            password='VoterPass123!',
            role=UserRole.VOTER
        )
        client = APIClient()
        client.force_authenticate(user=voter)
        response = client.delete(f'/api/admin/candidates/{self.candidate.id}/moderate/')
        assert response.status_code == http_status.HTTP_403_FORBIDDEN
        assert CandidateProfile.objects.filter(id=self.candidate.id).exists()

    def test_admin_purge_test_data(self):
        """Admin ka netwaye tout done tès yo pou kite sèlman done reyèl."""
        from elections.models import Vote
        # Kreye yon fo vòt
        voter = User.objects.create_user(
            username='voter_purge_test',
            phone='+50937000086',
            password='VoterPass123!',
            role=UserRole.VOTER
        )
        Vote.objects.create(
            voter=voter,
            candidate=self.candidate,
            post=self.candidate.post,
            commune=self.candidate.commune
        )
        assert Vote.objects.count() >= 1

        client = APIClient()
        client.force_authenticate(user=self.admin)
        response = client.post('/api/admin/purge-test-data/', {'clear_pending_candidates': True}, format='json')
        assert response.status_code == http_status.HTTP_200_OK
        assert Vote.objects.count() == 0
        assert not User.objects.filter(role=UserRole.VOTER).exists()
