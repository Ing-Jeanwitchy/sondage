import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
try:
    from elections.models import AppTranslation
except ImportError:
    from apps.elections.models import AppTranslation

def get_category_from_key(key):
    k = key.lower()
    if k.startswith('hero_'):
        return 'HERO_BANNER'
    elif k.startswith('countdown_'):
        return 'COUNTDOWN'
    elif k.startswith('showcase_'):
        return 'SHOWCASE'
    elif k.startswith('filter_'):
        return 'FILTERS'
    elif k.startswith('booth_'):
        return 'VOTING_BOOTH'
    elif k.startswith('voter_'):
        return 'VOTER_DASHBOARD'
    elif k.startswith('results_'):
        return 'RESULTS'
    elif k.startswith('admin_users_'):
        return 'ADMIN_USERS'
    elif k.startswith('admin_donation'):
        return 'ADMIN_DONATIONS'
    elif k.startswith('admin_export_'):
        return 'ADMIN_EXPORTS'
    elif k.startswith('admin_'):
        return 'ADMIN'
    elif k.startswith('cand_reg_') or k.startswith('cand_'):
        return 'CANDIDATE_REGISTRATION'
    elif k.startswith('sec_') or 'security' in k:
        return 'SECURITY_AUDIT'
    elif k.startswith('donation_'):
        return 'DONATIONS'
    elif k.startswith('auth_'):
        return 'AUTHENTICATION'
    elif k.startswith('nav_'):
        return 'NAVIGATION'
    elif k.startswith('rule') or k.startswith('about_'):
        return 'RULES_AND_ABOUT'
    elif k.startswith('brand_'):
        return 'BRAND'
    return 'GENERAL'

class Command(BaseCommand):
    help = 'Chaje tout tradiksyon yo (Kreyòl, Français, English) nan tab AppTranslation nan Baz de Done a.'

    def handle(self, *args, **options):
        # Chèche fichye translations_seed.json
        possible_paths = [
            os.path.join(settings.BASE_DIR, 'translations_seed.json'),
            os.path.join(settings.BASE_DIR, '..', 'translations_seed.json'),
        ]
        
        json_path = None
        for p in possible_paths:
            if os.path.exists(p):
                json_path = p
                break

        if not json_path:
            self.stderr.write(self.style.ERROR(f"Fichye translations_seed.json pa jwenn nan {possible_paths}"))
            return

        self.stdout.write(self.style.NOTICE(f"Chajman fichye tradiksyon depi : {json_path}"))
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        dict_ht = data.get('ht', {})
        dict_fr = data.get('fr', {})
        dict_en = data.get('en', {})

        all_keys = set(dict_ht.keys()) | set(dict_fr.keys()) | set(dict_en.keys())
        self.stdout.write(f"Total kle inik pou anrejistre : {len(all_keys)}")

        from django.db import transaction
        with transaction.atomic():
            AppTranslation.objects.all().delete()
            items = []
            for key in all_keys:
                text_ht = dict_ht.get(key, '')
                text_fr = dict_fr.get(key, '') or text_ht
                text_en = dict_en.get(key, '') or text_ht
                category = get_category_from_key(key)
                items.append(AppTranslation(
                    key=key,
                    category=category,
                    text_ht=text_ht,
                    text_fr=text_fr,
                    text_en=text_en
                ))

            AppTranslation.objects.bulk_create(items, batch_size=500)

        self.stdout.write(self.style.SUCCESS(
            f"Operasyon fini avèk siksè ! {len(items)} tradiksyon anrejistre nan baz de done a."
        ))
