"""
Management command pou migre foto kandida ki sou disk lokal sou Cloudinary.
Chak imaj ki gen yon chemen lokal (candidates/xxx.jpeg) ap uploade sou Cloudinary
epi chemen an nan baz de done a ap mete ajou ak URL Cloudinary a.
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from accounts.models import CandidateProfile


class Command(BaseCommand):
    help = "Migre foto kandida lokal yo sou Cloudinary. Fè sa apre konfigirasyon Cloudinary."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Jis montre ki foto ki ta migre, san fè okenn chanjman.'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Verifye Cloudinary konfigiire
        if not getattr(settings, 'IS_CLOUDINARY_ACTIVE', False):
            self.stderr.write(self.style.ERROR(
                "❌ Cloudinary pa konfigiire! Mete CLOUDINARY_CLOUD_NAME, "
                "CLOUDINARY_API_KEY, ak CLOUDINARY_API_SECRET nan anviwònman w."
            ))
            return

        try:
            import cloudinary
            import cloudinary.uploader
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
            )
        except ImportError:
            self.stderr.write(self.style.ERROR(
                "❌ Pake 'cloudinary' pa enstale. Kouri: pip install cloudinary"
            ))
            return

        candidates = CandidateProfile.objects.exclude(photo='').exclude(photo__isnull=True)
        self.stdout.write(self.style.NOTICE(
            f"🔍 Jwenn {candidates.count()} kandida ki gen foto..."
        ))

        migrated = 0
        skipped = 0
        errors = 0

        for candidate in candidates:
            photo_name = candidate.photo.name if candidate.photo else ''
            if not photo_name:
                skipped += 1
                continue

            # Si foto a deja yon URL Cloudinary, skip li
            if photo_name.startswith('http://') or photo_name.startswith('https://'):
                self.stdout.write(f"  ⏭ {candidate.first_name} {candidate.last_name} — deja sou Cloudinary")
                skipped += 1
                continue

            # Chemen fichye lokal
            local_path = os.path.join(settings.MEDIA_ROOT, photo_name)

            if dry_run:
                exists = os.path.exists(local_path)
                self.stdout.write(
                    f"  📋 {candidate.first_name} {candidate.last_name} — "
                    f"{photo_name} ({'fichye egziste' if exists else '⚠ fichye pa la'})"
                )
                migrated += 1
                continue

            if not os.path.exists(local_path):
                self.stderr.write(self.style.WARNING(
                    f"  ⚠ {candidate.first_name} {candidate.last_name} — "
                    f"Fichye {local_path} pa egziste sou disk la. Imaj sa a pèdi."
                ))
                errors += 1
                continue

            # Upload sou Cloudinary
            try:
                public_id = f"candidates/{candidate.id}_{candidate.first_name}_{candidate.last_name}"
                result = cloudinary.uploader.upload(
                    local_path,
                    public_id=public_id,
                    folder="sondage-nordouest",
                    overwrite=True,
                    resource_type="image",
                )
                new_url = result.get('secure_url', result.get('url', ''))
                if new_url:
                    candidate.photo = new_url
                    candidate.save(update_fields=['photo'])
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✅ {candidate.first_name} {candidate.last_name} — migre sou Cloudinary"
                    ))
                    migrated += 1
                else:
                    self.stderr.write(self.style.ERROR(
                        f"  ❌ {candidate.first_name} {candidate.last_name} — "
                        f"Upload reyisi men pa gen URL nan repons lan"
                    ))
                    errors += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(
                    f"  ❌ {candidate.first_name} {candidate.last_name} — Erè: {e}"
                ))
                errors += 1

        self.stdout.write("")
        action = "ta migre" if dry_run else "migre"
        self.stdout.write(self.style.SUCCESS(f"📊 Rezime:"))
        self.stdout.write(f"   ✅ {migrated} foto {action}")
        self.stdout.write(f"   ⏭ {skipped} deja sou Cloudinary / skip")
        self.stdout.write(f"   ❌ {errors} erè")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\n💡 Sa se yon dry-run. Pou fè migrasyon an, retire --dry-run."
            ))
