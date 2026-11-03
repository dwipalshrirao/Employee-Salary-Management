import os
from datetime import UTC, datetime

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DEBUG", "true")
from rest_framework.test import APIClient

from common.clock import Clock


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def fixed_clock(monkeypatch):
    fixed_now = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(Clock, "now", lambda self: fixed_now)
    monkeypatch.setattr(Clock, "today", lambda self: fixed_now.date())
    return Clock()
