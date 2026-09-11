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

    # Si baz done a vid san kandida, peple li otomatikman ak done demo ofisyèl yo
    from accounts.models import CandidateProfile
    if CandidateProfile.objects.count() == 0:
        call_command('seed_demo_data')
except Exception as startup_err:
    import logging
    logging.getLogger('django').warning(f"Auto-startup task on WSGI: {startup_err}")

