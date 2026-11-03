import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings


def test_secret_key_is_required_when_debug_is_false():
    env = {**os.environ, "DEBUG": "false", "SECRET_KEY": ""}
    env.pop("DJANGO_SETTINGS_MODULE", None)
    backend_dir = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "SECRET_KEY is required when DEBUG is false." in result.stderr


def test_auth_user_model_is_hr_user():
    assert settings.AUTH_USER_MODEL == "accounts.HrUser"


def test_password_hashers_use_argon2_only():
    assert settings.PASSWORD_HASHERS == ["django.contrib.auth.hashers.Argon2PasswordHasher"]


def test_openapi_version_is_31():
    assert settings.SPECTACULAR_SETTINGS["OAS_VERSION"] == "3.1.0"
