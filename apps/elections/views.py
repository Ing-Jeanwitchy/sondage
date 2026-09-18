import hashlib
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from accounts.models import CandidateProfile, CandidateStatus, ElectivePostChoices, CommuneChoices
from accounts.permissions import IsAdminRole, CanManagePosts, IsStaffRole
from accounts.throttles import VoteRateThrottle
from .models import Vote, PublicAnnouncement
from .serializers import (
    BallotCandidateSerializer,
    CastVoteSerializer,
    VoteReceiptSerializer,
    PublicAnnouncementSerializer
)


class BallotListView(APIView):
    """
    Endpoint pou rekipere biltan vòt yo avèk filtraj jewografik strik selon komin elektè a.
    Chak biltan gen estati li : 'already_voted: true/false' ak lis kandida ki kalifye yo.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        
        # Rekipere komin verouye elektè a
        voter_commune = 'PORT_DE_PAIX'
        if hasattr(user, 'voter_profile'):
            voter_commune = user.voter_profile.commune
        elif hasattr(user, 'candidate_profile'):
            voter_commune = user.candidate_profile.commune

        # Definisyon biltan ofisyèl yo
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
                "scope_desc": f"Sirkonskripsyon {voter_commune}"
            },
            {
                "code": "MAIRE",
                "title": "Maire / Conseil Municipal",
                "scope": "COMMUNE",
                "scope_desc": f"Komin {voter_commune}"
            },
            {
                "code": "CASEC",
                "title": "CASEC / ASEC (Seksyon Riral)",
                "scope": "COMMUNAL_SECTION",
                "scope_desc": f"Seksyon Kominal nan {voter_commune}"
            },
            {
                "code": "DELEGUE_VILLE",
                "title": "Délégué de Ville (Katye / Sant Vil)",
                "scope": "CITY",
                "scope_desc": f"Sant Vil {voter_commune}"
            }
        ]

        # Vòt itilizatè a deja fè
        user_votes = {
            v.post: v for v in Vote.objects.filter(voter=user)
        }

        # Bati repons pou chak biltan
        ballots_data = []
        for b in ballots_config:
            post_code = b["code"]
            already_voted = post_code in user_votes
            receipt_code = str(user_votes[post_code].receipt_code) if already_voted else None
            voted_at = user_votes[post_code].created_at if already_voted else None
            voted_candidate_name = None
            if already_voted and user_votes[post_code].candidate:
                c = user_votes[post_code].candidate
                voted_candidate_name = f"{c.first_name} {c.last_name}".strip()

            # Filtraj kandida ki kalifye pou biltan sa a
            candidate_qs = CandidateProfile.objects.filter(
                post=post_code,
                status=CandidateStatus.APPROVED
            )

            # Senatè se tout depatman an, lòt pòs yo filtre sou komin elektè a
            if b["scope"] != "DEPARTMENT":
                candidate_qs = candidate_qs.filter(commune=voter_commune)

            ballots_data.append({
                "post_code": post_code,
                "post_title": b["title"],
                "scope": b["scope"],
                "scope_desc": b["scope_desc"],
                "already_voted": already_voted,
                "receipt_code": receipt_code,
                "voted_at": voted_at,
                "candidate_name": voted_candidate_name,
                "candidates": BallotCandidateSerializer(candidate_qs, many=True).data
            })

        from accounts.models import SurveyConfig
        survey_cfg = SurveyConfig.get_config()

        return Response({
            "voter_phone": user.phone,
            "voter_commune": voter_commune,
            "is_voting_open": survey_cfg.is_voting_open,
            "ballots": ballots_data
        }, status=status.HTTP_200_OK)


class CastVoteView(APIView):
    """
    Endpoint pou anrejistre yon vòt préliminaire anba tranzaksyon atomik.
    Pwoteksyon strik kont doub vòt ak verifikasyon jewografik.
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [VoteRateThrottle]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # 0. Tcheke si faz vòt la louvri ofisyèlman
        from accounts.models import SurveyConfig
        survey_cfg = SurveyConfig.get_config()
        if not survey_cfg.is_voting_open:
            return Response({
                "error": "Faz vòt la poko louvri. Kounye a se faz enskripsyon kandida yo ki an kou. Oken sitwayen pa ka vote toutotan sesyon vòt la pa aktif ofisyèlman."
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = CastVoteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        candidate_id = serializer.validated_data['candidate_id']
        post = serializer.validated_data['post']
        device_fp = serializer.validated_data.get('device_fingerprint', '').strip()
        user = request.user

        # 1. Tcheke si elektè a pa gentan vote pou pòs sa a deja (Anti-doub vòt)
        if Vote.objects.filter(voter=user, post=post).exists():
            return Response({
                "error": f"Ou gentan vote pou pòs {post} sa a deja. Règleman an entèdi plis pase 1 vòt pa pòs."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 1b. Kalkile fallback fingerprint sou IP ak User-Agent si sa nesesè
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR', '')
        ua = request.META.get('HTTP_USER_AGENT', '')
        if not device_fp and ip and ua:
            device_fp = hashlib.sha256(f"dev_{ip}_{ua}".encode()).hexdigest()

        # 1c. Sekirite Strik Aparèy Fizik : Yon aparèy pa ka vote plizyè fwa pou menm pòs la
        if device_fp and Vote.objects.filter(device_fingerprint=device_fp, post=post).exists():
            return Response({
                "error": f"Aparèy sa a deja vote pou pòs {post} sa a. Règleman sekirite a entèdi pou yon sèl aparèy vote plizyè fwa (1 Aparèy = 1 Vòt pa Pòs)."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 1d. Sekirite Strik Aparèy Fizik : Yon aparèy pa ka sèvi plizyè patisipan pou vote
        if device_fp:
            if Vote.objects.filter(device_fingerprint=device_fp).exclude(voter=user).exists():
                return Response({
                    "error": "Aparèy sa a te deja itilize pou yon lòt patisipan vote. Règleman sekirite a entèdi pou plizyè moun sèvi ak menm aparèy la pou vote (1 Aparèy = 1 Patisipan)."
                }, status=status.HTTP_403_FORBIDDEN)

            from accounts.models import DeviceRegistration
            registered_device = DeviceRegistration.objects.filter(device_fingerprint=device_fp).first()
            if registered_device and registered_device.user_id != user.id:
                return Response({
                    "error": "Aparèy sa a anrejistre sou kont yon lòt sitwayen. Ou pa ka vote sou aparèy yon lòt moun."
                }, status=status.HTTP_403_FORBIDDEN)

        # 2. Rekipere komin elektè a (Elektè, Kandida, oswa Manm Ekip/Admin)
        voter_commune = 'PORT_DE_PAIX'
        voter_profile = getattr(user, 'voter_profile', None)
        candidate_profile = getattr(user, 'candidate_profile', None)
        if voter_profile:
            voter_commune = voter_profile.commune
        elif candidate_profile:
            voter_commune = candidate_profile.commune
        elif serializer.validated_data.get('commune'):
            voter_commune = serializer.validated_data.get('commune')

        # 3. Tcheke si kandida a egziste epi li apwouve
        try:
            candidate = CandidateProfile.objects.get(id=candidate_id, status=CandidateStatus.APPROVED)
        except CandidateProfile.DoesNotExist:
            return Response({
                "error": "Kandida ou chwazi a pa egziste oswa dosye l poko apwouve."
            }, status=status.HTTP_404_NOT_FOUND)

        # 4. Verifikasyon kowòdinasyon pòs la
        if candidate.post != post:
            return Response({
                "error": "Pòs kandida a pa koresponn ak biltan w ap vote a."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 5. Verifikasyon jewografik strik
        if post != 'SENATEUR' and candidate.commune != voter_commune:
            return Response({
                "error": f"Ou pa ka vote pou yon kandida nan komin {candidate.get_commune_display()} paske komin ou verouye sou {voter_commune}."
            }, status=status.HTTP_403_FORBIDDEN)

        # 6. Hachaj IP anonimize pou sekirite
        ip_hash = hashlib.sha256(ip.encode()).hexdigest() if ip else ''

        # 7. Anrejistreman vòt la avèk anpwent inik aparèy la
        vote = Vote.objects.create(
            voter=user,
            candidate=candidate,
            post=post,
            commune=voter_commune,
            ip_hash=ip_hash,
            device_fingerprint=device_fp or ''
        )

        # 8. Mizajou drapo sou VoterProfile
        if voter_profile:
            flag_attr = f"has_voted_{post.lower()}"
            if hasattr(voter_profile, flag_attr):
                setattr(voter_profile, flag_attr, True)
                voter_profile.save()

        return Response({
            "message": f"Felisitasyon ! Vòt ou pou pòs {vote.get_post_display()} anrejistre avèk siksè nan sondaj la.",
            "receipt": VoteReceiptSerializer(vote).data
        }, status=status.HTTP_201_CREATED)


class MyVotesReceiptView(APIView):
    """
    Endpoint pou rekipere tout resi vòt patisipan an fè.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        votes = Vote.objects.filter(voter=request.user)
        return Response({
            "count": votes.count(),
            "receipts": VoteReceiptSerializer(votes, many=True).data
        }, status=status.HTTP_200_OK)


class SurveyResultsView(APIView):
    """
    Endpoint piblik pou konsilte rezilta sondaj preliminè a an tan reyèl.
    Kalkile kantite vwa, pousantaj, to patisipasyon ak repatisyon pa komin.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        User = get_user_model()

        post = request.query_params.get('post', 'SENATEUR')
        commune = request.query_params.get('commune', 'ALL')

        # 1. Total jeneral sitwayen ki enskri ak total vòt
        total_voters = User.objects.filter(role='VOTER').count()
        total_votes_global = Vote.objects.count()
        unique_voters_count = Vote.objects.values('voter').distinct().count()
        turnout_percentage = round((unique_voters_count / total_voters * 100), 1) if total_voters > 0 else 0.0

        # 2. Filtraj vòt pou pòs seleksyone a
        votes_qs = Vote.objects.filter(post=post)
        if post != 'SENATEUR' and commune and commune != 'ALL':
            votes_qs = votes_qs.filter(commune=commune)
        total_post_votes = votes_qs.count()

        # 3. Kandida ki apwouve pou pòs sa a
        candidates_qs = CandidateProfile.objects.filter(post=post, status=CandidateStatus.APPROVED)
        if post != 'SENATEUR' and commune and commune != 'ALL':
            candidates_qs = candidates_qs.filter(commune=commune)

        # 4. Kalkil vwa ak pousantaj pou chak kandida
        candidate_results = []
        for cand in candidates_qs:
            cand_votes = Vote.objects.filter(candidate=cand, post=post)
            if post != 'SENATEUR' and commune and commune != 'ALL':
                cand_votes = cand_votes.filter(commune=commune)
            vote_count = cand_votes.count()
            percentage = round((vote_count / total_post_votes * 100), 1) if total_post_votes > 0 else 0.0

            photo_url = cand.photo.url if cand.photo else None

            candidate_results.append({
                "id": str(cand.id),
                "name": f"{cand.first_name} {cand.last_name}",
                "first_name": cand.first_name,
                "last_name": cand.last_name,
                "post": cand.post,
                "post_display": cand.get_post_display(),
                "commune": cand.commune,
                "commune_display": cand.get_commune_display(),
                "photo": photo_url,
                "slogan": cand.slogan,
                "votes_count": vote_count,
                "percentage": percentage
            })

        # Triye pa kantite vwa décroissant
        candidate_results.sort(key=lambda x: x['votes_count'], reverse=True)

        # Bay chak kandida ran li (1, 2, 3...)
        for idx, item in enumerate(candidate_results):
            item['rank'] = idx + 1

        # 5. Repatisyon vòt yo nan 10 komin Nòdwès yo
        commune_stats = []
        for c_code, c_name in CommuneChoices.choices:
            c_vote_count = Vote.objects.filter(commune=c_code).count()
            commune_stats.append({
                "code": c_code,
                "name": c_name,
                "votes_count": c_vote_count
            })

        return Response({
            "metrics": {
                "total_registered_voters": total_voters,
                "total_votes_global": total_votes_global,
                "unique_voters_participated": unique_voters_count,
                "turnout_percentage": turnout_percentage,
                "communes_count": 10
            },
            "filters": {
                "selected_post": post,
                "selected_commune": commune,
                "total_post_votes": total_post_votes
            },
            "candidate_results": candidate_results,
            "commune_breakdown": commune_stats,
            "last_updated": timezone.now().isoformat()
        }, status=status.HTTP_200_OK)


class AdminVoteAuditView(APIView):
    """
    Endpoint pou administratè a enspekte jounal odit 50 dènye vòt ki anrejistre yo.
    Garanti transparans ak deteksyon fwod (kòd resi, anpwent IP anonimize, dat ak komin).
    """
    permission_classes = [IsAdminRole]

    def get(self, request, *args, **kwargs):
        recent_votes = Vote.objects.select_related('candidate', 'voter').order_by('-created_at')[:50]
        
        audit_data = []
        for v in recent_votes:
            audit_data.append({
                "id": str(v.id),
                "receipt_code": str(v.receipt_code),
                "post": v.post,
                "post_display": v.get_post_display(),
                "commune": v.commune,
                "commune_display": v.get_commune_display(),
                "candidate_name": f"{v.candidate.first_name} {v.candidate.last_name}",
                "voter_phone_masked": f"{v.voter.phone[:5]}***{v.voter.phone[-2:]}" if len(v.voter.phone) >= 7 else v.voter.phone,
                "ip_hash_short": v.ip_hash[:12] + '...' if v.ip_hash else 'Lokal / SSL',
                "created_at": v.created_at.isoformat()
            })

        return Response({
            "total_audited": len(audit_data),
            "audit_logs": audit_data
        }, status=status.HTTP_200_OK)


class PublicAnnouncementListView(APIView):
    """
    Endpoint piblik pou tout sitwayen konsilte anons ak kominike ofisyèl yo.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        announcements = PublicAnnouncement.objects.filter(is_published=True).order_by('-created_at')
        category = request.query_params.get('category')
        if category:
            announcements = announcements.filter(category=category)
        serializer = PublicAnnouncementSerializer(announcements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminAnnouncementView(APIView):
    """
    Endpoint pou Kominikatè ak Admin kreye, liste ak jere kominike/anons yo.
    """
    permission_classes = [CanManagePosts]

    def get(self, request, *args, **kwargs):
        announcements = PublicAnnouncement.objects.all().order_by('-created_at')
        serializer = PublicAnnouncementSerializer(announcements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        title = request.data.get('title', '').strip()
        content = request.data.get('content', '').strip()
        category = request.data.get('category', 'COMMUNIQUE')
        author_name = request.data.get('author_name', '').strip()
        is_published = request.data.get('is_published', True)

        if not title or not content:
            return Response({"error": "Tit ak kontni kominike a obligatwa."}, status=status.HTTP_400_BAD_REQUEST)

        if not author_name:
            user = request.user
            author_name = f"{user.first_name} {user.last_name}".strip() or "Komisyon Kominikasyon"

        announcement = PublicAnnouncement.objects.create(
            title=title,
            content=content,
            category=category,
            author=request.user,
            author_name=author_name,
            is_published=is_published
        )
        return Response({
            "message": "Kominike a pibliye avèk siksè !",
            "announcement": PublicAnnouncementSerializer(announcement).data
        }, status=status.HTTP_201_CREATED)

    def delete(self, request, pk=None, *args, **kwargs):
        post_id = pk or request.data.get('id') or request.query_params.get('id')
        if not post_id:
            return Response({"error": "ID kominike a obligatwa."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            announcement = PublicAnnouncement.objects.get(id=post_id)
            announcement.delete()
            return Response({"message": "Kominike a efase avèk siksè !"}, status=status.HTTP_200_OK)
        except PublicAnnouncement.DoesNotExist:
            return Response({"error": "Kominike sa a pa egziste."}, status=status.HTTP_404_NOT_FOUND)


class DonationCreateView(APIView):
    """
    Endpoint piblik pou resevwa donasyon ak sipò sitwayen sèlman.
    Done finansyè yo ak kantite kòb ki antre rete 100% prive pou administrasyon an.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        """Retounen sèlman kantite donatè — pa janm montan total la."""
        from .models import Donation
        count = Donation.objects.count()
        return Response({"total_count": count}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        from .models import Donation
        from .serializers import DonationSerializer
        
        serializer = DonationSerializer(data=request.data)
        if serializer.is_valid():
            donation = serializer.save()
            return Response({
                "message": "Donasyon w la anrejistre avèk siksè !",
                "receipt_code": f"DON-{str(donation.id)[:8].upper()}",
                "donation": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class AdminDonationListView(APIView):
    """
    Endpoint rezève pou Admin konsilte tout donasyon sitwayen yo.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request, *args, **kwargs):
        from .models import Donation
        from .serializers import DonationSerializer

        donations = Donation.objects.all().order_by('-created_at')
        serializer = DonationSerializer(donations, many=True)
        return Response({
            "total_count": donations.count(),
            "donations": serializer.data
        }, status=status.HTTP_200_OK)


class AppTranslationView(APIView):
    """
    Endpoint piblik pou delivre tout tradiksyon ak kontni tèks platfòm nan ki estoke nan Baz de Done a.
    Sipòte filtraj pa lang (?lang=ht|fr|en) oswa pa kategori (?category=...).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        from .models import AppTranslation

        lang = request.query_params.get('lang')
        category = request.query_params.get('category')

        qs = AppTranslation.objects.all()
        if category:
            qs = qs.filter(category__iexact=category)

        # Si kliyan an mande yon sèl lang espesifik
        if lang in ['ht', 'fr', 'en']:
            field_name = f"text_{lang}"
            result = {}
            for item in qs:
                val = getattr(item, field_name, '')
                # Si tradiksyon lang nan vid, fallback sou Kreyòl (HT)
                result[item.key] = val if val else item.text_ht
            return Response(result, status=status.HTTP_200_OK)

        # Si yo mande fòma detaye pou Dashboard Admin lan
        if request.query_params.get('format') in ['detailed', 'list']:
            search_query = request.query_params.get('search', '').strip().lower()
            items_list = []
            for item in qs:
                if search_query:
                    if (search_query not in item.key.lower() and 
                        search_query not in item.text_ht.lower() and 
                        search_query not in item.text_fr.lower() and 
                        search_query not in item.text_en.lower() and
                        search_query not in item.category.lower()):
                        continue
                items_list.append({
                    "id": item.id,
                    "key": item.key,
                    "category": item.category,
                    "text_ht": item.text_ht,
                    "text_fr": item.text_fr,
                    "text_en": item.text_en,
                    "description": item.description,
                    "updated_at": item.updated_at.isoformat() if item.updated_at else None
                })
            return Response({
                "count": len(items_list),
                "results": items_list
            }, status=status.HTTP_200_OK)

        # Pa defo, delivre tout 3 diksyonè yo konplè
        dict_ht = {}
        dict_fr = {}
        dict_en = {}

        for item in qs:
            dict_ht[item.key] = item.text_ht
            dict_fr[item.key] = item.text_fr if item.text_fr else item.text_ht
            dict_en[item.key] = item.text_en if item.text_en else item.text_ht

        return Response({
            "count": qs.count(),
            "translations": {
                "ht": dict_ht,
                "fr": dict_fr,
                "en": dict_en,
            }
        }, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        """
        Mete a jou yon tradiksyon nan baz de done a dirèkteman depi nan Dashboard Admin lan.
        Rezève pou Administratè yo sèlman.
        """
        from .models import AppTranslation
        from accounts.permissions import IsAdminRole

        # Verifikasyon sekirite : Sèlman Admin ki ka modifye tradiksyon
        if not request.user.is_authenticated:
            return Response({"error": "Ou dwe konekte kòm Administratè."}, status=status.HTTP_401_UNAUTHORIZED)
        
        user_role = getattr(request.user, 'role', '')
        if user_role not in ['ADMIN', 'MODERATOR'] and not request.user.is_staff and not request.user.is_superuser:
            return Response({"error": "Aksè rezève pou Administratè yo sèlman."}, status=status.HTTP_403_FORBIDDEN)

        trans_id = request.data.get('id')
        trans_key = request.data.get('key')

        if not trans_id and not trans_key:
            return Response({"error": "ID oswa Kle tradiksyon an obligatwa."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if trans_id:
                obj = AppTranslation.objects.get(id=trans_id)
            else:
                obj = AppTranslation.objects.get(key=trans_key)
        except AppTranslation.DoesNotExist:
            return Response({"error": "Tradiksyon sa a pa jwenn nan baz de done a."}, status=status.HTTP_404_NOT_FOUND)

        if 'text_ht' in request.data:
            obj.text_ht = request.data['text_ht']
        if 'text_fr' in request.data:
            obj.text_fr = request.data['text_fr']
        if 'text_en' in request.data:
            obj.text_en = request.data['text_en']
        if 'category' in request.data:
            obj.category = request.data['category']

        obj.save()

        return Response({
            "message": f"Tradiksyon « {obj.key} » mete a jou avèk siksè nan baz de done a !",
            "item": {
                "id": obj.id,
                "key": obj.key,
                "category": obj.category,
                "text_ht": obj.text_ht,
                "text_fr": obj.text_fr,
                "text_en": obj.text_en,
                "updated_at": obj.updated_at.isoformat()
            }
        }, status=status.HTTP_200_OK)

