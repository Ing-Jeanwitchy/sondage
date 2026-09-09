import hashlib
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.html import strip_tags
from .models import (
    CandidateProfile, 
    VoterProfile, 
    UserRole, 
    ElectivePostChoices, 
    CommuneChoices, 
    CandidateStatus,
    DeviceRegistration
)

User = get_user_model()

class CandidateProfileSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'affichage public et privé du profil d'un candidat.
    """
    post_display = serializers.CharField(source='get_post_display', read_only=True)
    commune_display = serializers.CharField(source='get_commune_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = CandidateProfile
        fields = [
            'id', 'phone', 'email', 'first_name', 'last_name',
            'post', 'post_display', 'commune', 'commune_display',
            'section_or_city', 'photo', 'slogan', 'biography',
            'platform_priorities', 'status', 'status_display',
            'rejection_reason', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'created_at']


class CandidateRegistrationSerializer(serializers.Serializer):
    """
    Serializer pour l'inscription officielle d'un candidat avec création atomique
    du compte User et de son profil électoral, et vérification d'appareil unique.
    """
    phone = serializers.CharField(max_length=25, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=6, required=True)
    first_name = serializers.CharField(max_length=100, required=True)
    last_name = serializers.CharField(max_length=100, required=True)

    post = serializers.ChoiceField(choices=ElectivePostChoices.choices, required=True)
    commune = serializers.CharField(max_length=100, required=True)
    custom_commune = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    section_or_city = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')

    photo = serializers.ImageField(required=False, allow_null=True)
    slogan = serializers.CharField(max_length=255, required=True)
    biography = serializers.CharField(required=True)
    platform_priorities = serializers.CharField(required=True)
    device_fingerprint = serializers.CharField(max_length=128, required=False, allow_blank=True, default='')

    def validate_phone(self, value):
        cleaned_phone = value.strip().replace(" ", "").replace("-", "")
        if User.objects.filter(phone=cleaned_phone).exists():
            raise serializers.ValidationError("Gen yon kont ki deja enskri ak nimewo telefòn sa a.")
        return cleaned_phone

    def validate_email(self, value):
        cleaned_email = value.strip().lower()
        if User.objects.filter(email__iexact=cleaned_email).exists():
            raise serializers.ValidationError("Gen yon kont ki deja enskri ak adrès imèl sa a. Chak kont dwe gen yon imèl inik.")
        return cleaned_email

    def validate_photo(self, value):
        if value:
            max_size = 5 * 1024 * 1024  # 5 MB
            if value.size > max_size:
                raise serializers.ValidationError("Fichye foto a twò lou. Gwosè maksimòm otorize a se 5 Mo (5MB).")
        return value

    def validate(self, attrs):
        device_fp = attrs.get('device_fingerprint', '').strip()
        request = self.context.get('request')
        ip_addr = None
        ua = ''
        if request:
            ip_addr = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
            ua = request.META.get('HTTP_USER_AGENT', '')

        # Si fingerprint pa bay, kalkile yon fallback sou IP ak User-Agent
        if not device_fp and ip_addr and ua:
            device_fp = hashlib.sha256(f"dev_{ip_addr}_{ua}".encode()).hexdigest()
            attrs['device_fingerprint'] = device_fp

        if device_fp and DeviceRegistration.is_device_registered(device_fp):
            raise serializers.ValidationError(
                "Aparèy sa a deja anrejistre yon kont sou platfòm nan. Règleman sekirite a entèdi pou yon sèl aparèy fè plizyè enskripsyon (1 Aparèy = 1 Enskripsyon)."
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        phone = validated_data.pop('phone')
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        device_fp = validated_data.pop('device_fingerprint', '').strip()

        user = User.objects.create_user(
            username=phone,
            phone=phone,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.CANDIDATE,
            is_verified=False
        )
        user.set_password(password)
        user.save()

        # Rezoud komin koutim si chwazi lòt komin
        commune_val = validated_data.get('commune', '').strip()
        custom_val = validated_data.pop('custom_commune', '').strip()
        if commune_val in ['OTHER', 'LOT', 'AUTRE', 'Autre'] and custom_val:
            validated_data['commune'] = custom_val
        elif commune_val in ['OTHER', 'LOT', 'AUTRE', 'Autre']:
            validated_data['commune'] = custom_val or 'Lòt Komin'

        # Assainissement contre les attaques XSS / injections HTML
        if 'slogan' in validated_data:
            validated_data['slogan'] = strip_tags(validated_data['slogan']).strip()
        if 'biography' in validated_data:
            validated_data['biography'] = strip_tags(validated_data['biography']).strip()
        if 'platform_priorities' in validated_data:
            validated_data['platform_priorities'] = strip_tags(validated_data['platform_priorities']).strip()

        candidate_profile = CandidateProfile.objects.create(
            user=user,
            email=email,
            first_name=first_name,
            last_name=last_name,
            status=CandidateStatus.PENDING,
            **validated_data
        )

        # Enskri anpwent inik aparèy la pou anpeche doub enskripsyon
        if device_fp:
            request = self.context.get('request')
            ip_addr = None
            ua = ''
            if request:
                ip_addr = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
                ua = request.META.get('HTTP_USER_AGENT', '')
            DeviceRegistration.objects.create(
                device_fingerprint=device_fp,
                user=user,
                ip_address=ip_addr,
                user_agent=ua,
                role=UserRole.CANDIDATE
            )

        return candidate_profile


class VoterProfileSerializer(serializers.ModelSerializer):
    """
    Serializer pou profil patisipan / elektè ak komin verouye a.
    """
    commune_display = serializers.CharField(source='get_commune_display', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = VoterProfile
        fields = [
            'id', 'phone', 'email', 'commune', 'commune_display', 'commune_locked',
            'has_voted_senateur', 'has_voted_depute', 'has_voted_maire',
            'has_voted_casec', 'has_voted_delegue', 'created_at'
        ]
        read_only_fields = ['id', 'commune_locked', 'created_at']


class VoterRegistrationSerializer(serializers.Serializer):
    """
    Serializer pou enskripsyon patisipan / elektè (VOTER) avèk verouyaj komin li
    ak restriksyon 1 sèl enskripsyon pa aparèy fizik, telefòn inik ak imèl inik.
    """
    phone = serializers.CharField(max_length=25, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=6, required=True)
    commune = serializers.ChoiceField(choices=CommuneChoices.choices, required=True)
    device_fingerprint = serializers.CharField(max_length=128, required=False, allow_blank=True, default='')

    def validate_phone(self, value):
        cleaned_phone = value.strip().replace(" ", "").replace("-", "")
        if User.objects.filter(phone=cleaned_phone).exists():
            raise serializers.ValidationError("Gen yon kont ki deja anrejistre ak nimewo telefòn sa a.")
        return cleaned_phone

    def validate_email(self, value):
        cleaned_email = value.strip().lower()
        if User.objects.filter(email__iexact=cleaned_email).exists():
            raise serializers.ValidationError("Gen yon kont ki deja anrejistre ak adrès imèl sa a. Chak kont dwe gen yon imèl inik.")
        return cleaned_email

    def validate(self, attrs):
        device_fp = attrs.get('device_fingerprint', '').strip()
        request = self.context.get('request')
        ip_addr = None
        ua = ''
        if request:
            ip_addr = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
            ua = request.META.get('HTTP_USER_AGENT', '')

        # Si fingerprint pa bay, kalkile yon fallback sou IP ak User-Agent
        if not device_fp and ip_addr and ua:
            device_fp = hashlib.sha256(f"dev_{ip_addr}_{ua}".encode()).hexdigest()
            attrs['device_fingerprint'] = device_fp

        if device_fp and DeviceRegistration.is_device_registered(device_fp):
            raise serializers.ValidationError(
                "Aparèy sa a deja anrejistre yon kont sou platfòm nan. Règleman sekirite a entèdi pou yon sèl aparèy fè plizyè enskripsyon (1 Aparèy = 1 Enskripsyon)."
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        phone = validated_data.pop('phone')
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        commune = validated_data.pop('commune')
        device_fp = validated_data.pop('device_fingerprint', '').strip()

        # 1. Kreye itilizatè a ak wòl VOTER ak imèl inik
        user = User.objects.create_user(
            username=phone,
            phone=phone,
            email=email,
            role=UserRole.VOTER,
            is_verified=True # Auto-verifié pour la participation citoyenne
        )
        user.set_password(password)
        user.save()

        # 2. Kreye profil elektè a ak komin li verouye definitivman
        voter_profile = VoterProfile.objects.create(
            user=user,
            commune=commune,
            commune_locked=True
        )

        # 3. Enskri anpwent inik aparèy la pou anpeche doub enskripsyon
        if device_fp:
            request = self.context.get('request')
            ip_addr = None
            ua = ''
            if request:
                ip_addr = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
                ua = request.META.get('HTTP_USER_AGENT', '')
            DeviceRegistration.objects.create(
                device_fingerprint=device_fp,
                user=user,
                ip_address=ip_addr,
                user_agent=ua,
                role=UserRole.VOTER
            )

        return voter_profile


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Serializer konplè pou itilizatè ki konekte a avèk profil li (kandida oswa elektè).
    """
    candidate_profile = CandidateProfileSerializer(read_only=True)
    voter_profile = VoterProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'phone', 'email', 'first_name', 'last_name',
            'role', 'is_verified', 'candidate_profile',
            'voter_profile', 'created_at'
        ]
