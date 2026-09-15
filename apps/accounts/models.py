import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Sipè Administratè'
    MODERATOR = 'MODERATOR', 'Moderatè / Analis Dosye'
    OPERATOR = 'OPERATOR', 'Operatè Saisie'
    COMMUNICATOR = 'COMMUNICATOR', 'Ofisye Kominikasyon'
    CANDIDATE = 'CANDIDATE', 'Kandida'
    VOTER = 'VOTER', 'Patisipan / Électeur'

class ElectivePostChoices(models.TextChoices):
    SENATEUR = 'SENATEUR', 'Sénateur (Département du Nord-Ouest)'
    DEPUTE = 'DEPUTE', 'Député (Circonscription)'
    MAIRE = 'MAIRE', 'Maire (Commune)'
    CASEC = 'CASEC', 'CASEC (Section Communale)'
    ASEC = 'ASEC', 'ASEC (Section Communale)'
    DELEGUE_VILLE = 'DELEGUE_VILLE', 'Délégué de Ville (Ville / Quartier)'

class CommuneChoices(models.TextChoices):
    PORT_DE_PAIX = 'PORT_DE_PAIX', 'Port-de-Paix'
    SAINT_LOUIS_DU_NORD = 'SAINT_LOUIS_DU_NORD', 'Saint-Louis-du-Nord'
    JEAN_RABEL = 'JEAN_RABEL', 'Jean-Rabel'
    MOLE_SAINT_NICOLAS = 'MOLE_SAINT_NICOLAS', 'Môle-Saint-Nicolas'
    BOMBARDOPOLIS = 'BOMBARDOPOLIS', 'Bombardopolis'
    BAIE_DE_HENNE = 'BAIE_DE_HENNE', 'Baie-de-Henne'
    BASSIN_BLEU = 'BASSIN_BLEU', 'Bassin-Bleu'
    ANSE_A_FOLEUR = 'ANSE_A_FOLEUR', 'Anse-à-Foleur'
    CHANSOLME = 'CHANSOLME', 'Chansolme'
    LA_TORTUE = 'LA_TORTUE', 'La Tortue'

class CandidateStatus(models.TextChoices):
    PENDING = 'PENDING', 'En attente'
    APPROVED = 'APPROVED', 'Approuvé'
    REJECTED = 'REJECTED', 'Rejeté'
    DISABLED = 'DISABLED', 'Désactivé'

