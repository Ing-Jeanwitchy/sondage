import uuid
import hashlib
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db import transaction

from accounts.models import (
    UserRole,
    ElectivePostChoices,
    CommuneChoices,
    CandidateStatus,
    CandidateProfile,
    VoterProfile,
    SurveyConfig
)
from elections.models import Vote

User = get_user_model()

class Command(BaseCommand):
    help = "Peple baz done a ak done reyalis pou tes sondaj elektoral Nodwes."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Efase tout ansyen done sondaj yo anvan kreye nouvo yo'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("=== KAMANSE PEPLE BAZ DONE SONDAJ ELEKTORAL NODWES ==="))

        if options['clear']:
            self.stdout.write(self.style.WARNING("Netwayaj tout ansyen vot ak pwofil..."))
            Vote.objects.all().delete()
            CandidateProfile.objects.all().delete()
            VoterProfile.objects.all().delete()
            User.objects.exclude(is_superuser=True).delete()
            self.stdout.write(self.style.SUCCESS("Netwayaj fini !"))

        with transaction.atomic():
            # 1. KONFIGIRASYON SONDAJ LA
            config, _ = SurveyConfig.objects.get_or_create(id=1, defaults={
                'registration_deadline': timezone.now() + timedelta(days=6),
                'is_registration_open': True,
                'is_voting_open': False
            })
            config.registration_deadline = timezone.now() + timedelta(days=6)
            config.save()
            self.stdout.write(self.style.SUCCESS(f"[OK] Konfigirasyon sondaj valide (Limit: {config.registration_deadline.strftime('%d/%m/%Y')})"))

            # Hachaj modpas yon sel fwa pou optimize vitès ekzekisyon
            admin_pwd_hash = make_password("AdminPassword123!")
            voter_pwd_hash = make_password("VoterPassword123!")
            cand_pwd_hash = make_password("CandidatePassword123!")

            # 2. KONT ADMINISTRATE
            admin_phone = "+50930000000"
            admin_user, created = User.objects.get_or_create(
                phone=admin_phone,
                defaults={
                    'username': admin_phone,
                    'password': admin_pwd_hash,
                    'first_name': "Super",
                    'last_name': "Admin",
                    'role': UserRole.ADMIN,
                    'is_staff': True,
                    'is_superuser': True,
                    'is_verified': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"[OK] Kont Administrate kreye: {admin_phone} / AdminPassword123!"))
            else:
                self.stdout.write(self.style.NOTICE(f"[OK] Kont Administrate egziste deja: {admin_phone}"))

            # 3. KONT PATISIPAN TES
            demo_voter_phone = "+50937000001"
            demo_voter, v_created = User.objects.get_or_create(
                phone=demo_voter_phone,
                defaults={
                    'username': demo_voter_phone,
                    'password': voter_pwd_hash,
                    'first_name': "Jean-Claude",
                    'last_name': "Pierre",
                    'role': UserRole.VOTER,
                    'is_verified': True
                }
            )
            VoterProfile.objects.get_or_create(
                user=demo_voter,
                defaults={
                    'commune': CommuneChoices.PORT_DE_PAIX,
                    'commune_locked': True
                }
            )
            self.stdout.write(self.style.SUCCESS(f"[OK] Kont Elekte Tes kreye: {demo_voter_phone} / VoterPassword123! (Komin: Port-de-Paix)"))

            # 4. KREYE KANDIDA REYALIS POU DIVERS POS ELEKTIF
            candidates_data = [
                # --- SENATEURS (Départemental) ---
                {
                    "first_name": "Jean-Robert", "last_name": "Desir",
                    "post": ElectivePostChoices.SENATEUR, "commune": CommuneChoices.PORT_DE_PAIX,
                    "slogan": "Yon Nodwes Ini, Moden e Pwospe pou Tout Moun",
                    "biography": "Enjenye agwonom ki gen 22 lane eksperyans nan devlopman teritoryal nan depatman Nodwes la. Li te kowodone plizye pwoje enfrastrikti riral ak kanalizasyon dlo.",
                    "platform_priorities": "1. Reyabilite wout nasyonal Kafou Lanmo - Podpe\n2. Sipo direk pou agrikilte ak kowoperativ Kafe/Kowosol\n3. Kouran 24/24 atrave eneji sole ak idwo-elektrik nan tout depatman an",
                    "status": CandidateStatus.APPROVED
                },
                {
                    "first_name": "Marie-Flore", "last_name": "Saint-Fleur",
                    "post": ElectivePostChoices.SENATEUR, "commune": CommuneChoices.SAINT_LOUIS_DU_NORD,
                    "slogan": "Entegrite, Jistis Sosyal ak Otonomi Fanm Nodwes",
                    "biography": "Avokat nan bawo Podpe e militan dwa moun depi 15 lane. Li defann jistis sosyal, edikasyon timoun yo ak otonomi ekonomik fanm riral yo.",
                    "platform_priorities": "1. Kreye sant fomasyon pwofesyonel nan chak komin\n2. Pwoteksyon anviwonman ak rebwazman mon Nodwes yo\n3. Reform jistis lokal ak asistans legal gratis pou moun vilnerab",
                    "status": CandidateStatus.APPROVED
                },
                {
                    "first_name": "Dumas", "last_name": "Moise",
                    "post": ElectivePostChoices.SENATEUR, "commune": CommuneChoices.JEAN_RABEL,
                    "slogan": "Kiltive Lespwa, Refonde Ekonomi Nodwes",
                    "biography": "Ekonomis ak ansyen pwofese inivesite, li travay anpil sou kesyon mikwo-finans ak jesyon resous natirel nan zon Jan Rabel ak Mol Sen Nikola.",
                    "platform_priorities": "1. Kreye yon Bank Kredi Agrikol Departamantal\n2. Modenize po komesyal Podpe ak Mol Sen Nikola\n3. Sipote jen antreprene ak ekonomi dijital",
                    "status": CandidateStatus.APPROVED
                },
                {
                    "first_name": "Frantz", "last_name": "Chery",
                    "post": ElectivePostChoices.SENATEUR, "commune": CommuneChoices.BOMBARDOPOLIS,
                    "slogan": "Reform Radikal ak Sekirite pou Nodwes",
                    "biography": "Spesyalis nan sekirite piblik ak koperasyon entenasyonal. Li dedye lavi li nan defans souverente nasyonal ak reform enstitisyonel.",
                    "platform_priorities": "1. Sekirize tout korido transpo nan depatman an\n2. Fomasyon polis kominal ak gad-kot moden\n3. Transparans fiskal total sou lajan Leta",
                    "status": CandidateStatus.APPROVED
                },

                # --- MAIRES (Par Commune) ---
                {
                    "first_name": "Marc-Antoine", "last_name": "Bien-Aime",
                    "post": ElectivePostChoices.MAIRE, "commune": CommuneChoices.PORT_DE_PAIX,
                    "slogan": "Podpe Pwop, Sekirize e Modenize",
                    "biography": "Antreprene lokal ak ansyen prezidan Chanm Komes Nodwes la. Li viv e envesti nan komin Podpe depi plis pase 20 lane.",
                    "platform_priorities": "1. Plan irbansim moden ak jesyon fatra dijital\n2. Renovasyon mache piblik ak sekirizasyon waf la\n3. Klere tout lari Podpe ak panno sole entelijan",
                    "status": CandidateStatus.APPROVED
                },
                {
                    "first_name": "Dr. Judith", "last_name": "Valcin",
                    "post": ElectivePostChoices.MAIRE, "commune": CommuneChoices.PORT_DE_PAIX,
                    "slogan": "Sante, Edikasyon ak Dekote Sosyal pou Podpe",
                    "biography": "Medsen jeneralis ki te dirije plizye klinik mobil nan katye popile Podpe yo pandan kriz lasante yo.",
                    "platform_priorities": "1. Lopital minisipal aksesib 24 sou 24\n2. Pwogram manje cho pou lekol kominal yo\n3. Sant kominote pou jen ak espo nan chak zon",
                    "status": CandidateStatus.APPROVED
                },
                {
                    "first_name": "Wilson", "last_name": "Joseph",
                    "post": ElectivePostChoices.MAIRE, "commune": CommuneChoices.SAINT_LOUIS_DU_NORD,
                    "slogan": "Sen Lwi sou Chimen Pwogre ak Lape",
                    "biography": "Met edikate ak lide kominote respekte nan tout komin Sen Lwi dino.",
                    "platform_priorities": "1. Dlo potab nan tout ri ak seksyon kominal\n2. Pwoteksyon bo lanme ak sipo pou peche yo\n3. Asfaltaj sant vil la ak drenaj dlo lapli",
                    "status": CandidateStatus.APPROVED
                },
                {
                    "first_name": "Evens", "last_name": "Charles",
                    "post": ElectivePostChoices.MAIRE, "commune": CommuneChoices.JEAN_RABEL,
                    "slogan": "Gran Granye Nodwes la dwe Fleri Anko",
                    "biography": "Agwonom espesyalis nan zon semi-arid ak jesyon kouran dlo irigasyon.",
                    "platform_priorities": "1. Sistem irigasyon pou plenn Jan Rabel\n2. Wout penetrasyon pou transpote danre agrikol yo\n3. Elektrik ak telekominikasyon nan tout seksyon",
                    "status": CandidateStatus.APPROVED
                },
                {
                    "first_name": "Claudine", "last_name": "Augustin",
                    "post": ElectivePostChoices.MAIRE, "commune": CommuneChoices.MOLE_SAINT_NICOLAS,
                    "slogan": "Reviv Istwa ak Potansyel Touristik Mol la",
                    "biography": "Jesyone patrimwan kiltirel ak akte devlopman dirab nan preskil nodwes la.",
                    "platform_priorities": "1. Pwomosyon ekotouris ak restorasyon fo istorik yo\n2. Konstriksyon yon nouvo ayewopo rejyonal\n3. Sipo pou koperativ peche ak endistri sel la",
                    "status": CandidateStatus.APPROVED
                },
                {
                    "first_name": "Patrick", "last_name": "Bastien",
                    "post": ElectivePostChoices.MAIRE, "commune": CommuneChoices.LA_TORTUE,
                    "slogan": "Zile Latoti dwe Jwenn Respe ak Devlopman",
                    "biography": "Natif natal Zile Latoti, li goumen depi lontan pou koneksyon maritim regilye ak sant sante pou zile a.",
                    "platform_priorities": "1. Bato transpo sekirize ant Podpe ak Latoti\n2. Eneji sole ak dlo dessalee pou tout abitan yo\n3. Pwoteje fore ak plaj istorik zile a",
                    "status": CandidateStatus.APPROVED
                },
                {
                    "first_name": "Sony", "last_name": "Metellus",
                    "post": ElectivePostChoices.MAIRE, "commune": CommuneChoices.BASSIN_BLEU,
                    "slogan": "Bassin-Bleu : Potay Agrikol Nodwes",
                    "biography": "Ansyen fonksyonè minisipal ak pwodiktè kafe.",
                    "platform_priorities": "1. Wout agrikòl ak mache santral modèn\n2. Sant fòmasyon agwonomik\n3. Pwoteksyon sous dlo dous yo",
                    "status": CandidateStatus.APPROVED
                },

                # --- DEPUTES ---
                {
                    "first_name": "Lionel", "last_name": "Jean-Baptiste",
                    "post": ElectivePostChoices.DEPUTE, "commune": CommuneChoices.PORT_DE_PAIX,
                    "slogan": "Vwa Fem Podpe nan Palman an",
                    "biography": "Jurist ak orate ki toujou defann lwa an fave desantralizasyon.",
                    "platform_priorities": "1. Lwa sou devlopman po Podpe\n2. Bidje espesyal pou inivesite leta Nodwes\n3. Transparans nan itilizasyon lajan komin nan",
                    "status": CandidateStatus.APPROVED
                },
                {
                    "first_name": "Sabine", "last_name": "Pierre-Louis",
                    "post": ElectivePostChoices.DEPUTE, "commune": CommuneChoices.PORT_DE_PAIX,
                    "slogan": "Yon Jen Jenerasyon pou Chanje Pratik yo",
                    "biography": "Enjenye enfomatik ak konsiltan jesyon pwoje.",
                    "platform_priorities": "1. Teknoloji nan administrasyon piblik\n2. Akse entenet gratis nan bibliyotek piblik yo\n3. Finansman pou kreyasyon ti biznis jen",
                    "status": CandidateStatus.APPROVED
                },

                # --- CASEC / ASEC ---
                {
                    "first_name": "Jean-Baptiste", "last_name": "Altenor",
                    "post": ElectivePostChoices.CASEC, "commune": CommuneChoices.PORT_DE_PAIX,
                    "section_or_city": "1ere Section Baudin",
                    "slogan": "Devlopman Riral ak Sekirite pou Baudin",
                    "biography": "Agrikiltè ak prezidan asosyasyon kiltivatè seksyon Baudin.",
                    "platform_priorities": "1. Reparasyon wout tè pou machin ka monte\n2. Kaptaj sous dlo pou irigasyon ak bwè\n3. Sant sante kominotè pou seksyon an",
                    "status": CandidateStatus.APPROVED
                },
                {
                    "first_name": "Pierre-Richard", "last_name": "Noel",
                    "post": ElectivePostChoices.CASEC, "commune": CommuneChoices.PORT_DE_PAIX,
                    "section_or_city": "2eme Section La Pointe",
                    "slogan": "Lapwent Ini pou Pwogrè",
                    "biography": "Lidè kominotè ki angaje nan defans anviwònman ak lapèch nan La Pointe.",
                    "platform_priorities": "1. Pwoteksyon zòn kòt La Pointe\n2. Elektrisite solè pou ti mache lokal la\n3. Ankadreman pou jèn pechè ak kiltivatè",
                    "status": CandidateStatus.APPROVED
                },
                {
                    "first_name": "Jude", "last_name": "Saint-Hilaire",
                    "post": ElectivePostChoices.CASEC, "commune": CommuneChoices.SAINT_LOUIS_DU_NORD,
                    "section_or_city": "1ere Section Rivière des Barres",
                    "slogan": "Rivière des Barres Pi Djanm",
                    "biography": "Ansyen pwofesè lekòl ak agwonòm kominotè nan Sen Lwi.",
                    "platform_priorities": "1. Ranfòse lekòl nasyonal riral yo\n2. Ti pon bwa ranplase pa pon beton\n3. Kredi agrikòl pou fanm kiltivatris",
                    "status": CandidateStatus.APPROVED
                },

                # --- DELEGUE DE VILLE ---
                {
                    "first_name": "Wilner", "last_name": "Bellevue",
                    "post": ElectivePostChoices.DELEGUE_VILLE, "commune": CommuneChoices.PORT_DE_PAIX,
                    "section_or_city": "Centre-Ville & Haut-de-Paix",
                    "slogan": "Lari Pwòp, Sekirite ak Viv Ansanm nan Podpè",
                    "biography": "Aktivis kominotè ak manm komite katye Sant Vil Pòdpè depi 15 lane.",
                    "platform_priorities": "1. Netwayaj kanalizasyon ak jesyon fatra nan ri prensipal yo\n2. Ranfòse sekirite katye a nan aswè\n3. Sipò pou machann bò lari ak ti komès",
                    "status": CandidateStatus.APPROVED
                },
                {
                    "first_name": "Ketsia", "last_name": "Joseph",
                    "post": ElectivePostChoices.DELEGUE_VILLE, "commune": CommuneChoices.PORT_DE_PAIX,
                    "section_or_city": "Bas-de-Paix / Bord-de-Mer",
                    "slogan": "Bò Lanmè Podpè Merite Vivab ak Klere",
                    "biography": "Jèn antreprenèz sosyal ki dirije plizyè inisyativ anviwònman bò lanmè Pòdpè.",
                    "platform_priorities": "1. Pwoteksyon rivaj la kont ewozyon\n2. Eklere ri ak panno solè entelijan\n3. Espas espòtif ak kiltirèl pou jèn yo",
                    "status": CandidateStatus.APPROVED
                },
                {
                    "first_name": "Fabienne", "last_name": "Desrameaux",
                    "post": ElectivePostChoices.DELEGUE_VILLE, "commune": CommuneChoices.SAINT_LOUIS_DU_NORD,
                    "section_or_city": "Centre-Ville Sen Lwi",
                    "slogan": "Sen Lwi Pwòp e Atire",
                    "biography": "Edikatris ak animatris radyo kominotè nan Sen Lwi dinò.",
                    "platform_priorities": "1. Òganizasyon mache santral la\n2. Pwogram sansibilizasyon sou ijyèn piblik\n3. Rekreyasyon ak aktivite pou timoun",
                    "status": CandidateStatus.APPROVED
                },

                # --- DOSYE AN ATANT (Pou tès moderasyon Admin) ---
                {
                    "first_name": "Gilles", "last_name": "Paul",
                    "post": ElectivePostChoices.MAIRE, "commune": CommuneChoices.CHANSOLME,
                    "slogan": "Chansol Dwe Vanse",
                    "biography": "Komesan nan zon Chansol.",
                    "platform_priorities": "Devlope agrikilti ak wout.",
                    "status": CandidateStatus.PENDING
                },
                {
                    "first_name": "Roseline", "last_name": "Dorsainvil",
                    "post": ElectivePostChoices.CASEC, "commune": CommuneChoices.ANSE_A_FOLEUR,
                    "section_or_city": "1ere Section Mayance",
                    "slogan": "Seksyon riral la merite atansyon",
                    "biography": "Enstititris kominote.",
                    "platform_priorities": "Kanal dlo ak ti pon pou moun travese.",
                    "status": CandidateStatus.PENDING
                }
            ]

            approved_candidates = []
            for c_idx, c_data in enumerate(candidates_data):
                cand_phone = f"+5093800{c_idx:04d}"
                cand_user, _ = User.objects.get_or_create(
                    phone=cand_phone,
                    defaults={
                        'username': cand_phone,
                        'password': cand_pwd_hash,
                        'first_name': c_data['first_name'],
                        'last_name': c_data['last_name'],
                        'role': UserRole.CANDIDATE,
                        'is_verified': True
                    }
                )

                c_profile, _ = CandidateProfile.objects.update_or_create(
                    user=cand_user,
                    defaults={
                        'first_name': c_data['first_name'],
                        'last_name': c_data['last_name'],
                        'post': c_data['post'],
                        'commune': c_data['commune'],
                        'section_or_city': c_data.get('section_or_city', ''),
                        'slogan': c_data['slogan'],
                        'biography': c_data['biography'],
                        'platform_priorities': c_data['platform_priorities'],
                        'status': c_data['status'],
                        'validated_at': timezone.now() if c_data['status'] == CandidateStatus.APPROVED else None
                    }
                )
                if c_data['status'] == CandidateStatus.APPROVED:
                    approved_candidates.append(c_profile)

            self.stdout.write(self.style.SUCCESS(f"[OK] {len(candidates_data)} Kandida kreye (ki gen ladan {len(approved_candidates)} Apwouve ak 2 An Atant pou tes Admin)."))

            # 5. KREYE 75 ELEKTE VITYEL AK REPATISYON SOU 10 KOMIN YO
            commune_weights = {
                CommuneChoices.PORT_DE_PAIX: 22,
                CommuneChoices.SAINT_LOUIS_DU_NORD: 12,
                CommuneChoices.JEAN_RABEL: 10,
                CommuneChoices.MOLE_SAINT_NICOLAS: 6,
                CommuneChoices.BOMBARDOPOLIS: 5,
                CommuneChoices.BAIE_DE_HENNE: 4,
                CommuneChoices.BASSIN_BLEU: 5,
                CommuneChoices.ANSE_A_FOLEUR: 4,
                CommuneChoices.CHANSOLME: 4,
                CommuneChoices.LA_TORTUE: 6,
            }

            voters = []
            voter_index = 100
            for commune_code, count in commune_weights.items():
                for _ in range(count):
                    voter_index += 1
                    phone = f"+5093100{voter_index:04d}"
                    u, _ = User.objects.get_or_create(
                        phone=phone,
                        defaults={
                            'username': phone,
                            'password': voter_pwd_hash,
                            'first_name': "Elekte",
                            'last_name': f"#{voter_index}",
                            'role': UserRole.VOTER,
                            'is_verified': True
                        }
                    )

                    vp, _ = VoterProfile.objects.update_or_create(
                        user=u,
                        defaults={
                            'commune': commune_code,
                            'commune_locked': True
                        }
                    )
                    voters.append((u, vp))

            self.stdout.write(self.style.SUCCESS(f"[OK] {len(voters)} Patisipan / Elekte kreye atraves 10 komin Nodwes yo."))

            # 6. SIMILE VOT POU BAY BEL TABLO REZILTA AK GRAPHIQUES
            senateur_cands = [c for c in approved_candidates if c.post == ElectivePostChoices.SENATEUR]
            maire_cands = [c for c in approved_candidates if c.post == ElectivePostChoices.MAIRE]
            depute_cands = [c for c in approved_candidates if c.post == ElectivePostChoices.DEPUTE]

            votes_created = 0
            for u, vp in voters:
                # A) Vot Senatè
                if senateur_cands and random.random() < 0.88:
                    chosen_sen = random.choices(
                        senateur_cands,
                        weights=[40, 32, 18, 10],
                        k=1
                    )[0]

                    ip_sim = f"190.115.{random.randint(10, 250)}.{random.randint(1, 254)}"
                    ip_hash = hashlib.sha256(ip_sim.encode()).hexdigest()

                    Vote.objects.update_or_create(
                        voter=u,
                        post=ElectivePostChoices.SENATEUR,
                        defaults={
                            'candidate': chosen_sen,
                            'commune': vp.commune,
                            'ip_hash': ip_hash,
                            'receipt_code': uuid.uuid4()
                        }
                    )
                    vp.has_voted_senateur = True
                    votes_created += 1

                # B) Vot Maire
                local_maires = [c for c in maire_cands if c.commune == vp.commune]
                if local_maires and random.random() < 0.82:
                    chosen_maire = random.choice(local_maires)
                    ip_sim = f"190.115.{random.randint(10, 250)}.{random.randint(1, 254)}"
                    Vote.objects.update_or_create(
                        voter=u,
                        post=ElectivePostChoices.MAIRE,
                        defaults={
                            'candidate': chosen_maire,
                            'commune': vp.commune,
                            'ip_hash': hashlib.sha256(ip_sim.encode()).hexdigest(),
                            'receipt_code': uuid.uuid4()
                        }
                    )
                    vp.has_voted_maire = True
                    votes_created += 1

                # C) Vot Depite
                local_deputes = [c for c in depute_cands if c.commune == vp.commune]
                if local_deputes and random.random() < 0.78:
                    chosen_dep = random.choice(local_deputes)
                    Vote.objects.update_or_create(
                        voter=u,
                        post=ElectivePostChoices.DEPUTE,
                        defaults={
                            'candidate': chosen_dep,
                            'commune': vp.commune,
                            'ip_hash': hashlib.sha256(f"190.115.{random.randint(1,250)}".encode()).hexdigest(),
                            'receipt_code': uuid.uuid4()
                        }
                    )
                    vp.has_voted_depute = True
                    votes_created += 1

                vp.save()

            self.stdout.write(self.style.SUCCESS(f"[OK] {votes_created} Vot prelimine anrejistre avek sikse nan baz done a !"))

        self.stdout.write(self.style.NOTICE("========================================================="))
        self.stdout.write(self.style.SUCCESS("[SUCCES] TOUT DONE DE DEMONSTRASYON YO PARE AK SIKSE !"))
        self.stdout.write(self.style.NOTICE("Identifiants de test :"))
        self.stdout.write(self.style.WARNING(f" * Admin:  {admin_phone}  | Modpas: AdminPassword123!"))
        self.stdout.write(self.style.WARNING(f" * Elekte: {demo_voter_phone}  | Modpas: VoterPassword123!"))
        self.stdout.write(self.style.NOTICE("========================================================="))
