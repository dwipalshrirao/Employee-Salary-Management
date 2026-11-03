#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    from django.core.management import execute_from_command_line

    from accounts.apps import clear_expired_sessions

    clear_expired_sessions()
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