class User(AbstractUser):
    """
    Modèle utilisateur personnalisé avec UUID, téléphone unique et gestion des rôles.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(
        max_length=25,
        unique=True,
        db_index=True,
        verbose_name="Numéro de téléphone",
        help_text="Format international ou local (ex: +509 3700 0000 ou 37000000)"
    )
    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Adrès Imèl Inik",
        help_text="Chak kont dwe gen yon adrès imèl inik"
    )
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.VOTER,
        verbose_name="Rôle"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Compte vérifié"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.email:
            self.email = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.phone} ({self.get_role_display()})"


class CandidateProfile(models.Model):
    """
    Profil officiel de candidature d'un citoyen pour le sondage électoral.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='candidate_profile',
        verbose_name="Compte utilisateur"
    )
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom de famille")
    email = models.EmailField(
        blank=True, 
        default='', 
        verbose_name="Adrès Imèl Ofisyèl Kandida a"
    )
    
    post = models.CharField(
        max_length=30,
        choices=ElectivePostChoices.choices,
        verbose_name="Poste électif"
    )
    commune = models.CharField(
        max_length=100,
        verbose_name="Commune de rattachement"
    )
    section_or_city = models.CharField(
        max_length=150,
        blank=True,
        default='',
        verbose_name="Section communale ou Ville / Quartier",
        help_text="Obligatoire pour les postes de CASEC, ASEC ou Délégué de Ville"
    )
    
    photo = models.ImageField(
        upload_to='candidates/',
        blank=True,
        null=True,
        verbose_name="Photo officielle"
    )
    slogan = models.CharField(max_length=255, verbose_name="Slogan de campagne")
    biography = models.TextField(verbose_name="Biographie & Parcours")
    platform_priorities = models.TextField(
        verbose_name="Priorités / Programme",
        help_text="Les 3 à 4 axes majeurs de votre programme"
    )
    
    # Chan Kartèl 3 Moun (sitou pou Mèri / Majistra ak CASEC)
    cartel_name = models.CharField(
        max_length=150,
        blank=True,
        default='',
        verbose_name="Non Kartèl la / Bannè Politik",
        help_text="Egzanp : Kartèl Tèt Ansanm pou Pòdepè"
    )
    cartel_member2_name = models.CharField(
        max_length=150,
        blank=True,
        default='',
        verbose_name="1e Majistra Adjwen (1er Adjoint)",
        help_text="Non ak Prenon dezyèm manm kartèl la"
    )
    cartel_member3_name = models.CharField(
        max_length=150,
        blank=True,
        default='',
        verbose_name="2e Majistra Adjwen (2ème Adjoint)",
        help_text="Non ak Prenon twazyèm manm kartèl la"
    )
    
    status = models.CharField(
        max_length=20,
        choices=CandidateStatus.choices,
        default=CandidateStatus.PENDING,
        verbose_name="Statut de la candidature"
    )
    rejection_reason = models.TextField(
        blank=True,
        default='',
        verbose_name="Motif de rejet ou observation"
    )
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de validation"
    )
    withdrawal_requested = models.BooleanField(
        default=False,
        verbose_name="Demann retrè soumèt"
    )
    withdrawal_reason = models.TextField(
        blank=True,
        default='',
        verbose_name="Rezon retrè kandidati a"
    )
    withdrawal_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Dat demand retrè a"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil Candidat"
        verbose_name_plural = "Profils Candidats"
        ordering = ['-created_at']

    def get_commune_display(self):
        choice_dict = dict(CommuneChoices.choices)
        return choice_dict.get(self.commune, self.commune)

    def __str__(self):
        return f"{self.first_name} {self.last_name} – {self.get_post_display()} ({self.get_status_display()})"


