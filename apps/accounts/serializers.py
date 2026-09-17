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

def extract_clean_ip(request):
    """
    Ekstrè epi netwaye adrès IP a pou evite erè fòma nan GenericIPAddressField (PostgreSQL/SQLite).
    """
    if not request:
        return None
    raw_ip = request.META.get('HTTP_X_FORWARDED_FOR')
    if raw_ip:
        ip_addr = raw_ip.split(',')[0].strip()
    else:
        ip_addr = request.META.get('REMOTE_ADDR', '').strip()

    if not ip_addr:
        return None

    # Retire pò si genyen (eg: 192.168.1.1:8000 oswa [IPv6]:port)
    if ':' in ip_addr and '.' in ip_addr:
        ip_addr = ip_addr.split(':')[0].strip()
    elif ip_addr.startswith('[') and ']' in ip_addr:
        ip_addr = ip_addr.split(']')[0].lstrip('[')

    return ip_addr or None

class AbsoluteImageField(serializers.ImageField):
    """
    Retounen URL absoli pou foto kandida yo.
    Si foto a sou Cloudinary (URL kòmanse ak http), retounen l dirèkteman.
    Si foto a se yon chemen lokal (/media/...), ajoute backend URL devan.
    """
    def to_representation(self, value):
        if not value:
            return None
        try:
            url = value.url
        except Exception:
            return None
        # Si URL la deja absoli (Cloudinary oswa lòt CDN), retounen l dirèkteman
        if url.startswith('http://') or url.startswith('https://'):
            # Toujou fòse HTTPS
            if url.startswith('http://'):
                url = 'https://' + url[7:]
            return url
        # Si URL relatif, konstwi URL absoli ak request la
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(url)
        # Fallback: retounen URL relatif la (frontend ap ajoute baseURL)
        return url


class CandidateProfileSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'affichage public et privé du profil d'un candidat.
    """
    post_display = serializers.CharField(source='get_post_display', read_only=True)
    commune_display = serializers.CharField(source='get_commune_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    photo = AbsoluteImageField(read_only=True)

    class Meta:
        model = CandidateProfile
        fields = [
            'id', 'phone', 'email', 'first_name', 'last_name',
            'post', 'post_display', 'commune', 'commune_display',
            'section_or_city', 'photo', 'slogan', 'biography',
            'platform_priorities', 'cartel_name', 'cartel_member2_name', 'cartel_member3_name',
            'status', 'status_display',
            'rejection_reason', 'withdrawal_requested', 'withdrawal_reason',
            'withdrawal_requested_at', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'withdrawal_requested', 'withdrawal_reason', 'withdrawal_requested_at', 'created_at']



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
    cartel_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    cartel_member2_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    cartel_member3_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
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
            max_size = 20 * 1024 * 1024  # 20 MB
            if value.size > max_size:
                raise serializers.ValidationError("Fichye foto a twò lou. Gwosè maksimòm otorize a se 20 Mo (20MB).")
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

        if device_fp:
            request = self.context.get('request')
            ip_addr = extract_clean_ip(request)
            ua = request.META.get('HTTP_USER_AGENT', '') if request else ''
            try:
                DeviceRegistration.objects.create(
                    device_fingerprint=device_fp,
                    user=user,
                    ip_address=ip_addr,
                    user_agent=ua,
                    role=UserRole.CANDIDATE
                )
            except Exception as dev_err:
                import logging
                logging.getLogger('django').warning(f"DeviceRegistration CANDIDATE warning: {dev_err}")

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
            ip_addr = extract_clean_ip(request)
            ua = request.META.get('HTTP_USER_AGENT', '') if request else ''
            try:
                DeviceRegistration.objects.create(
                    device_fingerprint=device_fp,
                    user=user,
                    ip_address=ip_addr,
                    user_agent=ua,
                    role=UserRole.VOTER
                )
            except Exception as dev_err:
                import logging
                logging.getLogger('django').warning(f"DeviceRegistration VOTER warning: {dev_err}")

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


class AdminCandidateDirectCreateSerializer(serializers.Serializer):
    """
    Serializer pou Admin ak Operatè Saisie ajoute yon kandida dirèkteman nan panèl la.
    Pa gen kontrent fingerprint aparèy pou operatè a ka ajoute plizyè kandida.
    """
    phone = serializers.CharField(max_length=25, required=True)
    first_name = serializers.CharField(max_length=100, required=True)
    last_name = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')

    post = serializers.ChoiceField(choices=ElectivePostChoices.choices, required=True)
    commune = serializers.CharField(max_length=100, required=True)
    custom_commune = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    section_or_city = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')

    photo = serializers.ImageField(required=False, allow_null=True)
    slogan = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    biography = serializers.CharField(required=False, allow_blank=True, default='')
    platform_priorities = serializers.CharField(required=False, allow_blank=True, default='')
    cartel_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    cartel_member2_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    cartel_member3_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    status = serializers.ChoiceField(choices=CandidateStatus.choices, required=False, default=CandidateStatus.APPROVED)

    def validate_phone(self, value):
        cleaned_phone = value.strip().replace(" ", "").replace("-", "")
        existing_user = User.objects.filter(phone=cleaned_phone).first()
        if existing_user and hasattr(existing_user, 'candidate_profile'):
            raise serializers.ValidationError("Gen yon kandida ki deja anrejistre ak nimewo telefòn sa a.")
        return cleaned_phone

    @transaction.atomic
    def create(self, validated_data):
        from django.utils import timezone
        import secrets

        phone = validated_data.pop('phone')
        first_name = validated_data.pop('first_name').strip()
        last_name = validated_data.pop('last_name').strip()
        email = validated_data.pop('email', '').strip() or None
        password = validated_data.pop('password', '').strip() or f"Kandida{secrets.randbelow(899999)+100000}!"
        cand_status = validated_data.pop('status', CandidateStatus.APPROVED)

        # Si user a te deja egziste san pwofil kandida
        user = User.objects.filter(phone=phone).first()
        if not user:
            user = User.objects.create_user(
                username=phone,
                phone=phone,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.CANDIDATE,
                is_verified=True
            )
            user.set_password(password)
            user.save()
        else:
            user.role = UserRole.CANDIDATE
            user.first_name = first_name
            user.last_name = last_name
            if email and not user.email:
                user.email = email
            user.save()

        # Rezoud komin
        commune_val = validated_data.get('commune', '').strip()
        custom_val = validated_data.pop('custom_commune', '').strip()
        if commune_val in ['OTHER', 'LOT', 'AUTRE', 'Autre'] and custom_val:
            validated_data['commune'] = custom_val
        elif commune_val in ['OTHER', 'LOT', 'AUTRE', 'Autre']:
            validated_data['commune'] = custom_val or 'Lòt Komin'

        # Netwaye tèks
        for field in ['slogan', 'biography', 'platform_priorities']:
            if field in validated_data and validated_data[field]:
                validated_data[field] = strip_tags(validated_data[field]).strip()

        candidate_profile = CandidateProfile.objects.create(
            user=user,
            email=email or '',
            first_name=first_name,
            last_name=last_name,
            status=cand_status,
            validated_at=timezone.now() if cand_status == CandidateStatus.APPROVED else None,
            **validated_data
        )

        return candidate_profile


class TeamMemberSerializer(serializers.ModelSerializer):
    """
    Serializer pou afiche manm ekip jesyon an (ADMIN, MODERATOR, OPERATOR, COMMUNICATOR).
    """
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'phone', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_display', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else obj.phone


class TeamMemberCreateSerializer(serializers.Serializer):
    """
    Serializer pou Sipè Admin kreye yon nouvo kolaboratè nan ekip la.
    """
    phone = serializers.CharField(max_length=25, required=True)
    password = serializers.CharField(write_only=True, min_length=6, required=True)
    first_name = serializers.CharField(max_length=100, required=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    role = serializers.ChoiceField(
        choices=[
            ('ADMIN', 'Sipè Administratè'),
            ('MODERATOR', 'Moderatè / Analis Dosye'),
            ('OPERATOR', 'Operatè Saisie'),
            ('COMMUNICATOR', 'Ofisye Kominikasyon'),
        ],
        required=True
    )

    def validate_phone(self, value):
        cleaned_phone = value.strip().replace(" ", "").replace("-", "")
        if User.objects.filter(phone=cleaned_phone).exists():
            raise serializers.ValidationError("Gen yon kont ki deja itilize nimewo telefòn sa a.")
        return cleaned_phone

    def create(self, validated_data):
        phone = validated_data['phone']
        password = validated_data['password']
        first_name = validated_data.get('first_name', '').strip()
        last_name = validated_data.get('last_name', '').strip()
        email = validated_data.get('email', '').strip() or None
        role = validated_data['role']

        user = User.objects.create_user(
            username=phone,
            phone=phone,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_staff=True,
            is_verified=True
        )
        user.set_password(password)
        user.save()
        return user


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """
    Serializer konplè pou jesyon tout itilizatè sistèm nan (Elektè, Kandida, Ekip).
    """
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.SerializerMethodField()
    voter_info = serializers.SerializerMethodField()
    candidate_info = serializers.SerializerMethodField()
    device_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'phone', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_display', 'is_active', 'is_verified', 'is_staff',
            'created_at', 'last_login', 'voter_info', 'candidate_info', 'device_count'
        ]
        read_only_fields = ['id', 'created_at', 'last_login']

    def get_full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else obj.phone

    def get_voter_info(self, obj):
        if hasattr(obj, 'voter_profile') and obj.voter_profile:
            vp = obj.voter_profile
            voted_posts = []
            if vp.has_voted_senateur: voted_posts.append('SENATEUR')
            if vp.has_voted_depute: voted_posts.append('DEPUTE')
            if vp.has_voted_maire: voted_posts.append('MAIRE')
            if vp.has_voted_casec: voted_posts.append('CASEC')
            if vp.has_voted_delegue: voted_posts.append('DELEGUE_VILLE')
            return {
                'commune': vp.commune,
                'commune_display': vp.get_commune_display(),
                'commune_locked': vp.commune_locked,
                'has_voted_any': len(voted_posts) > 0,
                'voted_posts': voted_posts,
                'voted_count': len(voted_posts),
            }
        return None

    def get_candidate_info(self, obj):
        if hasattr(obj, 'candidate_profile') and obj.candidate_profile:
            cp = obj.candidate_profile
            return {
                'id': str(cp.id),
                'post': cp.post,
                'post_display': cp.get_post_display(),
                'commune': cp.commune,
                'commune_display': cp.get_commune_display(),
                'status': cp.status,
                'status_display': cp.get_status_display(),
                'slogan': cp.slogan,
                'photo': cp.photo.url if cp.photo else None,
            }
        return None

    def get_device_count(self, obj):
        return DeviceRegistration.objects.filter(user=obj).count()


class AdminUserResetPasswordSerializer(serializers.Serializer):
    """
    Serializer pou Sipè Admin chanje modpas yon itilizatè dirèkteman.
    """
    new_password = serializers.CharField(min_length=6, write_only=True, required=True)

    def validate_new_password(self, value):
        if len(value.strip()) < 6:
            raise serializers.ValidationError("Modpas la dwe gen omwen 6 karaktè.")
        return value.strip()


