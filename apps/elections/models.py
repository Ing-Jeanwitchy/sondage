import uuid
from django.db import models
from django.conf import settings
from accounts.models import ElectivePostChoices, CommuneChoices, CandidateProfile

class Vote(models.Model):
    """
    Modèl Vòt Preliminè Sekirize.
    Kontrent inik sou (voter, post) anpeche nenpòt sitwayen vote 2 fwa pou menm pòs la.
    Resi vòt la (receipt_code) garanti konfidansyalite ak prèv patisipasyon.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Elektè ki vote a (One vote per post)
    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='votes',
        verbose_name="Patisipan / Elektè"
    )
    
    # Kandida li chwazi a
    candidate = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name='votes_received',
        verbose_name="Kandida chwazi"
    )
    
    # Pòs elektif vòt la
    post = models.CharField(
        max_length=30,
        choices=ElectivePostChoices.choices,
        verbose_name="Pòs Elektif"
    )
    
    # Komin elektè a te ye lè l t ap vote a (verouye)
    commune = models.CharField(
        max_length=50,
        choices=CommuneChoices.choices,
        verbose_name="Komin kote vòt la anrejistre"
    )
    
    # Kòd resi inik pou elektè a ka verifye vòt li san revele pou kiyès li te vote
    receipt_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Kòd Resi Vòt (UUID)"
    )
    
    # Hash IP anonimizé pou odit ak deteksyon fwod
    ip_hash = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name="Hachaj IP anonimize"
    )
    
    # Anpwent inik aparèy la pou anpeche menm aparèy la vote plizyè fwa
    device_fingerprint = models.CharField(
        max_length=128,
        blank=True,
        default='',
        db_index=True,
        verbose_name="Anpwent inik aparèy vòt la"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dat & Lè Vòt la")

    class Meta:
        verbose_name = "Vòt Preliminè"
        verbose_name_plural = "Vòt Preliminè yo"
        ordering = ['-created_at']
        constraints = [
            # Kontrent strik nan baz de done : 1 sèl vòt pou chak patisipan sou chak pòs elektif
            models.UniqueConstraint(
                fields=['voter', 'post'],
                name='unique_vote_per_voter_per_post'
            ),
            # Kontrent strik aparèy : 1 sèl vòt pou chak aparèy fizik sou chak pòs elektif
            models.UniqueConstraint(
                fields=['device_fingerprint', 'post'],
                condition=models.Q(device_fingerprint__gt=''),
                name='unique_vote_per_device_per_post'
            )
        ]

    def __str__(self):
        return f"Vòt {self.get_post_display()} pa {self.voter.phone} ({self.receipt_code})"


class AnnouncementCategory(models.TextChoices):
    COMMUNIQUE = 'COMMUNIQUE', 'Kominike Ofisyèl'
    ALERT = 'ALERT', 'Alèt Enpòtan'
    UPDATE = 'UPDATE', 'Mizajou Kalandriye'
    GENERAL = 'GENERAL', 'Enfòmasyon Jeneral'


class PublicAnnouncement(models.Model):
    """
    Modèl pou piblikasyon ak kominike ofisyèl Komisyon an oswa chaje kominikasyon an.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, verbose_name="Tit Pòs la")
    content = models.TextField(verbose_name="Kontni / Tèks Kominike a")
    category = models.CharField(
        max_length=30,
        choices=AnnouncementCategory.choices,
        default=AnnouncementCategory.COMMUNIQUE,
        verbose_name="Kategori"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='announcements',
        verbose_name="Otè"
    )
    author_name = models.CharField(
        max_length=150, 
        blank=True, 
        default="Komisyon Elektoral Nòdwès", 
        verbose_name="Non Otè a"
    )
    is_published = models.BooleanField(default=True, verbose_name="Pibliye")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dat kreyasyon")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dènye modifikasyon")

    class Meta:
        verbose_name = "Kominike & Piblikasyon"
        verbose_name_plural = "Kominike & Piblikasyon yo"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"


class Donation(models.Model):
    """
    Modèl pou anrejistre donasyon ak sipò sitwayen pou platfòm nan.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donor_name = models.CharField(max_length=150, verbose_name="Non Donatè")
    donor_contact = models.CharField(max_length=100, verbose_name="Telefòn oswa Imèl")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montan Don")
    currency = models.CharField(max_length=10, default="HTG", verbose_name="Deviz (HTG/USD)")
    payment_method = models.CharField(max_length=50, verbose_name="Metòd Peman")
    transaction_reference = models.CharField(max_length=120, blank=True, default='', verbose_name="Kòd Referans / Tranzaksyon")
    message = models.TextField(blank=True, default='', verbose_name="Mesaj Ankourajman")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dat Kreyasyon")

    class Meta:
        verbose_name = "Donasyon Sitwayen"
        verbose_name_plural = "Donasyon Sitwayen yo"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.donor_name} - {self.amount} {self.currency} ({self.payment_method})"
