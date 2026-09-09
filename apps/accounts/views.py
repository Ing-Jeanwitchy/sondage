from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from django.db.models import Q
from .models import CandidateProfile, CandidateStatus, SurveyConfig, VoterProfile, DeviceRegistration
from .serializers import (
    CandidateRegistrationSerializer, 
    CandidateProfileSerializer,
    VoterRegistrationSerializer,
    VoterProfileSerializer,
    UserDetailSerializer
)
from .permissions import IsAdminRole, IsCandidateRole
from .throttles import AuthRateThrottle

User = get_user_model()

class CandidateRegisterView(APIView):
    """
    Endpoint d'inscription pour les candidats du Département du Nord-Ouest.
    Création du compte User (Role CANDIDATE) et du profil électoral (Statut PENDING).
    Bloque strictement toute inscription si le compte à rebours / la date limite est expirée
    ou si l'appareil a déjà été utilisé pour une inscription.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        # 1. Verifikasyon strik dat limit ak estati enskripsyon an
        config = SurveyConfig.get_config()
        if config.is_expired():
            return Response(
                {"error": "Peryòd enskripsyon kandida yo fèmen. Kalandriye a te rive nan bout li, pa gen okenn moun ki ka enskri ankò nan sondaj la."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 2. Tretman ak validasyon dosye a avèk kontèks requete (pou IP ak aparèy inik)
        serializer = CandidateRegistrationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            candidate_profile = serializer.save()
            user = candidate_profile.user

            # Génération des tokens JWT
            refresh = RefreshToken.for_user(user)

            return Response({
                "message": "Enskripsyon kandidati w la soumèt avèk siksè ! L ap pase anba verifikasyon Admin anvan li vin vizib nan sondaj la.",
                "candidate": CandidateProfileSerializer(candidate_profile).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                "role": user.role,
                "status": candidate_profile.status
            }, status=status.HTTP_201_CREATED)

        # Retounen erè klè (egzanp: si aparèy la deja anrejistre)
        first_err = None
        for k, v in serializer.errors.items():
            first_err = v[0] if isinstance(v, list) and len(v) > 0 else str(v)
            break
        return Response({"error": first_err or "Erè nan fòmilè enskripsyon an.", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class VoterRegisterView(APIView):
    """
    Endpoint d'inscription pour les électeurs / participants citoyens du Nord-Ouest.
    Création du compte User (Role VOTER) et du profil avec commune verrouillée de façon permanente.
    Restreint strictement à une seule inscription par appareil physique.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = VoterRegistrationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            voter_profile = serializer.save()
            user = voter_profile.user

            # Génération des tokens JWT
            refresh = RefreshToken.for_user(user)

            return Response({
                "message": "Enskripsyon ou reyisi ! Komin ou verouye definitivman pou tout vòt nan sondaj la.",
                "user": {
                    "id": str(user.id),
                    "phone": user.phone,
                    "role": user.role,
                    "is_verified": user.is_verified,
                },
                "voter": VoterProfileSerializer(voter_profile).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)

        first_err = None
        for k, v in serializer.errors.items():
            first_err = v[0] if isinstance(v, list) and len(v) > 0 else str(v)
            break
        return Response({"error": first_err or "Erè nan enskripsyon patisipan an.", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class CheckDeviceRegistrationView(APIView):
    """
    Endpoint de sécurité pour vérifier en amont si cet appareil a déjà un compte enregistré.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        device_fp = request.query_params.get('fingerprint', '').strip()
        is_registered = False
        registered_role = None

        if device_fp:
            reg = DeviceRegistration.objects.filter(device_fingerprint=device_fp).first()
            if reg:
                is_registered = True
                registered_role = reg.role

        return Response({
            "is_registered": is_registered,
            "role": registered_role,
            "message": "Aparèy sa a deja anrejistre yon kont sou platfòm nan." if is_registered else "Aparèy disponib pou enskripsyon."
        })


class SurveyConfigView(APIView):
    """
    Endpoint public pour récupérer les dates officielles du sondage et le compte à rebours de l'inscription.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        config = SurveyConfig.get_config()
        now = timezone.now()
        seconds_remaining = max(0, int((config.registration_deadline - now).total_seconds())) if config.is_registration_open else 0
        is_expired = config.is_expired()

        return Response({
            "is_registration_open": config.is_registration_open,
            "registration_deadline": config.registration_deadline.isoformat(),
            "server_time": now.isoformat(),
            "seconds_remaining": seconds_remaining,
            "is_expired": is_expired,
            "is_voting_open": config.is_voting_open,
        })


class CandidateListView(generics.ListAPIView):
    """
    Endpoint public pour lister les candidats validés avec filtres optionnels par poste et par commune.
    Renvoie la liste complète des candidats approuvés sans pagination bloquante.
    """
    serializer_class = CandidateProfileSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    pagination_class = None

    def get_queryset(self):
        queryset = CandidateProfile.objects.filter(status=CandidateStatus.APPROVED)
        
        post = self.request.query_params.get('post')
        commune = self.request.query_params.get('commune')
        search = self.request.query_params.get('search')

        if post and post != 'ALL':
            queryset = queryset.filter(post=post)
        
        if commune and commune != 'ALL':
            # Si yon sitwayen chwazi yon komin men li pa chwazi pòs, li dwe wè kandida komin sa a 
            # PLUS senatè yo (ki prezante pou tout 10 komin depatman an).
            if not post or post == 'ALL':
                queryset = queryset.filter(Q(commune=commune) | Q(post='SENATEUR'))
            else:
                queryset = queryset.filter(commune=commune)
            
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(slogan__icontains=search)
            )

        return queryset.order_by('-created_at')


class UnifiedLoginView(APIView):
    """
    Endpoint de connexion unifié (par numéro de téléphone et mot de passe).
    Détecte automatiquement le rôle de l'utilisateur (ADMIN, CANDIDATE, VOTER).
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        phone = request.data.get('phone', '').strip().replace(" ", "").replace("-", "")
        password = request.data.get('password', '')

        if not phone or not password:
            return Response(
                {"error": "Tanpri antre nimewo telefòn ou ak modpas ou."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Authentification par phone
        try:
            user = User.objects.get(phone=phone)
            if not user.check_password(password):
                return Response(
                    {"error": "Nimewo telefòn oswa modpas la pa kòrèk."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except User.DoesNotExist:
            return Response(
                {"error": "Pa gen pyès kont ki anrejistre ak nimewo sa a."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Génération des tokens JWT
        refresh = RefreshToken.for_user(user)

        candidate_data = None
        if user.role == 'CANDIDATE' and hasattr(user, 'candidate_profile'):
            candidate_data = CandidateProfileSerializer(user.candidate_profile).data

        voter_data = None
        if user.role == 'VOTER' and hasattr(user, 'voter_profile'):
            voter_data = VoterProfileSerializer(user.voter_profile).data

        return Response({
            "message": "Koneksyon reyisi !",
            "user": {
                "id": str(user.id),
                "phone": user.phone,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "is_verified": user.is_verified,
            },
            "candidate": candidate_data,
            "voter": voter_data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    """
    Endpoint sécurisé pour récupérer le profil complet de l'utilisateur connecté via JWT.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminCandidateListView(APIView):
    """
    Endpoint pou administratè a liste tout dosye kandidati ak filtè pa estati (PENDING, APPROVED, REJECTED, ALL).
    """
    permission_classes = [IsAdminRole]

    def get(self, request, *args, **kwargs):
        status_filter = request.query_params.get('status', 'ALL')
        queryset = CandidateProfile.objects.all().order_by('-created_at')

        if status_filter and status_filter != 'ALL':
            queryset = queryset.filter(status=status_filter)

        serializer = CandidateProfileSerializer(queryset, many=True)
        
        # Konte pa estati
        counts = {
            "total": CandidateProfile.objects.count(),
            "pending": CandidateProfile.objects.filter(status=CandidateStatus.PENDING).count(),
            "approved": CandidateProfile.objects.filter(status=CandidateStatus.APPROVED).count(),
            "rejected": CandidateProfile.objects.filter(status=CandidateStatus.REJECTED).count(),
        }

        return Response({
            "counts": counts,
            "candidates": serializer.data
        }, status=status.HTTP_200_OK)


class AdminCandidateModerateView(APIView):
    """
    Endpoint pou administratè a apwouve oswa rejte yon dosye kandidati.
    """
    permission_classes = [IsAdminRole]

    def post(self, request, candidate_id, *args, **kwargs):
        try:
            candidate = CandidateProfile.objects.get(id=candidate_id)
        except CandidateProfile.DoesNotExist:
            return Response({"error": "Kandida sa a pa egziste nan sistèm nan."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action') # 'approve' | 'reject'
        reason = request.data.get('reason', '')

        if action == 'approve':
            candidate.status = CandidateStatus.APPROVED
            candidate.validated_at = timezone.now()
            candidate.rejection_reason = ''
            candidate.save()
            return Response({
                "message": f"Kandidati {candidate.first_name} {candidate.last_name} apwouve avèk siksè ! Li vizib kounye a nan biltan vòt la.",
                "candidate": CandidateProfileSerializer(candidate).data
            }, status=status.HTTP_200_OK)

        elif action == 'reject':
            candidate.status = CandidateStatus.REJECTED
            candidate.rejection_reason = reason or 'Dosye a pa satisfè kritè validasyon yo.'
            candidate.save()
            return Response({
                "message": f"Kandidati {candidate.first_name} {candidate.last_name} rejte.",
                "candidate": CandidateProfileSerializer(candidate).data
            }, status=status.HTTP_200_OK)

        return Response({"error": "Aksyon sa a pa valid. Sèl aksyon ki otorize se 'approve' oswa 'reject'."}, status=status.HTTP_400_BAD_REQUEST)


class AdminSurveyConfigView(APIView):
    """
    Endpoint pou administratè a konsilte ak ajiste paramèt kalandriye sondaj la.
    """
    permission_classes = [IsAdminRole]

    def get(self, request, *args, **kwargs):
        config = SurveyConfig.get_config()
        return Response({
            "is_registration_open": config.is_registration_open,
            "registration_deadline": config.registration_deadline.isoformat(),
            "is_voting_open": config.is_voting_open,
            "is_expired": config.is_expired(),
        }, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        config = SurveyConfig.get_config()
        
        has_reg = 'is_registration_open' in request.data
        has_vote = 'is_voting_open' in request.data

        if has_reg and has_vote:
            new_reg = bool(request.data['is_registration_open'])
            new_vote = bool(request.data['is_voting_open'])
            # RÈG EKSKLIZIF : Tou de pa ka louvri ansanm !
            if new_reg and new_vote:
                # Si tou de voye kòm True, priyorite bay vòt la oswa enskripsyon
                if not config.is_voting_open and new_vote:
                    new_reg = False
                else:
                    new_vote = False
            config.is_registration_open = new_reg
            config.is_voting_open = new_vote
        elif has_reg:
            config.is_registration_open = bool(request.data['is_registration_open'])
            if config.is_registration_open:
                config.is_voting_open = False
        elif has_vote:
            config.is_voting_open = bool(request.data['is_voting_open'])
            if config.is_voting_open:
                config.is_registration_open = False
            
        if 'registration_deadline' in request.data:
            from django.utils.dateparse import parse_datetime
            new_deadline = parse_datetime(request.data['registration_deadline'])
            if new_deadline:
                config.registration_deadline = new_deadline

        config.save()
        return Response({
            "message": "Paramèt kalandriye sondaj la mete a jou avèk siksè !",
            "config": {
                "is_registration_open": config.is_registration_open,
                "registration_deadline": config.registration_deadline.isoformat(),
                "is_voting_open": config.is_voting_open,
                "is_expired": config.is_expired(),
            }
        }, status=status.HTTP_200_OK)


class AdminDashboardStatsView(APIView):
    """
    Endpoint pou rekipere estatistik konplè ak 100% dinamik pou Tablo Admin lan :
    Total vòt reyèl, patisipan reyèl, to patisipasyon, repatisyon reyèl pa pòs ak pa komin.
    """
    permission_classes = [IsAdminRole]

    def get(self, request, *args, **kwargs):
        from elections.models import Vote
        from .models import CommuneChoices

        total_votes = Vote.objects.count()
        registered_voters = User.objects.filter(role='VOTER').count()
        unique_voters = Vote.objects.values('voter').distinct().count()
        turnout_pct = round((unique_voters / registered_voters * 100), 1) if registered_voters > 0 else 0.0

        cand_total = CandidateProfile.objects.count()
        cand_pending = CandidateProfile.objects.filter(status=CandidateStatus.PENDING).count()
        cand_approved = CandidateProfile.objects.filter(status=CandidateStatus.APPROVED).count()
        cand_rejected = CandidateProfile.objects.filter(status=CandidateStatus.REJECTED).count()

        # Mobilizasyon reyèl pa pòs elektif
        post_configs = [
            ("SENATEUR", "Sénateur (Nord-Ouest)", "Senatè (Nòdwès)", "Senator (Northwest)"),
            ("DEPUTE", "Député (Circonscription)", "Depite (Sikonskripsyon)", "Deputy (Constituency)"),
            ("MAIRE", "Maire (Commune)", "Majistra (Komin)", "Mayor (Commune)"),
            ("CASEC", "CASEC & Délégué", "CASEC & Delegasyon", "CASEC & Delegate")
        ]

        post_breakdown = []
        for code, l_fr, l_ht, l_en in post_configs:
            count = Vote.objects.filter(post=code).count()
            pct = round((count / total_votes * 100), 1) if total_votes > 0 else 0.0
            post_breakdown.append({
                "code": code,
                "label_fr": l_fr,
                "label_ht": l_ht,
                "label_en": l_en,
                "votes": count,
                "percentage": pct
            })

        # Repatisyon reyèl pa komin
        commune_breakdown = []
        for code, name in CommuneChoices.choices:
            count = Vote.objects.filter(commune=code).count()
            pct = round((count / total_votes * 100), 1) if total_votes > 0 else 0.0
            commune_breakdown.append({
                "code": code,
                "name": name,
                "votes": count,
                "percentage": pct
            })

        # Triye komin yo pa kantite vòt décroissant
        commune_breakdown.sort(key=lambda x: (x['votes'], x['name']), reverse=True)

        return Response({
            "total_votes": total_votes,
            "registered_voters": registered_voters,
            "turnout_percentage": turnout_pct,
            "candidates": {
                "total": cand_total,
                "pending": cand_pending,
                "approved": cand_approved,
                "rejected": cand_rejected
            },
            "post_breakdown": post_breakdown,
            "commune_breakdown": commune_breakdown
        }, status=status.HTTP_200_OK)


class CandidateDashboardView(APIView):
    """
    Endpoint dedye pou kandida ki konekte a konsilte tablo de bò li,
    estatistik vòt li resevwa an tan reyèl, ak modifikasyon pwofil kanpay li.
    """
    permission_classes = [permissions.IsAuthenticated, IsCandidateRole]

    def get(self, request, *args, **kwargs):
        from elections.models import Vote
        from .models import CommuneChoices

        try:
            profile = request.user.candidate_profile
        except CandidateProfile.DoesNotExist:
            return Response({"error": "Profil kandida pa jwenn pou kont sa a."}, status=status.HTTP_404_NOT_FOUND)

        # 1. Estatistik vòt kandida a an tan reyèl
        total_votes = Vote.objects.filter(candidate=profile).count()
        post_total_votes = Vote.objects.filter(post=profile.post).count()
        vote_percentage = round((total_votes / post_total_votes * 100), 1) if post_total_votes > 0 else 0.0

        # 2. Klasman kandida a nan kous pòs elektif li
        same_post_candidates = CandidateProfile.objects.filter(post=profile.post, status=CandidateStatus.APPROVED)
        candidate_vote_counts = []
        for c in same_post_candidates:
            v_count = Vote.objects.filter(candidate=c).count()
            candidate_vote_counts.append((c.id, v_count))
        
        candidate_vote_counts.sort(key=lambda x: x[1], reverse=True)
        rank = 1
        for idx, (c_id, v_count) in enumerate(candidate_vote_counts):
            if c_id == profile.id:
                rank = idx + 1
                break

        # 3. Repatisyon vòt kandida a pa komin nan depatman an
        commune_breakdown = []
        for code, name in CommuneChoices.choices:
            c_votes = Vote.objects.filter(candidate=profile, commune=code).count()
            c_pct = round((c_votes / total_votes * 100), 1) if total_votes > 0 else 0.0
            commune_breakdown.append({
                "code": code,
                "commune": code,
                "name": name,
                "commune_display": name,
                "votes": c_votes,
                "percentage": c_pct
            })
        commune_breakdown.sort(key=lambda x: (x['votes'], x['commune_display']), reverse=True)
        leading_commune = commune_breakdown[0]['commune_display'] if total_votes > 0 else (profile.get_commune_display() if hasattr(profile, 'get_commune_display') else profile.commune)

        # 4. Estati kalandriye elektoral la
        config = SurveyConfig.get_config()

        serializer = CandidateProfileSerializer(profile)

        return Response({
            "profile": serializer.data,
            "stats": {
                "total_votes": total_votes,
                "post_total_votes": post_total_votes,
                "vote_percentage": vote_percentage,
                "vote_share_pct": vote_percentage,
                "rank": rank,
                "total_candidates_in_post": max(1, len(candidate_vote_counts)),
                "commune_breakdown": commune_breakdown,
                "leading_commune": leading_commune,
            },
            "communes_breakdown": commune_breakdown,
            "survey_status": {
                "is_registration_open": config.is_registration_open,
                "is_voting_open": config.is_voting_open,
                "registration_deadline": config.registration_deadline.isoformat(),
                "is_expired": config.is_expired()
            }
        }, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        try:
            profile = request.user.candidate_profile
        except CandidateProfile.DoesNotExist:
            return Response({"error": "Profil kandida pa jwenn pou kont sa a."}, status=status.HTTP_404_NOT_FOUND)

        allowed_fields = ['slogan', 'biography', 'platform_priorities']
        updated = False
        for f in allowed_fields:
            if f in request.data:
                setattr(profile, f, request.data[f])
                updated = True

        if 'photo' in request.FILES:
            photo_file = request.FILES['photo']
            if photo_file.size > 5 * 1024 * 1024:
                return Response(
                    {"error": "Fichye foto a twò lou. Gwosè maksimòm otorize a se 5 Mo (5MB)."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            profile.photo = photo_file
            updated = True

        # Si dosye a te REJECTED, kandida a ka soumèt li ankò -> li tounen PENDING pou re-egzamen
        if profile.status == CandidateStatus.REJECTED and updated:
            profile.status = CandidateStatus.PENDING
            profile.rejection_reason = ''

        if updated:
            profile.save()

        serializer = CandidateProfileSerializer(profile)
        return Response({
            "message": "Pwofil ou mete ajou avèk siksè !",
            "profile": serializer.data
        }, status=status.HTTP_200_OK)


class VoterDashboardView(APIView):
    """
    Endpoint dedye pou patisipan / elektè ki konekte a konsilte tablo de bò li :
    - Enfòmasyon sitwayen li (Komin verouye, telefòn, imèl, dat enskripsyon)
    - Estati anpwent aparèy li (Sekirite 1 Aparèy = 1 Elektè)
    - Pwogresyon vòt li (konbyen biltan li vote sou 5 pòs elektif yo)
    - Detay chak pòs (Senatè, Depite, Majistra, CASEC, Délégué) ak estati vòt / kandida li te vote a
    - Lis tout resi ofisyèl vòt li yo ak kòd UUID pou telechaje fich PDF
    - Estatistik patisipasyon nan komin li
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        voter_profile = getattr(user, 'voter_profile', None)
        if not voter_profile and user.role != 'ADMIN':
            return Response({"error": "Profil elektè pa jwenn pou kont sa a."}, status=status.HTTP_404_NOT_FOUND)

        from elections.models import Vote
        from .models import CommuneChoices, ElectivePostChoices

        voter_commune = voter_profile.commune if voter_profile else 'PORT_DE_PAIX'
        voter_commune_display = voter_profile.get_commune_display() if voter_profile else 'Port-de-Paix'

        # 1. Konfigirasyon 5 biltan ofisyèl yo
        ballots_config = [
            {
                "code": "SENATEUR",
                "title": "Sénateur de la République",
                "scope": "DEPARTMENT",
                "scope_desc": "Tout Depatman Nòdwès (10 Komin yo)"
            },
            {
                "code": "DEPUTE",
                "title": "Député au Parlement",
                "scope": "CONSTITUENCY",
                "scope_desc": f"Sirkonskripsyon {voter_commune_display}"
            },
            {
                "code": "MAIRE",
                "title": "Maire / Conseil Municipal",
                "scope": "COMMUNE",
                "scope_desc": f"Komin {voter_commune_display}"
            },
            {
                "code": "CASEC",
                "title": "CASEC / ASEC (Seksyon Riral)",
                "scope": "COMMUNAL_SECTION",
                "scope_desc": f"Seksyon Kominal nan {voter_commune_display}"
            },
            {
                "code": "DELEGUE_VILLE",
                "title": "Délégué de Ville (Katye / Sant Vil)",
                "scope": "CITY",
                "scope_desc": f"Sant Vil {voter_commune_display}"
            }
        ]

        # 2. Vòt itilizatè a deja fè
        user_votes = {v.post: v for v in Vote.objects.filter(voter=user)}

        ballots_status = []
        receipts_list = []
        votes_cast_count = 0

        for b in ballots_config:
            p_code = b["code"]
            has_voted = p_code in user_votes
            if has_voted:
                votes_cast_count += 1
                v = user_votes[p_code]
                c_name = f"{v.candidate.first_name} {v.candidate.last_name}".strip() if v.candidate else "Kandida Valide"
                candidate_photo = v.candidate.photo.url if v.candidate and v.candidate.photo else None
                receipt_data = {
                    "id": str(v.id),
                    "receipt_code": str(v.receipt_code),
                    "post": p_code,
                    "post_display": v.get_post_display(),
                    "commune": v.commune,
                    "commune_display": v.get_commune_display(),
                    "candidate_name": c_name,
                    "candidate_photo": candidate_photo,
                    "created_at": v.created_at.isoformat()
                }
                receipts_list.append(receipt_data)
                ballots_status.append({
                    "post_code": p_code,
                    "post_title": b["title"],
                    "scope": b["scope"],
                    "scope_desc": b["scope_desc"],
                    "has_voted": True,
                    "receipt_code": str(v.receipt_code),
                    "voted_at": v.created_at.isoformat(),
                    "candidate_name": c_name,
                    "candidate_photo": candidate_photo
                })
            else:
                # Kandida ki disponib pou biltan sa a
                qs = CandidateProfile.objects.filter(post=p_code, status=CandidateStatus.APPROVED)
                if b["scope"] != "DEPARTMENT":
                    qs = qs.filter(commune=voter_commune)
                
                ballots_status.append({
                    "post_code": p_code,
                    "post_title": b["title"],
                    "scope": b["scope"],
                    "scope_desc": b["scope_desc"],
                    "has_voted": False,
                    "receipt_code": None,
                    "voted_at": None,
                    "candidate_name": None,
                    "candidates_available_count": qs.count()
                })

        # 3. Aparèy & Sekirite
        dev_reg = DeviceRegistration.objects.filter(user=user).first()
        device_fp = dev_reg.device_fingerprint if dev_reg else None

        # 4. Estatistik komin elektè a
        commune_votes_total = Vote.objects.filter(commune=voter_commune).count()
        commune_voters_total = VoterProfile.objects.filter(commune=voter_commune).count()

        # 5. Estati kalandriye
        config = SurveyConfig.get_config()

        return Response({
            "voter": {
                "id": str(user.id),
                "phone": user.phone,
                "email": user.email,
                "role": user.role,
                "is_verified": user.is_verified,
                "commune": voter_commune,
                "commune_display": voter_commune_display,
                "commune_locked": True,
                "created_at": voter_profile.created_at.isoformat() if voter_profile else user.created_at.isoformat(),
            },
            "device_security": {
                "is_locked_to_device": bool(dev_reg),
                "device_fingerprint_short": f"{device_fp[:16]}..." if device_fp else "Aktif sou Sesyon",
                "registered_at": dev_reg.created_at.isoformat() if dev_reg else None,
                "security_rule": "1 Aparèy Fizik = 1 Sèl Elektè • 1 Vòt pa Pòs"
            },
            "voting_summary": {
                "total_ballots": 5,
                "votes_cast": votes_cast_count,
                "votes_remaining": 5 - votes_cast_count,
                "completion_percentage": round((votes_cast_count / 5) * 100),
                "all_completed": votes_cast_count == 5
            },
            "ballots_status": ballots_status,
            "receipts": receipts_list,
            "commune_stats": {
                "commune": voter_commune,
                "commune_display": voter_commune_display,
                "total_voters": commune_voters_total,
                "total_votes_cast": commune_votes_total
            },
            "survey_status": {
                "is_voting_open": config.is_voting_open,
                "is_registration_open": config.is_registration_open,
                "is_expired": config.is_expired(),
                "registration_deadline": config.registration_deadline.isoformat()
            }
        }, status=status.HTTP_200_OK)

