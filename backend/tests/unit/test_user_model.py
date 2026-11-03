import pytest
from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction

from accounts.models import HrUser

pytestmark = pytest.mark.django_db


def _create_user(**overrides):
    data = {
        "email": "hr@example.com",
        "full_name": "HR User",
        "password": "secret-password",
    }
    data.update(overrides)
    return HrUser.objects.create_user(**data)


def test_hr_user_uses_email_as_username_field():
    assert HrUser.USERNAME_FIELD == "email"
    assert HrUser._meta.db_table == "hr_users"


def test_create_user_hashes_password():
    user = _create_user()

    assert user.email == "hr@example.com"
    assert user.password != "secret-password"
    assert user.check_password("secret-password")


def test_get_by_natural_key_is_case_insensitive():
    user = _create_user(email="HR@Example.com")

    assert HrUser.objects.get_by_natural_key("hr@example.com") == user


def test_email_is_unique_case_insensitively():
    _create_user(email="hr@example.com")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _create_user(email="HR@example.com")


def test_inactive_user_cannot_authenticate():
    _create_user(is_active=False)

    assert authenticate(username="hr@example.com", password="secret-password") is None


def test_active_user_can_authenticate_case_insensitively():
    _create_user(email="HR@Example.com")

    user = authenticate(username="hr@example.com", password="secret-password")

    assert user is not None
    assert user.email == "HR@Example.com"
