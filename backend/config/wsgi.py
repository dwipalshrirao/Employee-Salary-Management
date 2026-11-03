import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def _create_application():
    from accounts.apps import clear_expired_sessions

    application = get_wsgi_application()
    clear_expired_sessions()
    return application


application = _create_application()
