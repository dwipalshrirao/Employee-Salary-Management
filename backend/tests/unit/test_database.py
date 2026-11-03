import pytest
from django.db import connection
from django.db.backends.sqlite3.base import DatabaseWrapper


@pytest.mark.django_db
def test_database_foreign_keys_are_on():
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys")

        assert cursor.fetchone()[0] == 1


@pytest.mark.django_db(transaction=True)
def test_sqlite_file_database_uses_wal(tmp_path, settings):
    database_settings = settings.DATABASES["default"].copy()
    database_settings["NAME"] = str(tmp_path / "test.sqlite3")
    test_connection = DatabaseWrapper(database_settings, alias="wal-test")

    try:
        test_connection.ensure_connection()
        with test_connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode")

            assert cursor.fetchone()[0].lower() == "wal"
    finally:
        test_connection.close()
