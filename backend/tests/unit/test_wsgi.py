from config import wsgi


def test_wsgi_application_is_exposed():
    assert callable(wsgi.application)
