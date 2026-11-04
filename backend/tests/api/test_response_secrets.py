import pytest

FORBIDDEN_KEYS = {"password", "password_hash", "passwordhash", "session_key"}

pytestmark = pytest.mark.django_db


def _keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _keys(child)


@pytest.mark.parametrize(
    "path",
    [
        "/api/auth/me",
        "/api/employees",
        "/api/analytics/summary",
        "/api/analytics/outliers",
    ],
)
def test_responses_do_not_expose_credentials_or_session_keys(
    auth_client,
    hr_user,
    path,
):
    response = auth_client.get(path)

    assert response.status_code == 200
    payload = response.json()
    assert FORBIDDEN_KEYS.isdisjoint({key.lower() for key in _keys(payload)})

    body = response.content.decode()
    assert hr_user.password not in body
    session_key = auth_client.session.session_key
    if session_key:
        assert session_key not in body
