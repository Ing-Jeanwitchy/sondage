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
except Exception as migrate_err:
    import logging
    logging.getLogger('django').warning(f"Auto-migration on WSGI startup: {migrate_err}")

