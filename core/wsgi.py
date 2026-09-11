"""
WSGI config for core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_wsgi_application()

# Sekirite adisyonèl: Egzekite migrasyon baz de done otomatikman depi Gunicorn/WSGI demare
try:
    from django.core.management import call_command
    call_command('migrate', interactive=False)

    # Garanti kont Sipè Administratè a toujou egziste pou siveyans
    from django.contrib.auth import get_user_model
    from accounts.models import UserRole
    User = get_user_model()
    admin_phone = "+50930000000"
    if not User.objects.filter(phone=admin_phone).exists():
        User.objects.create_superuser(
            phone=admin_phone,
            username=admin_phone,
            password="AdminPassword123!",
            role=UserRole.ADMIN,
            is_staff=True,
            is_superuser=True,
            is_verified=True
        )
except Exception as startup_err:
    import logging
    logging.getLogger('django').warning(f"Auto-startup task on WSGI: {startup_err}")

