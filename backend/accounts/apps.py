"""Accounts app configuration and startup maintenance."""

import logging

from django.apps import AppConfig
from django.core.management import call_command
from django.db import DatabaseError

logger = logging.getLogger("common")


def clear_expired_sessions():
    """Remove expired database sessions when the application starts.

    A missing session table must not prevent migrations or management commands
    from running, so an unready database is treated as a no-op.
    """
    try:
        call_command("clearsessions", verbosity=0)
    except (DatabaseError, RuntimeError):
        # Missing tables and pytest-django's DB guard both mean there is
        # nothing safe to clean during this process start-up.
        logger.debug("clearsessions skipped because the database is not ready")


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
