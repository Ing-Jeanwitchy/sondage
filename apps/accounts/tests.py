"""
Tests automatisés — Application Accounts
Sondage Électoral Nord-Ouest, Haïti
"""
import pytest
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status as http_status
from accounts.models import (
    User, UserRole, CandidateProfile, VoterProfile, SurveyConfig,
    DeviceRegistration, CommuneChoices, ElectivePostChoices, CandidateStatus
)


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

    def setUp(self):
        # Pa defo, pou tès enskripsyon elektè ki dwe reyisi, louvri faz vòt la
        config = SurveyConfig.get_config()
        config.is_voting_open = True
        config.save()

    def test_register_voter_blocked_during_candidate_phase(self):
        """Pandan faz enskripsyon kandida yo (vòt fèmen), oken elektè pa ka enskri."""
        config = SurveyConfig.get_config()
        config.is_voting_open = False
        config.save()

        client = APIClient()
        response = client.post('/api/auth/register/voter/', {
            'phone': '+50937000020',
            'email': 'voter20@example.com',
            'password': 'SecurePass123!',
            'commune': 'PORT_DE_PAIX',
        }, format='json')
        assert response.status_code == http_status.HTTP_403_FORBIDDEN
        assert 'poko louvri' in response.json().get('error', '').lower()

    def test_register_voter_success(self):
        """Inscription réussie d'un électeur lè faz vòt la louvri."""
        client = APIClient()
        response = client.post('/api/auth/register/voter/', {
            'phone': '+50937000020',
            'email': 'voter20@example.com',
            'password': 'SecurePass123!',
            'commune': 'PORT_DE_PAIX',
            'device_fingerprint': 'dev_test_unique_voter_fp_1'
        }, format='json')
        assert response.status_code == http_status.HTTP_201_CREATED
        data = response.json()
        assert 'tokens' in data
        assert 'user' in data
        assert data['user']['role'] == 'VOTER'

    def test_register_voter_duplicate_device_blocked(self):
        """Menm aparèy la pa ka anrejistre yon 2e kont (1 Aparèy = 1 Enskripsyon)."""
        client = APIClient()
        # 1ère inscription avec ce device
        client.post('/api/auth/register/voter/', {
            'phone': '+50937000020',
            'email': 'voter20@example.com',
            'password': 'SecurePass123!',
            'commune': 'PORT_DE_PAIX',
            'device_fingerprint': 'dev_test_shared_physical_device'
        }, format='json')

        # 2e inscription avec le même device
        response = client.post('/api/auth/register/voter/', {
            'phone': '+50937000022',
            'email': 'voter22@example.com',
            'password': 'SecurePass123!',
            'commune': 'JEAN_RABEL',
            'device_fingerprint': 'dev_test_shared_physical_device'
        }, format='json')
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert 'aparèy' in response.json().get('error', '').lower()

    def test_register_voter_duplicate_phone(self):
        """Inscription avec un numéro déjà utilisé doit échouer."""
        client = APIClient()
        # 1ère inscription
        client.post('/api/auth/register/voter/', {
            'phone': '+50937000021',
            'email': 'voter21@example.com',
            'password': 'SecurePass123!',
            'commune': 'PORT_DE_PAIX',
            'device_fingerprint': 'dev_test_phone_dup_1'
        }, format='json')
        # 2e inscription (même téléphone)
        response = client.post('/api/auth/register/voter/', {
            'phone': '+50937000021',
            'email': 'voter21_other@example.com',
            'password': 'AnotherPass!',
            'commune': 'JEAN_RABEL',
            'device_fingerprint': 'dev_test_phone_dup_2'
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


# ============================================================
# Tests Kolaboratè & Wòl RBAC (Admin, Moderatè, Operatè, Kominikatè)
# ============================================================

class TestTeamAndRBAC(TestCase):
    """
    Tests sistèm manm ekip ak pèmisyon pa wòl :
    - Moderatè ka modere kandida
    - Operatè ka kreye kandida dirèkteman
    - Kominikatè ka kreye pòs/kominike
    - Sipè Admin ka jere ekip la
    """

    def setUp(self):
        self.super_admin = User.objects.create_user(
            username='admin_boss',
            phone='+50930000000',
            password='AdminPass123!',
            role=UserRole.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.moderator = User.objects.create_user(
            username='mod_user',
            phone='+50937000050',
            password='ModPass123!',
            role=UserRole.MODERATOR,
            is_staff=True
        )
        self.operator = User.objects.create_user(
            username='op_user',
            phone='+50937000060',
            password='OpPass123!',
            role=UserRole.OPERATOR,
            is_staff=True
        )
        self.communicator = User.objects.create_user(
            username='com_user',
            phone='+50937000070',
            password='ComPass123!',
            role=UserRole.COMMUNICATOR,
            is_staff=True
        )
        self.voter = User.objects.create_user(
            username='citizen',
            phone='+50937000080',
            password='CitizenPass123!',
            role=UserRole.VOTER
        )

        cand_user = User.objects.create_user(
            username='cand_rbac',
            phone='+50937000090',
            password='CandPass123!',
            role=UserRole.CANDIDATE
        )
        self.candidate = CandidateProfile.objects.create(
            user=cand_user,
            first_name='Jean',
            last_name='Pierre',
            post=ElectivePostChoices.MAIRE,
            commune='PORT_DE_PAIX',
            status='PENDING'
        )

    def test_super_admin_create_team_member(self):
        """Sipè Admin ka kreye yon nouvo manm ekip."""
        client = APIClient()
        client.force_authenticate(user=self.super_admin)
        response = client.post('/api/admin/team/create/', {
            'phone': '+50937999999',
            'password': 'StaffPassword123!',
            'first_name': 'Marie',
            'last_name': 'Duval',
            'role': 'MODERATOR'
        }, format='json')
        assert response.status_code == http_status.HTTP_201_CREATED
        assert User.objects.filter(phone='+50937999999', role=UserRole.MODERATOR).exists()

    def test_moderator_cannot_create_team_member(self):
        """Moderatè pa gen dwa kreye lòt manm ekip."""
        client = APIClient()
        client.force_authenticate(user=self.moderator)
        response = client.post('/api/admin/team/create/', {
            'phone': '+50937888888',
            'password': 'StaffPassword123!',
            'first_name': 'Alex',
            'role': 'OPERATOR'
        }, format='json')
        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_moderator_can_approve_candidate(self):
        """Moderatè ka apwouve yon kandida."""
        client = APIClient()
        client.force_authenticate(user=self.moderator)
        response = client.post(f'/api/admin/candidates/{self.candidate.id}/moderate/', {
            'action': 'approve'
        }, format='json')
        assert response.status_code == http_status.HTTP_200_OK
        self.candidate.refresh_from_db()
        assert self.candidate.status == 'APPROVED'

    def test_operator_cannot_moderate_candidate(self):
        """Operatè pa ka apwouve/rejte dosye kandida."""
        client = APIClient()
        client.force_authenticate(user=self.operator)
        response = client.post(f'/api/admin/candidates/{self.candidate.id}/moderate/', {
            'action': 'approve'
        }, format='json')
        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_operator_can_create_candidate_directly(self):
        """Operatè ka ajoute yon kandida dirèkteman depi panèl la."""
        client = APIClient()
        client.force_authenticate(user=self.operator)
        response = client.post('/api/admin/candidates/create/', {
            'phone': '+50936112233',
            'first_name': 'Paul',
            'last_name': 'Destin',
            'post': 'SENATEUR',
            'commune': 'PORT_DE_PAIX',
            'slogan': 'Yon Nòdwès Pi Fò',
            'status': 'APPROVED'
        }, format='json')
        assert response.status_code == http_status.HTTP_201_CREATED
        assert CandidateProfile.objects.filter(first_name='Paul', last_name='Destin').exists()

    def test_communicator_can_publish_and_delete_announcement(self):
        """Kominikatè ka pibliye epi efase yon kominike."""
        client = APIClient()
        client.force_authenticate(user=self.communicator)
        # 1. Pibliye
        res = client.post('/api/elections/admin/announcements/', {
            'title': 'Ouvèti Ofisyèl Vòt la',
            'content': 'Vòt la louvri pou tout sitwayen nan 10 komin yo.',
            'category': 'COMMUNIQUE'
        }, format='json')
        assert res.status_code == http_status.HTTP_201_CREATED
        announcement_id = res.data['announcement']['id']

        # 2. Piblik ka wè l
        pub_client = APIClient()
        pub_res = pub_client.get('/api/elections/announcements/')
        assert pub_res.status_code == http_status.HTTP_200_OK
        assert len(pub_res.data) >= 1

        # 3. Kominikatè efase l
        del_res = client.delete(f'/api/elections/admin/announcements/{announcement_id}/')
        assert del_res.status_code == http_status.HTTP_200_OK


# ============================================================
# Tests Jesyon Itilizatè yo (Admin User Management)
# ============================================================

class TestAdminUserManagement(TestCase):
    """
    Tests pou nouvo modil jesyon itilizatè yo :
    - Lis tout itilizatè avèk filtè pa wòl ak rechèch
    - Bloke / debloke kont (toggle active)
    - Pwoteksyon Sipè Admin kont bloke oswa efasman
    - Reyinisyalize modpas itilizatè
    - Efase itilizatè
    """

    def setUp(self):
        self.super_admin = User.objects.create_user(
            username='admin_boss',
            phone='+50930000000',
            password='AdminPass123!',
            role=UserRole.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.voter = User.objects.create_user(
            username='voter_test',
            phone='+50937112233',
            password='VoterPass123!',
            first_name='Jean',
            last_name='Baptiste',
            role=UserRole.VOTER
        )
        VoterProfile.objects.create(
            user=self.voter,
            commune=CommuneChoices.PORT_DE_PAIX
        )
        self.cand_user = User.objects.create_user(
            username='cand_test',
            phone='+50938112233',
            password='CandPass123!',
            first_name='Marie',
            last_name='Clair',
            role=UserRole.CANDIDATE
        )
        CandidateProfile.objects.create(
            user=self.cand_user,
            first_name='Marie',
            last_name='Clair',
            post=ElectivePostChoices.SENATEUR,
            commune=CommuneChoices.PORT_DE_PAIX,
            slogan='Pwogrè pou Nòdwès',
            biography='Enjenyè',
            platform_priorities='Edikasyon',
            status=CandidateStatus.APPROVED
        )

    def test_admin_can_list_users_with_counts(self):
        """Sipè admin ka jwenn lis tout itilizatè ak statistik."""
        client = APIClient()
        client.force_authenticate(user=self.super_admin)
        res = client.get('/api/admin/users/')
        assert res.status_code == http_status.HTTP_200_OK
        assert 'users' in res.data
        assert 'counts' in res.data
        assert res.data['counts']['total'] >= 3
        assert res.data['counts']['voters'] >= 1
        assert res.data['counts']['candidates'] >= 1

    def test_admin_can_filter_and_search_users(self):
        """Admin ka filtre itilizatè pa wòl ak rechèch tèks."""
        client = APIClient()
        client.force_authenticate(user=self.super_admin)
        # Filtre pa VOTER
        res_voter = client.get('/api/admin/users/?role=VOTER')
        assert res_voter.status_code == http_status.HTTP_200_OK
        assert all(u['role'] == 'VOTER' for u in res_voter.data['users'])

        # Rechèch Jean
        res_search = client.get('/api/admin/users/?q=Jean')
        assert res_search.status_code == http_status.HTTP_200_OK
        assert any('Jean' in u['full_name'] for u in res_search.data['users'])

    def test_admin_can_toggle_user_active_status(self):
        """Admin ka bloke oswa debloke yon kont."""
        client = APIClient()
        client.force_authenticate(user=self.super_admin)

        # 1. Bloke
        res = client.post(f'/api/admin/users/{self.voter.id}/toggle-active/')
        assert res.status_code == http_status.HTTP_200_OK
        assert res.data['is_active'] is False
        self.voter.refresh_from_db()
        assert self.voter.is_active is False

        # 2. Debloke
        res2 = client.post(f'/api/admin/users/{self.voter.id}/toggle-active/')
        assert res2.status_code == http_status.HTTP_200_OK
        assert res2.data['is_active'] is True

    def test_super_admin_cannot_be_blocked(self):
        """Pwoteksyon : Sipè Admin prensipal la pa ka bloke."""
        client = APIClient()
        client.force_authenticate(user=self.super_admin)
        res = client.post(f'/api/admin/users/{self.super_admin.id}/toggle-active/')
        assert res.status_code in [http_status.HTTP_400_BAD_REQUEST, http_status.HTTP_403_FORBIDDEN]

    def test_admin_can_reset_user_password(self):
        """Admin ka chanje modpas yon itilizatè."""
        client = APIClient()
        client.force_authenticate(user=self.super_admin)
        res = client.post(f'/api/admin/users/{self.voter.id}/reset-password/', {
            'new_password': 'NewSecurePassword123!'
        }, format='json')
        assert res.status_code == http_status.HTTP_200_OK
        self.voter.refresh_from_db()
        assert self.voter.check_password('NewSecurePassword123!')

    def test_admin_can_delete_user(self):
        """Admin ka efase yon kont itilizatè."""
        client = APIClient()
        client.force_authenticate(user=self.super_admin)
        res = client.delete(f'/api/admin/users/{self.voter.id}/delete/')
        assert res.status_code == http_status.HTTP_200_OK
        assert not User.objects.filter(id=self.voter.id).exists()


