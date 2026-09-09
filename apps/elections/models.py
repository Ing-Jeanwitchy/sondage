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