class VoterProfile(models.Model):
    """
    Profil elektè / patisipan ak komin li verouye definitivman.
    Pwoteksyon kont magouy ak vòt nan plizyè komin.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='voter_profile',
        verbose_name="Koneksyon itilizatè"
    )
    commune = models.CharField(
        max_length=50,
        choices=CommuneChoices.choices,
        verbose_name="Komin de rezidans (Verouye)"
    )
    commune_locked = models.BooleanField(
        default=True,
        verbose_name="Komin verouye definitivman",
        help_text="Yon fwa enskri, patisipan an pa ka chanje komin li ankò"
    )
    # Drapo kont doub vòt pa pòs elektif
    has_voted_senateur = models.BooleanField(default=False, verbose_name="Vote pou Sénateur")
    has_voted_depute = models.BooleanField(default=False, verbose_name="Vote pou Député")
    has_voted_maire = models.BooleanField(default=False, verbose_name="Vote pou Maire")
    has_voted_casec = models.BooleanField(default=False, verbose_name="Vote pou CASEC")
    has_voted_delegue = models.BooleanField(default=False, verbose_name="Vote pou Délégué de Ville")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil Patisipan / Elektè"
        verbose_name_plural = "Profils Patisipan yo"
        ordering = ['-created_at']

    def __str__(self):
        return f"Patisipan {self.user.phone} – Komin {self.get_commune_display()}"


class SurveyConfig(models.Model):
    """
    Konfigirasyon global pou peryòd ak dat limit sondaj la.
    Bloke otomatikman tout enskripsyon depi dat limit la rive nan bout li.
    """
    is_registration_open = models.BooleanField(
        default=True,
        verbose_name="Enskripsyon kandida yo louvri ?"
    )
    registration_deadline = models.DateTimeField(
        verbose_name="Dat & Lè limit enskripsyon kandida yo"
    )
    is_voting_open = models.BooleanField(
        default=False,
        verbose_name="Faz vòt la louvri ?"
    )

    # Konfigirasyon Peman Donasyon Sitwayen (Super Admin jere l)
    donation_moncash_number = models.CharField(
        max_length=50, 
        blank=True, 
        default='+509 37 00 0000', 
        verbose_name="Nimewo MonCash"
    )
    donation_moncash_name = models.CharField(
        max_length=150, 
        blank=True, 
        default='Kowòdinasyon Sondaj Nòdwès', 
        verbose_name="Non Mèt Kont MonCash"
    )
    donation_natcash_number = models.CharField(
        max_length=50, 
        blank=True, 
        default='+509 40 00 0000', 
        verbose_name="Nimewo Natcash"
    )
    donation_natcash_name = models.CharField(
        max_length=150, 
        blank=True, 
        default='Kowòdinasyon Sondaj Nòdwès', 
        verbose_name="Non Mèt Kont Natcash"
    )
    donation_zelle_info = models.CharField(
        max_length=150, 
        blank=True, 
        default='sondagenordouest@gmail.com', 
        verbose_name="Imèl / Nimewo Zelle"
    )
    donation_zelle_name = models.CharField(
        max_length=150, 
        blank=True, 
        default='Nord-Ouest Citizen Civic Initiative', 
        verbose_name="Non Mèt Kont Zelle"
    )
    donation_cashapp_tag = models.CharField(
        max_length=100, 
        blank=True, 
        default='$SondageNordOuest', 
        verbose_name="Tag CashApp ($cashtag)"
    )
    donation_bank_info = models.TextField(
        blank=True, 
        default='Unibank HTG: 123-4567-890123 | Sogebank USD: 987-6543-210987', 
        verbose_name="Enfòmasyon Kont Labank"
    )
    donation_bank_name = models.CharField(
        max_length=150, 
        blank=True, 
        default='Inisyativ Sitwayen Nòdwès', 
        verbose_name="Non Mèt Kont Labank"
    )

    show_official_publications = models.BooleanField(
        default=True,
        verbose_name="Afiche Seksyon Kominike ak Piblikasyon yo sou Paj Akèy ?"
    )

    # Kontak Sipò pou seksyon "Bezwen Èd pou Fè Don an ?"
    support_whatsapp = models.CharField(
        max_length=30,
        blank=True,
        default='+50937000000',
        verbose_name="Nimewo WhatsApp Sipò (fòma entènasyonal, ex: +50937000000)"
    )
    support_email = models.EmailField(
        blank=True,
        default='sondagenordouest@gmail.com',
        verbose_name="Imèl Sipò Ofisyèl"
    )

    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        verbose_name = "Konfigirasyon Sondaj la"
        verbose_name_plural = "Konfigirasyon Sondaj la"

    @classmethod
    def get_config(cls):
        from django.utils import timezone
        from datetime import timedelta
        # Default deadline: 5 jou apati kounye a si li poko defini
        config, created = cls.objects.get_or_create(id=1, defaults={
            'registration_deadline': timezone.now() + timedelta(days=5, hours=12),
            'is_registration_open': True
        })
        return config

    def is_expired(self):
        from django.utils import timezone
        if not self.is_registration_open:
            return True
        return timezone.now() >= self.registration_deadline


class DeviceRegistration(models.Model):
    """
    Modèl sekirite pou anpeche menm aparèy la anrejistre plizyè fwa.
    Règleman: 1 Aparèy Fizik = 1 Sèl Enskripsyon sou tout platfòm nan.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_fingerprint = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        verbose_name="Anpwent inik aparèy la (Device Fingerprint)"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='device_registrations',
        verbose_name="Kont itilizatè anrejistre"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Adrès IP aparèy la"
    )
    user_agent = models.TextField(
        blank=True,
        default='',
        verbose_name="User-Agent aparèy la"
    )
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        verbose_name="Ròl nan enskripsyon an"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dat enskripsyon aparèy la")

    class Meta:
        verbose_name = "Enskripsyon Aparèy"
        verbose_name_plural = "Enskripsyon Aparèy yo"
        ordering = ['-created_at']

    def __str__(self):
        return f"Aparèy [{self.device_fingerprint[:12]}...] - {self.user.phone} ({self.role})"

    @classmethod
    def is_device_registered(cls, fingerprint):
        if not fingerprint:
            return False
        return cls.objects.filter(device_fingerprint=fingerprint).exists()

