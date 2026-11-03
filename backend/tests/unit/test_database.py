import pytest
from django.db import connection


@pytest.mark.django_db
def test_database_foreign_keys_are_on():
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys")

        assert cursor.fetchone()[0] == 1


@pytest.mark.django_db(transaction=True)
def test_sqlite_file_database_uses_wal(tmp_path, settings):
    database_name = str(tmp_path / "test.sqlite3")
    settings.DATABASES["default"]["NAME"] = database_name
    connection.settings_dict["NAME"] = database_name
    connection.in_atomic_block = False
    connection.closed_in_transaction = False
    connection.close()
    connection.ensure_connection()

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode")

        assert cursor.fetchone()[0].lower() == "wal"
    connection.in_atomic_block = True
