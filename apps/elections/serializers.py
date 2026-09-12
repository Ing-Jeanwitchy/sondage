from rest_framework import serializers
from accounts.models import CandidateProfile, ElectivePostChoices, CommuneChoices
from .models import Vote

class BallotCandidateSerializer(serializers.ModelSerializer):
    """
    Serializer pou kandida ki kalifye pou parèt sou biltan vòt la.
    """
    name = serializers.SerializerMethodField()
    commune_display = serializers.CharField(source='get_commune_display', read_only=True)
    post_display = serializers.CharField(source='get_post_display', read_only=True)

    class Meta:
        model = CandidateProfile
        fields = [
            'id', 'name', 'first_name', 'last_name',
            'post', 'post_display', 'commune', 'commune_display',
            'section_or_city', 'photo', 'slogan', 'biography',
            'platform_priorities'
        ]

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class CastVoteSerializer(serializers.Serializer):
    """
    Serializer pou soumèt yon vòt pou yon kandida avèk verifikasyon anpwent aparèy.
    """
    candidate_id = serializers.UUIDField(required=True)
    post = serializers.ChoiceField(choices=ElectivePostChoices.choices, required=True)
    device_fingerprint = serializers.CharField(max_length=128, required=False, allow_blank=True, default='')


class VoteReceiptSerializer(serializers.ModelSerializer):
    """
    Serializer pou resi ofisyèl vòt la.
    """
    post_display = serializers.CharField(source='get_post_display', read_only=True)
    commune_display = serializers.CharField(source='get_commune_display', read_only=True)
    candidate_name = serializers.SerializerMethodField()

    class Meta:
        model = Vote
        fields = [
            'id', 'receipt_code', 'post', 'post_display',
            'commune', 'commune_display', 'candidate_name', 'created_at'
        ]
        read_only_fields = fields

    def get_candidate_name(self, obj):
        if obj.candidate:
            return f"{obj.candidate.first_name} {obj.candidate.last_name}".strip()
        return "Kandida Konfime"


class PublicAnnouncementSerializer(serializers.ModelSerializer):
    """
    Serializer pou piblikasyon, kominike ak anons ofisyèl.
    """
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    author_phone = serializers.CharField(source='author.phone', read_only=True, default='')

    class Meta:
        from .models import PublicAnnouncement
        model = PublicAnnouncement
        fields = [
            'id', 'title', 'content', 'category', 'category_display',
            'author_name', 'author_phone', 'is_published',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DonationSerializer(serializers.ModelSerializer):
    """
    Serializer pou fòmilè donasyon sitwayen an.
    """
    class Meta:
        from .models import Donation
        model = Donation
        fields = [
            'id', 'donor_name', 'donor_contact', 'amount', 'currency',
            'payment_method', 'transaction_reference', 'message', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


