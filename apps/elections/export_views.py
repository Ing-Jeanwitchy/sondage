import csv
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework import permissions
from accounts.permissions import IsAdminRole
from accounts.models import CandidateProfile, CandidateStatus, ElectivePostChoices, CommuneChoices, User
from elections.models import Vote

class AdminExportResultsCSVView(APIView):
    """
    Ekspòte rezilta ofisyèl sondaj la sou fòma CSV konpatib Excel ak UTF-8 BOM.
    """
    permission_classes = [IsAdminRole]

    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="rezilta_ofisyel_sondaj_nodwes.csv"'

        writer = csv.writer(response)
        # Antèt dokiman an
        writer.writerow([
            "PÒS ELEKTIF",
            "NON KANDIDA",
            "KOMIN",
            "ESTATI",
            "KANTITE VWA",
            "POUSANTAJ (%)",
            "SLOGAN"
        ])

        for post_code, post_label in ElectivePostChoices.choices:
            total_post_votes = Vote.objects.filter(post=post_code).count()
            candidates = CandidateProfile.objects.filter(post=post_code, status=CandidateStatus.APPROVED)

            for cand in candidates:
                cand_votes = Vote.objects.filter(candidate=cand, post=post_code).count()
                pct = round((cand_votes / total_post_votes * 100), 2) if total_post_votes > 0 else 0.0
                writer.writerow([
                    post_label,
                    f"{cand.first_name} {cand.last_name}".strip(),
                    cand.get_commune_display(),
                    cand.get_status_display(),
                    cand_votes,
                    f"{pct}%",
                    cand.slogan
                ])

        return response


class AdminExportCandidatesCSVView(APIView):
    """
    Ekspòte tout lis kandida yo (apwouve, an atant, rejte) sou fòma CSV.
    """
    permission_classes = [IsAdminRole]

    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="lis_kandida_sondaj_nodwes.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "ID KANDIDA",
            "NON",
            "SIYI",
            "PÒS ELEKTIF",
            "KOMIN",
            "SEKSYON / VIL",
            "TELEFÒN",
            "IMÈL",
            "ESTATI",
            "DAT ENSKRIPSYON"
        ])

        candidates = CandidateProfile.objects.select_related('user').order_by('-created_at')
        for c in candidates:
            writer.writerow([
                str(c.id),
                c.first_name,
                c.last_name,
                c.get_post_display(),
                c.get_commune_display(),
                c.section_or_city or "N/A",
                c.user.phone,
                c.user.email or c.email or "N/A",
                c.get_status_display(),
                c.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])

        return response


class AdminExportVotesAuditCSVView(APIView):
    """
    Ekspòte jounal odit legal tout vòt ki fèt yo pou sètifikasyon transparans.
    """
    permission_classes = [IsAdminRole]

    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="jounal_odit_vot_sondaj.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "KÒD RESI (UUID INIK)",
            "PÒS ELEKTIF",
            "KOMIN VÒT LA",
            "KANDIDA CHWAZI",
            "TELEFÒN ELEKTÈ (MASKED)",
            "ANPWENT IP (SHA-256)",
            "ANPWENT APARÈY",
            "DAT AK LÈ VÒT LA"
        ])

        votes = Vote.objects.select_related('candidate', 'voter').order_by('-created_at')
        for v in votes:
            phone_masked = f"{v.voter.phone[:5]}***{v.voter.phone[-2:]}" if len(v.voter.phone) >= 7 else v.voter.phone
            cand_name = f"{v.candidate.first_name} {v.candidate.last_name}".strip() if v.candidate else "N/A"
            dev_short = v.device_fingerprint[:16] + "..." if v.device_fingerprint else "N/A"
            writer.writerow([
                str(v.receipt_code),
                v.get_post_display(),
                v.get_commune_display(),
                cand_name,
                phone_masked,
                v.ip_hash or "Lokal / SSL",
                dev_short,
                v.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])

        return response
